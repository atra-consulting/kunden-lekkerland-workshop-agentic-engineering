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

from agentic_factory import copied, config, copilot, jira_mcp
from agentic_factory import ticket as ticket_mod
from .fakes import AGENTS_LINE, CFG, FACTORY_BASE, FULL_CFG, HAVE_PWD, HERE, KEY, LAB_CFG, TICKET, drop_usage


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
        prompts, tools, env_extra = copilot.plan(LAB_CFG, mode, KEY, fw, ticket, change, spec_file)
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
        prompts, tools, _ = copilot.plan(LAB_CFG, "spec", KEY, "openspec", dict(TICKET), *BUILD["openspec"][:1], None)
        ours = copilot.copilot_argv(LAB_CFG, {}, prompts[0], tools, "/x/usage-1.json", mcp_off=["a-b", "jira"])
        self.assertEqual(drop_usage(ours), drop_usage(theirs) + ["--disable-mcp-server=a-b", "--disable-mcp-server=jira"])
        self.assertIn("--disable-builtin-mcps", theirs)


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
        return copilot.plan({**FULL_CFG, "test_command": cmd}, "build", KEY, fw, TICKET, "c", "x")

    def test_build_tool_is_whole_command(self):
        prompts, tools, _ = self.build("make test")
        self.assertEqual(tools[-1], "shell(make test:*)")
        self.assertIn("Run the tests with exactly: make test.", prompts[0])

    def test_empty_test_command_stops_build(self):
        with self.assertRaisesRegex(config.Stop, r"set test_command in config\.json \(or run init\)"):
            copilot.plan(FULL_CFG, "build", KEY, "openspec", TICKET, "c", "x")

    def test_spec_needs_no_test_command(self):
        copilot.plan(FULL_CFG, "spec", KEY, "openspec", TICKET, "c", "x")

    def test_inline_code_refused(self):
        for cmd in ("bash -c x", "sh -c x", "python3 -c 1", "node -e 1", "python3 -I -c 1", "python3 -u -c 1",
                    "node --no-warnings -e 1", "bash -x -c x", "bash -lc x", "python3 -Sc 1", "node --eval 1",
                    "python3 -W error -c 1", "bash -o pipefail -c x", "python3 -X importtime -c 1",
                    "node --require x -e 1", "node -p 1", "node --print 1", "perl -E 1", "pwsh -e x", "pwsh -enc x",
                    "powershell -ep x", "pwsh -Com x", "pwsh -COMMAND x", "python3 run.py -c x", "python3 -I run.py -e x",
                    "bash test.sh -c", "bash -xe scripts/test.sh",
                    "pwsh -C x", "powershell -co x", "uv run python -c 1", "env python3 -c 1", "timeout 60 python3 -c 1",
                    "poetry run python -c 1", "python3.12 -c 1", "PYTHON3 -c 1", "pypy3 -c 1", "php -r x", "deno eval x",
                    "bun eval x", "uv run python", "python3 -m", "env node", "FISH -c x"):
            with self.subTest(cmd=cmd), self.assertRaises(config.Stop):
                self.build(cmd)

    def test_option_ending_after_a_script_or_module_allowed(self):
        for cmd in ("python3 -m pytest -v", "python3 test.py --verbose", "node test.js --silent", "bash test.sh -x",
                    "uv run pytest -q", "python3 -m unittest discover -v"):
            with self.subTest(cmd=cmd):
                self.assertEqual(self.build(cmd)[1][-1], f"shell({cmd}:*)")

    def test_open_endings_refused(self):
        for cmd in ("python3 -m", "env node", "uv run python", "python3 -I", "python3 -I -B", "bash -x", "node --no-warnings",
                    "timeout 60 bash", "env python3 -u"):
            with self.subTest(cmd=cmd), self.assertRaisesRegex(config.Stop, "fixed script, module, or target"):
                self.build(cmd)

    def test_interpreter_name_variants_refused(self):
        for cmd in ("python3.13t -c 1", "python3.12.1 -c 1", "pypy3 -c 1", "php8.2 -r x", "python3-dbg -c 1",
                    "/usr/bin/python3.13t -c 1", "C:/Python/PYTHON.EXE -c 1", "python3.13t", "cmd /c x", "cmd /K x",
                    "julia -e 1", "julia -E 1", "tsx -e 1", "ts-node -e 1", "ts-node -p 1", "nodejs -e 1", "tclsh",
                    "node18 -e 1", "ruby3.2 -e 1", "python3.12-dbg -c 1", "bash5 -c x"):
            with self.subTest(cmd=cmd), self.assertRaises(config.Stop):
                self.build(cmd)

    def test_interpreter_name_variants_with_a_script_allowed(self):
        for cmd in ("python3.13t test.py", "python3.12.1 -m pytest", "pypy3 -m pytest -v", "php8.2 vendor/bin/phpunit",
                    "tsx test.ts", "nodejs test.js", "julia test.jl"):
            with self.subTest(cmd=cmd):
                self.build(cmd)

    def test_not_interpreters(self):
        self.assertIsNone(copilot.interpreter_name("pythonista"))
        self.assertIsNone(copilot.interpreter_name("nodes"))
        self.assertIsNone(copilot.interpreter_name("shell"))
        self.assertEqual(copilot.interpreter_name("python3.13t"), "python3.13t")

    def test_powershell_slash_switches_refused(self):
        for cmd in ("pwsh /c x", "powershell /enc x", "pwsh /Command x", "pwsh /EncodedCommand x", "powershell /co x"):
            with self.subTest(cmd=cmd), self.assertRaises(config.Stop):
                self.build(cmd)

    def test_powershell_script_allowed(self):
        for cmd in ("pwsh test.ps1", "powershell ./test.ps1 -Verb", "pwsh /tmp/test.ps1", "pwsh test.ps1 /x"):
            with self.subTest(cmd=cmd):
                self.build(cmd)

    def test_bare_wrapper_endings_refused(self):
        for cmd in ("env", "timeout", "nice", "nohup", "sudo", "xargs", "exec", "command", "busybox", "uv run",
                    "poetry run", "pipenv run", "pdm run", "hatch run", "rye run", "UV run", "timeout 60", "timeout 60s",
                    "env timeout 60", "timeout 60 env FOO=1", "timeout --signal=KILL 60", "uv run --python=3.12", "env FOO=1"):
            with self.subTest(cmd=cmd), self.assertRaisesRegex(config.Stop, "fixed script, module, or target"):
                self.build(cmd)

    def test_wrapper_with_a_target_allowed(self):
        for cmd in ("uv run pytest", "poetry run pytest -q", "timeout 60 make test", "timeout --signal=KILL 60 make test",
                    "uv run --python=3.12 pytest", "uv run -- pytest", "make run", "npm run test", "cargo run",
                    "make timeout 60"):
            with self.subTest(cmd=cmd):
                self.build(cmd)

    def test_arguments_are_never_wrappers_or_interpreters(self):
        for cmd in ("./bin/phpunit tests/Command", "./bin/phpunit --filter Command", "pytest tests/env", "pytest tests/python",
                    "pytest tests/bash tests/node", "make timeout 60", "./bin/phpunit --filter env", "npm test timeout",
                    "make test python3", "make test -c"):
            with self.subTest(cmd=cmd):
                self.assertEqual(self.build(cmd)[1][-1], f"shell({cmd}:*)")

    def test_wrapper_chain_reaches_the_interpreter(self):
        for cmd in ("env timeout 60 python3 -c 1", "sudo -n env FOO=1 bash -c x", "nice -n 10 uv run python -c 1",
                    "uv run env node", "timeout 60 nice python3 -m", "poetry run nohup bash"):
            with self.subTest(cmd=cmd), self.assertRaises(config.Stop):
                self.build(cmd)

    def test_wrapper_options_must_carry_their_value(self):
        for cmd in ("sudo -u bob python -c 1", "timeout -s KILL 60 python -c 1", "env -u FOO python -c 1",
                    "sudo -u bob make test", "nice -n 10 make test", "timeout --foreground 60 make test",
                    "uv run --frozen pytest", "uv run --with x pytest", "sudo -n", "uv run --frozen", "nice -n 10"):
            with self.subTest(cmd=cmd), self.assertRaisesRegex(config.Stop, r"--opt=value"):
                copilot.check_test_command(cmd)

    def test_wrapper_with_assignment_passes_the_check(self):
        copilot.check_test_command("env FOO=1 make test")  # the template deny list (shell(env:*)) may still stop it

    def test_shell_syntax_refused(self):
        for cmd in ("make test && rm x", "a; b", "a | b", "$(x)", "`x`", 'pytest -k "a b"', "CI=1 npm test"):
            with self.subTest(cmd=cmd), self.assertRaises(config.Stop):
                self.build(cmd)

    def test_interpreter_commands_without_inline_flags_pass(self):
        for cmd in ("python3 -m pytest", "python3 run.py", "uv run pytest", "bash test.sh", "make test", "npm test",
                    "python3 -I -B -m unittest discover -s tests -t ."):
            with self.subTest(cmd=cmd):
                self.build(cmd)

    def test_refusal_says_to_wrap_in_a_script(self):
        with self.assertRaisesRegex(config.Stop, "script file or a Make target"):
            self.build("python3 run.py -c x")

    def test_equals_sign_allowed_after_the_first_word(self):
        for cmd in ("pytest --maxfail=1", "pytest -k a=b", "a a=b"):
            with self.subTest(cmd=cmd):
                self.assertEqual(self.build(cmd)[1][-1], f"shell({cmd}:*)")

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
        self.assertEqual(copilot.fill(LAB_CFG["build_rules"], {"test_command": "./bin/phpunit"}, "x"),
                         copied.BUILD_RULES)
        self.assertEqual(FULL_CFG["build_rules"], LAB_CFG["build_rules"] + AGENTS_LINE)  # the template adds AGENTS.md
        self.assertEqual(FULL_CFG["spec_rules"], copied.SPEC_RULES + AGENTS_LINE)


DEFAULT_READ_TOOLS = ["shell(ls:*)", "shell(cat:*)", "shell(head:*)", "shell(tail:*)", "shell(wc:*)", "shell(grep:*)",
                      "shell(pwd:*)", "shell(diff:*)", "shell(stat:*)", "shell(cd:*)"]


class ReadTools(unittest.TestCase):
    """Default read-only shell tools for the spec and build calls and their revisions (read_tools in config.json)."""

    CFG = {**FULL_CFG, "test_command": "make test"}

    def plan(self, mode, fw, cfg=None):
        return copilot.plan(cfg or self.CFG, mode, KEY, fw, TICKET, "c", "x")[1]

    def test_default_list(self):
        self.assertEqual(FULL_CFG["read_tools"], DEFAULT_READ_TOOLS)

    def test_spec_and_build_get_read_tools(self):
        for fw in FULL_CFG["frameworks"]:
            for mode in ("spec", "build"):
                tools = self.plan(mode, fw)
                for entry in DEFAULT_READ_TOOLS:
                    with self.subTest(fw=fw, mode=mode, entry=entry):
                        self.assertIn(entry, tools)

    def test_revise_and_amend_get_read_tools_like_spec_and_build(self):
        """The user's answer to security I1 item 3: the revision calls get read_tools too; amend no test tool."""
        for fw, F in FULL_CFG["frameworks"].items():
            with self.subTest(fw=fw):
                _, tools, _ = copilot.revise_plan(self.CFG, KEY, fw, TICKET, "c", "<<<COMMENTS\nCOMMENTS>>>")
                self.assertEqual(tools, [*F["spec_tools"], *DEFAULT_READ_TOOLS])
                _, tools, _ = copilot.amend_plan(self.CFG, KEY, fw, TICKET, "c", "<<<COMMENTS\nCOMMENTS>>>",
                                                 "t.md", 2)
                self.assertEqual(tools, [*F["spec_tools"], *DEFAULT_READ_TOOLS])
                self.assertNotIn("shell(make test:*)", tools)

    def test_dangerous_ones_absent(self):
        words = {e[len("shell("):-len(":*)")] for e in FULL_CFG["read_tools"]}
        for bad in ("find", "sed", "awk", "xargs", "rg", "git grep", "tree", "sort"):
            self.assertNotIn(bad, words)
        for entry in FULL_CFG["read_tools"]:  # git in any form: --output= writes files, .git/config can run code
            self.assertNotIn("git", entry)

    def test_order_test_tool_last(self):
        for fw, F in FULL_CFG["frameworks"].items():
            self.assertEqual(self.plan("spec", fw), [*F["spec_tools"], *DEFAULT_READ_TOOLS])
            self.assertEqual(self.plan("build", fw), [*F["build_tools"], *DEFAULT_READ_TOOLS, "shell(make test:*)"])

    def test_empty_read_tools_add_nothing(self):
        cfg = {**self.CFG, "read_tools": []}
        self.assertEqual(self.plan("spec", "openspec", cfg), FULL_CFG["frameworks"]["openspec"]["spec_tools"])
        self.assertEqual(self.plan("build", "openspec", cfg),
                         [*FULL_CFG["frameworks"]["openspec"]["build_tools"], "shell(make test:*)"])

    def test_non_shell_entry_stops(self):
        for entry in ("write", "shell", "read", "ls", "url(example.com)", "powershell(ls:*)", "shell(ls:*", 7):
            cfg = {**self.CFG, "read_tools": ["shell(ls:*)", entry]}
            with self.subTest(entry=entry), self.assertRaisesRegex(config.Stop, "read_tools"):
                self.plan("spec", "openspec", cfg)

    def test_denied_entry_stops(self):
        cfg = {**self.CFG, "read_tools": ["shell(ls:*)", "shell(git push:*)"]}
        for mode in ("spec", "build"):
            with self.subTest(mode=mode), self.assertRaises(config.Stop) as cm:
                self.plan(mode, "openspec", cfg)
            self.assertIn("shell(git push:*)", str(cm.exception))
            self.assertIn("deny_tools", str(cm.exception))

    def test_entry_below_a_denied_prefix_stops(self):
        cfg = {**self.CFG, "read_tools": ["shell(git status:*)"], "deny_tools": ["shell(git:*)"]}
        with self.assertRaisesRegex(config.Stop, r"shell\(git status:\*\)"):
            self.plan("spec", "openspec", cfg)

    def test_check_read_tools_returns_the_list(self):
        self.assertEqual(copilot.check_read_tools(FULL_CFG), DEFAULT_READ_TOOLS)
        self.assertEqual(copilot.check_read_tools({**FULL_CFG, "read_tools": []}), [])

    def test_template_deny_list_covers_no_default(self):
        self.assertEqual(copilot.check_read_tools(FULL_CFG), DEFAULT_READ_TOOLS)
        for entry in DEFAULT_READ_TOOLS:
            self.assertIsNone(copilot.denied_by(entry[len("shell("):-len(":*)")], FULL_CFG["deny_tools"]))

    def test_assess_and_clarify_unchanged(self):
        self.assertEqual(FULL_CFG["assess"]["tools"], [])
        self.assertEqual(FULL_CFG["clarify"]["tools"], [])

    def test_lab_fixture_has_none(self):
        self.assertEqual(LAB_CFG["read_tools"], [])


class Overrides(unittest.TestCase):
    def test_model(self):
        argv = copilot.copilot_argv(CFG, {"model": "gpt-9"}, "p", [], "/u")
        self.assertEqual(argv[argv.index("--model") + 1], "gpt-9")

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


class EventCanary(unittest.TestCase):
    """A WARNING when Copilot's events may have changed shape: the blocked log, the shell backstop and the test line
    read them (arbiter ruling 2)."""

    def events(self, *lines):
        d = Path(tempfile.mkdtemp(prefix="canary-"))
        self.addCleanup(shutil.rmtree, d, True)
        p = d / "events.jsonl"
        p.write_text("\n".join(x if isinstance(x, str) else json.dumps(x) for x in lines) + "\n", encoding="utf-8")
        return p

    START = {"type": "session.start", "data": {"copilotVersion": "1.0.115"}}
    TOOL = {"type": "tool.execution_start", "data": {"toolCallId": "1", "toolName": "write", "arguments": {}}}
    MSG = {"type": "assistant.message", "data": {"content": "fertig"}}

    def test_known_events_no_warning(self):
        self.assertEqual(copilot.event_warnings(self.events(self.START, self.TOOL, self.MSG), 0), [])

    def test_no_session_start(self):
        (w,) = copilot.event_warnings(self.events(self.TOOL, self.MSG), 0)
        self.assertIn("Copilot events not recognized (no session.start)", w)
        self.assertIn("blocked.jsonl, the shell check and the test line may miss", w)

    def test_exit_0_without_tool_or_message_events(self):
        (w,) = copilot.event_warnings(self.events(self.START, {"type": "tool.run", "data": {}}), 0)
        self.assertIn("Copilot 1.0.115 events not recognized (no tool or message events)", w)
        self.assertEqual(copilot.event_warnings(self.events(self.START), 1), [])  # a failed call says so itself

    def test_other_version(self):
        start = {"type": "session.start", "data": {"copilotVersion": "1.0.200"}}
        (w,) = copilot.event_warnings(self.events(start, self.TOOL, self.MSG), 0)
        self.assertIn("Copilot 1.0.200 is not the tested 1.0.115", w)

    def test_non_json_tail(self):
        p = self.events(self.START, "Error: one", self.TOOL, "Error: two", "Error: three")
        self.assertEqual(copilot.non_json_tail(p, 2), ["Error: two", "Error: three"])
        self.assertEqual(copilot.non_json_tail(self.events(self.START), 5), [])


class AgentsMd(unittest.TestCase):
    """AGENTS.md reaches every work call: Copilot loads it, nothing switches that off, and the rules exist."""

    def test_no_custom_instructions_is_forbidden_even_in_an_old_config(self):
        old = {**FULL_CFG, "forbidden_flags": [f for f in FULL_CFG["forbidden_flags"] if f != copilot.NO_INSTRUCTIONS]}
        self.assertIn(copilot.NO_INSTRUCTIONS, FULL_CFG["forbidden_flags"])
        for cfg in (FULL_CFG, old):
            with self.assertRaisesRegex(config.Stop, "forbidden flag --no-custom-instructions"):
                copilot.copilot_argv(cfg, {}, "p", [], "/x/u.json", exe=("copilot", "--no-custom-instructions"))

    def test_missing_rules_stop_instead_of_the_lab_copy(self):
        for name, mode in (("spec_rules", "spec"), ("build_rules", "build")):
            cfg = {k: v for k, v in FULL_CFG.items() if k != name}
            cfg["test_command"] = "make test"
            with self.subTest(name=name), self.assertRaisesRegex(config.Stop, f"config.json has no {name}"):
                copilot.plan(cfg, mode, KEY, "openspec", dict(TICKET), "lower-tags", None)

    def test_build_prompt_has_the_configured_test_command_and_agents_md(self):
        cfg = {**FULL_CFG, "test_command": "make test"}
        prompts, _, _ = copilot.plan(cfg, "build", KEY, "openspec", dict(TICKET), "lower-tags", None)
        self.assertIn("Run the tests with exactly: make test.", prompts[0])
        self.assertNotIn("phpunit", prompts[0])
        self.assertTrue(prompts[0].endswith(AGENTS_LINE))

    def test_instruction_notes(self):
        self.assertEqual(copilot.instruction_notes([("repository", "AGENTS.md"), ("repository", "CLAUDE.md")]),
                         ["instruction files Copilot loads: ['AGENTS.md', 'CLAUDE.md']"])
        notes = copilot.instruction_notes([("repository", ".github/copilot-instructions.md")])
        self.assertIn("note: the project has no AGENTS.md, so the calls get no rules of your team", notes)
        notes = copilot.instruction_notes([("repository", "AGENTS.md"), ("User home", "/h/.copilot/copilot-instructions.md")])
        self.assertTrue(notes[-1].startswith("WARNING: Copilot also loads instruction files from outside the project"))
        self.assertIn("/h/.copilot/copilot-instructions.md", notes[-1])
        self.assertTrue(copilot.instruction_notes(None)[0].startswith("WARNING: can't list the instruction files"))

    def test_instruction_sources_reads_the_listing(self):
        listing = [{"location": "repository", "sourcePath": "AGENTS.md"},
                   {"location": "User home", "sourcePath": "/h/x.md"},
                   {"location": "repository", "sourcePath": "off.md", "defaultDisabled": True}]
        ok = subprocess.CompletedProcess([], 0, json.dumps(listing).encode(), b"")
        with mock.patch.object(copilot.subprocess, "run", return_value=ok) as run:
            self.assertEqual(copilot.instruction_sources(["copilot"], Path("/r"), {}),
                             [("repository", "AGENTS.md"), ("User home", "/h/x.md")])
        self.assertEqual(run.call_args.args[0], ["copilot", "instruction", "list", "--json"])
        bad = subprocess.CompletedProcess([], 1, b"", b"error")
        with mock.patch.object(copilot.subprocess, "run", return_value=bad):
            self.assertIsNone(copilot.instruction_sources(["copilot"], Path("/r"), {}))

    def test_agents_links(self):
        with tempfile.TemporaryDirectory() as d:
            repo = Path(d)
            self.assertEqual(copilot.agents_links(repo), set())
            (repo / "AGENTS.md").write_text(
                "Read [style](docs/style.md#top), [arch]( ./docs/arch.md ), [dir](conventions/), <https://x.example>,\n"
                "[web](https://example.com/a.md), [mail](mailto:a@b.c), [anchor](#rules), [out](../outside.md),\n"
                "[abs](/root.md)\n\n[ref]: docs/ref.md \"Title\"\n", encoding="utf-8")
            self.assertEqual(copilot.agents_links(repo),
                             {"docs/style.md", "docs/arch.md", "conventions", "root.md", "docs/ref.md"})
        self.assertEqual(copilot.linked_hits({"conventions", "docs/a.md"}, ["conventions/x.md", "docs/a.md", "docs/b.md",
                                                                           "conventions-old.md"]),
                         ["conventions/x.md", "docs/a.md"])

    def test_protected_hits_ignore_case_for_every_pattern(self):
        cfg = {**FULL_CFG, "protected_paths": ["^tools/"]}  # as init may add it, without (?i)
        self.assertEqual(copilot.protected_hits(cfg, ["Tools/x.sh", "src/tools/x", "FACTORY-QUESTIONS.md"]),
                         ["Tools/x.sh"])
