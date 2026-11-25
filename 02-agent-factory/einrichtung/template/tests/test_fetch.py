"""Tests for agentic_factory/fetch.py: the split steps and the plugin check before the mcp route."""
import contextlib
import io
import json
import unittest
from unittest import mock

from agentic_factory import config, jira_mcp, clarify, main
from .fakes import CFG, E2E, JiraE2E, KEY, NOT_READY_FAKE, PAT, PIPE, TICKET


class PluginCheck(E2E, unittest.TestCase):
    def test_mcp_route_stops_without_the_plugin(self):  # M5
        with mock.patch.object(jira_mcp, "PLUGIN_DIR", self.d / "agentic-factory-plugin"), \
                self.assertRaisesRegex(config.Stop, "agentic-factory-plugin/hooks/guard.py is missing: copy the folder "
                                                "agentic-factory-plugin next to agentic-factory.py"):
            self.run_main("assess", "--key", KEY, "--jira", "mcp", "--readiness", str(self.rd), cfg=self.acfg)
        self.assertFalse((self.d / "calls.jsonl").exists())
        self.assertFalse((self.d / ".factory-local").exists())  # stopped before the log folder, too
        with self.assertRaisesRegex(config.Stop, "no MCP server named 'atlassian'"):  # with the plugin it gets further
            self.run_main("assess", "--key", KEY, "--jira", "mcp", "--readiness", str(self.rd), cfg=self.acfg)


class Steps(JiraE2E, unittest.TestCase):
    def test_split_equals_all(self):
        rc, out = self.api("assess", "--readiness", str(self.rd), cfg=self.acfg, verdict="not_ready")
        self.assertEqual(rc, config.EXIT_NOT_READY, out)
        self.assertEqual(out.count("Jira route: api (--jira)"), 1, out)
        (posted,) = self.posts()
        io = self.repo / "agentic-io"  # as in a pipeline: inside the clone; the work call's snapshot ignores it
        common = ("--readiness", str(self.rd), "--io-dir", str(io))
        rc, out = self.run_main("assess", "--step", "fetch", "--key", KEY, "--jira", "api", *common, cfg=self.acfg,
                                env=self.env)
        self.assertEqual(rc, 0, out)
        self.assertEqual(json.loads((io / "in/request.json").read_text(encoding="utf-8")),
                         {"mode": "assess", "key": KEY, "route": "api", "framework": None, "change": None,
                          "no_assess": False, "no_post": False, "fresh": False})
        self.assertEqual(json.loads((io / "in/ticket.json").read_text(encoding="utf-8"))["key"], KEY)
        self.assertEqual(json.loads((io / "in/comments.json").read_text(encoding="utf-8")), [])
        rc, out = self.run_main("assess", "--step", "agent", *common, cfg=self.acfg, verdict="not_ready")
        self.assertEqual(rc, 0, out)  # decision 2: split steps exit 0
        self.assertIn("not ready", out)
        self.assertEqual(self.posts(), [posted])
        rc, out = self.run_main("assess", "--step", "post", *common, cfg=self.acfg, env=self.env)
        self.assertEqual(rc, 0, out)
        self.assertIn("Jira route: api", out)
        self.assertEqual(self.posts(), [posted, posted])
        self.assertEqual(self.comment(io), self.comment())
        self.assertEqual(self.comment(), clarify.render_assess(KEY, NOT_READY_FAKE))

    def test_split_equals_all_offline(self):
        rc, out = self.run_main("assess", "--ticket-file", str(self.tf), "--readiness", str(self.rd), "--io-dir",
                                str(self.io), cfg=self.acfg, verdict="not_ready")
        self.assertEqual(rc, config.EXIT_NOT_READY, out)
        io = self.repo / "agentic-io"
        common = ("--readiness", str(self.rd), "--io-dir", str(io))
        for step in ("fetch", "agent", "post"):
            extra = ("--ticket-file", str(self.tf)) if step == "fetch" else ()
            rc, out = self.run_main("assess", "--step", step, *extra, *common, cfg=self.acfg, verdict="not_ready")
            self.assertEqual(rc, 0, out)
        self.assertEqual(self.comment(io), self.comment())
        self.assertEqual(self.fake.seen, [])

    def test_post_rechecks_tampered_out(self):
        io = self.repo / "agentic-io"
        common = ("--readiness", str(self.rd), "--io-dir", str(io))
        self.run_main("assess", "--step", "fetch", "--key", KEY, "--jira", "api", *common, cfg=self.acfg, env=self.env)
        self.run_main("assess", "--step", "agent", *common, cfg=self.acfg, verdict="not_ready")
        path = io / "out/assessment.json"
        good = json.loads(path.read_text(encoding="utf-8"))
        token = "ghp_" + "A" * 36
        bad = {"token in a detail": {**good, "reasons": [{"id": "already_exists", "detail": "siehe " + token}]},
               "secret value in a question": {**good, "questions": ["Gilt " + PAT + "?"]},
               "bidi control in a detail": {**good, "reasons": [{"id": "already_exists", "detail": "a\u202eb"}]},
               "FACTORY- as reason id": {**good, "reasons": [{"id": "FACTORY-SPEC", "detail": "x"}]},
               "invisible character": {**good, "questions": ["a\u200bb"]},
               "detail not a string": {**good, "reasons": [{"id": "already_exists", "detail": ["x"]}]},
               "ready with reasons": {**good, "verdict": "ready"}}
        for name, v in bad.items():
            with self.subTest(name=name):
                path.write_text(json.dumps(v), encoding="utf-8")
                with self.assertRaises(config.Stop):
                    self.run_main("assess", "--step", "post", *common, cfg=self.acfg, env=self.env)
                self.assertEqual(self.writes(), [])
                self.assertFalse((io / "out/comment-1.txt").exists())
        path.write_text(json.dumps(good), encoding="utf-8")
        (io / "out/spec.json").write_text("{}", encoding="utf-8")  # a result the mode doesn't make
        with self.assertRaisesRegex(config.Stop, "spec.json"):
            self.run_main("assess", "--step", "post", *common, cfg=self.acfg, env=self.env)
        self.assertEqual(self.writes(), [])

    def test_factory_marker_in_model_text_is_neutralized(self):
        io = self.repo / "agentic-io"
        common = ("--readiness", str(self.rd), "--io-dir", str(io))
        self.run_main("assess", "--step", "fetch", "--key", KEY, "--jira", "api", *common, cfg=self.acfg, env=self.env)
        self.run_main("assess", "--step", "agent", *common, cfg=self.acfg, verdict="not_ready")
        path = io / "out/assessment.json"
        v = json.loads(path.read_text(encoding="utf-8"))
        v["reasons"][0]["detail"] = "wie FACTORY-X"
        v["questions"] = ["FACTORY-SPEC v1?"]
        path.write_text(json.dumps(v), encoding="utf-8")
        rc, out = self.run_main("assess", "--step", "post", *common, cfg=self.acfg, env=self.env)
        self.assertEqual(rc, 0, out)
        (posted,) = self.posts()
        self.assertIn("Grund already_exists: wie FACTORY_X", self.comment(io))
        self.assertIn("Frage 1: FACTORY_SPEC v1?", self.comment(io))
        self.assertNotIn("FACTORY-", self.comment(io))
        self.assertNotIn("FACTORY-", posted)

    def test_all_returns_the_mode_code_split_steps_return_0(self):  # decision 2
        rc, out = self.run_main("spec", "--ticket-file", str(self.tf), "--io-dir", str(self.io), mode="questions")
        self.assertEqual(rc, config.EXIT_QUESTIONS, out)
        (self.repo / config.QUESTIONS).unlink()
        io = self.repo / "agentic-io"
        for step in ("fetch", "agent", "post"):
            extra = ("--ticket-file", str(self.tf)) if step == "fetch" else ()
            rc, out = self.run_main("spec", "--step", step, *extra, "--io-dir", str(io), mode="questions")
            self.assertEqual(rc, 0, out)
        self.assertIn("questions", out)
        self.assertEqual(self.comment(io), self.comment())
        self.assertTrue(self.comment().startswith("[KI] agentic-factory spec fragen key=FLAB-7"))

    def test_log_folder_never_inside_the_project(self):
        with self.assertRaisesRegex(config.Stop, "log folder .* lies inside the project"):
            self.run_main("assess", "--ticket-file", str(self.tf), "--readiness", str(self.rd), cfg=self.acfg,
                          env={"HOME": str(self.repo), "USERPROFILE": str(self.repo)})
        self.assertFalse((self.repo / ".factory-local").exists())

    def test_agent_step_refuses_a_changed_io_folder(self):
        io = self.repo / "agentic-io"
        common = ("--io-dir", str(io), "--framework", "openspec")
        self.run_main("spec", "--step", "fetch", "--ticket-file", str(self.tf), *common)
        with self.assertRaisesRegex(config.Stop, "changed the io folder"):
            self.run_main("spec", "--step", "agent", *common, mode="io")
        self.assertEqual(sorted(p.name for p in (io / "out").iterdir()), [])

    def test_agent_step_checks_in(self):
        io = self.repo / "agentic-io"
        common = ("--readiness", str(self.rd), "--io-dir", str(io))
        self.run_main("assess", "--step", "fetch", "--ticket-file", str(self.tf), *common, cfg=self.acfg)
        req = json.loads((io / "in/request.json").read_text(encoding="utf-8"))
        with self.assertRaisesRegex(config.Stop, "this is mode spec, but .* is for mode assess"):
            self.run_main("spec", "--step", "agent", *common, cfg=self.acfg)
        (io / "in/request.json").write_text(json.dumps({**req, "extra": 1}), encoding="utf-8")
        with self.assertRaisesRegex(config.Stop, "request.json"):
            self.run_main("assess", "--step", "agent", *common, cfg=self.acfg)
        (io / "in/request.json").write_text(json.dumps(req), encoding="utf-8")
        with self.assertRaisesRegex(config.Stop, "--key FLAB-8 differs"):
            self.run_main("assess", "--step", "agent", "--key", "FLAB-8", *common, cfg=self.acfg)
        (io / "in/ticket.json").write_text(json.dumps({**TICKET, "key": "FLAB-8"}), encoding="utf-8")
        with self.assertRaisesRegex(config.Stop, "ticket.json"):
            self.run_main("assess", "--step", "agent", *common, cfg=self.acfg)
        (io / "in/ticket.json").write_text(json.dumps(TICKET), encoding="utf-8")
        good = {"id": "1", "created": "", "updated": "", "author": "", "body": "[Mensch] ok"}
        for bad in ({k: v for k, v in good.items() if k != "updated"}, {**good, "updated": None}, {**good, "x": ""}):
            with self.subTest(bad=bad):
                (io / "in/comments.json").write_text(json.dumps([bad]), encoding="utf-8")
                with self.assertRaisesRegex(config.Stop, "comments.json must be a list of comments with the strings id, "
                                                         "created, updated, author, body"):
                    self.run_main("assess", "--step", "agent", *common, cfg=self.acfg)

    def test_pipeline_env_checks(self):
        with self.assertRaisesRegex(config.Stop, "--step fetch.*--step agent.*--step post"):
            self.run_main("assess", "--key", KEY, cfg=self.acfg, env={**PIPE, **self.env})
        for step in ("fetch", "post"):
            with self.subTest(step=step), self.assertRaisesRegex(config.Stop, "COPILOT_GITHUB_TOKEN"):
                self.run_main("assess", "--step", step, "--key", KEY, "--io-dir", str(self.io), cfg=self.acfg,
                              env={**PIPE, **self.env, "COPILOT_GITHUB_TOKEN": "gho_x"})
        with self.assertRaisesRegex(config.Stop, "JIRA_API_TOKEN"):
            self.run_main("assess", "--step", "agent", "--io-dir", str(self.io), cfg=self.acfg,
                          env={**PIPE, "JIRA_API_TOKEN": PAT, "COPILOT_GITHUB_TOKEN": "gho_x"})
        self.assertEqual(self.fake.seen, [])
        with self.assertRaisesRegex(config.Stop, "mcp route is refused inside a pipeline"):
            self.run_main("assess", "--step", "fetch", "--key", KEY, "--jira", "mcp", "--io-dir", str(self.io),
                          cfg=self.acfg, env={**PIPE, **self.env})
        rc, out = self.run_main("assess", "--step", "fetch", "--key", KEY, "--io-dir", str(self.io), cfg=self.acfg,
                                env={**PIPE, **self.env})
        self.assertEqual(rc, 0, out)
        self.assertIn("Jira route: api (default in a pipeline)", out)

    def test_env_checks_only_in_a_pipeline(self):
        both = {**self.env, "COPILOT_GITHUB_TOKEN": "gho_local_login"}
        io = self.repo / "agentic-io"
        common = ("--readiness", str(self.rd), "--io-dir", str(io))
        rc, out = self.run_main("assess", "--step", "fetch", "--key", KEY, "--jira", "api", *common, cfg=self.acfg,
                                env=both)
        self.assertEqual(rc, 0, out)
        rc, out = self.run_main("assess", "--step", "agent", *common, cfg=self.acfg, verdict="not_ready", env=both)
        self.assertEqual(rc, 0, out)
        rc, out = self.run_main("assess", "--step", "post", *common, cfg=self.acfg, env=both)
        self.assertEqual(rc, 0, out)
        self.assertEqual(len(self.posts()), 1)

    def test_build_refused_in_pipeline(self):
        for step in ("fetch", "agent", "post"):
            with self.subTest(step=step), self.assertRaisesRegex(config.Stop, "build"):
                self.run_main("build", "--step", step, "--key", KEY, "--io-dir", str(self.io), env={**PIPE})
        self.assertEqual(self.fake.seen, [])

    def test_ticket_file_never_posts(self):
        rc, out = self.run_main("assess", "--ticket-file", str(self.tf), "--jira", "api", "--readiness", str(self.rd),
                                "--io-dir", str(self.io), cfg=self.acfg, verdict="not_ready", env=self.env)
        self.assertEqual(rc, config.EXIT_NOT_READY, out)
        self.assertIn("Jira route: offline (offline input)", out)
        self.assertEqual(self.fake.seen, [])
        self.assertIn(str(self.io / "out" / "comment-1.txt"), out)
        self.assertTrue(self.comment().startswith("[KI] agentic-factory assess key=FLAB-7"))

    def test_comments_file(self):
        cf = self.d / "comments.json"
        cf.write_text(json.dumps([{"body": "[Mensch] 1 ok", "created": "2026-11-24T10:00:00.000+0100"}]),
                      encoding="utf-8")
        self.run_main("assess", "--step", "fetch", "--ticket-file", str(self.tf), "--comments-file", str(cf),
                      "--io-dir", str(self.io), cfg=self.acfg)
        self.assertEqual(json.loads((self.io / "in/comments.json").read_text(encoding="utf-8")),
                         [{"id": "1", "created": "2026-11-24T09:00:00.000Z", "updated": "", "author": "",
                           "body": "[Mensch] 1 ok"}])
        with self.assertRaisesRegex(config.Stop, "--comments-file"):
            self.api("assess", "--step", "fetch", "--comments-file", str(cf), cfg=self.acfg)

    def test_clarify_needs_its_config_blocks(self):
        for cfg in ({k: v for k, v in self.acfg.items() if k != "clarify"},
                    {k: v for k, v in CFG.items() if k != "assess"}):
            with self.subTest(blocks=sorted(k for k in ("assess", "clarify") if k in cfg)), \
                    self.assertRaisesRegex(config.Stop, "clarify is not available in this config"):
                self.api("clarify", cfg=cfg)
        self.assertEqual(self.fake.seen, [])
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
            main.parse(["assess", "--jira", "rest"])
