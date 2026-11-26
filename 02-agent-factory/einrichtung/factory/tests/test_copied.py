"""Tests for agentic_factory/copied.py: the copied blocks equal their originals. Drift needs FACTORY_BASE;
JiraTicketDrift needs werkzeuge/schreibe-ticket/ next to this template.
"""
import ast
import re
import unittest
from pathlib import Path

from agentic_factory import clarify
from .fakes import FACTORY_BASE, HERE


def jira_ticket_path():
    return HERE / ".." / ".." / "werkzeuge" / "schreibe-ticket" / "jira_ticket.py"


@unittest.skipUnless(jira_ticket_path().exists(),
                     "werkzeuge/schreibe-ticket/jira_ticket.py is not next to this template")
class JiraTicketDrift(unittest.TestCase):
    def test_copied_functions_equal_jira_ticket_py(self):
        for name in ("bloecke", "_inline_adf", "als_adf", "als_wiki"):
            with self.subTest(name=name):
                theirs = top_level_source(jira_ticket_path(), name)
                self.assertIsNotNone(theirs, f"{name} not found in jira_ticket.py")
                self.assertEqual(top_level_source(HERE / "agentic_factory" / "copied.py", name), theirs)


def top_level_source(path, name):
    """The source text of the top-level def or assignment `name` in the Python file at path."""
    text = Path(path).read_text(encoding="utf-8")
    for node in ast.parse(text).body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name == name:
            return ast.get_source_segment(text, node)
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
            return ast.get_source_segment(text, node)
    return None


COPIED_FROM_COMMON = ("TOKEN_PATTERNS", "INVISIBLE", "EMOJI_VS", "LINK_DEF", "secret_values", "redact",
                      "token_findings", "invisible_findings")


@unittest.skipUnless(FACTORY_BASE, "set FACTORY_BASE to the factory/ folder to run the drift tests")
class Drift(unittest.TestCase):
    def test_copied_names_equal_the_factory(self):
        for name in COPIED_FROM_COMMON:
            with self.subTest(name=name):
                ours = top_level_source(HERE / "agentic_factory" / "copied.py", name)
                theirs = top_level_source(Path(FACTORY_BASE) / "common.py", name)
                self.assertIsNotNone(theirs, f"{name} not found in factory/common.py")
                self.assertEqual(ours, theirs)

    def test_render_samples_never_match_the_guards_marker(self):
        """guard.py imports /opt/factory modules, so its MARKER assignment is evaluated with `re` only."""
        text = (Path(FACTORY_BASE) / "guard.py").read_text(encoding="utf-8")
        node = next(n for n in ast.parse(text).body if isinstance(n, ast.Assign)
                    and any(isinstance(t, ast.Name) and t.id == "MARKER" for t in n.targets))
        guard_marker = eval(compile(ast.Expression(node.value), "guard.py", "eval"), {"re": re})
        self.assertTrue(clarify.RENDER_SAMPLES)
        for s in clarify.RENDER_SAMPLES:
            with self.subTest(sample=s[:60]):
                self.assertIsNone(guard_marker.search(s))
