"""`init`: the checks on the suggestions a read-only Copilot call writes to FACTORY-INIT.json. The project's docs go into
that call's prompt and may carry a prompt injection, so a suggestion may only add or tighten: it never loosens
deny_tools, protected_paths, forbidden_flags, or forbidden_env. Pure functions: no Copilot call, no file written."""
import copy
import difflib
import json
import re
from collections import Counter

from . import config, copilot, readiness

OUT = "FACTORY-INIT.json"
SUGGESTION_KEYS = ("test_command", "add_tools", "add_protected_paths", "add_deny_tools", "enabled_frameworks", "readiness_md")
MODES = ("spec", "build")  # the modes whose tool lists add_tools may extend
NETWORK = {"curl", "wget", "ssh", "scp", "nc", "ncat", "netcat", "telnet", "sftp", "ftp", "rsync"}
LAUNCHERS = {"npx", "pnpx", "bunx", "uvx", "pipx"}  # download and run a package
LAUNCHER_SUBCOMMANDS = {"npm": {"exec", "x"}, "pnpm": {"dlx", "exec"}, "yarn": {"dlx"}}
INSTALLERS = {("pip", "install"), ("uv", "pip"), ("uv", "add"), ("poetry", "add"), ("poetry", "install"), ("npm", "install"),
              ("npm", "i"), ("npm", "ci"), ("yarn", "add"), ("yarn", "install"), ("pnpm", "add"), ("pnpm", "install"),
              ("gem", "install"), ("bundle", "install"), ("cargo", "install"), ("go", "install"), ("go", "get"),
              ("composer", "install"), ("composer", "require")}  # package installers run the packages' setup code
PIP = re.compile(r"pip\d*(\.\d+)*")  # pip, pip3, pip3.12
SHAPE = "not a suggestion {value, reason, source}"
CONTROL = re.compile(r"[\x00-\x1f\x7f-\x9f]+")


def shell_prefix(tool):
    """X of "shell(X:*)" or "shell(X)", or None when the tool isn't of that form or X is empty."""
    if not (isinstance(tool, str) and tool.startswith("shell(") and tool.endswith(")")):
        return None
    x = tool[len("shell("):-1]
    x = x[:-2] if x.endswith(":*") else x
    return x or None


def refusal(tool, cfg):
    """Why init may not add this tool to an allow list, or None. Bare shell, tools a deny_tools entry covers, any git
    tool (.git/config can turn git calls into code execution), network tools, interpreters, wrappers, and package
    launchers are refused: they let the agent run what it likes."""
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
    first = copilot.base_name(words[0])
    if first == "git":
        return "git tools are refused: .git/config can turn git calls into code execution"
    if first in NETWORK:
        return f"{first} reaches the network"
    if first in copilot.WRAPPERS:
        return f"{first} runs any command"
    if first in LAUNCHERS or (len(words) > 1 and words[1] in LAUNCHER_SUBCOMMANDS.get(first, ())):
        return f"{first} downloads and runs a package"
    head = ("pip" if PIP.fullmatch(first) else first,) + tuple(words[1:2])
    if head in INSTALLERS or (len(words) == 1 and PIP.fullmatch(first)):
        return "installs packages, which runs their setup code"
    if first in copilot.RUNNERS and len(words) == 1:
        return f"{first} runs any command; use a specific command such as {first} run pytest"
    for w in words:
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
            entry = copilot.denied_by(cmd, deny)
            if entry:
                raise config.Stop(f"test_command {cmd!r} is covered by {entry} in deny_tools, which beats every allow")
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
            re.compile(value)
            yes("add_protected_paths", "", sg)
        except (re.error, ValueError) as e:
            no("add_protected_paths", "", sg, f"not a regular expression: {e}")

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
