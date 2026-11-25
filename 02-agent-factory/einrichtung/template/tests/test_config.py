"""Tests for agentic_factory/config.py: the Jira route."""
import json
import tempfile
import unittest
from pathlib import Path

from agentic_factory import config

from .fakes import FULL_CFG, HERE


class TemplateConfig(unittest.TestCase):
    def test_template_config_is_stack_neutral(self):
        text = json.dumps(FULL_CFG)
        for word in ("phpunit", "Symfony", "composer", "symfony.lock"):
            self.assertNotIn(word, text)
        for key in ("project_key", "bitbucket", "composer_install", "workspace_exclude", "max_patch_bytes"):
            self.assertNotIn(key, FULL_CFG)
        self.assertEqual(list(FULL_CFG["jira"]), ["max_comment_chars"])
        for name, fw in FULL_CFG["frameworks"].items():
            self.assertNotIn("run2_editable_re", fw, name)

    def test_no_team_rules_left(self):
        self.assertNotIn("rules", FULL_CFG)
        self.assertFalse((HERE / "regeln").exists())
        for path in sorted((HERE / "agentic_factory").glob("*.py")):
            text = path.read_text(encoding="utf-8")
            for word in ("TEAM RULES", "team_rules"):
                self.assertNotIn(word, text, f"{path.name} still mentions {word}")

    def test_rules_block_stops(self):
        with self.assertRaisesRegex(config.Stop, "AGENTS.md"):
            config.check_config({**FULL_CFG, "rules": {}})
        self.assertIsNone(config.check_config(FULL_CFG))


class Route(unittest.TestCase):
    API_ENV = {"JIRA_BASE_URL": "https://j.example.invalid", "JIRA_API_TOKEN": "tok"}
    PIPE = {"BITBUCKET_PIPELINE_UUID": "{abc}"}

    def test_in_pipeline(self):
        self.assertTrue(config.in_pipeline(self.PIPE))
        self.assertFalse(config.in_pipeline({}))
        self.assertFalse(config.in_pipeline({"BITBUCKET_PIPELINE_UUID": ""}))

    def test_offline_wins(self):
        self.assertEqual(config.choose_route(None, {}, True), "offline")
        self.assertEqual(config.choose_route("mcp", self.PIPE, True), "offline")
        self.assertEqual(config.choose_route("api", {}, True), "offline")

    def test_mcp_refused_in_a_pipeline(self):
        with self.assertRaisesRegex(config.Stop, "the mcp route is refused inside a pipeline"):
            config.choose_route("mcp", {**self.PIPE, **self.API_ENV}, False)

    def test_defaults(self):
        self.assertEqual(config.choose_route(None, {**self.PIPE, **self.API_ENV}, False), "api")
        self.assertEqual(config.choose_route(None, {}, False), "mcp")
        self.assertEqual(config.choose_route(None, self.API_ENV, False), "mcp")

    def test_explicit_choice(self):
        self.assertEqual(config.choose_route("mcp", {}, False), "mcp")
        self.assertEqual(config.choose_route("api", self.API_ENV, False), "api")
        self.assertEqual(config.choose_route("api", {**self.PIPE, **self.API_ENV}, False), "api")

    def test_api_needs_url_and_token(self):
        with self.assertRaisesRegex(config.Stop, "JIRA_BASE_URL"):
            config.choose_route("api", {"JIRA_API_TOKEN": "tok"}, False)
        with self.assertRaisesRegex(config.Stop, "JIRA_API_TOKEN"):
            config.choose_route("api", {"JIRA_BASE_URL": "https://j.example.invalid"}, False)
        with self.assertRaises(config.Stop):  # the pipeline default is api, so it needs the same
            config.choose_route(None, self.PIPE, False)

    def test_unknown_option(self):
        with self.assertRaises(config.Stop):
            config.choose_route("soap", {}, False)

    def test_reason(self):
        self.assertEqual(config.route_reason("api", {}, False), "--jira")
        self.assertEqual(config.route_reason("mcp", self.PIPE, False), "--jira")
        self.assertEqual(config.route_reason(None, self.PIPE, False), "default in a pipeline")
        self.assertEqual(config.route_reason(None, {}, False), "default outside a pipeline")
        self.assertEqual(config.route_reason(None, {}, True), "offline input")
        self.assertEqual(config.route_reason("api", {}, True), "offline input")


class LocalFile(unittest.TestCase):
    def load(self, text):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "local.json"
            p.write_text(text, encoding="utf-8")
            return config.load_local(p)

    def test_keys_are_machine_settings_only(self):
        self.assertEqual(config.LOCAL_KEYS, {"model", "copilot", "jira_mcp_server", "jira_site"})

    def test_unknown_local_key_stops(self):
        with self.assertRaisesRegex(config.Stop, "unknown keys"):
            self.load('{"modle": "gpt-9"}')

    def test_moved_key_stops(self):
        for key, place in (("test_command", "config.json (key test_command)"),
                           ("stack_hint", "AGENTS.md (describe the stack there)")):
            with self.subTest(key=key):
                with self.assertRaises(config.Stop) as cm:
                    self.load(json.dumps({key: "make test"}))
                self.assertIn("moved to", str(cm.exception))
                self.assertIn(place, str(cm.exception))

    def test_moved_key_stops_before_unknown_key_check(self):
        with self.assertRaisesRegex(config.Stop, "moved to"):
            self.load('{"typo": 1, "test_command": "make test"}')

    def test_example_file_loads(self):
        d = config.load_local(HERE / "local.example.json")
        self.assertLessEqual(set(d), config.LOCAL_KEYS)
        self.assertFalse(set(d) & set(config.MOVED_KEYS))
        text = (HERE / "local.example.json").read_text(encoding="utf-8")
        self.assertNotIn("test_command", text)
        self.assertNotIn("stack_hint", text)


class TestCommand(unittest.TestCase):
    MSG = 'test_command must be a string such as "make test"; an old config has a list'

    def test_string_or_empty(self):
        self.assertEqual(config.test_command({"test_command": "make test"}), "make test")
        self.assertEqual(config.test_command({"test_command": ""}), "")
        self.assertEqual(config.test_command({"test_command": None}), "")
        self.assertEqual(config.test_command({}), "")

    def test_old_list_stops_with_a_clear_message(self):
        for value in (["./bin/phpunit"], 3, {"cmd": "x"}):
            with self.subTest(value=value), self.assertRaisesRegex(config.Stop, self.MSG):
                config.test_command({"test_command": value})

    def test_not_part_of_check_config(self):
        config.check_config({"test_command": ["./bin/phpunit"]})  # assess, clarify and spec still run



class RequiredKeys(unittest.TestCase):
    def test_template_config_has_them(self):
        config.check_required(FULL_CFG, "config.json")

    def test_missing_key_is_named(self):
        for key in config.REQUIRED_KEYS:
            cfg = {k: v for k, v in FULL_CFG.items() if k != key}
            with self.subTest(key=key), self.assertRaisesRegex(config.Stop, f"config.json has no key {key}; copy it "
                                                                            "from the template's config.json"):
                config.check_required(cfg, "config.json")

    def test_not_an_object(self):
        with self.assertRaisesRegex(config.Stop, "must be a JSON object"):
            config.check_required([], "config.json")
