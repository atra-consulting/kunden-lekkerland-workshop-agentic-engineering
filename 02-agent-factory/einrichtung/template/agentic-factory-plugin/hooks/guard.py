"""agentic-factory guard: Copilot CLI preToolUse hook for agentic-factory.py's Jira calls over MCP.

agentic-factory.py writes <cwd>/af-expect.json before each Jira call:
  {"tool": "<server>-<tool>", "key": "LL-123", "site": "https://…", "body_file": "comment.txt" | null,
   "body_arg": "commentBody" | "fields.description" | null, "args": ["cloudId", "issueIdOrKey", ...],
   "fields_list": ["summary", ...] | null, "fields_keys": ["description"] | null}
Allowed: tool_search_tool, and one call of the expected tool with that issueIdOrKey and cloudId, no arguments
but those in "args", fields exactly fields_list (a list of names) or exactly the keys fields_keys (an object), and,
with a body_file, the file's text (trailing newlines ignored) at body_arg (a dotted path). Everything else is denied,
and so is everything when the expect file is missing or broken, or anything goes wrong. Each decision is appended
to <cwd>/hook.log. Copilot 1.0.115 runs no plugin hooks in -p mode, so agentic-factory.py also checks every call
afterwards from the events. Python standard library only.
"""
import json
import os
import sys

PREFIX = "agentic-factory-guard: "


def arg_at(args, path):
    cur = args
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def args_problem(args, exp):
    """Why the arguments aren't allowed, or None. agentic-factory.py has the same function as jira_args_problem."""
    allowed = exp["args"]
    if not isinstance(allowed, list):
        return "af-expect.json has no argument list"
    extra = sorted(set(args) - set(allowed))
    if extra:
        return f"arguments not allowed: {extra}"
    f = args.get("fields")
    if exp.get("fields_list") is not None and not (
            isinstance(f, list) and all(isinstance(x, str) for x in f) and len(f) == len(set(f))
            and set(f) == set(exp["fields_list"])):
        return f"fields must be exactly {exp['fields_list']}"
    if exp.get("fields_keys") is not None and not (isinstance(f, dict) and set(f) == set(exp["fields_keys"])):
        return f"fields may hold exactly {exp['fields_keys']}"
    return None


def earlier_allowed(log_path, tool, call_id):
    """True when hook.log already allowed this tool for another call id: only one call per Jira call."""
    try:
        with open(log_path, encoding="utf-8") as fh:
            lines = fh.read().splitlines()
    except FileNotFoundError:
        return False
    for line in lines:
        e = json.loads(line)
        if e.get("toolName") == tool and e.get("decision") == "allow" and e.get("toolCallId") != call_id:
            return True
    return False


def check(data, cwd):
    """(decision, reason) for one hook input."""
    with open(os.path.join(cwd, "af-expect.json"), encoding="utf-8") as fh:
        exp = json.load(fh)
    tool, key, site = exp["tool"], exp["key"], exp["site"]
    if not (isinstance(tool, str) and isinstance(key, str) and isinstance(site, str) and tool and key and site):
        return "deny", "af-expect.json is incomplete"
    name = data.get("toolName")
    if name == "tool_search_tool":
        return "allow", ""
    if name != tool:
        return "deny", f"only {tool} is allowed in this call, not {name}"
    args = data.get("toolArgs")
    if isinstance(args, str):
        args = json.loads(args)
    if not isinstance(args, dict):
        return "deny", "no tool arguments"
    if args.get("issueIdOrKey") != key:
        return "deny", f"issueIdOrKey must be {key}"
    if args.get("cloudId") != site:
        return "deny", f"cloudId must be {site}"
    problem = args_problem(args, exp)
    if problem:
        return "deny", problem
    if exp.get("body_file"):
        with open(os.path.join(cwd, exp["body_file"]), "rb") as fh:
            want = fh.read().decode("utf-8")
        got = arg_at(args, exp["body_arg"])
        if not isinstance(got, str) or got.rstrip("\n") != want.rstrip("\n"):
            return "deny", f"{exp['body_arg']} differs from {exp['body_file']}"
    if earlier_allowed(os.path.join(cwd, "hook.log"), name, data.get("toolCallId")):
        return "deny", f"{tool} was already called once"
    return "allow", ""


def main():
    data, cwd = {}, os.getcwd()
    try:
        parsed = json.loads(sys.stdin.buffer.read().decode("utf-8"))
        if not isinstance(parsed, dict):
            raise ValueError("the hook input is not a JSON object")
        data = parsed
        cwd = data.get("cwd") or cwd
        decision, why = check(data, cwd)
    except Exception as e:  # noqa: BLE001 - any error denies, including a missing or broken af-expect.json
        decision, why = "deny", f"denied after an error ({e.__class__.__name__})"
    try:
        with open(os.path.join(cwd, "hook.log"), "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"toolCallId": data.get("toolCallId"), "toolName": data.get("toolName"),
                                 "decision": decision}) + "\n")
    except Exception:  # noqa: BLE001 - the decision counts, not the log
        pass
    # A guard that can't print can't deny: if stdout fails, Copilot runs the call (fail open). The check afterwards
    # from the events (agentic-factory.py check_jira_call) is the backstop.
    if decision != "allow":
        print(json.dumps({"permissionDecision": "deny", "permissionDecisionReason": PREFIX + why}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
