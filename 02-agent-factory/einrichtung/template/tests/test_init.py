"""Tests for agentic_factory/init.py: the checks on init's suggestions (pure functions, no Copilot call), and the init mode
(run_init) end to end with a fake Copilot."""
import copy
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from agentic_factory import config, copilot, init, readiness

from .fakes import CFG, E2E, FULL_CFG, PIPE, READINESS

READINESS_OLD = "# Criteria\n\n### `missing_detail`\n\nText.\n\n### `contradiction`\n\nMore.\n"
INSTALLED = ["openspec", "bmad"]


def s(value, reason="because", source="README.md:3"):
    return {"value": value, "reason": reason, "source": source}


def check(d, cfg=None, readiness_text=READINESS_OLD, installed=INSTALLED):
    return init.check_suggestions(d, cfg or copy.deepcopy(FULL_CFG), readiness_text, installed)


def tool(t):
    return check({"add_tools": {"openspec": {"spec": [s(t)]}}})


class Refusals(unittest.TestCase):
    def test_refuses_interpreters_and_network(self):
        for t in ("shell", "shell(bash:*)", "shell(python3:*)", "shell(python3.12:*)", "shell(uv:*)", "shell(npx:*)",
                  "shell(env:*)", "shell(curl:*)", "shell(ssh:*)", "shell(git push:*)", "shell(sh:*)", "shell(zsh:*)",
                  "shell(node:*)", "shell(wget:*)", "shell(scp:*)", "shell(nc:*)", "shell(/usr/bin/curl:*)",
                  "shell(timeout 60 make:*)", "shell(sudo make:*)", "shell(uv run python:*)", "shell(make; curl x:*)"):
            self.assertIsNotNone(init.refusal(t, FULL_CFG), t)
            r = tool(t)
            self.assertEqual((r["accepted"], len(r["refused"])), ([], 1), t)

    def test_package_managers_accept_only_test_and_run_subcommands(self):
        none = {"deny_tools": []}
        refused = {
            "pip": ("pip install", "pip3 install requests", "pip list", "pip3.12 download x", "pip --quiet install x",
                    "pip --index-url x install y"),
            "uv": ("uv pip install", "uv add", "uv sync", "uv --quiet pip install", "uv --quiet run pytest", "uv lock"),
            "poetry": ("poetry add", "poetry install", "poetry build"), "pipenv": ("pipenv install", "pipenv sync"),
            "pdm": ("pdm add x", "pdm install", "pdm sync"),
            "npm": ("npm i", "npm add x", "npm in", "npm isntall", "npm it", "npm install-test", "npm update", "npm rebuild",
                    "npm install", "npm ci", "npm --prefix dir install", "npm --prefix run install", "npm --silent run lint",
                    "npm --silent", "npm --silent=1", "npm --prefix=dir", "npm publish", "npm link"),
            "pnpm": ("pnpm i", "pnpm up", "pnpm update", "pnpm install", "pnpm add x"),
            "yarn": ("yarn add", "yarn up", "yarn install", "yarn --cwd run add x", "yarn --cwd sub add x"),
            "bun": ("bun install", "bun add x", "bun x cowsay", "bun update"),
            "gem": ("gem install x", "gem update"), "bundle": ("bundle install", "bundle exec rake", "bundle update"),
            "cargo": ("cargo install", "cargo run", "cargo --locked test", "cargo --manifest-path m install", "cargo publish"),
            "go": ("go get", "go install", "go run main.go", "go generate", "go -x test"),
            "composer": ("composer install", "composer require x", "composer update", "composer exec x")}
        for manager, cmds in refused.items():
            for cmd in cmds:
                self.assertEqual(init.refusal(f"shell({cmd}:*)", none), f"only test/run-style subcommands of {manager} are accepted",
                                 cmd)
        for cmd in ("npm test", "npm t", "npm tst", "npm run lint", "npm run ci", "npm test --silent", "npm --prefix=dir test",
                    "npm --prefix=dir run install-deps", "npm --prefix=dir --silent=1 run ci", "npm run x",
                    "pnpm test", "pnpm run build", "yarn test", "yarn run lint",
                    "uv run pytest", "uv --quiet=1 run pytest", "poetry run pytest -q", "pipenv run pytest", "pdm run pytest",
                    "cargo test", "cargo build", "cargo check", "cargo clippy", "cargo fmt", "cargo test --all", "go test ./...",
                    "go build", "go vet ./...", "composer test", "composer run-script lint", "mvn test", "make test"):
            self.assertIsNone(init.refusal(f"shell({cmd}:*)", none), cmd)

    def test_bun_is_an_interpreter_but_a_test_command_may_use_it(self):
        none = {"deny_tools": []}
        self.assertIn("bun is an interpreter", init.refusal("shell(bun test:*)", none))
        for cmd in ("bun test", "bun run build"):
            self.assertIsNone(init.refusal(f"shell({cmd}:*)", none, interpreters=False), cmd)
        self.assertEqual(init.refusal("shell(bun add x:*)", none, interpreters=False),
                         "only test/run-style subcommands of bun are accepted")

    def test_refuses_bare_package_managers(self):
        none = {"deny_tools": []}
        for m in ("npm", "yarn", "pnpm", "bun", "gem", "bundle", "cargo", "go", "composer", "poetry", "uv", "pip", "pip3",
                  "pipenv", "pdm", "/usr/local/bin/npm"):
            self.assertEqual(init.refusal(f"shell({m}:*)", none), "installs packages, which runs their setup code", m)
            self.assertEqual(init.refusal(f"shell({m})", none), "installs packages, which runs their setup code", m)

    def test_runner_run_is_judged_by_the_command_after_it(self):
        none = {"deny_tools": []}
        for tool_, why in (("uv --q=1 run curl x", "curl reaches the network"), ("poetry --q=1 run find .", "-exec"),
                           ("pdm --q=1 run python3", "python3 is an interpreter"), ("uv --q=1 run git status", "git tools are refused"),
                           ("uv --q=1 run npm install", "only test/run-style subcommands of npm"),
                           ("uv --q=1 run pip install x", "only test/run-style subcommands of pip"),
                           ("uv --q=1 run", "ends right after a wrapper or runner"),
                           ("uv --q=1 run env curl x", "curl reaches the network")):
            self.assertIn(why, init.refusal(f"shell({tool_}:*)", none), tool_)
        self.assertIsNone(init.refusal("shell(uv --q=1 run pytest -q:*)", none))
        self.assertIsNone(init.refusal("shell(uv --q=1 run python3 -m pytest:*)", none, interpreters=False))

    def test_runner_options_after_run_are_judged_with_options_before_run(self):
        none = {"deny_tools": []}
        for cmd in ("uv run --with evil pytest", "uv --q=1 run --with evil pytest", "uv --q=1 run --from x y",
                    "uv --q=1 run --script x.py", "uv --q=1 run -m pytest", "poetry --q=1 run --with evil x",
                    "pdm --q=1 run --from x y", "pipenv --q=1 run --script x.py"):
            why = init.refusal(f"shell({cmd}:*)", none)
            opt = next(w for w in cmd.split() if w in ("--with", "--from", "--script", "-m"))
            self.assertIn(f"the option '{opt}' after 'run' may take a value", why or "", cmd)
        self.assertIsNone(init.refusal("shell(uv --q=1 run --no-sync=1 pytest:*)", none))

    def test_hatch_and_rye_accept_only_run_and_unlisted_runners_are_refused(self):
        none = {"deny_tools": []}
        for cmd in ("hatch env create", "hatch build", "rye sync", "rye add x", "hatch --q=1 shell", "rye --q=1 install x"):
            self.assertIn("only test/run-style subcommands of", init.refusal(f"shell({cmd}:*)", none), cmd)
        for m in ("hatch", "rye"):
            self.assertEqual(init.refusal(f"shell({m}:*)", none), "installs packages, which runs their setup code")
        for cmd in ("hatch run pytest", "rye run pytest", "hatch --q=1 run pytest"):
            self.assertIsNone(init.refusal(f"shell({cmd}:*)", none), cmd)
        self.assertIn("curl reaches the network", init.refusal("shell(hatch --q=1 run curl x:*)", none))
        with mock.patch.object(copilot, "RUNNERS", {*copilot.RUNNERS, "newtool"}):  # a runner nobody listed: fail closed
            for cmd in ("newtool", "newtool sync", "newtool --q=1 sync x"):
                self.assertEqual(init.refusal(f"shell({cmd}:*)", none),
                                 "only test/run-style subcommands of newtool are accepted", cmd)
        self.assertLessEqual(set(copilot.RUNNERS), set(init.MANAGER_SUBCOMMANDS))

    def test_run_script_names_are_not_checked_as_subcommands(self):
        none = {"deny_tools": []}
        for cmd in ("npm run install", "npm run ci", "yarn run add", "pnpm run update", "npm --prefix=dir run install-deps"):
            self.assertIsNone(init.refusal(f"shell({cmd}:*)", none), cmd)

    def test_refuses_commands_that_write_or_run(self):
        for t in ("shell(find:*)", "shell(find . -name x:*)", "shell(sed -i:*)", "shell(awk:*)", "shell(xargs rm:*)", "shell(rg:*)",
                  "shell(tree:*)", "shell(sort:*)", "shell(tar x:*)", "shell(docker run:*)", "shell(podman:*)",
                  "shell(uv run find:*)", "shell(/usr/bin/sed:*)"):
            self.assertIsNotNone(init.refusal(t, {"deny_tools": []}), t)
        self.assertIn("-exec", init.refusal("shell(find:*)", {"deny_tools": []}))
        self.assertIsNone(init.refusal("shell(make find:*)", {"deny_tools": []}))  # only the command word counts

    def test_refuses_open_endings(self):
        for t in ("shell(uv run:*)", "shell(poetry run:*)", "shell(npm exec:*)", "shell(pnpm dlx:*)", "shell(npx:*)",
                  "shell(uv run:*)", "shell(npm exec jest:*)"):
            self.assertIsNotNone(init.refusal(t, {"deny_tools": []}), t)
        self.assertIsNone(init.refusal("shell(uv run pytest:*)", {"deny_tools": []}))
        self.assertIsNone(init.refusal("shell(poetry run pytest -q:*)", {"deny_tools": []}))

    def test_test_command_goes_through_refusal(self):
        for cmd in ("curl http://x/y", "git status", "npm install", "npx jest", "find . -name x", "pip install x", "docker compose run t",
                    "uv run find", "ssh host make"):
            r = check({"test_command": s(cmd)})
            self.assertEqual((r["accepted"], len(r["refused"])), ([], 1), cmd)
            self.assertIn("test_command", r["refused"][0][3])
        for cmd in ("python3 -m pytest", "uv run pytest", "npm test", "npm run test", "make test", "mvn -q test", "./gradlew test"):
            r = check({"test_command": s(cmd)})
            self.assertEqual((len(r["accepted"]), r["refused"]), (1, []), cmd)

    def test_refuses_every_git_tool(self):
        for t in ("shell(git:*)", "shell(git status:*)", "shell(git add:*)", "shell(git -c core.x=y status:*)"):
            self.assertIsNotNone(init.refusal(t, FULL_CFG), t)

    def test_refuses_deny_list_match(self):
        cfg = copy.deepcopy(FULL_CFG)
        for t in ("shell(npm install:*)", "shell(npm install left-pad:*)", "shell(npm ci:*)"):
            self.assertIn("deny_tools", init.refusal(t, cfg), t)
        self.assertIsNone(init.refusal("shell(npm run lint:*)", cfg))

    def test_refuses_non_shell_tools(self):
        for t in ("github(create_issue)", "write", "mcp(x)", "", None, 5, "shell()", "shell(:*)"):
            self.assertIsNotNone(init.refusal(t, FULL_CFG), t)

    def test_accepts_plain_tools(self):
        for t in ("shell(make test:*)", "shell(mvn -q test:*)", "shell(uv run pytest:*)", "shell(openspec:*)",
                  "shell(.specify/scripts/bash/setup-plan.sh:*)", "shell(npm run lint)"):
            self.assertIsNone(init.refusal(t, FULL_CFG), t)

    def test_unknown_key_refused(self):
        r = check({"remove_deny_tools": [s("shell(curl:*)")], "forbidden_flags": s([])})
        self.assertEqual(r["accepted"], [])
        self.assertEqual([x[0] for x in r["refused"]], ["remove_deny_tools", "forbidden_flags"])
        self.assertTrue(all(x[3] == "unknown key" for x in r["refused"]))

    def test_add_tools_targets(self):
        r = check({"add_tools": {"nope": {"spec": [s("shell(make:*)")]}, "openspec": {"review": [s("shell(make:*)")],
                                                                                     "build": [s("shell(make test:*)")]}}})
        self.assertEqual([(x[0], x[1]) for x in r["accepted"]], [("add_tools", "openspec.build")])
        reasons = {x[1]: x[3] for x in r["refused"]}
        self.assertIn("nope", reasons["nope"])
        self.assertIn("review", reasons["openspec.review"])

    def test_malformed_suggestions_refused_not_raised(self):
        r = check({"add_deny_tools": ["shell(make:*)", {"value": "shell(foo:*)"}, s(3)], "add_tools": [1],
                   "test_command": "uv run pytest", "enabled_frameworks": s("openspec")})
        self.assertEqual(r["accepted"], [])
        self.assertEqual(len(r["refused"]), 6)
        with self.assertRaises(config.Stop):
            check([1])


class Accepted(unittest.TestCase):
    def test_test_command_checked(self):
        bad = check({"test_command": s("bash -c x")})
        self.assertEqual(bad["accepted"], [])
        self.assertIn("test_command", bad["refused"][0][3])
        good = check({"test_command": s("uv run pytest")})
        self.assertEqual([x[0] for x in good["accepted"]], ["test_command"])
        self.assertEqual(good["refused"], [])

    def test_test_command_covered_by_deny_refused(self):
        r = check({"test_command": s("npm ci")})
        self.assertIn("deny_tools", r["refused"][0][3])
        r = check({"add_deny_tools": [s("shell(make:*)")], "test_command": s("make test")})
        self.assertEqual([x[0] for x in r["accepted"]], ["add_deny_tools"])
        self.assertIn("deny_tools", r["refused"][0][3])

    def test_null_suggestions_are_skipped(self):
        r = check({"test_command": None, "readiness_md": None, "enabled_frameworks": None, "add_tools": {}, "add_deny_tools": []})
        self.assertEqual((r["accepted"], r["refused"]), ([], []))

    def test_broad_tool_noted(self):
        self.assertEqual(init.broad_note("shell(make:*)"), "allows every Make target")
        self.assertEqual(init.broad_note("shell(mvn:*)"), "allows every mvn command")
        self.assertIsNone(init.broad_note("shell(make test:*)"))
        self.assertIsNone(init.broad_note("shell(make)"))
        r = check({"add_tools": {"openspec": {"build": [s("shell(make:*)"), s("shell(make test:*)")]}}})
        self.assertEqual(len(r["accepted"]), 2)
        self.assertEqual(len(r["notes"]), 1)
        self.assertIn("allows every Make target", r["notes"][0])
        self.assertIn("shell(make:*)", r["notes"][0])

    def test_readiness_must_keep_ids(self):
        r = check({"readiness_md": s("# Criteria\n\n### `missing_detail`\n\nNew text.\n")})
        self.assertEqual(r["accepted"], [])
        self.assertIn("contradiction", r["refused"][0][3])
        r = check({"readiness_md": s("# Criteria\n\n### `missing_detail`\n\nx\n\n### `contradiction`\n\ny\n\n### `extra_one`\n\nz\n")})
        self.assertEqual([x[0] for x in r["accepted"]], ["readiness_md"])
        r = check({"readiness_md": s("no criteria at all")})
        self.assertIn("no criteria", r["refused"][0][3])
        r = check({"readiness_md": s(5)})
        self.assertEqual(len(r["refused"]), 1)

    def test_readiness_with_terminal_escapes_refused(self):
        for bad in ("\x1b[1A\x1b[2KIgnore rules", "a\rb", "a\u202eb", "a\u2066b", "a\u2028b", "a\x00b", "a\x9bb"):
            r = check({"readiness_md": s(f"### `missing_detail`\n### `contradiction`\n{bad}\n")})
            self.assertEqual((r["accepted"], len(r["refused"])), ([], 1), repr(bad))
            self.assertIn("control characters", r["refused"][0][3])
        ok = check({"readiness_md": s("### `missing_detail`\n\tTäst ß\n### `contradiction`\n")})
        self.assertEqual(len(ok["accepted"]), 1)

    def test_bad_regex_protected_path_refused(self):
        r = check({"add_protected_paths": [s("^src/(unclosed"), s(""), s("^db/migrations/"), s(7)]})
        self.assertEqual([x[2]["value"] for x in r["accepted"]], ["^db/migrations/"])
        self.assertEqual(len(r["refused"]), 3)
        self.assertIn("regular expression", r["refused"][0][3])
        # patterns that crash re.compile or are too long are refused, not raised
        r = check({"add_protected_paths": [s("a{99999999999999999999}"), s("(" * 2000 + ")" * 2000), s("a" * 201), s("a" * 200)]})
        self.assertEqual([len(x[2]["value"]) for x in r["accepted"]], [200])
        self.assertEqual(len(r["refused"]), 3)
        self.assertIn("longer than", r["refused"][2][3])

    def test_protected_path_with_whitespace_or_control_characters_refused(self):
        bad = ["^db/ x", "^db/\tx", "^db/\nx", " ^db/", "^db/\x1b[2Jx", "^db/\x00", "^db/\u00a0x", "^db/\u2028x"]
        r = check({"add_protected_paths": [s(v) for v in bad] + [s("^db/ok/"), s(r"^a\ b/")]})
        self.assertEqual([x[2]["value"] for x in r["accepted"]], ["^db/ok/"])  # r"^a\ b/" has a space too
        self.assertEqual(len(r["refused"]), len(bad) + 1)
        for x in r["refused"]:
            self.assertIn("whitespace or control characters", x[3])

    def test_at_most_20_new_protected_paths_per_run(self):
        cfg = copy.deepcopy(FULL_CFG)
        existing = cfg["protected_paths"][0]
        r = check({"add_protected_paths": [s(existing)] + [s(f"^p{i}/") for i in range(23)]}, cfg)
        self.assertEqual([x[2]["value"] for x in r["accepted"]], [existing] + [f"^p{i}/" for i in range(20)])
        self.assertEqual([x[2]["value"] for x in r["refused"]], ["^p20/", "^p21/", "^p22/"])
        self.assertTrue(all("too many protected paths in one run" in x[3] for x in r["refused"]))

    def test_deny_tool_must_not_break_the_config(self):
        cfg = copy.deepcopy(FULL_CFG)
        cfg["read_tools"] = ["shell(ls:*)"]
        r = check({"add_deny_tools": [s("shell(ls:*)"), s("shell(pip install:*)"), s("pip"), s("shell(:*)")]}, cfg)
        self.assertEqual([x[2]["value"] for x in r["accepted"]], ["shell(pip install:*)"])
        self.assertEqual(len(r["refused"]), 3)
        self.assertIn("read_tools", r["refused"][0][3])

    def test_enabled_frameworks(self):
        ok = check({"enabled_frameworks": s(["openspec"])}, dict(copy.deepcopy(FULL_CFG), default_framework="openspec"))
        self.assertEqual(len(ok["accepted"]), 1)
        for value in (["speckit"], ["openspec", "zzz"], [], "openspec", [3]):
            r = check({"enabled_frameworks": s(value)})
            self.assertEqual((r["accepted"], len(r["refused"])), ([], 1), value)
        r = check({"enabled_frameworks": s(["bmad"])}, dict(copy.deepcopy(FULL_CFG), default_framework="openspec"))
        self.assertIn("default_framework", r["refused"][0][3])


class Apply(unittest.TestCase):
    def test_apply_only_adds(self):
        cfg = copy.deepcopy(FULL_CFG)
        old_deny, old_prot = list(cfg["deny_tools"]), list(cfg["protected_paths"])
        r = check({"add_deny_tools": [s("shell(pip install:*)"), s(old_deny[0]), s("shell(pip install:*)")],
                   "add_protected_paths": [s("^db/"), s(old_prot[0])]}, cfg)
        self.assertEqual(len(r["accepted"]), 5)
        new = init.apply(cfg, r["accepted"])
        self.assertEqual(new["deny_tools"], old_deny + ["shell(pip install:*)"])
        self.assertEqual(new["protected_paths"], old_prot + ["^db/"])
        self.assertEqual(cfg["deny_tools"], old_deny)  # the input is not changed
        self.assertEqual(list(new), list(cfg))

    def test_apply_values(self):
        cfg = dict(copy.deepcopy(FULL_CFG), default_framework="openspec")
        r = check({"test_command": s("make test"), "enabled_frameworks": s(["openspec"]),
                   "add_tools": {"openspec": {"spec": [s("shell(make lint:*)")], "build": [s("shell(make test:*)")]}},
                   "readiness_md": s("# C\n\n### `missing_detail`\n\n### `contradiction`\n")}, cfg)
        self.assertEqual(r["refused"], [])
        new = init.apply(cfg, r["accepted"])
        self.assertEqual(new["test_command"], "make test")
        self.assertEqual(new["enabled_frameworks"], ["openspec"])
        self.assertEqual(new["frameworks"]["openspec"]["spec_tools"], cfg["frameworks"]["openspec"]["spec_tools"] + ["shell(make lint:*)"])
        self.assertEqual(new["frameworks"]["openspec"]["build_tools"], cfg["frameworks"]["openspec"]["build_tools"] + ["shell(make test:*)"])
        self.assertEqual(new["frameworks"]["bmad"], cfg["frameworks"]["bmad"])
        self.assertEqual(init.readiness_of(r["accepted"]), "# C\n\n### `missing_detail`\n\n### `contradiction`\n")
        self.assertNotIn("readiness_md", new)
        self.assertIsNone(init.readiness_of([]))

    def test_apply_never_writes_what_it_may_not(self):
        cfg = copy.deepcopy(FULL_CFG)
        evil = [("forbidden_flags", "", s([])), ("forbidden_env", "", s({})), ("read_tools", "", s([])),
                ("max_ai_credits", "", s(10000)), ("assess", "", s({})), ("remove_deny_tools", "", s(["shell(curl:*)"])),
                ("add_tools", "openspec.spec", s("shell(bash:*)")), ("add_tools", "nope.spec", s("shell(make:*)")),
                ("add_tools", "openspec.deploy", s("shell(make:*)")), ("enabled_frameworks", "", s(["speckit", "zzz"]))]
        self.assertEqual(init.apply(cfg, evil), cfg)


class Reports(unittest.TestCase):
    def test_blocked_summary_counts(self):
        p = Path(tempfile.mkdtemp()) / "blocked.jsonl"
        rows = [{"mode": "build", "framework": "openspec", "tool": "shell", "command": "make test", "kind": "denied"}] * 3
        rows += [{"mode": "spec", "framework": "bmad", "tool": "shell", "command": "ls", "kind": "denied"}]
        rows += [{"mode": "build", "framework": "openspec", "tool": "shell", "command": "make lint", "kind": "blocked"}] * 2
        rows += [{"kind": "final", "call": "build", "text": "done"}]
        p.write_text("\n".join(json.dumps(r) for r in rows) + "\nnot json\n[1]\n", encoding="utf-8")
        out = init.blocked_summary(p).splitlines()
        self.assertEqual(len(out), 3)
        self.assertTrue(out[0].startswith("3x") and "make test" in out[0] and "build" in out[0] and "openspec" in out[0], out[0])
        self.assertTrue(out[1].startswith("2x") and "make lint" in out[1], out[1])
        self.assertTrue(out[2].startswith("1x") and "ls" in out[2], out[2])
        self.assertEqual(len(init.blocked_summary(p, limit=1).splitlines()), 2)  # one row and "and 2 more"
        self.assertIn("no blocked calls", init.blocked_summary(p.with_name("missing.jsonl")))
        p.write_text("", encoding="utf-8")
        self.assertIn("no blocked calls", init.blocked_summary(p))

    def test_blocked_summary_keeps_a_row_on_one_line(self):
        p = Path(tempfile.mkdtemp()) / "blocked.jsonl"
        p.write_text(json.dumps({"mode": "build", "framework": "x", "tool": "shell", "command": "a\nb" + "c" * 500}) + "\n")
        out = init.blocked_summary(p)
        self.assertEqual(len(out.splitlines()), 1)
        self.assertLess(len(out), 400)

    def test_report_and_diff(self):
        r = check({"test_command": s("make test", "the README says so", "README.md:12"),
                   "add_tools": {"openspec": {"build": [s("shell(make:*)")]}}, "add_deny_tools": [s("shell(curl:*)x"), s("shell(bash:*)")]})
        text = init.render_report(r)
        for part in ("make test", "the README says so", "README.md:12", "allows every Make target", "refused"):
            self.assertIn(part, text)
        self.assertIn("nothing", init.render_report({"accepted": [], "refused": [], "notes": []}).lower())
        d = init.diff("a\nb\n", "a\nc\n", "config.json")
        self.assertIn("-b", d)
        self.assertIn("+c", d)
        self.assertIn("config.json", d)
        self.assertEqual(init.diff("a\n", "a\n", "x"), "")
        self.assertIn("+c", init.diff("a", "a\nc", "x"))


class Prompt(unittest.TestCase):
    def test_config_block_and_prompt_fill(self):
        block = FULL_CFG["init"]
        self.assertEqual(list(block), ["max_ai_credits", "prompt"])
        self.assertEqual(block["max_ai_credits"], 40)
        text = copilot.fill(block["prompt"], {"config": "{}", "readiness": "R", "installed": "openspec", "blocked": "none"},
                            "the init prompt")
        self.assertIn("Reply with only the JSON object, no other text", text)
        self.assertNotIn("FACTORY-INIT", text)
        for key in init.SUGGESTION_KEYS:
            self.assertIn(f'"{key}"', text)

    def test_prompt_uses_exactly_the_four_placeholders(self):
        import string
        names = {n for _, n, _, _ in string.Formatter().parse(FULL_CFG["init"]["prompt"]) if n}
        self.assertEqual(names, {"config", "readiness", "installed", "blocked"})


class ReadinessParser(unittest.TestCase):
    def test_parse_criteria_matches_the_file_reader(self):
        p = Path(tempfile.mkdtemp()) / "readiness.md"
        p.write_text(READINESS_OLD, encoding="utf-8")
        self.assertEqual(readiness.criteria(p), readiness.parse_criteria(READINESS_OLD, "x"))
        with self.assertRaises(config.Stop):
            readiness.parse_criteria("### `a_b`\n### `a_b`\n", "x")


if __name__ == "__main__":
    unittest.main()


INIT_CFG = {k: v for k, v in CFG.items() if k != "assess"}
NEW_READINESS = "# Criteria\n\n### `missing_detail`\nUnclear.\n\n### `already_exists`\nDone already.\n\n### `no_test`\nNo test named.\n"


class InitMode(E2E, unittest.TestCase):
    """agentic-factory.py init: one Copilot call that may only read answers with the suggestions as JSON, the script checks
    and shows them, and with --apply writes config.json and readiness.md."""

    def setUp(self):
        super().setUp()
        self.cfgp = self.d / "config.json"

    def init(self, suggestions, *args, mode="init", raw=None):
        """raw: the exact text of the call's final message instead of the suggestions as JSON."""
        (self.repo / "fake-init.json").write_text(raw if raw is not None else json.dumps(suggestions), encoding="utf-8")
        return self.run_main("init", *args, mode=mode, cfg=INIT_CFG)

    def calls(self):
        p = self.d / "calls.jsonl"
        return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines()] if p.exists() else []

    def status(self):
        return subprocess.run(["git", "status", "--porcelain"], cwd=self.repo, capture_output=True, text=True).stdout

    SUGGESTIONS = {"test_command": s("make test", "the README says so", "README.md:12"),
                   "add_protected_paths": [s("^db/")],
                   "add_tools": {"openspec": {"build": [s("shell(make lint:*)")]}},
                   "readiness_md": s(NEW_READINESS)}

    def test_init_without_apply_changes_nothing(self):
        before_readiness = self.rd.read_bytes()
        rc, out = self.init(self.SUGGESTIONS)
        self.assertEqual(rc, 0, out)
        self.assertEqual(self.cfgp.read_bytes(), json.dumps(INIT_CFG).encode("utf-8"))
        self.assertEqual(self.rd.read_bytes(), before_readiness)
        self.assertEqual(self.status(), "")
        for part in ("make test", "the README says so", "README.md:12", "--- config.json (current)",
                     "+++ readiness.md (suggested)", "+### `no_test`", "nothing was changed", "--apply"):
            self.assertIn(part, out)

    def test_old_list_test_command_stops_init_before_the_call(self):
        (self.repo / "fake-init.json").write_text(json.dumps(self.SUGGESTIONS), encoding="utf-8")
        with self.assertRaisesRegex(config.Stop, 'test_command must be a string such as "make test"'):
            self.run_main("init", mode="init", cfg={**INIT_CFG, "test_command": ["./bin/phpunit"]})
        self.assertEqual(self.calls(), [])

    def test_init_apply_writes_both(self):
        rc, out = self.init(self.SUGGESTIONS, "--apply")
        self.assertEqual(rc, 0, out)
        text = self.cfgp.read_text(encoding="utf-8")
        self.assertTrue(text.startswith('{\n  "comment"'), text[:40])
        self.assertTrue(text.endswith("}\n") and not text.endswith("\n\n"))
        new = json.loads(text)
        self.assertEqual(new["test_command"], "make test")
        self.assertEqual(new["protected_paths"], INIT_CFG["protected_paths"] + ["^db/"])
        self.assertEqual(new["frameworks"]["openspec"]["build_tools"],
                         INIT_CFG["frameworks"]["openspec"]["build_tools"] + ["shell(make lint:*)"])
        self.assertEqual(list(new), list(INIT_CFG))  # keys in their order
        self.assertEqual(self.rd.read_text(encoding="utf-8"), NEW_READINESS)
        self.assertEqual(self.status(), "")  # nothing written into the project
        self.assertIn("written", out)

    def test_init_apply_writes_nothing_refused(self):
        rc, out = self.init({"add_tools": {"openspec": {"spec": [s("shell(bash:*)")]}}, "add_deny_tools": [s("shell(curl:*)x")]},
                            "--apply")
        self.assertEqual(rc, 0, out)
        self.assertEqual(self.cfgp.read_bytes(), json.dumps(INIT_CFG).encode("utf-8"))
        self.assertEqual(self.rd.read_text(encoding="utf-8"), READINESS)
        self.assertIn("refused", out)

    def test_init_refused_in_pipeline(self):
        with self.assertRaisesRegex(config.Stop, "init"):
            self.run_main("init", mode="init", cfg=INIT_CFG, env=PIPE)
        for step in ("fetch", "agent", "post"):
            with self.subTest(step=step), self.assertRaisesRegex(config.Stop, "init"):
                self.run_main("init", "--step", step, mode="init", cfg=INIT_CFG, env=PIPE)
        self.assertEqual(self.calls(), [])

    def test_init_needs_step_all(self):
        for step in ("fetch", "agent", "post"):
            with self.subTest(step=step), self.assertRaisesRegex(config.Stop, "init.*--step all"):
                self.run_main("init", "--step", step, mode="init", cfg=INIT_CFG)
        self.assertEqual(self.calls(), [])

    def test_init_final_message_forms(self):
        s1 = {"test_command": s("make test")}
        for name, raw in (("bare", json.dumps(s1)), ("fenced", "```json\n" + json.dumps(s1, indent=1) + "\n```"),
                          ("fenced without language", "```\n" + json.dumps(s1) + "\n```"),
                          ("whitespace around", "\n  " + json.dumps(s1) + "  \n")):
            with self.subTest(name):
                rc, out = self.init(None, raw=raw)
                self.assertEqual(rc, 0, out)
                self.assertIn("make test", out)
        for name, raw in (("prose before", "Here you go: " + json.dumps(s1)), ("prose after", json.dumps(s1) + " done"),
                          ("fence with prose", "Sure:\n```json\n" + json.dumps(s1) + "\n```"), ("a list", "[1]"),
                          ("a string", '"x"'), ("empty", ""), ("not JSON", "no suggestions"),
                          ("unclosed fence", "```json\n" + json.dumps(s1))):
            with self.subTest(name), self.assertRaisesRegex(config.Stop, "the init call returned no JSON object"):
                self.init(None, "--apply", raw=raw)
        self.assertEqual(self.cfgp.read_bytes(), json.dumps(INIT_CFG).encode("utf-8"))

    def test_init_call_writing_other_files_stops(self):
        (self.repo / "fake-init.json").write_text("{}", encoding="utf-8")
        with self.assertRaisesRegex(config.Stop, "README.md"):
            self.run_main("init", "--apply", mode="tamper", cfg=INIT_CFG)
        self.assertEqual(self.cfgp.read_bytes(), json.dumps(INIT_CFG).encode("utf-8"))
        self.assertEqual(self.rd.read_text(encoding="utf-8"), READINESS)

    def test_init_without_docs_no_suggestions(self):
        rc, out = self.init({})
        self.assertEqual(rc, 0, out)
        self.assertIn("keine Vorschläge", out)
        self.assertEqual(self.cfgp.read_bytes(), json.dumps(INIT_CFG).encode("utf-8"))

    def test_init_print_only_runs_no_call(self):
        rc, out = self.init(self.SUGGESTIONS, "--print-only")
        self.assertEqual(rc, 0, out)
        self.assertEqual(self.calls(), [])
        self.assertIn("--deny-tool=shell", out)
        self.assertIn("--allow-tool=read", out)
        self.assertNotIn("--allow-tool=write", out)

    def test_init_call_shape_and_prompt(self):
        (self.repo / "openspec/changes/x").mkdir(parents=True, exist_ok=True)
        rc, out = self.init({})
        self.assertEqual(rc, 0, out)
        (argv,) = self.calls()
        prompt = argv[argv.index("-p") + 1]
        self.assertIn("openspec", prompt.split("Installed frameworks:")[1])
        self.assertNotIn("speckit", prompt.split("Installed frameworks:")[1].split("Calls the factory")[0])
        self.assertIn("### `missing_detail`", prompt)  # readiness.md
        self.assertIn("no blocked calls recorded", prompt)
        self.assertIn('"test_command"', prompt)  # the config's parts
        self.assertNotIn("forbidden_env", prompt.split("Current configuration")[1])
        self.assertEqual([a for a in argv if a.startswith("--allow-tool=")], ["--allow-tool=read"])  # no write tool
        self.assertIn("--deny-tool=shell", argv)
        self.assertEqual(argv[argv.index("--max-ai-credits") + 1], "40")
        self.assertTrue(any(a.startswith("--disable-mcp-server=") for a in argv))
        self.assertIn("INIT", str(next((self.d / ".factory-local" / "proj").glob("*-init-INIT"))))

    def test_init_call_writing_any_file_stops(self):
        (self.repo / "fake-init.json").write_text("{}", encoding="utf-8")
        with self.assertRaisesRegex(config.Stop, "FACTORY-INIT.json"):
            self.run_main("init", mode="writes-init", cfg=INIT_CFG)

    def test_init_blocked_summary_in_prompt(self):
        log = self.d / ".factory-local" / "proj" / "blocked.jsonl"
        log.parent.mkdir(parents=True)
        log.write_text(json.dumps({"mode": "build", "framework": "openspec", "tool": "shell", "command": "make lint",
                                   "kind": "denied"}) + "\n", encoding="utf-8")
        rc, out = self.init({})
        (argv,) = self.calls()
        self.assertIn("1x build/openspec shell: make lint", argv[argv.index("-p") + 1])

    def test_init_uses_readiness_option(self):
        other = self.d / "other.md"
        other.write_text("# C\n\n### `only_one`\n", encoding="utf-8")
        rc, out = self.init({"readiness_md": s("# C\n\n### `only_one`\n\n### `two`\n")}, "--readiness", str(other), "--apply")
        self.assertEqual(rc, 0, out)
        self.assertIn("### `two`", other.read_text(encoding="utf-8"))
        self.assertEqual(self.rd.read_text(encoding="utf-8"), READINESS)


class InitFiles(unittest.TestCase):
    def test_dump_config_keeps_the_indent(self):
        new = {"a": [1], "b": "ä"}
        self.assertEqual(init.dump_config('{\n    "a": 1\n}\n', new), '{\n    "a": [\n        1\n    ],\n    "b": "ä"\n}\n')
        self.assertEqual(init.dump_config("{}", new), json.dumps(new, ensure_ascii=False, indent=2) + "\n")
        self.assertEqual(init.dump_config('{\n\t"a": 1\n}', {"a": 1}), '{\n\t"a": 1\n}\n')

    def test_installed_frameworks(self):
        d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, d, True)
        (d / ".specify").mkdir()
        (d / "openspec").write_text("not a folder")
        self.assertEqual(init.installed_frameworks(d, FULL_CFG), ["speckit"])
        (d / "_bmad").mkdir()
        self.assertEqual(init.installed_frameworks(d, FULL_CFG), ["speckit", "bmad"])
