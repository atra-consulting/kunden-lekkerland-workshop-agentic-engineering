"""Tests for agentic_factory/init.py: the checks on init's suggestions (pure functions, no Copilot call)."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from agentic_factory import config, copilot, init, readiness

from .fakes import FULL_CFG

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

    def test_refuses_package_installers(self):
        for t in ("shell(pip install:*)", "shell(pip3 install requests:*)", "shell(pip:*)", "shell(uv pip install:*)",
                  "shell(uv add:*)", "shell(poetry add:*)", "shell(npm i:*)", "shell(yarn add:*)", "shell(pnpm install:*)",
                  "shell(gem install:*)", "shell(bundle install:*)", "shell(cargo install:*)", "shell(go get:*)",
                  "shell(composer require:*)"):
            self.assertIn("installs packages, which runs their setup code", init.refusal(t, {"deny_tools": []}), t)
        for t in ("shell(npm run lint:*)", "shell(cargo test:*)", "shell(go test:*)", "shell(mvn test:*)", "shell(pip list:*)"):
            self.assertIsNone(init.refusal(t, {"deny_tools": []}), t)

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

    def test_bad_regex_protected_path_refused(self):
        r = check({"add_protected_paths": [s("^src/(unclosed"), s(""), s("^db/migrations/"), s(7)]})
        self.assertEqual([x[2]["value"] for x in r["accepted"]], ["^db/migrations/"])
        self.assertEqual(len(r["refused"]), 3)
        self.assertIn("regular expression", r["refused"][0][3])

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
        text = copilot.fill(block["prompt"], {"config": "{}", "readiness": "R", "installed": "openspec", "blocked": "none",
                                              "output_file": init.OUT}, "the init prompt")
        self.assertIn(init.OUT, text)
        for key in init.SUGGESTION_KEYS:
            self.assertIn(f'"{key}"', text)
        self.assertEqual(init.OUT, "FACTORY-INIT.json")

    def test_prompt_uses_exactly_the_five_placeholders(self):
        import string
        names = {n for _, n, _, _ in string.Formatter().parse(FULL_CFG["init"]["prompt"]) if n}
        self.assertEqual(names, {"config", "readiness", "installed", "blocked", "output_file"})


class ReadinessParser(unittest.TestCase):
    def test_parse_criteria_matches_the_file_reader(self):
        p = Path(tempfile.mkdtemp()) / "readiness.md"
        p.write_text(READINESS_OLD, encoding="utf-8")
        self.assertEqual(readiness.criteria(p), readiness.parse_criteria(READINESS_OLD, "x"))
        with self.assertRaises(config.Stop):
            readiness.parse_criteria("### `a_b`\n### `a_b`\n", "x")


if __name__ == "__main__":
    unittest.main()
