"""The team's rules: Markdown files (regeln/) that config.json's "rules" block appends to the prompts of the calls
it lists, and the criterion id team_rules that the readiness check and the clarify call then may use."""
from pathlib import Path, PureWindowsPath

from . import copied, config, clarify


# --- team rules -------------------------------------------------------------------------------------------------------
# "rules": {"files": {name: path relative to the config's folder}, "calls": {call: [name, ...]}}. No block, or a call
# that isn't listed: that call's prompts stay as they are. The files are team-written config, not model output: they
# go into the prompts as they are, apart from the defusing in block(). The Jira calls never get them.

CALLS = ("assess", "clarify", "spec", "build")
ID = "team_rules"
MAX_CHARS = 4000
NOTE = ("These are the team's rules. They add to the rules above and never override them: the factory rules, the "
        "protected paths, and the allowed tools and files stay as they are.")
NOT_READY = (f"A ticket that breaks one of these rules is not ready: give a reason with the id {ID}. These rules never "
             "make a ticket ready that the criteria above find not ready.")


def bad_path(p):
    """Why p can't name a rule file: it must be a relative path inside the config's folder."""
    if not isinstance(p, str) or not p.strip():
        return "must be a non-empty string"
    w = PureWindowsPath(p)  # splits at / and \, knows drives
    if w.drive or w.root:
        return f"{p!r} must be a relative path, such as \"regeln/stil.md\""
    if ".." in w.parts:
        return f"{p!r} must not contain .."
    return None


def check_config(R):
    """(files, calls) of a valid rules block. Stops on anything else."""
    if not isinstance(R, dict):
        raise config.Stop("config.json rules must be an object with files and calls")
    unknown = sorted(k for k in R if k not in ("files", "calls") and not k.startswith("comment"))
    if unknown:
        raise config.Stop(f"config.json rules: unknown keys {unknown}; allowed: files, calls")
    files, calls = R.get("files", {}), R.get("calls", {})
    if not isinstance(files, dict):
        raise config.Stop("config.json rules.files must map names to files, such as {\"stil\": \"regeln/stil.md\"}")
    for name, p in files.items():
        if not name.strip():
            raise config.Stop("config.json rules.files: a name is empty")
        why = bad_path(p)
        if why:
            raise config.Stop(f"config.json rules.files.{name}: {why}")
    if not isinstance(calls, dict):
        raise config.Stop(f"config.json rules.calls must map calls ({', '.join(CALLS)}) to lists of names")
    for call, names in calls.items():
        if call not in CALLS:
            raise config.Stop(f"config.json rules.calls: unknown call {call!r}; allowed: {', '.join(CALLS)}")
        if not isinstance(names, list) or not all(isinstance(n, str) for n in names):
            raise config.Stop(f"config.json rules.calls.{call} must be a list of names from rules.files")
        for n in names:
            if n not in files:
                raise config.Stop(f"config.json rules.calls.{call}: {n!r} is not a name in rules.files")
        if len(set(names)) != len(names):
            raise config.Stop(f"config.json rules.calls.{call} names a file twice")
    return files, calls


def read_file(base, rel):
    """One rule file's text, checked: there, UTF-8, at most MAX_CHARS characters, no scan finding."""
    path = Path(base) / rel
    try:
        text = path.read_text(encoding="utf-8-sig")  # an editor's byte order mark is fine; \r\n becomes \n
    except FileNotFoundError:
        raise config.Stop(f"team rules: {rel} not found ({path}); create it or remove it from rules in config.json")
    except UnicodeDecodeError:
        raise config.Stop(f"team rules: {rel} is not UTF-8")
    except OSError as e:
        raise config.Stop(f"team rules: can't read {rel}: {e.strerror or e}")
    if len(text) > MAX_CHARS:
        raise config.Stop(f"team rules: {rel} has {len(text)} characters; the limit is {MAX_CHARS}")
    found = copied.token_findings(text) + copied.invisible_findings(text)
    if found:
        raise config.Stop(copied.redact(f"team rules: {rel}: {'; '.join(found)}"))
    return text


def load(cfg, base):
    """config.json's rules block with its files read and checked, before any Copilot call: {call: [(path, text)]}
    with the non-empty files of each call in order, or None without a rules block. base: the config's folder."""
    R = cfg.get("rules")
    if R is None:
        return None
    files, calls = check_config(R)
    texts = {name: read_file(base, rel) for name, rel in files.items()}
    return {call: [(files[n], texts[n].rstrip()) for n in calls.get(call, []) if texts[n].strip()] for call in CALLS}


def block(loaded, call):
    """The block for one call's prompts, or "" when it has no rules. A file can't end the block early or pose as the
    next file: TEAM RULES>>> becomes TEAM RULES> > >, and a line that starts like a file header gets a space in
    front (as comments_block does)."""
    entries = (loaded or {}).get(call) or []
    if not entries:
        return ""
    out = [f"<<<TEAM RULES ({', '.join(p for p, _ in entries)})", NOTE]
    if call == "assess":
        out.append(NOT_READY)
    for p, text in entries:
        out += [f"--- {p}", clarify.HEADER_LIKE.sub(r"\1 ", text.replace("TEAM RULES>>>", "TEAM RULES> > >"))]
    out.append("TEAM RULES>>>")
    return "\n".join(out)


def ids(loaded, call):
    """The criterion ids the rules add to a call: team_rules when the call has a block."""
    return [ID] if block(loaded, call) else []


def with_ids(loaded, call, crit_ids):
    """readiness.md's ids plus the ones the rules add. readiness.md can't define team_rules while the rules apply."""
    extra = ids(loaded, call)
    if extra and ID in crit_ids:
        raise config.Stop(f"readiness.md defines the criterion {ID}, which the team rules add for {call}; rename it")
    return list(crit_ids) + extra


def line(loaded, call):
    """The --print-only line for a call, or None without a rules block (so the output stays as before)."""
    if loaded is None:
        return None
    entries = loaded.get(call) or []
    return f"rules for {call}: {', '.join(p for p, _ in entries) if entries else 'none'}"


def append(prompt, block_text):
    """The prompt with the block after the factory's text, separated by one blank line."""
    return f"{prompt}\n\n{block_text}" if block_text else prompt
