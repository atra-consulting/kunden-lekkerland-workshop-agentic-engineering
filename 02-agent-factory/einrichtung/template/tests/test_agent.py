"""Tests for agentic_factory/agent.py: spec and build runs end to end, and the shell backstop."""
import json
import os
import subprocess
import re
import unittest
from pathlib import Path
from unittest import mock

from agentic_factory import config
from agentic_factory import ticket as ticket_mod
from .fakes import CFG, E2E


class EndToEnd(E2E, unittest.TestCase):

    def test_spec_then_build(self):
        rc, out = self.run_main("spec", "--ticket-file", str(self.tf))
        self.assertEqual(rc, 0, out)
        self.assertIn("framework openspec (from label)", out)
        self.assertIn("credits 2.50", out)
        self.assertIn("DENIED: shell(curl) denied", out)
        self.assertIn("openspec/changes/lower-tags/proposal.md", out)
        self.assertNotIn("WARNING", out)
        rc, out = self.run_main("build", "--ticket-file", str(self.tf), "--framework", "openspec", mode="build")
        self.assertEqual(rc, 0, out)
        self.assertIn("building change lower-tags", out)
        self.assertIn("src/New.php", out)

    def test_old_list_test_command_stops_build_before_any_call(self):
        self.run_main("spec", "--ticket-file", str(self.tf))
        (self.d / "calls.jsonl").unlink()
        cfg = {k: v for k, v in CFG.items() if k != "assess"}
        cfg["test_command"] = ["./bin/phpunit"]
        with self.assertRaisesRegex(config.Stop, 'test_command must be a string such as "make test"; an old config '
                                                 'has a list'):
            self.run_main("build", "--ticket-file", str(self.tf), "--framework", "openspec", mode="build", cfg=cfg)
        self.assertFalse((self.d / "calls.jsonl").exists())

    def test_missing_config_key_stops_with_its_name(self):
        cfg = {k: v for k, v in CFG.items() if k not in ("assess", "deny_tools")}
        with self.assertRaisesRegex(config.Stop, "has no key deny_tools"):
            self.run_main("spec", "--ticket-file", str(self.tf), cfg=cfg)
        self.assertFalse((self.d / "calls.jsonl").exists())

    def test_agent_commits_are_shown_and_checked(self):
        self.run_main("spec", "--ticket-file", str(self.tf))
        rc, out = self.run_main("build", "--ticket-file", str(self.tf), "--framework", "openspec", mode="commit")
        self.assertEqual(rc, 0, out)
        self.assertIn("the agent made 1 commit(s) on your branch, with 2 file(s)", out)
        self.assertIn("agent commit", out)
        self.assertIn("protected paths changed", out)
        self.assertIn("bin/x", out)

    def test_own_mcp_servers_switched_off(self):
        rc, out = self.run_main("spec", "--ticket-file", str(self.tf))
        self.assertEqual(rc, 0, out)
        self.assertIn("MCP servers switched off for this run: ['github-mcp-server', 'jira-cloud']", out)
        self.assertNotIn("not-a-real-token", out)
        calls = [json.loads(x) for x in (self.d / "calls.jsonl").read_text(encoding="utf-8").splitlines()]
        self.assertTrue(calls)
        for c in calls:  # the factory's argv, plus only the switches
            self.assertEqual(c[-2:], ["--disable-mcp-server=github-mcp-server", "--disable-mcp-server=jira-cloud"])
            self.assertIn("--disable-builtin-mcps", c)

    def test_mcp_list_failure_stops(self):
        (self.d / "mcp-fail").write_text("x", encoding="utf-8")
        with self.assertRaisesRegex(config.Stop, "can't list your MCP servers"):
            self.run_main("spec", "--ticket-file", str(self.tf))
        self.assertFalse((self.d / "calls.jsonl").exists())

    def test_questions_stop(self):
        rc, out = self.run_main("spec", "--ticket-file", str(self.tf), mode="questions")
        self.assertEqual(rc, config.EXIT_QUESTIONS, out)
        self.assertIn("Welche Seite?", out)
        with self.assertRaisesRegex(config.Stop, "FACTORY-QUESTIONS.md exists"):
            self.run_main("spec", "--ticket-file", str(self.tf))

    def test_print_only_runs_nothing(self):
        rc, out = self.run_main("spec", "--ticket-file", str(self.tf), "--print-only")
        self.assertEqual(rc, 0)
        self.assertIn("copilot -p '/openspec-propose ", out)
        self.assertIn("'--allow-tool=shell(openspec:*)'", out)
        self.assertFalse((self.repo / "openspec/changes/lower-tags").exists())
        self.assertNotIn("--disable-mcp-server=jira-cloud", out)  # print-only stays the factory's argv
        self.assertFalse((self.d / "calls.jsonl").exists())

    def test_assess_unavailable(self):
        with self.assertRaisesRegex(config.Stop, "not available in this config"):
            self.run_main("assess", "--ticket-file", str(self.tf))

    def test_assess_not_ready(self):
        rc, out = self.run_main("assess", "--ticket-file", str(self.tf), "--readiness", str(self.rd),
                                cfg=self.acfg, verdict="not_ready")
        self.assertEqual(rc, config.EXIT_NOT_READY, out)
        self.assertIn("verdict: not_ready", out)
        self.assertIn("already_exists: src/X.php macht das schon", out)
        self.assertIn("? Wirklich?", out)

    def test_assess_ready(self):
        rc, out = self.run_main("assess", "--ticket-file", str(self.tf), "--readiness", str(self.rd), cfg=self.acfg)
        self.assertEqual(rc, 0, out)
        self.assertIn("verdict: ready", out)
        self.assertFalse((self.repo / config.ASSESSMENT).exists())

    def test_spec_starts_with_assess_when_enabled(self):
        rc, out = self.run_main("spec", "--ticket-file", str(self.tf), "--readiness", str(self.rd), cfg=self.acfg)
        self.assertEqual(rc, 0, out)
        self.assertIn("ready: the spec calls start", out)
        self.assertIn("openspec/changes/lower-tags/proposal.md", out)
        self.assertNotIn(config.ASSESSMENT, out.split("uncommitted changes")[1])

    def test_spec_stops_when_not_ready(self):
        rc, out = self.run_main("spec", "--ticket-file", str(self.tf), "--readiness", str(self.rd), cfg=self.acfg,
                                verdict="not_ready")
        self.assertEqual(rc, config.EXIT_NOT_READY, out)
        self.assertFalse((self.repo / "openspec/changes/lower-tags").exists())

    def test_assess_catches_changes_to_already_modified_files(self):
        (self.repo / "README.md").write_text("changed before the run\n", encoding="utf-8")
        with self.assertRaisesRegex(config.Stop, "changed more than FACTORY-ASSESSMENT.json.*README.md"):
            self.run_main("assess", "--ticket-file", str(self.tf), "--readiness", str(self.rd), cfg=self.acfg,
                          mode="tamper")

    def test_spec_no_assess(self):
        rc, out = self.run_main("spec", "--ticket-file", str(self.tf), "--no-assess", cfg=self.acfg)
        self.assertEqual(rc, 0, out)
        self.assertNotIn("readiness check", out)

    def test_print_only_with_assess(self):
        rc, out = self.run_main("spec", "--ticket-file", str(self.tf), "--readiness", str(self.rd), "--print-only",
                                cfg=self.acfg)
        self.assertIn("# call 1/2 (readiness check)", out)
        self.assertIn("--max-ai-credits 40", out)
        self.assertIn("--max-ai-credits 150", out)

    def test_framework_not_installed(self):
        with self.assertRaisesRegex(config.Stop, "speckit is not installed"):
            self.run_main("spec", "--ticket-file", str(self.tf), "--framework", "speckit")

    def test_build_without_spec(self):
        with self.assertRaisesRegex(config.Stop, "no spec found"):
            self.run_main("build", "--ticket-file", str(self.tf), "--framework", "openspec")

    def test_build_picks_from_several_by_uncommitted_change(self):
        for n in ("old-one", "new-one"):
            d = self.repo / "openspec/changes" / n
            d.mkdir()
            (d / "proposal.md").write_text("p\n", encoding="utf-8")
            (d / "tasks.md").write_text("t\n", encoding="utf-8")
        env = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull}
        subprocess.run(["git", "add", "openspec/changes/old-one"], cwd=self.repo, check=True, env=env)
        subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "-q", "-m", "o"],
                       cwd=self.repo, check=True, env=env)
        name, _ = ticket_mod.find_change(self.repo, CFG["frameworks"]["openspec"], None)
        self.assertEqual(name, "new-one")
        name, _ = ticket_mod.find_change(self.repo, CFG["frameworks"]["openspec"], "old-one")
        self.assertEqual(name, "old-one")


class ShellBackstop(E2E, unittest.TestCase):
    """I1: a work call without shell tools that ran one anyway stops before out/ is written or anything is posted."""

    def shell(self, how, tool="bash"):
        (self.d / "fake-shell").write_text(f"{how} {tool}", encoding="utf-8")

    def assess(self, **kw):
        return self.run_main("assess", "--ticket-file", str(self.tf), "--readiness", str(self.rd), "--io-dir",
                             str(self.d / "io"), cfg=self.acfg, **kw)

    def test_shell_in_the_readiness_check_stops(self):
        for tool in ("bash", "powershell"):
            with self.subTest(tool=tool):
                self.shell("ran", tool)
                with self.assertRaisesRegex(config.Stop, f"the readiness check ran the shell tool {tool} although it may "
                                                     "not run shell commands; nothing was posted"):
                    self.assess(verdict="not_ready")
                self.assertFalse((self.d / "io/out/assessment.json").exists())

    def test_denied_shell_passes(self):
        self.shell("denied")
        rc, out = self.assess(verdict="not_ready")
        self.assertEqual(rc, config.EXIT_NOT_READY, out)
        self.assertTrue((self.d / "io/out/assessment.json").exists())
        for argv in (json.loads(x) for x in (self.d / "calls.jsonl").read_text(encoding="utf-8").splitlines()):
            self.assertIn("--deny-tool=shell", argv)

    def test_no_shell_passes(self):
        rc, out = self.assess(verdict="not_ready")
        self.assertEqual(rc, config.EXIT_NOT_READY, out)

    def test_spec_calls_with_shell_tools_are_not_checked(self):
        self.shell("ran")
        rc, out = self.run_main("spec", "--ticket-file", str(self.tf))
        self.assertEqual(rc, 0, out)
        for argv in (json.loads(x) for x in (self.d / "calls.jsonl").read_text(encoding="utf-8").splitlines()):
            self.assertNotIn("--deny-tool=shell", argv)

    def test_print_only_shows_the_deny(self):
        rc, out = self.run_main("assess", "--ticket-file", str(self.tf), "--readiness", str(self.rd), "--print-only",
                                cfg=self.acfg)
        self.assertEqual(rc, 0, out)
        self.assertIn("'--deny-tool=shell(npx:*)' --deny-tool=shell\n", out)


class GitGuard(E2E, unittest.TestCase):
    """A work call that changes .git/config or a hook stops the run before the script runs any git command, and every
    git command of the script runs without fsmonitor and hooks."""

    def stops_before_any_git(self, what, name):
        (self.d / "fake-git").write_text(what, encoding="utf-8")
        with mock.patch("subprocess.run", wraps=subprocess.run) as runs, \
                self.assertRaisesRegex(config.Stop, f"changed {re.escape(name)}; nothing is posted.*inspect .* with cat "
                                                    "and ls before you run any git command"):
            self.run_main("spec", "--ticket-file", str(self.tf))
        calls = [c.args[0] for c in runs.call_args_list if c.args and c.args[0][:1] == ["git"]]
        self.assertTrue(calls, "git ran before the call")
        self.assertEqual(calls[-1][-4:], ["rev-parse", "-q", "--verify", "HEAD"])  # the last one came before the call
        self.assertFalse((self.repo / "fsmonitor-ran").exists())

    def test_changed_git_config_stops_before_any_git(self):
        self.stops_before_any_git("config", ".git/config")

    def test_changed_hook_stops_before_any_git(self):
        self.stops_before_any_git("hook", ".git/hooks/post-checkout")

    def test_git_runs_without_fsmonitor_and_hooks(self):
        marker = self.repo / "fsmonitor-ran"
        subprocess.run(["git", "config", "core.fsmonitor", f"touch {marker}"], cwd=self.repo, check=True)
        with mock.patch.dict(os.environ, {"HOME": str(self.d)}):
            ticket_mod.git(self.repo, "status", "--porcelain")
            ticket_mod.head_commit(self.repo)
            with mock.patch("subprocess.run", wraps=subprocess.run) as runs:
                ticket_mod.git(self.repo, "status")
                ticket_mod.head_commit(self.repo)
        self.assertFalse(marker.exists())
        no_hooks = (self.d / ".factory-local" / "no-hooks").as_posix()
        for c in runs.call_args_list:
            self.assertEqual(c.args[0][:9], ["git", "-c", "core.fsmonitor=false", "-c", f"core.hooksPath={no_hooks}",
                                             "-c", "diff.external=", "-c", "core.pager=cat"])

    def test_diff_calls_run_no_external_diff_or_textconv(self):
        for path in ("agentic_factory/agent.py", "agentic_factory/feedback.py"):
            text = (Path(__file__).resolve().parent.parent / path).read_text(encoding="utf-8")
            for m in re.finditer(r'git\(repo, "diff", ([^)]*)\)', text):
                with self.subTest(path=path, call=m.group(0)):
                    self.assertTrue(m.group(1).startswith('"--no-ext-diff", "--no-textconv"'), m.group(0))

    def test_every_git_call_checks_the_git_files_first(self):
        """After the run's baseline, a git call stops when .git/config, a hook, or an included file changed."""
        inc = self.repo / "conf" / "extra.cfg"
        inc.parent.mkdir()
        inc.write_text("[user]\n\tname = x\n", encoding="utf-8")
        with open(self.repo / ".git/config", "a", encoding="utf-8") as fh:
            fh.write('[include]\n\tpath = ../conf/extra.cfg\n[includeIf "gitdir:/nowhere/"]\n\tpath = "../conf/if.cfg"\n')
        cases = {"config": (self.repo / ".git/config", "[core]\n\tfsmonitor = touch fsmonitor-ran\n"),
                 "hook": (self.repo / ".git/hooks/pre-commit", "#!/bin/sh\n"),
                 "include": (inc, "[core]\n\tfsmonitor = touch fsmonitor-ran\n"),
                 "includeIf, created": (self.repo / "conf" / "if.cfg", "[core]\n\tpager = touch x\n")}
        with mock.patch.dict(os.environ, {"HOME": str(self.d)}):
            for name, (path, text) in cases.items():
                with self.subTest(name=name):
                    old = path.read_bytes() if path.exists() else None
                    ticket_mod.trust_git_dir(self.repo)
                    ticket_mod.git(self.repo, "status")
                    with open(path, "a", encoding="utf-8") as fh:
                        fh.write(text)
                    for call in (lambda: ticket_mod.git(self.repo, "status"), lambda: ticket_mod.head_commit(self.repo)):
                        with self.assertRaisesRegex(config.Stop, f"{re.escape(path.relative_to(self.repo).as_posix())} "
                                                                 "changed since the run started; nothing is posted"):
                            call()
                    if old is None:
                        path.unlink()
                    else:
                        path.write_bytes(old)
        self.assertFalse((self.repo / "fsmonitor-ran").exists())

    def test_included_file_outside_the_repo_is_not_hashed(self):
        out = self.d / "outside.cfg"
        out.write_text("[user]\n", encoding="utf-8")
        with open(self.repo / ".git/config", "a", encoding="utf-8") as fh:
            fh.write(f"[include]\n\tpath = {out.as_posix()}\n")
        files = ticket_mod.git_dir_files(self.repo)
        self.assertNotIn(out.resolve().as_posix(), files)
        self.assertIn((self.repo.resolve() / ".git/config").as_posix(), files)

    def test_interrupted_call_is_checked_too(self):
        def interrupted(argv, repo, env, events_path, timeout):
            with open(repo / ".git/config", "a", encoding="utf-8") as fh:
                fh.write("[core]\n\tfsmonitor = touch fsmonitor-ran\n")
            raise KeyboardInterrupt
        with mock.patch("agentic_factory.copilot.run_call", interrupted), \
                self.assertRaisesRegex(config.Stop, r"the work call changed \.git/config; nothing is posted"):
            self.run_main("spec", "--ticket-file", str(self.tf))
        self.assertFalse((self.repo / "fsmonitor-ran").exists())
