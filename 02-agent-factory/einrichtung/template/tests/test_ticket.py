"""Tests for agentic_factory/ticket.py: choosing the framework, and the ticket argument."""
import contextlib
import io
import os
import unittest
from unittest import mock

from agentic_factory import config
from agentic_factory import ticket as ticket_mod
from .fakes import CFG, FACTORY_BASE, HAVE_PWD


class FrameworkChoice(unittest.TestCase):
    def test_option_wins_over_label(self):
        self.assertEqual(ticket_mod.choose_framework(CFG, "bmad", ["sdd-openspec"]), ("bmad", "--framework"))

    def test_one_label(self):
        self.assertEqual(ticket_mod.choose_framework(CFG, None, ["sdd-speckit", "test-nacht"]), ("speckit", "label"))

    def test_label_case_insensitive(self):
        self.assertEqual(ticket_mod.choose_framework(CFG, None, ["SDD-OpenSpec"]), ("openspec", "label"))

    def test_two_labels_stop(self):
        with self.assertRaisesRegex(config.Stop, "more than one framework label"):
            ticket_mod.choose_framework(CFG, None, ["sdd-speckit", "sdd-bmad"])

    def test_unknown_label_stops(self):
        with self.assertRaisesRegex(config.Stop, "unknown framework label"):
            ticket_mod.choose_framework(CFG, None, ["sdd-openspek"])

    def test_no_choice_stops(self):
        with self.assertRaisesRegex(config.Stop, "no framework chosen"):
            ticket_mod.choose_framework(CFG, None, ["test-nacht"])

    def test_unknown_option_stops(self):
        with self.assertRaisesRegex(config.Stop, "is not one of"):
            ticket_mod.choose_framework(CFG, "kiro", [])

    def test_same_messages_as_factory(self):
        if not FACTORY_BASE:
            self.skipTest("set FACTORY_BASE to the factory/ folder to compare with the factory")
        if not HAVE_PWD:
            self.skipTest("common.py import is fine, but keep the factory comparison on Unix")
        import common
        for labels in (["sdd-speckit", "sdd-bmad"], ["sdd-openspek"], ["test-nacht"]):
            with self.assertRaises(common.Abort) as theirs, mock.patch.dict(os.environ, {"FRAMEWORK": ""}):
                common.resolve_framework(labels)
            with self.assertRaises(config.Stop) as ours:
                ticket_mod.choose_framework(CFG, None, labels)
            self.assertEqual(str(ours.exception).split(":")[0], str(theirs.exception).split(":")[0])


class TicketArgument(unittest.TestCase):
    """The ticket as a positional argument: a key or a Jira URL (ruling R33)."""
    SITE = {"jira_site": "https://example.atlassian.net"}

    def key(self, value, local=None, env=None):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            k = ticket_mod.key_from_arg(value, CFG, self.SITE if local is None else local, env or {})
        self.said = out.getvalue()
        return k

    def test_plain_key(self):
        self.assertEqual(self.key("OFT-1"), "OFT-1")

    def test_browse_url(self):
        for url in ("https://example.atlassian.net/browse/OFT-1", "https://example.atlassian.net/browse/OFT-1/",
                    "https://example.atlassian.net/browse/OFT-1?focusedCommentId=10#comment-10",
                    "https://example.atlassian.net/browse/OFT-1#x", "https://EXAMPLE.atlassian.net:443/browse/OFT-1",
                    "https://example.atlassian.net/jira/browse/OFT-1"):
            with self.subTest(url=url):
                self.assertEqual(self.key(url), "OFT-1")

    def test_selected_issue_url(self):
        url = "https://example.atlassian.net/jira/software/projects/OFT/boards/1?selectedIssue=OFT-1&x=y"
        self.assertEqual(self.key(url), "OFT-1")

    def test_site_from_jira_base_url(self):
        self.assertEqual(self.key("https://jira.example.com/browse/OFT-2", local={},
                                  env={"JIRA_BASE_URL": "https://jira.example.com/"}), "OFT-2")

    def test_wrong_host_stops(self):
        with self.assertRaisesRegex(config.Stop, "the ticket URL is on other.atlassian.net, but the configured Jira site "
                                                 "is https://example.atlassian.net"):
            self.key("https://other.atlassian.net/browse/OFT-1")

    def test_no_site_takes_the_key_and_names_the_host(self):
        self.assertEqual(self.key("https://other.atlassian.net/browse/OFT-1", local={}), "OFT-1")
        self.assertIn("ignored the host other.atlassian.net", self.said)

    def test_junk_stops(self):
        for junk in ("oft-1", "OFT", "https://example.atlassian.net/projects/OFT", "ftp://example.atlassian.net/browse/OFT-1",
                     "https://example.atlassian.net/browse/not-a-key", "https://example.atlassian.net/?selectedIssue=x"):
            with self.subTest(junk=junk), self.assertRaisesRegex(config.Stop, "expected a ticket key such as OFT-1 or a "
                                                                              "Jira ticket URL"):
                self.key(junk)
