"""Tests for agentic_factory/jira_mcp.py: the guard hook, the check of a Jira call from its events, the read-back, and
JiraMcp with a fake copilot.

Event fixtures copy the structure of real Copilot 1.0.115 events; the data is invented.
"""
import ast
import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from agentic_factory import config, copilot, jira_mcp
from .fakes import CFG, FULL_CFG, HERE, ev_line, start


# --- Jira over MCP --------------------------------------------------------------------------------------------------
# Event fixtures copy the structure of real Copilot 1.0.115 events (session.start, tool.execution_start/complete paired
# by toolCallId, result.content with a cost suffix, result.detailedContent without it). The data is invented.

GUARD = HERE / "agentic-factory-plugin" / "hooks" / "guard.py"
SITE = "https://example.atlassian.net"
MKEY = "LL-123"
COST = "\n\n[cost: 8% used · $0.28 left]"


def guard_run(cwd, payload, raw=None):
    """Run guard.py like Copilot does: hook input JSON on stdin. Returns (decision, stdout)."""
    stdin = raw if raw is not None else json.dumps(payload)
    out = subprocess.run([sys.executable, "-I", str(GUARD)], input=stdin.encode("utf-8"), cwd=cwd,
                         capture_output=True, timeout=30)
    if out.returncode != 0 or out.stderr:  # a crashing guard prints nothing, which would look like an allow
        raise AssertionError(f"guard.py exited {out.returncode}: {out.stderr.decode('utf-8', 'replace')}")
    text = out.stdout.decode("utf-8").strip()
    if not text:
        return "allow", text
    d = json.loads(text)
    return d.get("permissionDecision"), d


def complete(cid, raw, ok=True):
    if not ok:
        return ev_line("tool.execution_complete", toolCallId=cid, success=False,
                       error={"code": "failure", "message": raw})
    return ev_line("tool.execution_complete", toolCallId=cid, success=True,
                   result={"content": raw + COST, "detailedContent": raw})


def write_events(path, lines, version="1.0.115"):
    head = [ev_line("session.start", sessionId="s-1", copilotVersion=version, context={"cwd": str(path.parent)}),
            "this line is not JSON (stderr)"]
    tail = [ev_line("assistant.message", content="done"),
            json.dumps({"type": "result", "exitCode": 0, "usage": {"premiumRequests": 1}})]
    path.write_text("\n".join(head + lines + tail) + "\n", encoding="utf-8")
    return path


COMMENT_RAW = json.dumps({"self": "https://api.atlassian.com/ex/jira/x/rest/api/3/issue/10001/comment/10100",
                          "id": "10100", "body": "\\[KI\\] Hallo _Welt_\n", "created": "2026-11-24T22:12:56.692+0100"})
SEARCH = ("toolu_s", "tool_search_tool", {"pattern": "addCommentToJiraIssue"})
POST = "atlassian-addCommentToJiraIssue"
READ_FIELDS = ["summary", "description", "labels", "status", "comment"]
ARG_RULES = {  # what agentic-factory.py writes to af-expect.json for each tool: args, fields_list, fields_keys
    "atlassian-getJiraIssue": {"args": ["cloudId", "issueIdOrKey", "fields"], "fields_list": READ_FIELDS,
                               "fields_keys": None},
    POST: {"args": ["cloudId", "issueIdOrKey", "commentBody"], "fields_list": None, "fields_keys": None},
    "atlassian-editJiraIssue": {"args": ["cloudId", "issueIdOrKey", "fields"], "fields_list": None,
                                "fields_keys": ["description"]}}


def expect_for(tool, body_file=None, body_arg=None):
    return {"tool": tool, "key": MKEY, "site": SITE, "body_file": body_file, "body_arg": body_arg, **ARG_RULES[tool]}


class Hook(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp(prefix="af-hook-"))
        self.addCleanup(shutil.rmtree, self.d, True)

    def expect(self, tool="atlassian-getJiraIssue", body=None, body_arg=None):
        if body is not None:
            (self.d / "comment.txt").write_bytes(body.encode("utf-8"))
        (self.d / "af-expect.json").write_text(json.dumps(expect_for(
            tool, "comment.txt" if body is not None else None, body_arg)), encoding="utf-8")

    def payload(self, tool, args, cid="toolu_1"):
        return {"sessionId": "s", "timestamp": 1795554735284, "cwd": str(self.d), "toolCallId": cid,
                "toolName": tool, "toolArgs": args}

    def read_args(self, **over):
        return {"cloudId": SITE, "issueIdOrKey": MKEY, "fields": list(reversed(READ_FIELDS)), **over}

    def test_allows_tool_search(self):
        self.expect()
        self.assertEqual(guard_run(self.d, self.payload("tool_search_tool", {"pattern": "getJiraIssue"}))[0], "allow")

    def test_allows_the_expected_read(self):
        self.expect()
        self.assertEqual(guard_run(self.d, self.payload("atlassian-getJiraIssue", self.read_args()))[0], "allow")

    def test_denies_another_key(self):
        self.expect()
        dec, out = guard_run(self.d, self.payload("atlassian-getJiraIssue", self.read_args(issueIdOrKey="LL-124")))
        self.assertEqual(dec, "deny")
        self.assertTrue(out["permissionDecisionReason"].startswith("agentic-factory-guard: "))

    def test_denies_another_cloud_id(self):
        self.expect()
        args = self.read_args(cloudId="https://evil.example.net")
        self.assertEqual(guard_run(self.d, self.payload("atlassian-getJiraIssue", args))[0], "deny")

    def test_post_body_equal_ignoring_trailing_newline(self):
        body = "[KI] Hallo\n\nZeile *zwei* ä\n"
        self.expect("atlassian-addCommentToJiraIssue", body, "commentBody")
        args = {"cloudId": SITE, "issueIdOrKey": MKEY, "commentBody": body.rstrip("\n")}
        self.assertEqual(guard_run(self.d, self.payload("atlassian-addCommentToJiraIssue", args))[0], "allow")

    def test_post_body_one_character_differs(self):
        body = "[KI] Hallo\n\nZeile zwei\n"
        self.expect("atlassian-addCommentToJiraIssue", body, "commentBody")
        args = {"cloudId": SITE, "issueIdOrKey": MKEY, "commentBody": "[KI] Hallo\n\nZeile zwel"}
        self.assertEqual(guard_run(self.d, self.payload("atlassian-addCommentToJiraIssue", args))[0], "deny")
        args.pop("commentBody")
        self.assertEqual(guard_run(self.d, self.payload("atlassian-addCommentToJiraIssue", args))[0], "deny")

    def test_denies_extra_arguments(self):
        self.expect("atlassian-addCommentToJiraIssue", "[KI] x\n", "commentBody")
        args = {"cloudId": SITE, "issueIdOrKey": MKEY, "commentBody": "[KI] x", "visibility": {"type": "role"}}
        self.assertEqual(guard_run(self.d, self.payload(POST, args))[0], "deny")
        self.expect("atlassian-editJiraIssue", "Neu\n", "fields.description")
        args = {"cloudId": SITE, "issueIdOrKey": MKEY, "fields": {"description": "Neu", "labels": []}}
        dec, out = guard_run(self.d, self.payload("atlassian-editJiraIssue", args))
        self.assertEqual(dec, "deny")
        self.assertIn("description", out["permissionDecisionReason"])
        self.expect()
        for fields in (READ_FIELDS[:-1], READ_FIELDS + ["assignee"], READ_FIELDS + ["comment"], "summary,comment"):
            with self.subTest(fields=fields):
                dec, _ = guard_run(self.d, self.payload("atlassian-getJiraIssue", self.read_args(fields=fields)))
                self.assertEqual(dec, "deny")
        dec, _ = guard_run(self.d, self.payload("atlassian-getJiraIssue", self.read_args(expand="changelog")))
        self.assertEqual(dec, "deny")

    def test_live_hook_input_shape(self):
        """The keys Copilot 1.0.114 sent live: cwd, sessionId, timestamp, toolArgs (an object), toolCallId,
        toolName."""
        self.expect()
        payload = {"sessionId": "8e5", "timestamp": 1795554736382, "cwd": str(self.d), "toolCallId": "toolu_01Q",
                   "toolName": "atlassian-getJiraIssue", "toolArgs": self.read_args()}
        self.assertEqual(guard_run(self.d, payload)[0], "allow")

    def test_dotted_body_path(self):
        self.expect("atlassian-editJiraIssue", "## Ziel\n\nText\n", "fields.description")
        args = {"cloudId": SITE, "issueIdOrKey": MKEY, "fields": {"description": "## Ziel\n\nText"}}
        self.assertEqual(guard_run(self.d, self.payload("atlassian-editJiraIssue", args))[0], "allow")
        args["fields"]["description"] = "## Ziel\n\nTest"
        self.assertEqual(guard_run(self.d, self.payload("atlassian-editJiraIssue", args))[0], "deny")
        args["fields"] = "## Ziel\n\nText"
        self.assertEqual(guard_run(self.d, self.payload("atlassian-editJiraIssue", args))[0], "deny")

    def test_denies_other_tools(self):
        self.expect()
        for tool, args in (("create", {"path": "x"}), ("bash", {"command": "ls"}), ("view", {"path": "/"}),
                           ("atlassian-addCommentToJiraIssue", {"cloudId": SITE, "issueIdOrKey": MKEY,
                                                                "commentBody": "x"}),
                           ("atlassian-getAccessibleAtlassianResources", {}),
                           ("other-getJiraIssue", self.read_args())):
            with self.subTest(tool=tool):
                self.assertEqual(guard_run(self.d, self.payload(tool, args))[0], "deny")

    def test_denies_without_expect_file(self):
        self.assertEqual(guard_run(self.d, self.payload("atlassian-getJiraIssue", self.read_args()))[0], "deny")
        self.assertEqual(guard_run(self.d, self.payload("tool_search_tool", {"pattern": "x"}))[0], "deny")

    def test_denies_with_broken_expect_file(self):
        for broken in ("{not json", "[]", json.dumps({"tool": "atlassian-getJiraIssue"})):
            with self.subTest(broken=broken):
                (self.d / "af-expect.json").write_text(broken, encoding="utf-8")
                self.assertEqual(guard_run(self.d, self.payload("atlassian-getJiraIssue", self.read_args()))[0],
                                 "deny")

    def test_denies_non_json_stdin(self):
        self.expect()
        self.assertEqual(guard_run(self.d, None, raw="this is not json")[0], "deny")
        self.assertEqual(guard_run(self.d, None, raw="[1, 2]")[0], "deny")

    def test_denies_a_second_call_of_the_tool(self):
        self.expect()
        self.assertEqual(guard_run(self.d, self.payload("atlassian-getJiraIssue", self.read_args(), "t1"))[0], "allow")
        self.assertEqual(guard_run(self.d, self.payload("atlassian-getJiraIssue", self.read_args(), "t2"))[0], "deny")

    def test_hook_log_written(self):
        self.expect()
        guard_run(self.d, self.payload("tool_search_tool", {"pattern": "x"}, "toolu_a"))
        guard_run(self.d, self.payload("bash", {"command": "ls"}, "toolu_b"))
        lines = [json.loads(x) for x in (self.d / "hook.log").read_text(encoding="utf-8").splitlines()]
        self.assertEqual(lines, [{"toolCallId": "toolu_a", "toolName": "tool_search_tool", "decision": "allow"},
                                 {"toolCallId": "toolu_b", "toolName": "bash", "decision": "deny"}])

    def test_hooks_json(self):
        d = json.loads((HERE / "agentic-factory-plugin" / "hooks" / "hooks.json").read_text(encoding="utf-8"))
        self.assertEqual(d, {"version": 1, "hooks": {"preToolUse": [{
            "type": "command", "bash": "python3 -I \"$AF_GUARD_ROOT/hooks/guard.py\"",
            "env": {"AF_GUARD_ROOT": "${PLUGIN_ROOT}"}, "timeoutSec": 10}]}})
        p = json.loads((HERE / "agentic-factory-plugin" / "plugin.json").read_text(encoding="utf-8"))
        self.assertTrue(p["name"])


def function_without_docstring(path, name):
    """ast.dump of the top-level def `name` in the Python file at path, renamed to f, without its docstring. The file
    is parsed, not imported. None when there is no such def."""
    tree = ast.parse(Path(path).read_text(encoding="utf-8"))
    fn = next((n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name), None)
    if fn is None:
        return None
    first = fn.body[0] if fn.body else None
    if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
        fn.body = fn.body[1:]
    fn.name = "f"
    return ast.dump(fn)


class GuardParity(unittest.TestCase):
    """guard.py keeps its own copy of the argument check: it runs as a hook, without the package."""

    def test_argument_check_equals_jira_args_problem(self):
        theirs = function_without_docstring(GUARD, "args_problem")
        ours = function_without_docstring(HERE / "agentic_factory" / "jira_mcp.py", "jira_args_problem")
        self.assertIsNotNone(theirs, "guard.py has no args_problem")
        self.assertIsNotNone(ours, "jira_mcp.py has no jira_args_problem")
        self.assertEqual(theirs, ours, "guard.py's copy of the argument check drifted from jira_mcp.jira_args_problem")


class McpEvents(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp(prefix="af-ev-"))
        self.addCleanup(shutil.rmtree, self.d, True)
        self.out = io.StringIO()

    def post_expect(self, body="[KI] Hallo *Welt*\n"):
        (self.d / "comment.txt").write_bytes(body.encode("utf-8"))
        return expect_for(POST, "comment.txt", "commentBody")

    def post_args(self, **over):
        return {"cloudId": SITE, "issueIdOrKey": MKEY, "commentBody": "[KI] Hallo *Welt*", **over}

    def check(self, lines, expect, hook=None):
        ev = copilot.mcp_events(write_events(self.d / "events.jsonl", lines))
        if hook is not None:
            (self.d / "hook.log").write_text("".join(json.dumps(h) + "\n" for h in hook), encoding="utf-8")
        with contextlib.redirect_stdout(self.out):
            return jira_mcp.check_jira_call(ev, expect, self.d / "hook.log")

    def test_pairs_by_id_and_uses_detailed_content(self):
        lines = [start("a", "tool_search_tool", {"pattern": "x"}), start("b", "atlassian-getJiraIssue", {"k": 1}),
                 complete("b", '{"id": "2"}'), complete("a", "found x"), start("c", "bash", {"command": "ls"}),
                 start("d", "bash", {"command": "rm"}),
                 ev_line("tool.execution_complete", toolCallId="d", success=False,
                         error={"code": "denied", "message": "denied"})]
        ev = copilot.mcp_events(write_events(self.d / "events.jsonl", lines, version="1.0.999"))
        self.assertEqual(ev["version"], "1.0.999")
        self.assertEqual(ev["calls"], [
            {"id": "a", "tool": "tool_search_tool", "args": {"pattern": "x"}, "ok": True, "raw": "found x",
             "denied": False},
            {"id": "b", "tool": "atlassian-getJiraIssue", "args": {"k": 1}, "ok": True, "raw": '{"id": "2"}',
             "denied": False},
            {"id": "c", "tool": "bash", "args": {"command": "ls"}, "ok": False, "raw": None, "denied": False},
            {"id": "d", "tool": "bash", "args": {"command": "rm"}, "ok": False, "raw": None, "denied": True}])
        self.assertNotIn("[cost:", json.dumps(ev))

    def raw_of(self, result):
        lines = [start("a", "atlassian-getJiraIssue", {"k": 1}),
                 ev_line("tool.execution_complete", toolCallId="a", success=True, result=result)]
        return copilot.mcp_events(write_events(self.d / "events.jsonl", lines))["calls"][0]["raw"]

    def test_raw_is_contents_when_detailed_content_is_truncated(self):  # Copilot 1.0.115 cuts it at about 10 KB
        full = json.dumps({"id": "10001", "key": MKEY, "fields": {"comment": {"comments": [
            {"id": str(10000 + i), "body": "Beispieltext " * 40} for i in range(30)]}}}, indent=2)
        self.assertGreater(len(full), 10300)
        res = {"content": full + COST, "detailedContent": full[:10299], "contents": [{"type": "text", "text": full}]}
        self.assertIsNone(jira_mcp.raw_json(res["detailedContent"]))
        raw = self.raw_of(res)
        self.assertEqual(raw, full)
        self.assertEqual(jira_mcp.raw_json(raw)["key"], MKEY)

    def test_raw_joins_text_items_in_order_and_skips_others(self):
        res = {"content": "ab" + COST, "detailedContent": "ab",
               "contents": [{"type": "text", "text": "a"}, {"type": "image", "data": "xx", "mimeType": "image/png"},
                            {"type": "text", "text": "b"}]}
        self.assertEqual(self.raw_of(res), "ab")
        res["detailedContent"] = "something else"
        self.assertEqual(self.raw_of(res), "ab")

    def test_raw_is_detailed_content_without_contents(self):
        self.assertEqual(self.raw_of({"content": "x" + COST, "detailedContent": "x"}), "x")

    def test_raw_falls_back_when_contents_has_no_text(self):
        for contents in ([], [{"type": "image", "data": "xx"}], [{"type": "text", "text": 5}, "x", None], "text"):
            with self.subTest(contents=contents):
                self.assertEqual(self.raw_of({"content": "x" + COST, "detailedContent": "dc", "contents": contents}),
                                 "dc")
        self.assertIsNone(self.raw_of({"content": "x" + COST, "contents": []}))

    def test_ok_returns_parsed_raw_and_warns_without_hook(self):
        lines = [start(*SEARCH), complete("toolu_s", "found"),
                 start("toolu_p", POST, self.post_args()), complete("toolu_p", COMMENT_RAW)]
        raw = self.check(lines, self.post_expect())
        self.assertEqual(raw["id"], "10100")
        self.assertIn("WARNING: Copilot 1.0.115 ran no plugin hook for this Jira call; checked afterwards from the "
                      "events instead", self.out.getvalue())

    def test_no_warning_when_hook_ran(self):
        lines = [start("toolu_p", POST, self.post_args()), complete("toolu_p", COMMENT_RAW)]
        self.check(lines, self.post_expect(),
                   hook=[{"toolCallId": "toolu_p", "toolName": "atlassian-addCommentToJiraIssue", "decision": "allow"}])
        self.assertNotIn("WARNING", self.out.getvalue())

    def test_other_tool_stops_and_names_the_comment(self):
        lines = [start("toolu_p", POST, self.post_args()), complete("toolu_p", COMMENT_RAW),
                 start("toolu_x", "atlassian-getJiraIssue", {"cloudId": SITE, "issueIdOrKey": "LL-9"}),
                 complete("toolu_x", "{}")]
        with self.assertRaisesRegex(config.Stop, r"atlassian-getJiraIssue.* — delete comment 10100 on LL-123 by hand$"):
            self.check(lines, self.post_expect())

    def test_other_tool_on_a_read_stops(self):
        expect = expect_for("atlassian-getJiraIssue")
        lines = [start("r", "atlassian-getJiraIssue", {"cloudId": SITE, "issueIdOrKey": MKEY}), complete("r", "{}"),
                 start("b", "bash", {"command": "ls"})]
        with self.assertRaisesRegex(config.Stop, "bash") as cm:
            self.check(lines, expect)
        self.assertNotIn("delete comment", str(cm.exception))

    def test_not_exactly_one_call(self):
        with self.assertRaisesRegex(config.Stop, "0 calls"):
            self.check([start(*SEARCH), complete("toolu_s", "found")], self.post_expect())
        lines = [start("p1", "atlassian-addCommentToJiraIssue", self.post_args()), complete("p1", COMMENT_RAW),
                 start("p2", "atlassian-addCommentToJiraIssue", self.post_args()),
                 complete("p2", COMMENT_RAW.replace("10100", "10101"))]
        with self.assertRaisesRegex(config.Stop, "2 calls.*delete comments? 10100, 10101 on LL-123 by hand$"):
            self.check(lines, self.post_expect())

    def test_wrong_key_or_site(self):
        for over in ({"issueIdOrKey": "LL-124"}, {"cloudId": "https://other.atlassian.net"}):
            with self.subTest(over=over):
                lines = [start("p", "atlassian-addCommentToJiraIssue", self.post_args(**over)),
                         complete("p", COMMENT_RAW)]
                with self.assertRaisesRegex(config.Stop, "delete comment 10100 on LL-123 by hand$"):
                    self.check(lines, self.post_expect())

    def test_body_differs(self):
        lines = [start("p", "atlassian-addCommentToJiraIssue", self.post_args(commentBody="[KI] Hallo *Welt!*")),
                 complete("p", COMMENT_RAW)]
        with self.assertRaisesRegex(config.Stop, "body.* — delete comment 10100 on LL-123 by hand$"):
            self.check(lines, self.post_expect())

    def test_failed_call_stops(self):
        lines = [start("p", "atlassian-addCommentToJiraIssue", self.post_args()), complete("p", "boom", ok=False)]
        with self.assertRaisesRegex(config.Stop, "failed.* — look for a new comment on LL-123 and delete it by hand$"):
            self.check(lines, self.post_expect())
        lines = [start("p", "atlassian-addCommentToJiraIssue", self.post_args())]  # no complete: killed, say
        with self.assertRaisesRegex(config.Stop, "look for a new comment on LL-123"):
            self.check(lines, self.post_expect())
        (self.d / "d.md").write_text("Neu\n", encoding="utf-8")
        args = {"cloudId": SITE, "issueIdOrKey": MKEY, "fields": {"description": "Neu"}}
        lines = [start("e", "atlassian-editJiraIssue", args), complete("e", "boom", ok=False)]
        with self.assertRaisesRegex(config.Stop, "failed.* — check the description of LL-123 by hand$"):
            self.check(lines, expect_for("atlassian-editJiraIssue", "d.md", "fields.description"))

    def test_extra_arguments_stop(self):
        lines = [start("p", POST, self.post_args(visibility={"type": "role", "value": "x"})),
                 complete("p", COMMENT_RAW)]
        with self.assertRaisesRegex(config.Stop, "visibility.* — delete comment 10100 on LL-123 by hand$"):
            self.check(lines, self.post_expect())
        (self.d / "d.md").write_text("Neu\n", encoding="utf-8")
        args = {"cloudId": SITE, "issueIdOrKey": MKEY, "fields": {"description": "Neu", "summary": "Anders"}}
        lines = [start("e", "atlassian-editJiraIssue", args), complete("e", "{}")]
        with self.assertRaisesRegex(config.Stop, "description.* — the description of LL-123 was changed"):
            self.check(lines, expect_for("atlassian-editJiraIssue", "d.md", "fields.description"))
        args = {"cloudId": SITE, "issueIdOrKey": MKEY, "fields": ["summary", "comment"]}
        lines = [start("r", "atlassian-getJiraIssue", args), complete("r", "{}")]
        with self.assertRaisesRegex(config.Stop, "fields must be exactly"):
            self.check(lines, expect_for("atlassian-getJiraIssue"))

    def test_denied_other_tool_is_only_a_note(self):
        lines = [start("b", "bash", {"command": "curl x"}),
                 ev_line("tool.execution_complete", toolCallId="b", success=False,
                         error={"code": "denied", "message": "denied"}),
                 start("p", POST, self.post_args()), complete("p", COMMENT_RAW)]
        self.assertEqual(self.check(lines, self.post_expect())["id"], "10100")
        self.assertIn("note: Copilot denied bash", self.out.getvalue())
        lines[1] = ev_line("tool.execution_complete", toolCallId="b", success=False,
                           error={"code": "failure", "message": "exit 1"})
        with self.assertRaisesRegex(config.Stop, "bash.* — delete comment 10100"):
            self.check(lines, self.post_expect())

    def test_unknown_version_in_warning(self):
        path = self.d / "events.jsonl"
        path.write_text("\n".join([start("p", POST, self.post_args()), complete("p", COMMENT_RAW)]) + "\n",
                        encoding="utf-8")
        with contextlib.redirect_stdout(self.out):
            jira_mcp.check_jira_call(copilot.mcp_events(path), self.post_expect(), self.d / "hook.log")
        self.assertIn("WARNING: Copilot (unknown version) ran no plugin hook", self.out.getvalue())

    def test_dotted_body_arg(self):
        (self.d / "d.md").write_text("Neu\n", encoding="utf-8")
        expect = expect_for("atlassian-editJiraIssue", "d.md", "fields.description")
        args = {"cloudId": SITE, "issueIdOrKey": MKEY, "fields": {"description": "Neu"}}
        self.assertEqual(self.check([start("e", "atlassian-editJiraIssue", args), complete("e", '{"key": "LL-123"}')],
                                    expect), {"key": "LL-123"})
        args["fields"]["description"] = "Alt"
        with self.assertRaisesRegex(config.Stop, "description of LL-123"):
            self.check([start("e", "atlassian-editJiraIssue", args), complete("e", "{}")], expect)


class Readback(unittest.TestCase):
    def test_md_unescape(self):
        self.assertEqual(jira_mcp.md_unescape("\\[KI\\] a\\_b \\*c\\* \\\\ \\a"), "[KI] a_b *c* \\ \\a")
        self.assertEqual(jira_mcp.md_unescape("x\n```\n\\[raw\\]\n```\n\\[y\\]"), "x\n```\n\\[raw\\]\n```\n[y]")

    def test_norm(self):
        self.assertEqual(jira_mcp.readback_norm("# Titel\n\n- *eins*\n2. `zwei`\n> drei\n```\ncode\n```\n"),
                         "Titel eins zwei drei code")

    def test_readback_tolerates_marks(self):  # Review Focus 1
        sent = ("[KI] Frage 1: Soll die Suche *Titel* und _Zusammenfassung_ durchsuchen? "
                "https://example.com/suche?q=a&b=1\n\n1. Treffer zuerst\n\n```\n# x\n- y `z`\n```")
        stored = sent.replace("[KI]", "\\[KI\\]").replace("*Titel*", "_Titel_")
        self.assertTrue(jira_mcp.readback_matches(sent, stored))
        self.assertFalse(jira_mcp.readback_matches(sent, stored.replace("Treffer", "Treffen")))


FAKE_JIRA_COPILOT = r'''
import json, pathlib, re, sys
argv = sys.argv[1:]
here = pathlib.Path(__file__).parent
if argv[:2] == ["mcp", "list"]:
    names = json.loads((here / "fake-servers.json").read_text()) if (here / "fake-servers.json").exists() \
        else ["atlassian", "github-mcp-server"]
    print(json.dumps({"mcpServers": {n: {"type": "http", "headers": {"Authorization": "Bearer not-a-real-token-1"}}
                                     for n in names}}))
    sys.exit(0)
with open(here / "calls.jsonl", "a") as fh: fh.write(json.dumps({"argv": argv, "cwd": str(pathlib.Path.cwd())}) + "\n")
prompt = argv[argv.index("-p") + 1]
usage = next(a.split("=", 1)[1] for a in argv if a.startswith("--usage-output-file="))
mode = (here / "fake-jira-mode").read_text().strip() if (here / "fake-jira-mode").exists() else "normal"
allowed = [a.split("=", 1)[1] for a in argv if a.startswith("--allow-tool=")]
server, tool = re.fullmatch(r"([^()]+)\((\w+)\)", allowed[0]).groups()
state_file = here / "fake-jira.json"
state = json.loads(state_file.read_text(encoding="utf-8"))
seq = [0]
def ev(t, **d): print(json.dumps({"type": t, "data": d}), flush=True)
def call(name, args, raw):
    seq[0] += 1
    cid = "toolu_fake%02d" % seq[0]
    srv, _, bare = name.partition("-")
    ev("tool.execution_start", toolCallId=cid, toolName=name, arguments=args,
       **({"mcpServerName": srv, "mcpToolName": bare} if bare else {}))
    res = {"content": raw + "\n\n[cost: 8% used · $0.28 left]", "detailedContent": raw}
    if mode == "truncated":  # Copilot 1.0.115: detailedContent cut at about 10 KB, contents complete
        res["detailedContent"] = raw[:10299]
        res["contents"] = [{"type": "text", "text": raw}]
    ev("tool.execution_complete", toolCallId=cid, success=True, result=res)
def md(s):  # what the Atlassian server sends back: [ ] escaped, *x* as _x_
    s = re.sub(r"(?<![*\w])\*([^*\s][^*\n]*?)\*(?![*\w])", r"_\1_", s)
    return s.replace("[", "\\[").replace("]", "\\]")
ev("session.start", sessionId="fake", copilotVersion="1.0.115", context={"cwd": str(pathlib.Path.cwd())})
call("tool_search_tool", {"pattern": tool}, "Tool search for '%s': found %s-%s" % (tool, server, tool))
arg = lambda name: re.search(name + r' "([^"]*)"', prompt).group(1)
args = {"cloudId": arg("cloudId"), "issueIdOrKey": arg("issueIdOrKey")}
key = args["issueIdOrKey"]
issue = state["issues"][key]
body = prompt.split("\nBEGIN-BODY\n", 1)[1].rsplit("\nEND-BODY", 1)[0] if "\nBEGIN-BODY\n" in prompt else None
if tool == "getJiraIssue":
    args["fields"] = ["summary", "description", "labels", "status", "comment"]
    raw = {"id": "10001", "key": key, "fields": {"summary": issue["summary"], "description": issue["description"],
           "labels": issue["labels"], "status": {"name": issue["status"]}, "comment": {"comments": issue["comments"]}},
           "comments": issue["comments"]}
elif tool == "addCommentToJiraIssue":
    sent = body + " (vom Modell ergänzt)" if mode == "altered-body" else body
    args["commentBody"] = sent
    stored = sent.replace("Frage", "Antwort") if mode == "altered-stored" else sent
    cid = str(state["next_id"]); state["next_id"] += 1
    c = {"id": cid, "body": md(stored) + "\n", "created": "2026-11-24T22:12:56.692+0100",
         "updated": "2026-11-24T22:12:56.692+0100", "author": {"accountId": "000000:fake", "displayName": "Fake"}}
    issue["comments"].append(c)
    raw = {"self": "https://api.atlassian.com/ex/jira/fake/rest/api/3/issue/10001/comment/" + cid, **c}
elif tool == "editJiraIssue":
    args["fields"] = {"description": body}
    issue["description"] = md(body + " extra" if mode == "altered-stored" else body)
    raw = {"id": "10001", "key": key}
call("%s-%s" % (server, tool), args, json.dumps(raw, ensure_ascii=False))
if mode == "extra-call":
    call("%s-getAccessibleAtlassianResources" % server, {}, "[]")
state_file.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
ev("assistant.message", content="done")
pathlib.Path(usage).write_text(json.dumps({"totalNanoAiu": 4000000000}))
'''


class JiraMcp(unittest.TestCase):
    """JiraMcp with a fake copilot that answers like Copilot with the Atlassian MCP server. It runs no hook."""
    SERVERS = ["atlassian", "github-mcp-server", "jira-cloud"]

    def setUp(self):
        self.d = Path(tempfile.mkdtemp(prefix="af-mcp-"))
        self.addCleanup(shutil.rmtree, self.d, True)
        (self.d / "fake.py").write_text(FAKE_JIRA_COPILOT, encoding="utf-8")
        (self.d / "fake-servers.json").write_text(json.dumps(self.SERVERS), encoding="utf-8")
        (self.d / "fake-jira.json").write_text(json.dumps({"next_id": 10100, "issues": {MKEY: {
            "summary": "Suche verbessern", "description": "Die Suche soll \\[Titel\\] finden.\n\n- eins\n",
            "labels": ["sdd-openspec"], "status": "Definition",
            "comments": [{"id": "10050", "body": "\\[Mensch\\] 1 ok\n", "created": "2026-11-24T23:00:00.000+0100"},
                         {"id": "10040", "body": "\\[KI\\] agentic-factory klärung runde=1 key=LL-123\n",
                          "created": "2026-11-24T22:12:56.692+0100", "updated": "2026-11-24T22:12:56.692+0100",
                          "author": {"accountId": "000000:bot", "displayName": "Bot"}}]}}}), encoding="utf-8")
        self.local = {"copilot": [sys.executable, "-I", str(self.d / "fake.py")], "jira_site": SITE}
        self.logdir = self.d / "logs"
        self.logdir.mkdir()
        self.out = io.StringIO()

    def mode(self, m):
        (self.d / "fake-jira-mode").write_text(m, encoding="utf-8")

    def jira(self, local=None):
        local = self.local if local is None else local
        return jira_mcp.JiraMcp(CFG, local, copilot.resolve_copilot(local), dict(os.environ), self.logdir,
                          HERE / "agentic-factory-plugin")

    def run_quiet(self, fn, *args):
        with contextlib.redirect_stdout(self.out):
            return fn(*args)

    def calls(self):
        p = self.d / "calls.jsonl"
        return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines()] if p.exists() else []

    def state(self):
        return json.loads((self.d / "fake-jira.json").read_text(encoding="utf-8"))

    def test_mcp_check_missing_server_stops(self):
        (self.d / "fake-servers.json").write_text(json.dumps(["github-mcp-server"]), encoding="utf-8")
        with self.assertRaisesRegex(config.Stop, "atlassian"):
            self.run_quiet(self.jira().read, MKEY)
        self.assertEqual(self.calls(), [])
        with self.assertRaisesRegex(config.Stop, "atlassian"):
            jira_mcp.mcp_check(copilot.resolve_copilot(self.local), "atlassian", self.d, dict(os.environ))
        self.assertEqual(jira_mcp.mcp_check(copilot.resolve_copilot(self.local), "github-mcp-server", self.d, dict(os.environ)),
                         ["github-mcp-server"])

    def test_read_parses_markdown_and_unescapes(self):
        ticket, comments = self.run_quiet(self.jira().read, MKEY)
        self.assertEqual(ticket, {"key": MKEY, "summary": "Suche verbessern", "labels": ["sdd-openspec"],
                                  "description": "Die Suche soll [Titel] finden.\n\n- eins"})
        self.assertEqual(comments, [
            {"id": "10040", "created": "2026-11-24T21:12:56.692Z", "updated": "2026-11-24T21:12:56.692Z",
             "author": "000000:bot", "body": "[KI] agentic-factory klärung runde=1 key=LL-123\n"},
            {"id": "10050", "created": "2026-11-24T22:00:00.000Z", "updated": "", "author": "", "body": "[Mensch] 1 ok\n"}])
        (call,) = self.calls()
        self.assertEqual(Path(call["cwd"]).resolve(), (self.logdir / "jira-1-getJiraIssue").resolve())
        self.assertIn("ran no plugin hook", self.out.getvalue())

    def test_jira_calls_get_no_team_rules(self):
        j = jira_mcp.JiraMcp(FULL_CFG, self.local, copilot.resolve_copilot(self.local), dict(os.environ), self.logdir,
                             HERE / "agentic-factory-plugin")
        self.run_quiet(j.read, MKEY)
        self.run_quiet(j.add_comment, MKEY, "[KI] agentic-factory klärung runde=2 key=LL-123\n\nFrage 1: Welche Seite?\n")
        self.run_quiet(j.set_description, MKEY, "Neu\n")
        prompts = [c["argv"][c["argv"].index("-p") + 1] for c in self.calls()]
        self.assertGreaterEqual(len(prompts), 3)
        for p in prompts:
            self.assertNotIn("TEAM RULES", p)
            self.assertNotIn("team_rules", p)
            self.assertNotIn("regeln/", p)

    def test_read_long_ticket_with_truncated_detailed_content(self):
        st = self.state()
        st["issues"][MKEY]["comments"] = [
            {"id": str(10200 + i), "body": "\\[Mensch\\] %d " % i + "Beispieltext " * 60,
             "created": "2026-11-24T23:00:00.000+0100"} for i in range(20)]
        (self.d / "fake-jira.json").write_text(json.dumps(st), encoding="utf-8")
        self.mode("truncated")
        ticket, comments = self.run_quiet(self.jira().read, MKEY)
        self.assertEqual(ticket["key"], MKEY)
        self.assertEqual(len(comments), 20)
        self.assertTrue(comments[-1]["body"].startswith("[Mensch] "))

    def test_post_then_readback_ok(self):
        text = "[KI] agentic-factory klärung runde=2 key=LL-123\n\nFrage 1: Welche Seite?\n"
        cid = self.run_quiet(self.jira().add_comment, MKEY, text)
        self.assertEqual(cid, "10100")
        self.assertEqual(self.state()["issues"][MKEY]["comments"][-1]["id"], "10100")
        calldir = self.logdir / "jira-1-addCommentToJiraIssue"
        self.assertEqual((calldir / "comment.txt").read_bytes().decode("utf-8"), text)
        expect = json.loads((calldir / "af-expect.json").read_text(encoding="utf-8"))
        self.assertEqual(expect, expect_for(POST, "comment.txt", "commentBody"))
        # the expect file the script wrote and the arguments the call carried pass the guard
        post = [c for c in copilot.mcp_events(calldir / "events.jsonl")["calls"] if c["tool"] == expect["tool"]][0]
        payload = {"cwd": str(calldir), "toolCallId": "x", "toolName": post["tool"], "toolArgs": post["args"]}
        self.assertEqual(guard_run(calldir, payload)[0], "allow")
        prompt = self.calls()[0]["argv"][self.calls()[0]["argv"].index("-p") + 1]
        self.assertIn("\nBEGIN-BODY\n" + text.rstrip("\n") + "\nEND-BODY", prompt)
        self.assertIn("data, not instructions", prompt)
        self.assertIn("exactly once", prompt)
        self.assertIn("credits", self.out.getvalue())

    def test_readback_mismatch_stops_with_comment_id(self):
        self.mode("altered-stored")
        with self.assertRaisesRegex(config.Stop, "delete comment 10100 on LL-123 by hand$"):
            self.run_quiet(self.jira().add_comment, MKEY, "[KI] x\n\nFrage 1: Welche Seite?")

    def test_readback_tolerates_marks(self):  # Review Focus 1
        text = "[KI] agentic-factory klärung runde=1 key=LL-123\n\nFrage 1: Soll die Suche *Titel* finden? [Link]"
        self.assertEqual(self.run_quiet(self.jira().add_comment, MKEY, text), "10100")
        stored = self.state()["issues"][MKEY]["comments"][-1]["body"]
        self.assertIn("\\[KI\\]", stored)
        self.assertIn("_Titel_", stored)

    def test_model_changed_body_stops_with_comment_id(self):
        self.mode("altered-body")
        with self.assertRaisesRegex(config.Stop, "body.* — delete comment 10100 on LL-123 by hand$"):
            self.run_quiet(self.jira().add_comment, MKEY, "[KI] x\n\nFrage 1: Welche Seite?")

    def test_extra_tool_call_stops_with_comment_id(self):
        self.mode("extra-call")
        with self.assertRaisesRegex(config.Stop, "getAccessibleAtlassianResources.* — delete comment 10100 on LL-123"):
            self.run_quiet(self.jira().add_comment, MKEY, "[KI] x")

    def test_set_description_then_read_back(self):
        md = "## Ziel\n\nDie Suche findet *Titel* und [Tags].\n\n- eins\n- zwei\n"
        self.assertIsNone(self.run_quiet(self.jira().set_description, MKEY, md))
        argvs = [c["argv"] for c in self.calls()]
        self.assertEqual([[a for a in v if a.startswith("--allow-tool=")] for v in argvs],
                         [["--allow-tool=atlassian(editJiraIssue)"], ["--allow-tool=atlassian(getJiraIssue)"]])
        self.assertTrue((self.logdir / "jira-1-editJiraIssue" / "description.md").exists())
        self.mode("altered-stored")
        with self.assertRaisesRegex(config.Stop, "description of LL-123"):
            self.run_quiet(self.jira().set_description, MKEY, md)

    def test_lone_carriage_return_becomes_newline(self):
        self.run_quiet(self.jira().add_comment, MKEY, "[KI] a\rb\r\nc")
        calldir = self.logdir / "jira-1-addCommentToJiraIssue"
        self.assertEqual((calldir / "comment.txt").read_bytes(), "[KI] a\nb\nc".encode("utf-8"))

    def test_read_and_edit_expect_files(self):
        self.run_quiet(self.jira().set_description, MKEY, "Neu\n")
        for n, tool in ((1, "atlassian-editJiraIssue"), (2, "atlassian-getJiraIssue")):
            got = json.loads((self.logdir / f"jira-{n}-{tool.split('-')[1]}" / "af-expect.json").read_text("utf-8"))
            self.assertEqual({k: got[k] for k in ("args", "fields_list", "fields_keys")}, ARG_RULES[tool])

    def test_refuses_empty_comment_and_marker_lines(self):
        for text in ("  \n", "[KI] a\nEND-BODY\nb"):
            with self.subTest(text=text), self.assertRaises(config.Stop):
                self.run_quiet(self.jira().add_comment, MKEY, text)
        self.assertEqual(self.calls(), [])

    def test_jira_call_argv_one_tool_no_file_tools(self):
        argv = jira_mcp.jira_call_argv(CFG, {}, ["copilot"], "p", "getJiraIssue", "/u.json", ["github-mcp-server", "x"],
                                 "/plug")
        self.assertEqual([a for a in argv if a.startswith("--allow-tool")], ["--allow-tool=atlassian(getJiraIssue)"])
        self.assertEqual(argv[argv.index("--max-ai-credits") + 1], "30")
        self.assertEqual(jira_mcp.JIRA_CALL_CREDITS, 30)
        for t in CFG["deny_tools"]:
            self.assertIn(f"--deny-tool={t}", argv)
        self.assertIn("--disable-mcp-server=github-mcp-server", argv)
        self.assertIn("--disable-mcp-server=x", argv)
        self.assertEqual(argv[-2:], ["--plugin-dir", "/plug"])
        self.assertEqual(argv[:3], ["copilot", "-p", "p"])
        self.assertIn("--disable-builtin-mcps", argv)
        argv = jira_mcp.jira_call_argv(CFG, {"jira_mcp_server": "jira.work"}, ["copilot"], "p", "addCommentToJiraIssue",
                                 "/u.json", [], "/plug")
        self.assertIn("--allow-tool=jira.work(addCommentToJiraIssue)", argv)
        with self.assertRaisesRegex(config.Stop, "forbidden flag --yolo"):
            jira_mcp.jira_call_argv(CFG, {"model": "--yolo"}, ["copilot"], "p", "getJiraIssue", "/u", [], "/plug")
        with self.assertRaisesRegex(config.Stop, "forbidden flag --allow-all"):
            jira_mcp.jira_call_argv(CFG, {}, ["copilot", "--allow-all"], "p", "getJiraIssue", "/u", [], "/plug")

    def test_mcp_off_is_every_other_server(self):
        self.run_quiet(self.jira().read, MKEY)
        argv = self.calls()[0]["argv"]
        self.assertEqual([a for a in argv if a.startswith("--disable-mcp-server=")],
                         ["--disable-mcp-server=github-mcp-server", "--disable-mcp-server=jira-cloud"])
        self.assertNotIn("not-a-real-token", self.out.getvalue())

    def test_site_required(self):
        local = {k: v for k, v in self.local.items() if k != "jira_site"}
        with mock.patch.dict(os.environ, {"JIRA_BASE_URL": ""}):
            with self.assertRaisesRegex(config.Stop, "^the mcp route needs jira_site in local.json "
                                                 r"\(your Jira Cloud address\)$"):
                self.jira(local)
        with mock.patch.dict(os.environ, {"JIRA_BASE_URL": SITE + "/"}):
            self.assertEqual(self.jira(local).site, SITE)
        with mock.patch.dict(os.environ, {"JIRA_BASE_URL": "https://jira.example.com/jira"}):
            with self.assertRaisesRegex(config.Stop, "JIRA_BASE_URL"):
                self.jira(local)
        with mock.patch.dict(os.environ, {"JIRA_BASE_URL": "https://other.atlassian.net"}):
            self.assertEqual(self.jira().site, SITE)  # jira_site wins

    def test_local_keys(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "local.json"
            p.write_text(json.dumps({"jira_mcp_server": "atl.as-sian_2", "jira_site": SITE + "/"}), encoding="utf-8")
            self.assertEqual(config.load_local(p), {"jira_mcp_server": "atl.as-sian_2", "jira_site": SITE})
            for bad in ({"jira_mcp_server": "a b"}, {"jira_mcp_server": ""}, {"jira_mcp_server": "x" * 65},
                        {"jira_mcp_server": ["atlassian"]}, {"jira_site": "http://example.atlassian.net"},
                        {"jira_site": SITE + "/wiki"}, {"jira_site": SITE + "?a=1"},
                        {"jira_site": "https://me@example.atlassian.net"}, {"jira_site": "example.atlassian.net"},
                        {"jira_site": SITE + "#x"}, {"jira_site": ""}, {"jira_site": 5}):
                with self.subTest(bad=bad):
                    p.write_text(json.dumps(bad), encoding="utf-8")
                    with self.assertRaises(config.Stop):
                        config.load_local(p)
