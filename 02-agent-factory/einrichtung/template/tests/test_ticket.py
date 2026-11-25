"""Tests for agentic_factory/ticket.py: choosing the framework."""
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
