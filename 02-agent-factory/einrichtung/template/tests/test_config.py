"""Tests for agentic_factory/config.py: the Jira route."""
import json
import unittest

from agentic_factory import config

from .fakes import FULL_CFG


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
