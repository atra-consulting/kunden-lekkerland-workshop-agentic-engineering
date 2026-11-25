"""Tests for agentic_factory/blocked.py: the per-project log of tool calls that unattended Copilot denied or blocked."""
import contextlib
import io
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from agentic_factory import blocked
from .fakes import E2E


def start(i, tool, **args):
    return {"type": "tool.execution_start", "data": {"toolCallId": i, "toolName": tool, "arguments": args}}


def done(i, success=True, **error):
    d = {"toolCallId": i, "success": success}
    if error:
        d["error"] = error
    return {"type": "tool.execution_complete", "data": d}


DENIED = {"code": "denied", "message": "Permission denied because no interactive user response was available."}
BLOCKED = {"code": "failure", "message": "Command blocked: contains dangerous shell expansion patterns"}
PLAIN = {"code": "failure", "message": "Parent directory does not exist"}


class Base(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp(prefix="blocked-"))
        self.addCleanup(shutil.rmtree, self.d, True)
        self.home = self.d / "home"
        self.home.mkdir()
        patch = mock.patch.dict(os.environ, {"HOME": str(self.home), "USERPROFILE": str(self.home)})
        patch.start()
        self.addCleanup(patch.stop)
        self.repo = self.d / "proj"
        self.repo.mkdir()
        self.ctx = {"mode": "spec", "framework": "openspec", "key": "FLAB-7", "run": "20260101-000000-spec-FLAB-7"}

    def events(self, *evs, name="events-1.jsonl"):
        p = self.d / name
        p.write_text("\n".join(json.dumps(e) for e in evs) + "\n", encoding="utf-8")
        return p

    def lines(self):
        return [json.loads(x) for x in blocked.log_path(self.repo).read_text(encoding="utf-8").splitlines()]


class Entries(Base):
    def test_denied_and_blocked_kept_failures_skipped(self):
        p = self.events(start("1", "bash", command="cat x | python3 y"), done("1", False, **DENIED),
                        start("2", "bash", command="echo $(id)"), done("2", False, **BLOCKED),
                        start("3", "write", path="a/b"), done("3", False, **PLAIN),
                        start("4", "bash", command="ls"), done("4"))
        got = blocked.entries(p)
        self.assertEqual([(e["kind"], e["tool"], e["command"]) for e in got],
                         [("denied", "bash", "cat x | python3 y"), ("blocked", "bash", "echo $(id)")])
        self.assertTrue(got[1]["message"].startswith("Command blocked"))

    def test_command_falls_back_to_the_arguments(self):
        p = self.events(start("1", "edit", path="a", text="b"), done("1", False, **DENIED))
        self.assertEqual(blocked.entries(p)[0]["command"], json.dumps({"path": "a", "text": "b"}))

    def test_final_message_is_the_last_one(self):
        p = self.events({"type": "assistant.message", "data": {"content": "one"}},
                        {"type": "assistant.message", "data": {"content": "two"}})
        self.assertEqual(blocked.final_message(p), "two")
        self.assertEqual(blocked.final_message(self.events(start("1", "bash"))), "")

    def test_summary(self):
        self.assertEqual(blocked.summary(0, Path("/x/blocked.jsonl")), "no blocked calls")
        self.assertEqual(blocked.summary(2, Path("/x/blocked.jsonl")), "2 blocked call(s), see /x/blocked.jsonl")

    def test_log_path_is_under_home_not_the_project(self):
        self.assertEqual(blocked.log_path(self.repo), self.home / ".factory-local" / "proj" / "blocked.jsonl")


class Record(Base):
    def record(self, p, allowed=("read", "write")):
        return blocked.record(self.repo, {**self.ctx, "call": "1"}, p, list(allowed))

    def test_tokens_are_redacted(self):
        pat = "ghp_" + "A" * 36
        with mock.patch.dict(os.environ, {"JIRA_API_TOKEN": "jira-secret-value-1"}):
            p = self.events(start("1", "bash", command=f"curl -H 'Authorization: {pat}' x"),
                            done("1", False, code="denied", message="denied: jira-secret-value-1"),
                            {"type": "assistant.message", "data": {"content": f"token {pat} jira-secret-value-1"}})
            self.record(p)
        text = blocked.log_path(self.repo).read_text(encoding="utf-8")
        self.assertNotIn(pat, text)
        self.assertNotIn("jira-secret-value-1", text)
        entry, final = self.lines()
        self.assertIn("[REDACTED-PATTERN]", entry["command"])
        self.assertIn("[REDACTED]", entry["message"])
        self.assertIn("[REDACTED-PATTERN]", final["text"])

    def test_line_fields_and_final(self):
        p = self.events(start("1", "bash", command="cat x | python3 y"), done("1", False, **DENIED),
                        {"type": "assistant.message", "data": {"content": "konnte nicht"}})
        self.assertEqual(self.record(p, ["read", "write", "shell(ls:*)"]), 1)
        entry, final = self.lines()
        for k in ("mode", "framework", "key", "run", "call"):
            self.assertEqual(entry[k], {**self.ctx, "call": "1"}[k])
        self.assertEqual((entry["kind"], entry["tool"], entry["command"]), ("denied", "bash", "cat x | python3 y"))
        self.assertEqual(entry["allowed"], ["read", "write", "shell(ls:*)"])
        self.assertIn("at", entry)
        self.assertEqual(final, {"kind": "final", "call": "1", "text": "konnte nicht"})

    def test_final_line_only_when_blocked(self):
        p = self.events(start("1", "bash", command="ls"), done("1"),
                        {"type": "assistant.message", "data": {"content": "fertig"}})
        self.assertEqual(self.record(p), 0)
        self.assertFalse(blocked.log_path(self.repo).exists())

    def test_appends_across_runs(self):
        p = self.events(start("1", "bash", command="a"), done("1", False, **DENIED))
        self.record(p)
        q = self.events(start("1", "bash", command="b"), done("1", False, **BLOCKED), name="events-2.jsonl")
        self.record(q)
        self.assertEqual([x.get("command") for x in self.lines() if x["kind"] != "final"], ["a", "b"])

    def test_write_error_warns_and_continues(self):
        blocked.log_path(self.repo).mkdir(parents=True)  # a folder where the file should be
        p = self.events(start("1", "bash", command="a"), done("1", False, **DENIED))
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            n = self.record(p)
        self.assertEqual(n, 1)
        self.assertIn("WARNING: can't write", out.getvalue())


class EndToEnd(E2E, unittest.TestCase):
    def test_spec_run_logs_denied_call(self):
        (self.repo / "fake-denied").write_text("", encoding="utf-8")
        rc, out = self.run_main("spec", "--ticket-file", str(self.tf))
        self.assertEqual(rc, 0, out)
        path = self.d / ".factory-local" / "proj" / "blocked.jsonl"
        lines = [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines()]
        entry = lines[0]
        self.assertEqual((entry["mode"], entry["kind"], entry["command"]), ("spec", "denied", "cat x | python3 y"))
        self.assertEqual(entry["key"], "FLAB-7")
        self.assertEqual(lines[-1]["kind"], "final")
        self.assertIn(f"1 blocked call(s), see {path}", out)

    def test_stopped_run_still_ends_with_the_summary_once(self):
        (self.repo / "fake-denied").write_text("", encoding="utf-8")
        (self.d / "fake-exit").write_text("3", encoding="utf-8")
        rc, out = self.run_main("spec", "--ticket-file", str(self.tf), entry=True)
        self.assertNotEqual(rc, 0)
        path = self.d / ".factory-local" / "proj" / "blocked.jsonl"
        self.assertIn("copilot exited with 3", out)
        self.assertEqual(out.count("1 blocked call(s), see"), 1, out)
        self.assertEqual(out.count(f"see {path}"), 1)
        self.assertEqual(json.loads(path.read_text(encoding="utf-8").splitlines()[0])["kind"], "denied")


if __name__ == "__main__":
    unittest.main()
