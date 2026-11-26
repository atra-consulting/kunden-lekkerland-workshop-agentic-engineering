"""Tests for agentic_factory/agent.py: spec and build runs end to end, and the shell backstop."""
import contextlib
import io
import json
import os
import subprocess
import re
import shutil
import sys
import unittest
from pathlib import Path
from unittest import mock

from agentic_factory import config, revise
from agentic_factory import ticket as ticket_mod
from .fakes import CFG, E2E, KEY


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

    def test_instruction_files_are_listed(self):
        rc, out = self.run_main("spec", "--ticket-file", str(self.tf))
        self.assertEqual(rc, 0, out)
        self.assertIn("instruction files Copilot loads: ['AGENTS.md']", out)

    def test_personal_instructions_warn(self):
        (self.d / "fake-instructions.json").write_text(json.dumps([
            {"location": "repository", "sourcePath": "AGENTS.md"},
            {"location": "User home", "sourcePath": "/home/me/.copilot/copilot-instructions.md"}]), encoding="utf-8")
        rc, out = self.run_main("spec", "--ticket-file", str(self.tf))
        self.assertEqual(rc, 0, out)
        self.assertIn("WARNING: Copilot also loads instruction files from outside the project", out)
        self.assertIn("/home/me/.copilot/copilot-instructions.md", out)

    def test_instruction_list_failure_warns_and_runs(self):
        (self.d / "fake-instructions.json").write_text("fail", encoding="utf-8")
        rc, out = self.run_main("spec", "--ticket-file", str(self.tf))
        self.assertEqual(rc, 0, out)
        self.assertIn("WARNING: can't list the instruction files", out)

    def test_changed_agents_md_stops_before_the_next_call(self):
        """A later call would load the changed AGENTS.md, so the run stops after the call that changed it."""
        cfg = {k: v for k, v in CFG.items() if k != "assess"}
        cfg["test_command"] = "./bin/phpunit"
        fw = cfg["frameworks"]["openspec"]
        cfg["frameworks"] = {**cfg["frameworks"], "openspec": {**fw, "spec_prompts": [*fw["spec_prompts"]] * 2}}
        with self.assertRaisesRegex(config.Stop, r"call 1/2 changed protected paths or files AGENTS.md links to "
                                                 r"\['AGENTS.md'\]; the next call"):
            self.run_main("spec", "--ticket-file", str(self.tf), mode="agents", cfg=cfg)
        self.assertEqual(len((self.d / "calls.jsonl").read_text(encoding="utf-8").splitlines()), 1)

    def two_spec_calls(self):
        cfg = {k: v for k, v in CFG.items() if k != "assess"}
        cfg["test_command"] = "./bin/phpunit"
        fw = cfg["frameworks"]["openspec"]
        cfg["frameworks"] = {**cfg["frameworks"], "openspec": {**fw, "spec_prompts": [*fw["spec_prompts"]] * 2}}
        return cfg

    def test_changed_linked_file_stops_before_the_next_call(self):
        """The prompts tell the agent to follow the files AGENTS.md links to, so they count like AGENTS.md."""
        (self.repo / "AGENTS.md").write_text("See [rules](docs/rules.md) and [web](https://x.example/a.md).\n",
                                             encoding="utf-8")
        (self.repo / "docs").mkdir()
        (self.repo / "docs/rules.md").write_text("Be careful.\n", encoding="utf-8")
        with self.assertRaisesRegex(config.Stop, r"call 1/2 changed protected paths or files AGENTS.md links to "
                                                 r"\['docs/rules.md'\]"):
            self.run_main("spec", "--ticket-file", str(self.tf), mode="linked", cfg=self.two_spec_calls())
        shutil.rmtree(self.repo / "openspec/changes/lower-tags")
        rc, out = self.run_main("spec", "--ticket-file", str(self.tf), mode="linked")  # one call: a warning
        self.assertEqual(rc, 0, out)
        self.assertIn("WARNING: files AGENTS.md links to changed: ['docs/rules.md']", out)

    def test_changed_instruction_list_stops_before_the_next_call(self):
        with self.assertRaisesRegex(config.Stop, r"call 1/2 changed the instruction files Copilot loads"):
            self.run_main("spec", "--ticket-file", str(self.tf), mode="new-instructions", cfg=self.two_spec_calls())

    def test_committed_path_with_non_ascii_name_is_checked(self):
        """git quotes such a path without -z, and a quoted path would slip past the protected patterns."""
        with self.assertRaisesRegex(config.Stop, "call 1/2 changed protected paths .*src/\u00e4/agents.md"):
            self.run_main("spec", "--ticket-file", str(self.tf), mode="commit-unicode", cfg=self.two_spec_calls())

    def test_changed_agents_md_in_the_last_call_warns(self):
        rc, out = self.run_main("spec", "--ticket-file", str(self.tf), mode="agents")
        self.assertEqual(rc, 0, out)
        self.assertIn("WARNING: protected paths changed (the factory's check step would refuse): ['AGENTS.md']", out)

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

    def test_unknown_event_format_warns(self):
        for version, part in (("none", "Copilot events not recognized (no session.start)"),
                              ("2.0.0", "Copilot 2.0.0 is not the tested 1.0.115")):
            with self.subTest(version=version):
                (self.d / "fake-version").write_text(version, encoding="utf-8")
                shutil.rmtree(self.repo / "openspec/changes/lower-tags", ignore_errors=True)
                rc, out = self.run_main("spec", "--ticket-file", str(self.tf))
                self.assertEqual(rc, 0, out)
                self.assertIn("WARNING: " + part, out)

    def test_report_never_claims_no_blocked_calls_on_unknown_events(self):
        from types import SimpleNamespace
        from agentic_factory import agent
        for unrecognized, blocked_n, part in ((True, 0, "WARNING: Copilot events not recognized: blocked calls may be "
                                                         "missing"), (False, 0, "no blocked calls"),
                                              (True, 2, "2 blocked call(s)")):
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                agent.Work.report(SimpleNamespace(unrecognized=unrecognized, blocked=blocked_n, repo=self.repo))
            self.assertIn(part, out.getvalue())

    def test_failed_call_shows_copilots_last_lines(self):
        (self.d / "fake-exit").write_text("3", encoding="utf-8")
        with self.assertRaisesRegex(config.Stop, "copilot exited with 3"):
            self.run_main("spec", "--ticket-file", str(self.tf))
        self.assertIn("Copilot's last lines:\n    Error: the model is not available", self.last_out)

    def test_ticket_as_positional_argument(self):
        rc, out = self.run_main("spec", KEY, "--ticket-file", str(self.tf), "--print-only")
        self.assertEqual(rc, 0, out)
        rc, out = self.run_main("spec", f"https://example.atlassian.net/browse/{KEY}?x=1#c", "--key", KEY,
                                "--ticket-file", str(self.tf), "--print-only")
        self.assertEqual(rc, 0, out)
        self.assertIn("ignored the host example.atlassian.net", out)

    def test_ticket_argument_stops(self):
        cases = ((("spec", "FLAB-8", "--key", KEY), "FLAB-8 differs from --key FLAB-7"),
                 (("spec", "kaputt"), "expected a ticket key such as OFT-1 or a Jira ticket URL"),
                 (("init", KEY), "init takes no ticket"))
        for args, msg in cases:
            with self.subTest(args=args), self.assertRaisesRegex(config.Stop, msg):
                self.run_main(*args, "--ticket-file", str(self.tf))
        self.lj.write_text(json.dumps({"copilot": [sys.executable, "-I", str(self.d / "fake.py")],
                                       "jira_site": "https://example.atlassian.net"}), encoding="utf-8")
        with self.assertRaisesRegex(config.Stop, "the ticket URL is on other.example, but the configured Jira site is "
                                                 "https://example.atlassian.net"):
            self.run_main("spec", f"https://other.example/browse/{KEY}", "--jira", "mcp")
        self.assertFalse((self.d / "calls.jsonl").exists())

    def test_agent_commits_are_shown_and_checked(self):
        self.run_main("spec", "--ticket-file", str(self.tf))
        rc, out = self.run_main("build", "--ticket-file", str(self.tf), "--framework", "openspec", mode="commit")
        self.assertEqual(rc, 0, out)
        self.assertIn("the agent made 1 commit(s) on your branch, with 2 file(s)", out)
        self.assertIn("agent commit", out)
        self.assertIn("protected paths changed", out)
        self.assertIn(".github/x", out)

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
        # the spec comment names a change: it wins over the uncommitted one (OroCommerce test, F17)
        with contextlib.redirect_stdout(io.StringIO()) as out:
            name, _ = ticket_mod.find_change(self.repo, CFG["frameworks"]["openspec"], None, ("old-one", "10108"))
        self.assertEqual(name, "old-one")
        self.assertIn("building old-one, the change of the spec comment 10108", out.getvalue())
        name, _ = ticket_mod.find_change(self.repo, CFG["frameworks"]["openspec"], None, ("gone", "10108"))
        self.assertEqual(name, "new-one")  # a change that isn't there any more: as before

    def test_first_build_takes_the_change_of_the_spec_comment(self):
        spec = {"id": "10108", "created": "2026-01-01T10:00:00", "updated": "2026-01-01T10:00:00",
                "body": "[KI] agentic-factory spec key=LL-123\n\nChange: old-one. Bereitschaftsprüfung: bestanden.\n"}
        req = {"mode": "build", "key": "LL-123", "fresh": False, "me": None}
        with contextlib.redirect_stdout(io.StringIO()):
            d = revise.decide_build(None, req, [spec])
        self.assertEqual((d["kind"], d["spec_change"]), ("first", ("old-one", "10108")))
        self.assertIsNone(revise.decide_build(None, {**req, "fresh": True}, [spec])["spec_change"])


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

    def include(self, path, target, cond=None):
        with open(path, "a", encoding="utf-8") as fh:
            fh.write((f'[includeIf "{cond}"]\n' if cond else "[include]\n") + f'\tpath = "{Path(target).as_posix()}"\n')

    def test_every_git_call_checks_the_git_files_first(self):
        """After the run's baseline, a git call stops when .git/config, a hook, or an included file changed."""
        inc, cond = self.d / "extra.cfg", self.d / "if.cfg"
        inc.write_text("[user]\n\tname = x\n", encoding="utf-8")
        self.include(self.repo / ".git/config", inc)
        self.include(self.repo / ".git/config", cond, "gitdir:/nowhere/")
        cases = {"config": (self.repo / ".git/config", "[core]\n\tfsmonitor = touch fsmonitor-ran\n"),
                 "hook": (self.repo / ".git/hooks/pre-commit", "#!/bin/sh\n"),
                 "include": (inc, "[core]\n\tfsmonitor = touch fsmonitor-ran\n"),
                 "includeIf, created": (cond, "[core]\n\tpager = touch x\n")}
        with mock.patch.dict(os.environ, {"HOME": str(self.d)}):
            for name, (path, text) in cases.items():
                with self.subTest(name=name):
                    old = path.read_bytes() if path.exists() else None
                    ticket_mod.trust_git_dir(self.repo)
                    ticket_mod.git(self.repo, "status")
                    with open(path, "a", encoding="utf-8") as fh:
                        fh.write(text)
                    shown = (path.relative_to(self.repo).as_posix() if path.is_relative_to(self.repo)
                             else path.resolve().as_posix())
                    for call in (lambda: ticket_mod.git(self.repo, "status"), lambda: ticket_mod.head_commit(self.repo)):
                        with self.assertRaisesRegex(config.Stop, f"{re.escape(shown)} changed since the run started; "
                                                                 "nothing is posted"):
                            call()
                    if old is None:
                        path.unlink()
                    else:
                        path.write_bytes(old)
        self.assertFalse((self.repo / "fsmonitor-ran").exists())

    def test_nested_include_and_cycle(self):
        a, b = self.d / "a.cfg", self.d / "sub" / "b.cfg"
        b.parent.mkdir()
        a.write_text("", encoding="utf-8")
        b.write_text("", encoding="utf-8")
        self.include(self.repo / ".git/config", a)
        self.include(a, "sub/b.cfg")  # relative to the including file
        self.include(b, a)  # a cycle
        files = ticket_mod.git_dir_files(self.repo)
        self.assertIn(a.resolve().as_posix(), files)
        self.assertIn(b.resolve().as_posix(), files)
        ticket_mod.trust_git_dir(self.repo)
        with open(b, "a", encoding="utf-8") as fh:
            fh.write("[core]\n\tfsmonitor = touch fsmonitor-ran\n")
        with mock.patch.dict(os.environ, {"HOME": str(self.d)}), \
                self.assertRaisesRegex(config.Stop, "b.cfg changed since the run started"):
            ticket_mod.git(self.repo, "status")

    def test_include_from_inside_the_project_stops_before_any_call(self):
        for where in ("conf/extra.cfg", ".git/extra.cfg"):
            with self.subTest(where=where):
                cfg = (self.repo / ".git/config").read_bytes()
                (self.repo / where).parent.mkdir(exist_ok=True)
                (self.repo / where).write_text("", encoding="utf-8")
                self.include(self.d / "outer.cfg", self.repo / where)  # nested: outside, then inside
                self.include(self.repo / ".git/config", self.d / "outer.cfg")
                with self.assertRaisesRegex(config.Stop, f"git config includes .*{re.escape(where)} from inside the "
                                                         "project; the agent could change it — move it out of the "
                                                         "project"):
                    self.run_main("spec", "--ticket-file", str(self.tf))
                self.assertFalse((self.d / "calls.jsonl").exists())
                (self.repo / ".git/config").write_bytes(cfg)
                (self.d / "outer.cfg").unlink()

    def test_interrupted_call_is_checked_too(self):
        def interrupted(argv, repo, env, events_path, timeout):
            with open(repo / ".git/config", "a", encoding="utf-8") as fh:
                fh.write("[core]\n\tfsmonitor = touch fsmonitor-ran\n")
            raise KeyboardInterrupt
        with mock.patch("agentic_factory.copilot.run_call", interrupted), \
                self.assertRaisesRegex(config.Stop, r"the work call changed \.git/config; nothing is posted"):
            self.run_main("spec", "--ticket-file", str(self.tf))
        self.assertFalse((self.repo / "fsmonitor-ran").exists())
