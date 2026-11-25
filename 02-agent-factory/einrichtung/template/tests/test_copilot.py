"""Tests for agentic_factory/copilot.py: prompts, flags, environment, and the shell deny.

The parity tests run the factory's agent.py with its side effects stubbed, capture the argv it would start
Copilot with, and compare it with agentic-factory.py's. They need a checkout of the factory: set FACTORY_BASE to its
factory/ folder (agent.py, common.py, prepare.py next to a config.json). Without it they skip. They also need the
pwd module, so they skip on Windows.
"""
import builtins
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
from types import SimpleNamespace
from unittest import mock

from agentic_factory import copied, config, copilot, jira_mcp, rules
from agentic_factory import ticket as ticket_mod
from .fakes import CFG, FACTORY_BASE, FULL_CFG, HAVE_PWD, HERE, KEY, LAB_CFG, TICKET, drop_usage


BUILD = {"openspec": ("add-lowercase-tags", ["openspec/changes/add-lowercase-tags/proposal.md",
                                             "openspec/changes/add-lowercase-tags/tasks.md"]),
         "speckit": ("001-lowercase-tags", ["specs/001-lowercase-tags/plan.md", "specs/001-lowercase-tags/spec.md",
                                            "specs/001-lowercase-tags/tasks.md"]),
         "bmad": ("flab-7", ["_bmad-output/planning-artifacts/prds/prd-tags/prd.md", "_bmad-output/specs/flab-7/SPEC.md"])}


def agent_calls(mode, fw):
    """Run factory/agent.py's run() with every side effect stubbed. Returns [(argv, env)] of its copilot calls."""
    import agent
    calls = []
    tmp = tempfile.mkdtemp(prefix="parity-")
    real_open = builtins.open

    def fake_as_agent(cmd, env, timeout, cwd=None, stdout=None):
        calls.append((list(cmd), dict(env)))
        return SimpleNamespace(returncode=0, stdout=b"")

    def fake_read_json(path):
        if path.endswith("ticket.json"):
            return {k: TICKET[k] for k in ("key", "summary", "description")}
        change, paths = BUILD[fw]
        return {"key": KEY, "commit": "c" * 40, "change": change, "spec_paths": paths, "framework": fw}

    def fake_make_patch(base, out):
        real_open(out, "wb").close()
        return []

    def fake_open(path, *a, **k):  # events and usage files go to the temp folder, not /tmp or /home/agent
        return real_open(os.path.join(tmp, os.path.basename(str(path))), *a, **k)

    fake_sub = SimpleNamespace(run=lambda *a, **k: SimpleNamespace(returncode=0, stdout=b""), PIPE=-1, DEVNULL=-3,
                               STDOUT=-2, TimeoutExpired=subprocess.TimeoutExpired)
    patches = [mock.patch.object(agent, n, v) for n, v in {
        "env_allowlist": lambda step: None, "jira_key": lambda: KEY, "run_framework": lambda m, k: (fw, "label"),
        "read_json": fake_read_json, "export_tree": lambda c, k: None, "seal_for_agent": lambda f: None,
        "as_agent": fake_as_agent, "kill_agent": lambda: None, "summarize_events": lambda p: ([], 0, "", {}),
        "make_patch": fake_make_patch, "write_json": lambda p, o: None, "memory_peak": lambda: None,
        "fetch_branch": lambda k: "c" * 40, "CLONE": tmp, "subprocess": fake_sub}.items()]
    patches.append(mock.patch.object(agent, "open", fake_open, create=True))
    if hasattr(agent, "assess"):  # the readiness check has its own parity test
        patches.append(mock.patch.object(agent.assess, "enabled", lambda: False))
    patches.append(mock.patch.dict(os.environ, {"COPILOT_GITHUB_TOKEN": "x" * 20, "BITBUCKET_COMMIT": "b" * 40}))
    patches.append(mock.patch.object(sys, "argv", ["agent.py", mode]))
    with contextlib.ExitStack() as st, contextlib.redirect_stdout(io.StringIO()):
        for p in patches:
            st.enter_context(p)
        agent.run()
    return [(argv, env) for argv, env in calls if argv[0] == "copilot"]


@unittest.skipUnless(FACTORY_BASE, "set FACTORY_BASE to the factory/ folder to run the parity tests")
@unittest.skipUnless(HAVE_PWD, "factory/agent.py needs the pwd module (not on Windows)")
class Parity(unittest.TestCase):
    def test_constants_match_the_factory(self):
        import agent
        import prepare
        self.assertEqual(copied.SPEC_RULES, agent.SPEC_RULES)
        self.assertEqual(copied.BUILD_RULES, agent.BUILD_RULES)
        self.assertEqual(copied.MAX_CHARS, prepare.MAX_CHARS)
        base = agent.base_env()
        for k, v in copied.SAFE_ENV.items():
            self.assertEqual(base[k], v)

    def test_adf_text_matches_common(self):
        import common
        adf = {"type": "doc", "content": [
            {"type": "paragraph", "content": [{"type": "text", "text": "Eins"}, {"type": "hardBreak"},
                                              {"type": "text", "text": "zwei"}]},
            {"type": "bulletList", "content": [{"type": "listItem", "content": [
                {"type": "paragraph", "content": [{"type": "text", "text": "Punkt"}]}]}]},
            {"type": "heading", "content": [{"type": "text", "text": "Titel"}]}]}
        self.assertEqual(ticket_mod.adf_text(adf), common.adf_text(adf))

    def check(self, mode, fw):
        theirs = agent_calls(mode, fw)
        ticket = dict(TICKET)
        change, paths = BUILD[fw]
        spec_file = next((p for p in paths if p.endswith("SPEC.md")), paths[0])
        prompts, tools, env_extra = copilot.plan(LAB_CFG, {}, mode, KEY, fw, ticket, change, spec_file)
        ours = [copilot.copilot_argv(LAB_CFG, {}, p, tools, f"/x/usage-{i}.json") for i, p in enumerate(prompts, 1)]
        self.assertEqual(len(ours), len(theirs))
        for o, (t, env) in zip(ours, theirs):
            self.assertEqual(drop_usage(o), drop_usage(t))
            factory_extra = {k: v for k, v in env.items() if k not in __import__("agent").base_env()
                             and k != "COPILOT_GITHUB_TOKEN"}
            self.assertEqual(env_extra, factory_extra)

    def test_spec_openspec(self):
        self.check("spec", "openspec")

    def test_spec_speckit(self):
        self.check("spec", "speckit")

    def test_spec_bmad(self):
        self.check("spec", "bmad")

    def test_build_openspec(self):
        self.check("build", "openspec")

    def test_build_speckit(self):
        self.check("build", "speckit")

    def test_build_bmad(self):
        self.check("build", "bmad")

    def test_mcp_switches_only_append_to_the_factory_argv(self):
        theirs = agent_calls("spec", "openspec")[0][0]
        prompts, tools, _ = copilot.plan(LAB_CFG, {}, "spec", KEY, "openspec", dict(TICKET), *BUILD["openspec"][:1], None)
        ours = copilot.copilot_argv(LAB_CFG, {}, prompts[0], tools, "/x/usage-1.json", mcp_off=["a-b", "jira"])
        self.assertEqual(drop_usage(ours), drop_usage(theirs) + ["--disable-mcp-server=a-b", "--disable-mcp-server=jira"])
        self.assertIn("--disable-builtin-mcps", theirs)

    def test_team_rules_only_append_to_the_prompts(self):
        """What the rules block adds: each prompt is the factory's prompt, a blank line, and the block."""
        loaded = rules.load(FULL_CFG, HERE)
        for mode, fw in (("spec", "speckit"), ("build", "openspec")):
            with self.subTest(mode=mode, fw=fw):
                block = rules.block(loaded, mode)
                self.assertTrue(block.startswith("<<<TEAM RULES (regeln/"))
                theirs = agent_calls(mode, fw)
                change, paths = BUILD[fw]
                prompts, tools, _ = copilot.plan(LAB_CFG, {}, mode, KEY, fw, dict(TICKET), change, paths[0], block)
                self.assertEqual(len(prompts), len(theirs))
                for p, (t, _) in zip(prompts, theirs):
                    i = t.index("-p") + 1
                    want = t[:i] + [t[i] + "\n\n" + block] + t[i + 1:]
                    self.assertEqual(drop_usage(copilot.copilot_argv(LAB_CFG, {}, p, tools, "/x/u.json")), drop_usage(want))


class ShellDeny(unittest.TestCase):
    """I1: Copilot 1.0.115 runs shell commands it thinks are read-only, even when no shell tool is allowed. A call
    without shell tools denies shell, and a work call that ran one anyway stops."""

    def argv(self, tools, **kw):
        return copilot.copilot_argv(CFG, {}, "p", tools, "/u.json", mcp_off=["x"], **kw)

    def test_denied_after_the_config_deny_list_without_shell_tools(self):
        argv = self.argv([])
        denies = [a for a in argv if a.startswith("--deny-tool=")]
        self.assertEqual(denies, [f"--deny-tool={t}" for t in CFG["deny_tools"]] + ["--deny-tool=shell"])
        self.assertEqual(argv[argv.index("--deny-tool=shell") + 1], "--disable-mcp-server=x")
        self.assertIn("--deny-tool=shell", self.argv(["view"], file_tools=()))

    def test_not_denied_with_a_shell_tool(self):
        for tools, file_tools in ((["shell(openspec:*)"], ("read", "write")), (["shell"], ("read", "write")),
                                  ([], ("read", "shell(git status:*)"))):
            with self.subTest(tools=tools, file_tools=file_tools):
                self.assertNotIn("--deny-tool=shell", self.argv(tools, file_tools=file_tools))
        self.assertIn("--deny-tool=shell", self.argv(["shellish(x)"]))  # only shell and shell(...) count

    def test_never_in_the_config(self):
        self.assertNotIn("shell", CFG["deny_tools"])

    def test_jira_calls_deny_shell(self):
        argv = jira_mcp.jira_call_argv(CFG, {}, ["copilot"], "p", "getJiraIssue", "/u.json", [], "/plug")
        self.assertIn("--deny-tool=shell", argv)
        self.assertEqual(argv[-2:], ["--plugin-dir", "/plug"])

    def events(self, *lines):
        p = Path(tempfile.mkdtemp(prefix="shell-ev-")) / "events.jsonl"
        self.addCleanup(shutil.rmtree, p.parent, True)
        p.write_text("".join(json.dumps(x) + "\n" for x in lines) + "not json\n", encoding="utf-8")
        return p

    @staticmethod
    def start(i, tool):
        return {"type": "tool.execution_start", "data": {"toolCallId": i, "toolName": tool, "arguments": {"command": "ls"}}}

    @staticmethod
    def done(i, **d):
        return {"type": "tool.execution_complete", "data": {"toolCallId": i, **d}}

    def test_shell_ran(self):
        for tool in ("bash", "shell", "powershell", "shell_exec", "Bash"):
            with self.subTest(tool=tool):
                self.assertEqual(copilot.shell_ran(self.events(self.start("1", tool), self.done("1", success=True))),
                                 [tool])
        self.assertEqual(copilot.shell_ran(self.events(self.start("1", "bash"))), ["bash"])  # no complete: it may have run
        self.assertEqual(copilot.shell_ran(self.events(self.start("1", "bash"), self.done("1", success=False))), ["bash"])

    def test_denied_or_other_tools_are_no_shell(self):
        ev = self.events(self.start("1", "bash"), self.done("1", success=False, error={"code": "denied"}),
                         self.start("2", "read"), self.done("2", success=True), self.start("3", "view"),
                         self.done("4", success=False, error={"code": "denied"}))
        self.assertEqual(copilot.shell_ran(ev), [])


class TestCommand(unittest.TestCase):
    """The test command of config.json: the build call's test tool is derived from it."""

    def build(self, cmd, fw="openspec"):
        return copilot.plan({**FULL_CFG, "test_command": cmd}, {}, "build", KEY, fw, TICKET, "c", "x")

    def test_build_tool_is_whole_command(self):
        prompts, tools, _ = self.build("make test")
        self.assertEqual(tools[-1], "shell(make test:*)")
        self.assertIn("Run the tests with exactly: make test.", prompts[0])

    def test_empty_test_command_stops_build(self):
        with self.assertRaisesRegex(config.Stop, r"set test_command in config\.json \(or run init\)"):
            copilot.plan(FULL_CFG, {}, "build", KEY, "openspec", TICKET, "c", "x")

    def test_spec_needs_no_test_command(self):
        copilot.plan(FULL_CFG, {}, "spec", KEY, "openspec", TICKET, "c", "x")

    def test_inline_code_refused(self):
        for cmd in ("bash -c x", "sh -c x", "python3 -c 1", "node -e 1"):
            with self.subTest(cmd=cmd), self.assertRaises(config.Stop):
                self.build(cmd)

    def test_shell_syntax_refused(self):
        for cmd in ("make test && rm x", "a; b", "a | b", "$(x)", "`x`", 'pytest -k "a b"', "CI=1 npm test"):
            with self.subTest(cmd=cmd), self.assertRaises(config.Stop):
                self.build(cmd)

    def test_denied_test_tool_stops(self):
        with self.assertRaises(config.Stop) as cm:
            self.build("npx jest")
        self.assertIn("npx jest", str(cm.exception))
        self.assertIn("shell(npx:*)", str(cm.exception))

    def test_npm_test_passes_template_deny_list(self):
        self.build("npm test")
        self.assertIn("shell(npm install:*)", FULL_CFG["deny_tools"])
        self.assertNotIn("shell(npm:*)", FULL_CFG["deny_tools"])

    def test_denied_by(self):
        deny = ["shell(npm install:*)", "shell(npx:*)"]
        self.assertEqual(copilot.denied_by("npx jest", deny), "shell(npx:*)")
        self.assertEqual(copilot.denied_by("npm install", deny), "shell(npm install:*)")
        self.assertIsNone(copilot.denied_by("npm test", deny))
        self.assertIsNone(copilot.denied_by("npxy", deny))

    def test_lab_build_rules_equal_factory(self):
        self.assertEqual(copilot.fill(FULL_CFG["build_rules"], {"test_command": "./bin/phpunit"}, "x"),
                         copied.BUILD_RULES)


class Overrides(unittest.TestCase):
    def test_stack_hint(self):
        hint = "Use the existing Laminas / PHP 8.3 stack, tests with make test"
        prompts, _, _ = copilot.plan(LAB_CFG, {"stack_hint": hint}, "spec", KEY, "speckit", dict(TICKET))
        self.assertIn(hint + "; no new dependencies.", prompts[1])
        self.assertNotIn("Symfony", prompts[1])

    def test_stack_hint_ignored_elsewhere(self):
        a = copilot.plan(CFG, {"stack_hint": "X"}, "spec", KEY, "openspec", dict(TICKET))
        self.assertEqual(a, copilot.plan(CFG, {}, "spec", KEY, "openspec", dict(TICKET)))

    def test_model(self):
        argv = copilot.copilot_argv(CFG, {"model": "gpt-9"}, "p", [], "/u")
        self.assertEqual(argv[argv.index("--model") + 1], "gpt-9")

    def test_unknown_local_key_stops(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "local.json"
            p.write_text('{"test_comand": "make test"}', encoding="utf-8")
            with self.assertRaisesRegex(config.Stop, "unknown keys"):
                config.load_local(p)

    def test_example_file_loads(self):
        d = config.load_local(HERE / "local.example.json")
        self.assertEqual(d["test_command"], "make test")

    def test_forbidden_flag_stops(self):
        with self.assertRaisesRegex(config.Stop, "forbidden flag --yolo"):
            copilot.copilot_argv(CFG, {"model": "--yolo"}, "p", [], "/u")
        with self.assertRaisesRegex(config.Stop, "forbidden flag --allow-all"):
            copilot.copilot_argv(CFG, {}, "p", [], "/u", exe=("copilot", "--allow-all"))

    def test_forbidden_env_stops(self):
        with self.assertRaisesRegex(config.Stop, "COPILOT_ALLOW_ALL"):
            copilot.child_env(CFG, {}, {"PATH": "/bin", "COPILOT_ALLOW_ALL": "true"})
        env = copilot.child_env(CFG, {"SPECIFY_FEATURE_DIRECTORY": "specs/001-x"},
                              {"PATH": "/bin", "SPECKIT_COPILOT_ALLOW_ALL_TOOLS": "0", "JIRA_API_TOKEN": "t",
                               "JIRA_EMAIL": "e", "JIRA_BASE_URL": "u"})
        self.assertFalse([k for k in env if k.startswith("JIRA_")])
        self.assertEqual(env["SPECKIT_COPILOT_ALLOW_ALL_TOOLS"], "0")
        self.assertEqual(env["SPECIFY_FEATURE_DIRECTORY"], "specs/001-x")


class Windows(unittest.TestCase):
    def test_speckit_powershell_mapping(self):
        with tempfile.TemporaryDirectory() as d:
            repo = Path(d)
            ps = repo / ".specify/scripts/powershell"
            ps.mkdir(parents=True)
            for n in ("create-new-feature", "setup-plan", "setup-tasks", "check-prerequisites", "resolve-template"):
                (ps / f"{n}.ps1").write_text("", encoding="utf-8")
            tools = ticket_mod.speckit_tool_map(repo, CFG["frameworks"]["speckit"]["spec_tools"])
            self.assertIn("shell(.specify/scripts/powershell/create-new-feature.ps1:*)", tools)
            self.assertFalse([t for t in tools if "/bash/" in t])
            (ps / "setup-tasks.ps1").unlink()
            with self.assertRaisesRegex(config.Stop, "setup-tasks.ps1 is missing"):
                ticket_mod.speckit_tool_map(repo, CFG["frameworks"]["speckit"]["spec_tools"])

    def test_speckit_bash_unchanged(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / ".specify/scripts/bash").mkdir(parents=True)
            t = CFG["frameworks"]["speckit"]["spec_tools"]
            self.assertEqual(ticket_mod.speckit_tool_map(Path(d), t), t)

    def test_batch_shim_refused(self):
        with mock.patch.object(copilot.shutil, "which", return_value=r"C:\npm\copilot.CMD"), \
                mock.patch.object(copilot.os, "name", "nt"):
            with self.assertRaisesRegex(config.Stop, "batch file"):
                copilot.resolve_copilot({})

    def test_copilot_override(self):
        self.assertEqual(copilot.resolve_copilot({"copilot": ["node", "c.js"]}), ["node", "c.js"])
