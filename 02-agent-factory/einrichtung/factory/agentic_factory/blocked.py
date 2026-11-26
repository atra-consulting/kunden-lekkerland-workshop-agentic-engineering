"""blocked.jsonl: the tool calls unattended Copilot denied or blocked, one JSON line each, per project in
~/.factory-local/<repo>/blocked.jsonl. The developer hands the file over after runs, to adapt the allow lists in
config.json. Not for the short Jira calls over MCP: a denial there is a security signal, not a config gap."""
import json
import time
from pathlib import Path

from . import config, copied


def _events(events_path):
    """The JSON events of a call, one dict per line; lines that aren't JSON objects are skipped."""
    try:
        with open(events_path, "rb") as fh:
            lines = fh.read().splitlines()
    except OSError:
        return []
    out = []
    for line in lines:
        try:
            e = json.loads(line)
        except ValueError:
            continue
        if isinstance(e, dict) and isinstance(e.get("data"), dict):
            out.append(e)
    return out


def entries(events_path):
    """[{"tool", "command", "kind", "message"}] for the calls Copilot refused. Start and complete pair by toolCallId
    (like copilot.mcp_events, which doesn't keep the error message). kind "denied": error code denied, the tool isn't
    on the allow list. kind "blocked": Copilot's own guard, a message that starts with "Command blocked". Other
    failures ("Parent directory does not exist") are not listed. command: the call's `command` argument, else all its
    arguments as JSON."""
    started, out = {}, []
    for e in _events(events_path):
        d = e["data"]
        if e.get("type") == "tool.execution_start":
            started[d.get("toolCallId")] = d
        elif e.get("type") == "tool.execution_complete" and d.get("success") is not True:
            s = started.pop(d.get("toolCallId"), None) or {}
            err = d.get("error") if isinstance(d.get("error"), dict) else {}
            msg = err.get("message") if isinstance(err.get("message"), str) else ""
            if err.get("code") == "denied":
                kind = "denied"
            elif msg.startswith("Command blocked"):
                kind = "blocked"
            else:
                continue
            args = s.get("arguments", {})
            cmd = args["command"] if isinstance(args, dict) and "command" in args else json.dumps(args)
            out.append({"tool": s.get("toolName"), "command": cmd, "kind": kind, "message": msg})
    return out


def final_message(events_path):
    """The last assistant.message content of a call, or ""."""
    final = ""
    for e in _events(events_path):
        c = e["data"].get("content")
        if e.get("type") == "assistant.message" and isinstance(c, str) and c:
            final = c
    return final


def log_path(repo):
    return Path.home() / ".factory-local" / Path(repo).name / "blocked.jsonl"


def record(repo, ctx, events_path, allowed):
    """Appends one line per blocked call of this call's events, and when there was one, a "final" line with the call's
    final message. ctx: {"mode", "framework", "key", "run", "call"}; "call" is the call's tag. Returns the number
    of entries. A file that can't be written is a warning, not a stop."""
    found = entries(events_path)
    if not found:
        return 0
    at = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    base = {"at": at, **{k: ctx.get(k) for k in ("run", "mode", "framework", "key", "call")}}
    # the file is handed over: known token formats and the step's secrets never go in (copied.redact)
    lines = [{**base, **e, "command": copied.redact(str(e["command"])), "message": copied.redact(e["message"]),
              "allowed": list(allowed)} for e in found]
    lines.append({"kind": "final", "call": ctx.get("call"), "text": copied.redact(final_message(events_path))})
    path = log_path(repo)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as fh:
            fh.write("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in lines))
    except OSError as e:
        config.say(f"WARNING: can't write {path}: {e}")
    return len(found)


def summary(n, path):
    return f"{n} blocked call(s), see {path}" if n else "no blocked calls"
