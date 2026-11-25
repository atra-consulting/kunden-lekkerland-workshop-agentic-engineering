"""Tests for agentic_factory/post.py: what assess, spec, and build post."""
import io
import json
import unittest

from agentic_factory import config, jira_rest, clarify, fetch
from .fakes import JiraE2E, KEY, NOT_READY_FAKE


SPEC_TEXT = ("=== openspec/changes/lower-tags/proposal.md ===\np\n\n"
             "=== openspec/changes/lower-tags/tasks.md ===\n- [ ] t\n")


class ExistingModesPost(JiraE2E, unittest.TestCase):
    def test_assess_not_ready(self):
        rc, out = self.api("assess", "--readiness", str(self.rd), cfg=self.acfg, verdict="not_ready")
        self.assertEqual(rc, config.EXIT_NOT_READY, out)
        text = clarify.render_assess(KEY, NOT_READY_FAKE)
        self.assertEqual(self.posts(), [jira_rest.text_to_wiki(text)])
        self.assertEqual(self.comment(), text)
        self.assertIn("comment 10050", out)

    def test_assess_ready_posts_nothing(self):
        rc, out = self.api("assess", "--readiness", str(self.rd), cfg=self.acfg)
        self.assertEqual(rc, 0, out)
        self.assertEqual(self.writes(), [])

    def test_spec_questions(self):
        rc, out = self.api("spec", mode="questions")
        self.assertEqual(rc, config.EXIT_QUESTIONS, out)
        text = clarify.render_spec_questions(KEY, "# Fragen\n- Welche Seite?\n")
        self.assertEqual(self.posts()[-1], jira_rest.text_to_wiki(text))
        self.assertEqual(self.comment(), text)

    def test_spec_done(self):
        rc, out = self.api("spec", "--readiness", str(self.rd), cfg=self.acfg)
        self.assertEqual(rc, 0, out)
        text = clarify.render_spec(KEY, "openspec", "Label sdd-openspec", "lower-tags", clarify.READINESS_PASSED, SPEC_TEXT)
        self.assertEqual(self.comment(), text)
        self.assertIn("Change: lower-tags", text)
        self.assertIn("=== openspec/changes/lower-tags/proposal.md ===\np\n", text)
        self.assertEqual(self.posts(), [jira_rest.text_to_wiki(text)])

    def test_spec_readiness_lines_and_source(self):
        self.api("spec", "--framework", "openspec")
        spec = json.loads((self.io / "out/spec.json").read_text(encoding="utf-8"))
        self.assertEqual(spec, {"fw": "openspec", "source": "--framework", "change": "lower-tags",
                                "readiness_line": clarify.READINESS_OFF, "spec_text": SPEC_TEXT})
        acfg = {**self.acfg}
        self.assertEqual(fetch.readiness_line(acfg, True), clarify.READINESS_SKIPPED)
        self.assertEqual(fetch.readiness_line(acfg, False), clarify.READINESS_PASSED)
        self.assertEqual(fetch.readiness_line({**acfg, "assess": {**acfg["assess"], "enabled": False}}, False),
                         clarify.READINESS_OFF)

    def test_build_done(self):
        self.run_main("spec", "--ticket-file", str(self.tf))
        rc, out = self.api("build", mode="build")
        self.assertEqual(rc, 0, out)
        text = clarify.render_build(KEY, "lower-tags", ["src/New.php"], "Testbefehl ./bin/phpunit: bestanden.")
        self.assertEqual(self.comment(), text)
        self.assertEqual(self.posts(), [jira_rest.text_to_wiki(text)])

    def test_build_files_leave_out_the_io_folder(self):
        self.run_main("spec", "--ticket-file", str(self.tf))
        io = self.repo / "agentic-io"
        rc, out = self.run_main("build", "--ticket-file", str(self.tf), "--io-dir", str(io), mode="commit-io")
        self.assertEqual(rc, 0, out)
        self.assertIn("agentic-io/in/request.json", out)  # the commit is shown as it is
        build = json.loads((io / "out/build.json").read_text(encoding="utf-8"))
        self.assertEqual(build["changed"], ["src/New.php"])
        self.assertNotIn("agentic-io", self.comment(io))

    def test_test_line(self):
        p = self.d / "events.jsonl"

        def line(cmd, ok, cid):
            return [json.dumps({"type": "tool.execution_start", "data": {"toolCallId": cid, "toolName": "bash",
                                                                         "arguments": {"command": cmd}}}),
                    json.dumps({"type": "tool.execution_complete", "data": {"toolCallId": cid, "success": ok}})]
        p.write_text("\n".join(line("./bin/phpunit", True, "a") + line("ls", False, "b")), encoding="utf-8")
        self.assertEqual(fetch.test_line([p], "./bin/phpunit"), "Testbefehl ./bin/phpunit: bestanden.")
        p.write_text("\n".join(line("./bin/phpunit", True, "a") + line("./bin/phpunit --filter X", False, "c")),
                     encoding="utf-8")
        self.assertEqual(fetch.test_line([p], "./bin/phpunit"), "Testbefehl ./bin/phpunit: fehlgeschlagen.")
        p.write_text("\n".join(line("./bin/phpunitx", True, "a")), encoding="utf-8")
        self.assertEqual(fetch.test_line([p], "./bin/phpunit"), "Der Agent hat den Testbefehl nicht ausgeführt.")

    def test_no_post(self):
        rc, out = self.api("assess", "--readiness", str(self.rd), "--no-post", cfg=self.acfg, verdict="not_ready")
        self.assertEqual(rc, config.EXIT_NOT_READY, out)
        self.assertEqual(self.writes(), [])
        self.assertEqual(self.comment(), clarify.render_assess(KEY, NOT_READY_FAKE))
        self.assertIn(str(self.io / "out" / "comment-1.txt"), out)

    def test_comment_over_the_limit_posts_nothing(self):
        empty = clarify.render_spec(KEY, "openspec", "Label sdd-openspec", "lower-tags", clarify.READINESS_OFF,
                               SPEC_TEXT.replace("\np\n", "\n\n"))
        size = 30001 - len(empty)
        (self.repo / "fake-size").write_text(str(size), encoding="utf-8")
        with self.assertRaisesRegex(config.Stop, "longer than 30000 characters"):
            self.api("spec", mode="big")
        spec = json.loads((self.io / "out/spec.json").read_text(encoding="utf-8"))
        self.assertEqual(len(clarify.render_spec(KEY, **spec)), 30001)
        self.assertEqual(self.writes(), [])
        self.assertFalse((self.io / "out/comment-1.txt").exists())
