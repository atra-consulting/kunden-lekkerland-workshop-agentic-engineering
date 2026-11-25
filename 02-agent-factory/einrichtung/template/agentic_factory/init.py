"""`init`: the checks on the suggestions a read-only Copilot call writes to FACTORY-INIT.json. The project's docs go into
that call's prompt and may carry a prompt injection, so a suggestion may only add or tighten: it never loosens
deny_tools, protected_paths, forbidden_flags, or forbidden_env. The checks are pure functions: no Copilot call, no file
written. run_init (at the end) is the mode: one Copilot call, the checks, the report, and with --apply the two files."""
import copy
import difflib
import json
import re
import shlex
import time
from collections import Counter
from pathlib import Path

from . import agent, blocked, config, copilot, readiness
from . import ticket as ticket_mod

OUT = "FACTORY-INIT.json"
KEY = "INIT"  # the log folder name and the blocked.jsonl key of an init run (there is no ticket)
SUGGESTION_KEYS = ("test_command", "add_tools", "add_protected_paths", "add_deny_tools", "enabled_frameworks", "readiness_md")
MODES = ("spec", "build")  # the modes whose tool lists add_tools may extend
NETWORK = {"curl", "wget", "ssh", "scp", "nc", "ncat", "netcat", "telnet", "sftp", "ftp", "rsync"}
LAUNCHERS = {"npx", "pnpx", "bunx", "uvx", "pipx"}  # download and run a package
LAUNCHER_SUBCOMMANDS = {"npm": {"exec", "x"}, "pnpm": {"dlx", "exec"}, "yarn": {"dlx"}}
INSTALLERS = {("pip", "install"), ("uv", "pip"), ("uv", "add"), ("poetry", "add"), ("poetry", "install"), ("npm", "install"),
              ("npm", "i"), ("npm", "ci"), ("yarn", "add"), ("yarn", "install"), ("pnpm", "add"), ("pnpm", "install"),
              ("gem", "install"), ("bundle", "install"), ("cargo", "install"), ("go", "install"), ("go", "get"),
              ("composer", "install"), ("composer", "require")}  # package installers run the packages' setup code
INSTALLER_MANAGERS = {m for m, _ in INSTALLERS}  # a bare "shell(npm:*)" allows their install commands too
PIP = re.compile(r"pip\d*(\.\d+)*")  # pip, pip3, pip3.12
SHAPE = "not a suggestion {value, reason, source}"
CONTROL = re.compile(r"[\x00-\x1f\x7f-\x9f]+")
UNSAFE_TEXT = re.compile("[\x00-\x08\x0b-\x1f\x7f-\x9f\u200e\u200f\u2028\u2029\u202a-\u202e\u2066-\u2069]")  # terminal escapes, bidi
MAX_PATTERN = 200  # chars of one protected_paths regex


def shell_prefix(tool):
    """X of "shell(X:*)" or "shell(X)", or None when the tool isn't of that form or X is empty."""
    if not (isinstance(tool, str) and tool.startswith("shell(") and tool.endswith(")")):
        return None
    x = tool[len("shell("):-1]
    x = x[:-2] if x.endswith(":*") else x
    return x or None


CAN_WRITE = {  # left out of read_tools on purpose: they can write files or run commands
    "find": "find can run commands (-exec) and delete files (-delete)",
    "sed": "sed can write files (-i, the w command) and run commands (the e command)",
    "awk": "awk can write files and run commands (system())",
    "rg": "rg can run commands (--pre)",
    "tree": "tree can write files (-o)",
    "sort": "sort can write files (-o)",
    "tar": "tar can write files and run commands (--to-command, --checkpoint-action)",
    "docker": "docker runs any code in a container that can mount the project",
    "podman": "podman runs any code in a container that can mount the project",
}


def refusal(tool, cfg, interpreters=True):
    """Why init may not add this tool to an allow list, or None. Bare shell, tools a deny_tools entry covers, any git
    tool (.git/config can turn git calls into code execution), network tools, package installers and launchers, commands
    that can write files or run commands (find, sed, ...), wrappers, runners without a concrete command, and
    interpreters are refused: they let the agent run what it likes. interpreters=False skips the wrapper and
    interpreter rules, for a test_command suggestion (check_test_command judges those: python3 -m pytest is fine)."""
    if not isinstance(tool, str):
        return "not a string"
    if tool == "shell":
        return "bare shell allows every command"
    x = shell_prefix(tool)
    if x is None:
        return "only shell(...) tools can be added"
    words = x.split(" ")
    for i, w in enumerate(words):
        if not (copilot.TEST_CHARS if i == 0 else copilot.ARG_CHARS).fullmatch(w):
            return (f"{w!r} has characters outside letters, digits and _ . / : @ + , % - (and = after the first word); "
                    "words are separated by single spaces")
    entry = copilot.denied_by(x, cfg["deny_tools"])
    if entry:
        return f"covered by {entry} in deny_tools, which beats every allow"
    if interpreters and copilot.base_name(words[0]) in copilot.WRAPPERS:
        return f"{copilot.base_name(words[0])} runs any command"
    try:
        start = copilot.command_start(x, words)  # past wrappers and "<runner> run"
    except config.Stop as e:
        return str(e)
    if start == len(words):
        return f"{x!r} ends right after a wrapper or runner; name the script, module, or target to run"
    first, words = copilot.base_name(words[start]), words[start:]
    if first == "git":
        return "git tools are refused: .git/config can turn git calls into code execution"
    if first in NETWORK:
        return f"{first} reaches the network"
    if first in CAN_WRITE:
        return CAN_WRITE[first]
    if first in LAUNCHERS or (len(words) > 1 and words[1] in LAUNCHER_SUBCOMMANDS.get(first, ())):
        return f"{first} downloads and runs a package"
    manager = "pip" if PIP.fullmatch(first) else first
    # any word after the manager that is its installer subcommand (an option may take a value: npm --prefix dir install),
    # up to "run": npm run ci runs a script, not an install; or only options after it (npm --silent)
    args = words[1:words.index("run") if "run" in words[1:] else len(words)]
    if (any((manager, w) in INSTALLERS for w in args) or (len(words) == 1 and manager in INSTALLER_MANAGERS | {"pip"})
            or (manager in INSTALLER_MANAGERS | {"pip"} and len(words) > 1 and all(w.startswith("-") for w in words[1:]))):
        return "installs packages, which runs their setup code"
    if first in copilot.RUNNERS and len(words) == 1:
        return f"{first} runs any command; use a specific command such as {first} run pytest"
    if interpreters:
        for w in x.split(" "):
            name = copilot.interpreter_name(w)
            if name:
                return f"{name} is an interpreter that runs any code"
    return None


def broad_note(tool):
    """A flag for a tool that allows a whole family of commands, or None: shell(x:*) with one word x."""
    if not (isinstance(tool, str) and tool.startswith("shell(") and tool.endswith(":*)")):
        return None
    x = tool[len("shell("):-len(":*)")]
    if not x or " " in x:
        return None
    return "allows every Make target" if x == "make" else f"allows every {x} command"


# --- the checks ---------------------------------------------------------------------------------------------------------

def _is_suggestion(x):
    return isinstance(x, dict) and "value" in x and isinstance(x.get("reason"), str) and isinstance(x.get("source"), str)


def _deny_problem(entry, cfg, deny):
    """Why a new deny_tools entry would break the config, or None: a deny entry beats every allow, so one that covers a
    read_tools entry or the test command makes the factory stop."""
    if shell_prefix(entry) is None:
        return "only shell(...) entries can be added to deny_tools"
    try:
        copilot.check_read_tools({"read_tools": cfg.get("read_tools"), "deny_tools": deny + [entry]})
    except config.Stop as e:
        return str(e)
    cmd = cfg.get("test_command")
    if cmd and copilot.denied_by(cmd, [entry]):
        return f"would cover the test command {cmd!r}, which a deny entry beats"
    return None


def check_suggestions(d, cfg, readiness_text, installed):
    """Checks the content of FACTORY-INIT.json against cfg (the current config.json), the current readiness.md text, and
    the installed frameworks. Returns {"accepted": [(key, path, suggestion)], "refused": [(key, path, suggestion,
    reason)], "notes": [str]}. path is "" except for add_tools ("<framework>.<mode>"). A refused suggestion is kept with
    its reason; nothing is dropped silently."""
    if not isinstance(d, dict):
        raise config.Stop(f"{OUT} must be a JSON object")
    accepted, refused, notes = [], [], []
    yes = lambda key, path, sg: accepted.append((key, path, sg))
    no = lambda key, path, sg, why: refused.append((key, path, sg, why))
    for key, value in d.items():
        if key not in SUGGESTION_KEYS:
            no(key, "", value, "unknown key")
    deny = list(cfg["deny_tools"])  # grows with accepted deny entries: later suggestions are checked against them

    def single(key):
        sg = d.get(key)
        if sg is None:
            return None
        if not _is_suggestion(sg):
            no(key, "", sg, SHAPE)
            return None
        return sg

    def many(key, value, path=""):
        if value is None:
            return []
        if not isinstance(value, list):
            no(key, path, value, "expected a list of suggestions")
            return []
        out = []
        for x in value:
            if _is_suggestion(x):
                out.append(x)
            else:
                no(key, path, x, SHAPE)
        return out

    for sg in many("add_deny_tools", d.get("add_deny_tools")):
        why = _deny_problem(sg["value"], cfg, deny)
        if why:
            no("add_deny_tools", "", sg, why)
        else:
            yes("add_deny_tools", "", sg)
            deny.append(sg["value"])
    checked = {**cfg, "deny_tools": deny}

    sg = single("test_command")
    if sg:
        cmd = sg["value"]
        try:
            if not isinstance(cmd, str):
                raise config.Stop(f"test_command {cmd!r} is not a string")
            copilot.check_test_command(cmd)
            why = refusal(f"shell({cmd}:*)", checked, interpreters=False)
            if why:
                raise config.Stop(f"test_command {cmd!r}: {why}")
            yes("test_command", "", sg)
        except config.Stop as e:
            no("test_command", "", sg, str(e))

    tools = d.get("add_tools")
    if tools is not None and not isinstance(tools, dict):
        no("add_tools", "", tools, "expected {framework: {spec: [...], build: [...]}}")
        tools = {}
    for fw, modes in (tools or {}).items():
        if fw not in cfg["frameworks"]:
            no("add_tools", fw, modes, f"unknown framework {fw!r}; known: {', '.join(cfg['frameworks'])}")
        elif not isinstance(modes, dict):
            no("add_tools", fw, modes, "expected {spec: [...], build: [...]}")
        else:
            for mode, value in modes.items():
                path = f"{fw}.{mode}"
                if mode not in MODES:
                    no("add_tools", path, value, f"unknown mode {mode!r}; only {' and '.join(MODES)} can get tools")
                    continue
                for sg in many("add_tools", value, path):
                    why = refusal(sg["value"], checked)
                    if why:
                        no("add_tools", path, sg, why)
                    else:
                        yes("add_tools", path, sg)
                        note = broad_note(sg["value"])
                        if note:
                            notes.append(f"{sg['value']}: {note}")

    for sg in many("add_protected_paths", d.get("add_protected_paths")):
        value = sg["value"]
        try:
            if not isinstance(value, str) or not value:
                raise ValueError("expected a non-empty string")
            if len(value) > MAX_PATTERN:
                raise ValueError(f"longer than {MAX_PATTERN} characters")
            re.compile(value)
            yes("add_protected_paths", "", sg)
        except (re.error, ValueError, OverflowError, RecursionError) as e:
            no("add_protected_paths", "", sg, f"not a usable regular expression: {e}")

    sg = single("enabled_frameworks")
    if sg:
        value = sg["value"]
        known = list(cfg["frameworks"])
        if not (isinstance(value, list) and value and all(isinstance(x, str) for x in value)):
            no("enabled_frameworks", "", sg, "expected a non-empty list of framework names")
        elif [x for x in value if x not in installed or x not in known]:
            bad = [x for x in value if x not in installed or x not in known]
            no("enabled_frameworks", "", sg, f"not installed here (installed: {', '.join(installed) or 'none'}): {', '.join(bad)}")
        elif cfg.get("default_framework") and cfg["default_framework"] not in value:
            no("enabled_frameworks", "", sg, f"default_framework {cfg['default_framework']!r} would not be enabled")
        else:
            yes("enabled_frameworks", "", sg)

    sg = single("readiness_md")
    if sg:
        try:
            if not isinstance(sg["value"], str):
                raise config.Stop("readiness_md must be the full new text, a string")
            if UNSAFE_TEXT.search(sg["value"]):
                raise config.Stop("readiness_md contains control characters or text-direction marks (only newline and tab "
                                  "are allowed); the diff goes to the terminal")
            new_ids = readiness.parse_criteria(sg["value"], "readiness_md")[1]
            lost = [i for i in readiness.parse_criteria(readiness_text, "readiness.md")[1] if i not in new_ids]
            if lost:
                raise config.Stop(f"the new text drops the criterion ids {', '.join(lost)}, which the clarify and assess "
                                  "checks rely on; a person removes a criterion by hand")
            yes("readiness_md", "", sg)
        except config.Stop as e:
            no("readiness_md", "", sg, str(e))
    return {"accepted": accepted, "refused": refused, "notes": notes}


def _add(lst, value):
    if value not in lst:
        lst.append(value)


def apply(cfg, accepted):
    """A new config with the accepted suggestions: additions appended once in order, test_command replaced,
    enabled_frameworks replaced. Never a removal, and nothing else is written: not forbidden_flags, forbidden_env,
    read_tools, prompts, or credit caps. The checks run again as a second line of defence. readiness_md is not part of
    the config: see readiness_of."""
    new = copy.deepcopy(cfg)
    for key, path, sg in accepted:
        value = sg.get("value") if isinstance(sg, dict) else None
        if key == "test_command" and isinstance(value, str):
            new["test_command"] = value
        elif key == "add_deny_tools" and isinstance(value, str) and shell_prefix(value):
            _add(new["deny_tools"], value)
        elif key == "add_protected_paths" and isinstance(value, str) and value:
            _add(new["protected_paths"], value)
        elif key == "add_tools":
            fw, _, mode = path.partition(".")
            if fw in new["frameworks"] and mode in MODES and not refusal(value, new):
                _add(new["frameworks"][fw].setdefault(f"{mode}_tools", []), value)
        elif key == "enabled_frameworks" and isinstance(value, list) and value and all(x in new["frameworks"] for x in value):
            new["enabled_frameworks"] = list(value)
    return new


def readiness_of(accepted):
    """The accepted readiness_md text, or None."""
    for key, _, sg in accepted:
        if key == "readiness_md" and isinstance(sg.get("value"), str):
            return sg["value"]
    return None


# --- what the person sees ----------------------------------------------------------------------------------------------

def _clean(x, limit=300):
    """One printable line of x: control characters (such as terminal escapes) become spaces, long text is cut."""
    text = CONTROL.sub(" ", x if isinstance(x, str) else json.dumps(x, ensure_ascii=False)).strip()
    return text if len(text) <= limit else text[:limit - 1] + "…"


def blocked_summary(path, limit=50):
    """Counts of the blocked calls in blocked.jsonl per (mode, framework, tool, command), most first, one line each, for
    the prompt: the agent can't read outside the repo."""
    counts = Counter()
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        lines = []
    for line in lines:
        try:
            e = json.loads(line)
        except ValueError:
            continue
        if isinstance(e, dict) and e.get("kind") != "final" and e.get("tool"):
            counts[tuple(_clean(e.get(k) if e.get(k) is not None else "?", 120) for k in ("mode", "framework", "tool", "command"))] += 1
    if not counts:
        return "no blocked calls recorded"
    rows = [f"{n}x {mode}/{fw} {tool}: {cmd}" for (mode, fw, tool, cmd), n in counts.most_common()]
    return "\n".join(rows[:limit] + ([f"... and {len(rows) - limit} more"] if len(rows) > limit else []))


def render_report(result):
    """The readable report: every suggestion with reason and source, refused ones with the reason, and the flags."""
    out = []

    def item(sign, key, path, sg, why=None):
        value = sg.get("value") if isinstance(sg, dict) else sg
        shown = f"<text of {len(value.splitlines())} lines, see the diff>" if key == "readiness_md" and isinstance(value, str) else _clean(value)
        out.append(f"  {sign} {key}{' ' + path if path else ''}: {shown}")
        if why:
            out.append(f"      refused: {_clean(why)}")
        if isinstance(sg, dict):
            out.append(f"      reason: {_clean(sg.get('reason'))}")
            out.append(f"      source: {_clean(sg.get('source'))}")

    if not (result["accepted"] or result["refused"]):
        return "init has no suggestions: nothing to change."
    if result["accepted"]:
        out.append(f"Suggestions ({len(result['accepted'])}):")
        for key, path, sg in result["accepted"]:
            item("+", key, path, sg)
    if result["refused"]:
        out.append(f"Refused suggestions ({len(result['refused'])}):")
        for key, path, sg, why in result["refused"]:
            item("-", key, path, sg, why)
    if result["notes"]:
        out.append("Flags:")
        out.extend(f"  ! {_clean(n)}" for n in result["notes"])
    return "\n".join(out)


def diff(old, new, name):
    """A unified diff of two texts, or "" when they are equal."""
    return "\n".join(difflib.unified_diff(old.splitlines(), new.splitlines(), f"{name} (current)", f"{name} (suggested)", lineterm=""))


# --- the mode ----------------------------------------------------------------------------------------------------------

def installed_frameworks(repo, cfg):
    """The frameworks of this config whose folder exists in the project (ticket.FRAMEWORK_MARKERS)."""
    return [fw for fw, marker in ticket_mod.FRAMEWORK_MARKERS.items() if fw in cfg["frameworks"] and (Path(repo) / marker).is_dir()]


def config_view(cfg):
    """The parts of config.json init may change, as the prompt shows them."""
    view = {k: cfg.get(k) for k in ("test_command", "enabled_frameworks", "protected_paths", "deny_tools")}
    view["frameworks"] = {fw: {k: F.get(k, []) for k in ("spec_tools", "build_tools")} for fw, F in cfg["frameworks"].items()}
    return json.dumps(view, ensure_ascii=False, indent=2)


def init_call(cfg, readiness_text, installed, blocked_text):
    """(prompt, tools, credit cap) of the one init call. No tools beyond the file tools: copilot_argv denies the shell."""
    block = cfg["init"]
    prompt = copilot.fill(block["prompt"], {"config": config_view(cfg), "readiness": readiness_text,
                                            "installed": ", ".join(installed) or "none", "blocked": blocked_text,
                                            "output_file": OUT}, "the init prompt")
    return prompt, [], block.get("max_ai_credits", 40)


def dump_config(old_text, new):
    """config.json's text for the dict new: the indent of the old text (two spaces if it has none), keys in order, and a
    trailing newline."""
    m = re.search(r"(?m)^([ \t]+)\S", old_text)
    return json.dumps(new, ensure_ascii=False, indent=m.group(1) if m else 2) + "\n"


def run_init(run, apply, print_only):
    """agentic-factory.py init: one Copilot call that reads the project's docs and writes FACTORY-INIT.json, the checks of
    check_suggestions, the report and the diffs; with apply, config.json and readiness.md are written, nothing else.
    No ticket and no Jira. Returns the exit code."""
    cfg, repo, a = run.cfg, run.repo, run.a
    if not isinstance(cfg.get("init"), dict):
        raise config.Stop("init is not available in this config: config.json has no \"init\" block")
    crit_path = Path(a.readiness) if a.readiness else Path(a.config).resolve().parent / run.A.get("criteria_file", "readiness.md")
    readiness_text, _ = run.criteria()
    installed = installed_frameworks(repo, cfg)
    prompt, tools, cap = init_call(cfg, readiness_text, installed, blocked_summary(blocked.log_path(repo)))
    logdir = run.log(KEY)
    if print_only:
        argv = copilot.copilot_argv(cfg, run.local, prompt, tools, (logdir / "usage-init.json").as_posix(), cap=cap)
        print(f"# 1 copilot call, init, run in {repo}\n{shlex.join(argv)}")
        print("\n# a local run also adds --disable-mcp-server=NAME for each server `copilot mcp list` shows")
        return 0
    run.set_io(logdir / "io")  # outside the project, so the work call's snapshots need no exception
    work = agent.Work(run, KEY, {}, {"mode": "init", "framework": None, "key": KEY, "run": logdir.name})
    try:  # the blocked-calls line ends every run, a stopped one too
        return _run_init_call(run, work, prompt, tools, cap, installed, readiness_text, crit_path, apply)
    finally:
        work.report()


def _run_init_call(run, work, prompt, tools, cap, installed, readiness_text, crit_path, write):
    cfg, repo, a = run.cfg, run.repo, run.a
    out = repo / OUT
    if out.is_file():
        out.unlink()
        config.say(f"removed the old {OUT}")
    before = work.snap()
    head = ticket_mod.head_commit(repo)
    if before:
        config.say(f"note: the working tree already has {len(before)} uncommitted change(s)")
    t0 = time.time()
    work.call("init", "init call", prompt, tools, cap)
    other = [x for x in copilot.changed_paths(before, work.snap()) if x[3:] != OUT]
    if other or ticket_mod.head_commit(repo) != head:
        raise config.Stop(f"the init call changed more than {OUT}: {other[:10]}; nothing is suggested or written")
    if not out.is_file():
        raise config.Stop(f"the init call wrote no {OUT}")
    try:
        d = config.read_json(out)
    finally:
        out.unlink()
    result = check_suggestions(d, cfg, readiness_text, installed)
    config.say(f"done: credits {work.total:.2f}, {int(time.time() - t0)} s, logs in {work.logdir}")
    if not (result["accepted"] or result["refused"]):
        config.say("keine Vorschläge: nothing to change.")
        return 0
    print(render_report(result))
    new = apply(cfg, result["accepted"])
    new_readiness = readiness_of(result["accepted"])
    cfg_path = Path(a.config)
    old_text = cfg_path.read_text(encoding="utf-8")
    new_text = dump_config(old_text, new) if new != cfg else old_text
    changes = []
    if new_text != old_text:
        changes.append((cfg_path, new_text, "config.json"))
    if new_readiness is not None and new_readiness != readiness_text:
        changes.append((crit_path, new_readiness, "readiness.md"))
    for path, text, name in changes:
        print("\n" + diff(readiness_text if name == "readiness.md" else old_text, text, name))
    if not changes:
        config.say("no change to config.json or readiness.md")
    elif not write:
        config.say("nothing was changed. Run init again with --apply to write config.json and readiness.md.")
    else:
        config.check_config(new)  # the checks again on what is about to be written
        for path, text, name in changes:
            path.write_bytes(text.encode("utf-8"))
            config.say(f"written: {path}")
        config.say("review the diff, then commit config.json and readiness.md by hand")
    return 0
