"""The Copilot calls: prompts and flags as factory/agent.py builds them, the environment, running a call,
reading its events, and what changed in the project afterwards."""
import hashlib
import json
import os
import re
import shutil
import subprocess
import threading

from . import copied, config
from . import ticket as ticket_mod

JIRA_ENV = ("JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_API_TOKEN")  # never passed on to Copilot
# Forbidden even when an old config.json doesn't list it: AGENTS.md carries the team's rules, and this flag drops it
NO_INSTRUCTIONS = "--no-custom-instructions"


# --- the calls --------------------------------------------------------------------------------------------------------

TEST_CHARS = re.compile(r"[A-Za-z0-9_./:@+,%-]+")  # the first word; no quotes, "$", "=", ";", "&", "|", "<", ">"
ARG_CHARS = re.compile(r"[A-Za-z0-9_./:@+,%=-]+")  # the other words: the same, plus "=" (--maxfail=1)
INTERPRETERS = ("bash", "sh", "zsh", "dash", "fish", "ksh", "csh", "tcsh", "node", "nodejs", "bun", "deno", "tsx", "ts-node",
                "ruby", "perl", "php", "lua", "julia", "rscript", "osascript", "tclsh", "cmd", "pwsh", "powershell",
                "python", "pypy")
# a known name, then a version (3, 3.12.1) with an optional letter (3.13t), then an optional -dbg
INTERPRETER_NAME = re.compile(r"(%s)(\d+(\.\d+)*[a-z]?)?(-dbg)?" % "|".join(INTERPRETERS))
INLINE_CODE_FLAGS = {"-c", "-e", "-E", "-p", "--print", "--eval", "-Command"}
SHORT_FLAGS_FOR_CODE = re.compile(r"-[A-Za-z]*[ceEp]")  # a cluster such as -lc, -Sc, -pe, -ep
POWERSHELL_CODE_FLAGS = ("command", "encodedcommand")  # PowerShell accepts any prefix of these, such as -C or /enc
WRAPPERS = {"env", "timeout", "nice", "nohup", "sudo", "xargs", "exec", "command", "busybox"}
RUNNERS = {"uv", "poetry", "pipenv", "pdm", "hatch", "rye"}  # "<runner> run" is a wrapper too
NUMBER = re.compile(r"\d+(\.\d+)?[smhd]?")  # timeout 60, timeout 1.5s


def base_name(word):
    """The lower-case basename of a word, without .exe."""
    name = os.path.basename(word).lower()
    return name[:-4] if name.endswith(".exe") else name


def interpreter_name(word):
    """The lower-case interpreter a word names (basename, no .exe), or None. Any word of a test command counts, so
    wrappers (uv run python, env node, timeout 60 bash) don't hide it."""
    name = base_name(word)
    return name if INTERPRETER_NAME.fullmatch(name) else None


def runs_inline_code(interpreter, word):
    """Whether an argument of an interpreter looks like a flag or word that runs code from the command line."""
    if word in INLINE_CODE_FLAGS or SHORT_FLAGS_FOR_CODE.fullmatch(word):
        return True
    if interpreter.startswith(("pwsh", "powershell")):
        return len(word) >= 2 and word[0] in "-/" and any(f.startswith(word[1:].lower()) for f in POWERSHELL_CODE_FLAGS)
    if interpreter.startswith("cmd"):
        return word.lower() in ("/c", "/k")
    if interpreter.startswith("php"):
        return word == "-r"
    return interpreter.startswith(("deno", "bun")) and word == "eval"


def command_start(cmd, words):
    """The index of the command a test command runs: wrappers (env, timeout 60, uv run) are skipped with their own
    numbers and KEY=VALUE words. Fail closed on options: one is accepted only as --opt=value or a bare --, because
    without a table of each wrapper's options a value word (-u bob) would be taken for the command. len(words) when
    only wrappers are left."""
    i = 0
    while i < len(words):
        name = base_name(words[i])
        if name in WRAPPERS:
            i += 1
        elif name in RUNNERS and i + 1 < len(words) and words[i + 1].lower() == "run":
            i += 2
        else:
            break
        while i < len(words) and (words[i].startswith("-") or NUMBER.fullmatch(words[i]) or "=" in words[i]):
            w = words[i]
            if w.startswith("-") and w != "--" and "=" not in w:
                raise config.Stop(f"test_command {cmd!r}: the option {w!r} after {words[i - 1]!r} may take a value that "
                                  "this check can't tell from the command; write wrapper options as --opt=value, "
                                  "or wrap the command in a script file or a Make target and use that")
            i += 1
    return i


def ends_open(rest):
    """Whether the words after an interpreter leave the code or module to the agent: no non-option word (the word
    after -m counts)."""
    return not any(not w.startswith("-") or (i and rest[i - 1] == "-m") for i, w in enumerate(rest))


def check_test_command(cmd):
    """Stops unless cmd is plain words: no shell syntax, no environment assignment, and no interpreter running inline
    code (bash -c, python -c, node -e, ...), because the build call's tool is the whole command as a prefix. A
    misconfiguration check, not a security boundary: the prefix lets the agent append arguments anyway."""
    words = cmd.split(" ")
    if not cmd or "" in words:
        raise config.Stop(f"test_command {cmd!r}: words must be separated by single spaces, with no leading or trailing space")
    if "=" in words[0]:
        raise config.Stop(f"test_command {cmd!r}: an environment assignment in front of the command isn't allowed; "
                          "put it in a script or a make target")
    for i, w in enumerate(words):
        if not (TEST_CHARS if i == 0 else ARG_CHARS).fullmatch(w):
            raise config.Stop(f"test_command {cmd!r}: {w!r} has characters outside letters, digits and _ . / : @ + , % - "
                              "(and = after the first word); shell syntax and quotes aren't allowed, "
                              "put them in a script or a make target")
    start = command_start(cmd, words)
    if start == len(words):
        raise config.Stop(f"test_command {cmd!r}: the command must end in a fixed script, module, or target; "
                          f"{words[-1]!r} with nothing after it lets the agent supply the command")
    interpreter = interpreter_name(words[start])  # only the command itself: its arguments are never wrappers or interpreters
    if interpreter:
        rest = words[start + 1:]
        for w in rest:
            if runs_inline_code(interpreter, w):
                raise config.Stop(f"test_command {cmd!r}: {interpreter} with {w} may run inline code, or this check can't "
                                  "tell; wrap the command in a script file or a Make target and use that")
        if ends_open(rest):
            raise config.Stop(f"test_command {cmd!r}: the command must end in a fixed script, module, or target; "
                              f"{words[start]!r} with nothing after it lets the agent supply the code or module")


def test_tool(cmd):
    """The one tool a build call gets for the test command: the whole command as a prefix."""
    return f"shell({cmd}:*)"


def denied_by(cmd, deny_tools):
    """The first deny_tools entry shell(X:*) that covers cmd (cmd == X or cmd starts with X and a space), or None."""
    for entry in deny_tools:
        if entry.startswith("shell(") and entry.endswith(":*)"):
            x = entry[len("shell("):-len(":*)")]
            if cmd == x or cmd.startswith(x + " "):
                return entry
    return None


def build_test_command(cfg):
    """The checked test command of config.json for a build call. A deny entry beats every allow, so a command a deny
    entry covers stops here, before any call."""
    cmd = config.test_command(cfg)
    if not cmd:
        raise config.Stop("set test_command in config.json (or run init)")
    check_test_command(cmd)
    entry = denied_by(cmd, cfg["deny_tools"])
    if entry:
        raise config.Stop(f"test_command {cmd!r} is covered by {entry} in deny_tools, which beats every allow; "
                          "use another test command or change deny_tools")
    return cmd


def check_read_tools(cfg):
    """The read_tools of config.json. Stops on an entry that isn't shell(...) or that a deny_tools entry covers, because
    a deny entry beats every allow and a non-shell tool would widen the calls."""
    tools = cfg.get("read_tools") or []
    for entry in tools:
        if not (isinstance(entry, str) and entry.startswith("shell(") and entry.endswith(")") and len(entry) > 7):
            raise config.Stop(f"read_tools entry {entry!r}: only shell(...) entries are allowed")
        x = entry[len("shell("):-1]
        x = x[:-2] if x.endswith(":*") else x
        denied = denied_by(x, cfg["deny_tools"])
        if denied:
            raise config.Stop(f"read_tools entry {entry!r} is covered by {denied} in deny_tools, which beats every "
                              "allow; remove it from read_tools or change deny_tools")
    return list(tools)


def fill(template, values, where):
    try:
        return template.format(**values)
    except KeyError as e:
        raise config.Stop(f"{where} uses the placeholder {{{e.args[0]}}}, which agentic-factory.py doesn't know")


def rules_of(cfg, name):
    """config.json's spec_rules or build_rules. No fallback: the copies in copied.py are the lab's, without the
    AGENTS.md sentence and with the lab's PHP test command."""
    rules = cfg.get(name)
    if not isinstance(rules, str) or not rules:
        raise config.Stop(f"config.json has no {name}: copy it from the template's config.json")
    return rules


def plan(cfg, mode, key, fw, ticket=None, change=None, spec_file=None, answers="", spec_changes=""):
    """The framework prompts, tools, and extra environment for one run, built the way factory/agent.py builds them.
    answers: spec after a `spec fragen` comment: the questions and their answers as a fenced block after the ticket.
    spec_changes: a build revision after hand edits of the spec: the text appended to every build prompt (the
    instruction and the fenced spec diff). The one place a build prompt is made."""
    F = cfg["frameworks"][fw]
    env_extra = {}
    if mode == "spec":
        rules = rules_of(cfg, "spec_rules").format(folder=F["spec_rule_folder"])
        vals = {"ticket_block": ticket_mod.ticket_block(ticket) + answers, "spec_rules": rules, "key": key,
                "slug": key.lower()}
        prompts = [fill(p, vals, f"{fw} spec_prompts") for p in F["spec_prompts"]]
        tools = [*F["spec_tools"], *check_read_tools(cfg)]
    elif mode == "build":
        cmd = build_test_command(cfg)
        rules = fill(rules_of(cfg, "build_rules"), {"test_command": cmd}, "build_rules")
        tools = [*F["build_tools"], *check_read_tools(cfg), test_tool(cmd)]
        vals = {"change": change, "build_rules": rules, "key": key, "spec_file": spec_file}
        prompts = [fill(p, vals, f"{fw} build_prompts") + spec_changes for p in F["build_prompts"]]
        if fw == "speckit" and F.get("env_feature_dir"):
            env_extra[F["env_feature_dir"]] = f"specs/{change}"
    else:
        raise config.Stop(f"unknown mode {mode}")
    return prompts, tools, env_extra


def revise_plan(cfg, key, fw, ticket, change, comments_block):
    """The spec revision call: the framework's revise_prompt, its spec tools and read_tools (as a spec run has them),
    and its extra environment. The spec rules name the change's own folder."""
    F = cfg["frameworks"][fw]
    if not isinstance(F.get("revise_prompt"), str) or not F["revise_prompt"]:
        raise config.Stop(f"config.json has no frameworks.{fw}.revise_prompt: copy it from the template's config.json")
    root = F["spec_root"].format(change=change)
    vals = {"ticket_block": ticket_mod.ticket_block(ticket), "comments_block": comments_block, "change": change,
            "spec_root": root, "spec_rules": rules_of(cfg, "spec_rules").format(folder=root), "key": key}
    prompt = fill(F["revise_prompt"], vals, f"{fw} revise_prompt")
    env_extra = {F["env_feature_dir"]: f"specs/{change}"} if fw == "speckit" and F.get("env_feature_dir") else {}
    return prompt, [*F["spec_tools"], *check_read_tools(cfg)], env_extra


def amend_plan(cfg, key, fw, ticket, change, comments_block, task_file, revision):
    """A build revision's amend call: the framework's amend_prompt, its spec tools and read_tools (no test tool), and
    its extra environment. The call turns the new [Mensch] comments into new, unchecked tasks in task_file (OpenSpec:
    and into the change's spec documents, see feedback.amend_paths)."""
    F = cfg["frameworks"][fw]
    if not isinstance(F.get("amend_prompt"), str) or not F["amend_prompt"]:
        raise config.Stop(f"config.json has no frameworks.{fw}.amend_prompt: copy it from the template's config.json")
    vals = {"ticket_block": ticket_mod.ticket_block(ticket), "comments_block": comments_block, "change": change,
            "task_file": task_file, "revision": revision, "key": key, "spec_root": F["spec_root"].format(change=change)}
    prompt = fill(F["amend_prompt"], vals, f"{fw} amend_prompt")
    env_extra = {F["env_feature_dir"]: f"specs/{change}"} if fw == "speckit" and F.get("env_feature_dir") else {}
    return prompt, [*F["spec_tools"], *check_read_tools(cfg)], env_extra


def has_shell_tool(tools):
    """Whether a call may use the shell: one of its allowed tools is shell or shell(...)."""
    return any(t == "shell" or t.startswith("shell(") for t in tools)


def copilot_argv(cfg, local, prompt, tools, usage_file, exe=("copilot",), cap=None, mcp_off=(),
                 file_tools=("read", "write"), extra=()):
    """One Copilot call, flag for flag as factory/agent.py builds it. mcp_off: your own MCP servers, switched off
    by name, because the factory's container has none (see mcp_servers). file_tools: the tools every work call
    gets; the Jira calls get none. extra: flags at the end, such as the Jira calls' --plugin-dir.
    A call without a shell tool also gets --deny-tool=shell after the config's deny list: Copilot 1.0.115 runs shell
    commands it thinks are read-only even when no shell tool is allowed. Never in config.json: a deny beats every
    allow, so spec and build would lose their shell(...) tools."""
    model = local.get("model") or cfg["model"]
    argv = [*exe, "-p", prompt, "--no-ask-user", "--model", model, "--output-format", "json",
            "--no-auto-update", "--disallow-temp-dir", "--disable-builtin-mcps", "--max-ai-credits",
            str(cap if cap is not None else cfg.get("max_ai_credits", copied.MAX_AI_CREDITS)),
            "--secret-env-vars=COPILOT_GITHUB_TOKEN", f"--usage-output-file={usage_file}"]
    argv += [f"--allow-tool={x}" for x in [*file_tools, *tools]]
    argv += [f"--deny-tool={x}" for x in cfg["deny_tools"]]
    if not has_shell_tool([*file_tools, *tools]):
        argv.append("--deny-tool=shell")
    argv += [f"--disable-mcp-server={x}" for x in mcp_off]
    argv += list(extra)
    for a in argv:  # including a local.json "copilot" prefix
        for f in [*cfg["forbidden_flags"], NO_INSTRUCTIONS]:
            if a == f or a.startswith(f + "="):
                raise config.Stop(f"forbidden flag {f}")
    return argv


def child_env(cfg, env_extra, base=None):
    """Your own environment (so your Copilot login works), minus the Jira credentials, plus the factory's safety
    settings. Stops if a permissive mode is switched on, as the factory does."""
    env = dict(os.environ if base is None else base)
    for k, bad in cfg["forbidden_env"].items():
        if k in env and (bad == "" or env[k] == bad):
            raise config.Stop(f"forbidden environment variable {k} is set; unset it first")
    for k in JIRA_ENV:
        env.pop(k, None)
    env.update(copied.SAFE_ENV)
    env.update(env_extra)
    return env


def mcp_servers(exe, repo, env):
    """Names of every MCP server your Copilot would start in this project: yours (~/.copilot/mcp-config.json),
    the project's (.mcp.json, .github/mcp.json, if you trusted the folder), plugins' and built-in ones.
    A local -p run starts them and shows their tools to the model; the allow list then denies each call.
    The factory's container has none, so agentic-factory.py switches each one off by name. Reads only the names:
    the listing also has your servers' env and headers, which may contain tokens."""
    try:
        out = subprocess.run([*exe, "mcp", "list", "--json"], cwd=repo, env=env, capture_output=True, timeout=60)
        servers = json.loads(out.stdout.decode("utf-8")).get("mcpServers") if out.returncode == 0 else None
    except (OSError, ValueError, subprocess.TimeoutExpired):
        servers = None
    if not isinstance(servers, dict):
        raise config.Stop("can't list your MCP servers with `copilot mcp list --json`, so agentic-factory.py can't switch "
                   "them off; update GitHub Copilot CLI")
    return sorted(str(k) for k in servers)


def instruction_sources(exe, repo, env):
    """The instruction files Copilot would load in this project, as `copilot instruction list --json` lists them:
    [(location, path)], location "repository", "working-directory", "User home", or a plugin's. None when Copilot
    can't list them."""
    try:
        out = subprocess.run([*exe, "instruction", "list", "--json"], cwd=repo, env=env, capture_output=True, timeout=60)
        items = json.loads(out.stdout.decode("utf-8")) if out.returncode == 0 else None
    except (OSError, ValueError, subprocess.TimeoutExpired):
        items = None
    if not isinstance(items, list):
        return None
    return [(str(x.get("location", "")), str(x.get("sourcePath") or x.get("label") or ""))
            for x in items if isinstance(x, dict) and not x.get("defaultDisabled")]


MD_LINK = re.compile(r"\]\(\s*<?([^)\s>]+)>?[^)]*\)|^[ \t]*\[[^\]]+\]:[ \t]*<?([^\s>]+)", re.M)


def agents_links(repo):
    """The project files the root AGENTS.md links to, relative to the project, as git shows them. The prompts tell the
    agent to follow them, so a change to one between two calls counts like a change to AGENTS.md. Links to the web,
    to anchors, and out of the project are left out."""
    repo = repo.resolve()
    try:
        text = (repo / "AGENTS.md").read_text(encoding="utf-8", errors="replace")
    except OSError:
        return set()
    out = set()
    for m in MD_LINK.finditer(text):
        target = (m.group(1) or m.group(2) or "").split("#", 1)[0].split("?", 1)[0]
        if not target or re.match(r"[A-Za-z][A-Za-z0-9+.-]*:", target):
            continue
        try:
            rel = (repo / target.lstrip("/")).resolve().relative_to(repo).as_posix()
        except (ValueError, OSError):
            continue
        if rel != ".":
            out.add(rel)
    return out


def linked_hits(linked, paths):
    """The paths that are a file AGENTS.md links to, or lie in a folder it links to."""
    return [p for p in paths if any(p == x or p.startswith(x + "/") for x in linked)]


def instruction_notes(sources):
    """What to say about the instruction files of a run: which ones Copilot loads, a warning for files from outside
    the project (the factory's container has none of them), and one when the project has no AGENTS.md."""
    if sources is None:
        return ["WARNING: can't list the instruction files with `copilot instruction list --json`, so "
                "agentic-factory.py can't check that Copilot loads AGENTS.md and nothing from outside the project; "
                "update GitHub Copilot CLI"]
    inside = [p for loc, p in sources if loc in ("repository", "working-directory")]
    outside = [p for loc, p in sources if loc not in ("repository", "working-directory")]
    out = [f"instruction files Copilot loads: {inside}" if inside else "Copilot loads no instruction files"]
    if "AGENTS.md" not in inside:
        out.append("note: the project has no AGENTS.md, so the calls get no rules of your team")
    if outside:
        out.append(f"WARNING: Copilot also loads instruction files from outside the project, which the factory's "
                   f"container doesn't have: {outside}. Move them away for a run like the factory's")
    return out


def resolve_copilot(local):
    if local.get("copilot"):
        return list(local["copilot"])
    exe = shutil.which("copilot")
    if not exe:
        raise config.Stop("copilot not found on PATH: install GitHub Copilot CLI and run `copilot` once to log in")
    if os.name == "nt" and os.path.splitext(exe)[1].lower() in (".cmd", ".bat"):
        raise config.Stop(f"{exe} is a batch file; multi-line prompts can't pass through cmd.exe safely. Install Copilot CLI "
                   "as copilot.exe (WinGet), or set \"copilot\" in local.json to a command without cmd.exe")
    return [exe]


def run_call(argv, repo, env, events_path, timeout):
    """Start Copilot, show its tool calls live, keep the JSON events. Returns (exit code, final message, denied)."""
    final, denied = "", 0
    with open(events_path, "wb") as log, subprocess.Popen(argv, cwd=repo, env=env, stdin=subprocess.DEVNULL,
                                                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT) as p:
        timer = threading.Timer(timeout, p.kill)
        timer.start()
        try:
            for raw in p.stdout:
                log.write(raw)
                try:
                    ev = json.loads(raw)
                except ValueError:
                    continue
                t, d = ev.get("type"), ev.get("data") or {}
                if t == "tool.execution_start":
                    a = d.get("arguments", {})
                    arg = (a.get("command") or a.get("path") or json.dumps(a)[:120]) if isinstance(a, dict) else str(a)
                    print(f"    {d.get('toolName')} {str(arg)[:140]}".replace("\n", " "), flush=True)
                elif t == "tool.execution_complete" and not d.get("success", True):
                    if (d.get("error") or {}).get("code") == "denied":
                        denied += 1
                        print(f"      DENIED: {str((d.get('error') or {}).get('message', ''))[:160]}", flush=True)
                elif t == "assistant.message" and d.get("content"):
                    final = d["content"]
            rc = p.wait()
        finally:
            timed_out = not timer.is_alive()
            timer.cancel()
    return ("timeout" if timed_out and rc != 0 else rc), final, denied


def credits_of(usage_file):
    try:
        return config.read_json(usage_file).get("totalNanoAiu", 0) / 1e9
    except Exception:  # noqa: BLE001 - credits are informational
        return None


# --- a call's JSON events: its tool calls, and the shell backstop -----------------------------------------------------

def mcp_events(events_path):
    """{"version", "calls": [{"id", "tool", "args", "ok", "raw", "denied"}]} from a call's JSON events. Start and
    complete pair by toolCallId. denied: Copilot refused the call (error code "denied"), so it did nothing.
    raw is the tool's own text: the text items of result.contents joined in order (the MCP server's complete answer).
    result.detailedContent is only the fallback (older Copilot): Copilot 1.0.115 cuts it off at about 10 KB, so a long
    ticket would not parse. result.content is never used: it has Copilot's cost note added.
    A complete without a start still counts as a call, with tool None."""
    version, calls, by_id = None, [], {}
    try:
        with open(events_path, "rb") as fh:
            lines = fh.read().splitlines()
    except OSError as e:
        raise config.Stop(f"can't read the events of the Jira call: {e}")
    for line in lines:
        try:
            e = json.loads(line)
        except ValueError:
            continue
        d = e.get("data") if isinstance(e, dict) else None
        if not isinstance(d, dict):
            continue
        t = e.get("type")
        if t == "session.start" and version is None:
            version = d.get("copilotVersion")
        elif t == "tool.execution_start":
            args = d.get("arguments")
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except ValueError:
                    pass
            c = {"id": d.get("toolCallId"), "tool": d.get("toolName"), "args": args, "ok": False, "raw": None,
                 "denied": False}
            calls.append(c)
            by_id[c["id"]] = c
        elif t == "tool.execution_complete":
            c = by_id.pop(d.get("toolCallId"), None)
            if c is None:
                c = {"id": d.get("toolCallId"), "tool": None, "args": None, "ok": False, "raw": None, "denied": False}
                calls.append(c)
            res = d.get("result") if isinstance(d.get("result"), dict) else {}
            c["ok"] = d.get("success") is True
            err = d.get("error") if isinstance(d.get("error"), dict) else {}
            c["denied"] = not c["ok"] and err.get("code") == "denied"
            items = res.get("contents") if isinstance(res.get("contents"), list) else []
            texts = [i["text"] for i in items if isinstance(i, dict) and i.get("type") == "text"
                     and isinstance(i.get("text"), str)]
            if texts:
                c["raw"] = "".join(texts)
            else:
                c["raw"] = res.get("detailedContent") if isinstance(res.get("detailedContent"), str) else None
    return {"version": version, "calls": calls}


TESTED_VERSION = "1.0.115"  # the Copilot CLI whose events the script reads
BLIND = ("; blocked.jsonl, the shell check and the test line may miss what this call did. Check the events in {} and "
         "the agentic-factory.py version")


def _event_lines(events_path):
    try:
        with open(events_path, "rb") as fh:
            return fh.read().splitlines()
    except OSError:
        return []


def event_warnings(events_path, rc):
    """Warnings when a call's events don't look like the tested Copilot's: no session.start, a call that exited 0
    without any tool or message event, or another copilotVersion (arbiter ruling 2). The blocked log, the shell
    backstop and the test line read these events; a changed format would make them report nothing."""
    version, seen, known = None, False, False
    for raw in _event_lines(events_path):
        try:
            e = json.loads(raw)
        except ValueError:
            continue
        if not isinstance(e, dict):
            continue
        t, d = e.get("type"), e.get("data") if isinstance(e.get("data"), dict) else {}
        if t == "session.start":
            seen, version = True, version or d.get("copilotVersion")
        elif t in ("tool.execution_start", "tool.execution_complete", "assistant.message"):
            known = True
    blind = BLIND.format(events_path)
    if not seen:
        return ["Copilot events not recognized (no session.start)" + blind]
    if rc == 0 and not known:
        return [f"Copilot {version} events not recognized (no tool or message events)" + blind]
    if version != TESTED_VERSION:
        return [f"Copilot {version} is not the tested {TESTED_VERSION}; its events may differ" + blind]
    return []


def non_json_tail(events_path, n=5):
    """The last n lines of a call's output that aren't JSON events: Copilot's own messages, such as an error."""
    out = []
    for raw in _event_lines(events_path):
        try:
            json.loads(raw)
        except ValueError:
            line = raw.decode("utf-8", errors="replace").strip()
            if line:
                out.append(line[:300])
    return out[-n:]


SHELL_TOOLS = ("bash", "shell", "powershell")


def shell_ran(events_path):
    """The shell tools a call started and Copilot didn't deny, from its JSON events: bash, shell, powershell, and
    names that start with shell. A start without a complete counts: the command may have run."""
    out = []
    for c in mcp_events(events_path)["calls"]:
        name = c["tool"] if isinstance(c["tool"], str) else ""
        if (name.lower() in SHELL_TOOLS or name.lower().startswith("shell")) and not c["denied"]:
            out.append(name)
    return out


# --- after the run ----------------------------------------------------------------------------------------------------

def snapshot(repo):
    """{path: (git status code, sha256 of the content)} for every uncommitted path. Content hashes catch an agent
    that changes a file which was already modified before the run (its status line stays the same)."""
    out = ticket_mod.git(repo, "status", "--porcelain=v1", "-z", "-uall").split("\0")
    snap, i = {}, 0
    while i < len(out):
        e = out[i]
        i += 1
        if len(e) < 4:
            continue
        code, path = e[:2], e[3:]
        if "R" in code or "C" in code:
            i += 1  # the rename's old path follows
        f = repo / path
        try:
            digest = hashlib.sha256(f.read_bytes()).hexdigest() if f.is_file() else None
        except OSError:
            digest = None
        snap[path] = (code, digest)
    return snap


def changed_paths(before, after):
    """Lines like `git status --short` for every path whose status or content changed during the run."""
    return [f"{after[p][0] if p in after else 'ok'} {p}" for p in sorted(set(before) | set(after))
            if before.get(p) != after.get(p)]


def protected_hits(cfg, paths):
    """The paths that match protected_paths, without the factory's own files FACTORY-QUESTIONS.md and the verdict."""
    prot = [re.compile(p) for p in cfg["protected_paths"]]
    return [p for p in paths if any(r.search(p) for r in prot) and p not in (config.QUESTIONS, config.ASSESSMENT)]


def warnings_for(cfg, mode, fw, paths):
    out = []
    hit = protected_hits(cfg, paths)
    if hit:
        out.append(f"protected paths changed (the factory's check step would refuse): {hit[:20]}")
    if mode == "spec":
        rx = re.compile(cfg["frameworks"][fw].get("spec_any_under") or cfg["frameworks"][fw]["spec_change_re"])
        outside = [p for p in paths if not rx.match(p) and p != config.QUESTIONS]
        if outside:
            out.append(f"files outside the spec folder changed (the factory refuses this in a spec run): {outside[:20]}")
    if mode == "assess":
        other = [p for p in paths if p != config.ASSESSMENT]
        if other:
            out.append(f"the readiness check changed files besides {config.ASSESSMENT}: {other[:20]}")
    return out
