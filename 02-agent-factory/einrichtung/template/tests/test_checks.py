"""Tests for agentic_factory/checks.py: the verdict limits, the scans before a comment is posted, and the clarify
contract.
"""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from agentic_factory import copied, config, checks, clarify


class VerdictLimits(unittest.TestCase):
    """check_verdict has factory/assess.py parse_verdict's limits; the agent step and post both run it."""
    IDS = ["already_exists", "unclear_scope"]

    def check(self, v):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / config.ASSESSMENT
            p.write_text(json.dumps(v), encoding="utf-8")
            return checks.check_verdict(p, self.IDS)

    def nr(self, reasons=None, questions=()):
        return {"verdict": "not_ready", "reasons": reasons or [{"id": "unclear_scope", "detail": "d"}],
                "questions": list(questions)}

    def test_constants(self):
        self.assertEqual((checks.VERDICT_MAX_ITEMS, checks.MAX_DETAIL_CHARS, checks.MAX_QUESTION_CHARS), (10, 1000, 500))

    def test_boundaries_pass(self):
        self.check(self.nr([{"id": "unclear_scope", "detail": "d" * 1000}] * 10, ["q" * 500] * 10))

    def test_too_many_reasons_or_questions(self):
        with self.assertRaisesRegex(config.Stop, "at most 10 reasons and 10 questions"):
            self.check(self.nr([{"id": "unclear_scope", "detail": "d"}] * 11))
        with self.assertRaisesRegex(config.Stop, "at most 10 reasons and 10 questions"):
            self.check(self.nr(questions=["q"] * 11))

    def test_too_long(self):
        with self.assertRaisesRegex(config.Stop, "reason detail is longer than 1000"):
            self.check(self.nr([{"id": "unclear_scope", "detail": "d" * 1001}]))
        with self.assertRaisesRegex(config.Stop, "question is longer than 500"):
            self.check(self.nr(questions=["q" * 501]))

    def test_non_empty_strings(self):
        for reasons, questions in (([{"id": "unclear_scope", "detail": " "}], ()),
                                   ([{"id": "unclear_scope", "detail": 5}], ()),
                                   (None, [""]), (None, [["q"]]), (None, [None])):
            with self.subTest(reasons=reasons, questions=questions), \
                    self.assertRaisesRegex(config.Stop, "must be a non-empty string"):
                self.check(self.nr(reasons, questions))

    def test_invisible_characters(self):
        with self.assertRaisesRegex(config.Stop, "reason detail contains"):
            self.check(self.nr([{"id": "unclear_scope", "detail": "a\u200bb"}]))
        with self.assertRaisesRegex(config.Stop, "question contains"):
            self.check(self.nr(questions=["<!-- x -->"]))

    def test_factory_marker_is_not_refused(self):
        self.check(self.nr([{"id": "unclear_scope", "detail": "FACTORY-X"}], ["FACTORY-Y?"]))


class Scans(unittest.TestCase):
    """The checks every comment passes before it is posted (copied from factory/common.py)."""

    def test_clean_text_has_no_findings(self):
        self.assertEqual(copied.token_findings("hello ghp_short"), [])
        self.assertEqual(copied.invisible_findings("Zeile 1\n\tZeile 2 \u2192 \u2764\ufe0f"), [])
        self.assertEqual(checks.post_findings("[KI] hallo", 100), [])

    def test_token_pattern(self):
        self.assertTrue(copied.token_findings("x github_pat_" + "A" * 25))
        self.assertTrue(copied.token_findings("-----BEGIN RSA PRIVATE KEY-----"))

    def test_secret_value_from_the_environment(self):
        with mock.patch.dict(os.environ, {"JIRA_API_TOKEN": "s3cret-value-123"}):
            self.assertEqual(copied.secret_values(), ["s3cret-value-123"])
            self.assertEqual(copied.token_findings("a s3cret-value-123 b"), ["exact value of a secret in this step"])
            self.assertEqual(copied.redact("a s3cret-value-123 b"), "a [REDACTED] b")
        self.assertEqual(copied.token_findings("a s3cret-value-123 b"), [])

    def test_secret_values_ignores_short_and_other_names(self):
        with mock.patch.dict(os.environ, {"JIRA_API_TOKEN": "short", "OTHER_TOKEN": "long-enough-value"}):
            self.assertNotIn("short", copied.secret_values())
            self.assertNotIn("long-enough-value", copied.secret_values())

    def test_redact_token_pattern(self):
        self.assertEqual(copied.redact("a ghp_" + "b" * 30 + " c"), "a [REDACTED-PATTERN] c")

    def test_invisible_characters(self):
        f = copied.invisible_findings("a\u200bb")
        self.assertEqual(len(f), 1)
        self.assertIn("U+200B", f[0])
        self.assertTrue(copied.invisible_findings("a\u202eb"))
        self.assertTrue(copied.invisible_findings("a\U000e0041b"))

    def test_emoji_variation_selector(self):
        self.assertEqual(copied.invisible_findings("ok \u2764\ufe0f"), [])
        self.assertTrue(copied.invisible_findings("ok \u2764\ufe0f\ufe0f"))
        self.assertTrue(copied.invisible_findings("ok a\ufe0f"))

    def test_html_comment(self):
        self.assertEqual(copied.invisible_findings("a <!-- b --> c"), ["HTML comment"])

    def test_link_definition(self):
        self.assertTrue(copied.invisible_findings("a\n[x]: http://evil\nb"))
        self.assertTrue(copied.invisible_findings("> - [x]: y"))
        self.assertEqual(copied.invisible_findings("see [x] and [y](z)"), [])

    def test_control_character(self):
        f = copied.invisible_findings("a\x07b")
        self.assertEqual(f, ["control character U+0007"])

    def test_post_findings_length(self):
        self.assertEqual(checks.post_findings("[KI] " + "a" * 5, 10), [])
        self.assertEqual(checks.post_findings("[KI] " + "a" * 6, 10), ["longer than 10 characters"])

    def test_post_findings_factory_marker(self):
        self.assertEqual(checks.post_findings("[KI] FACTORY-QUESTIONS.md", 100), ["contains FACTORY-"])
        self.assertEqual(checks.post_findings("[KI] FACTORY_QUESTIONS.md", 100), [])

    def test_post_findings_needs_ki_start(self):
        self.assertEqual(checks.post_findings("hallo", 100), ["does not start with [KI]"])
        self.assertEqual(checks.post_findings(" [KI] hallo", 100), ["does not start with [KI]"])

    def test_post_findings_refuses_links_outside_a_fence(self):  # M2
        for bad in ("[hier](https://x.example)", "![](https://x.example/p?d=1)", "[x|http://x.example]",
                    "!http://x.example/p.png!"):
            with self.subTest(bad=bad):
                self.assertEqual(checks.post_findings(f"[KI] Grund x: siehe {bad}", 1000),
                                 ["link or image outside a code block"])
                for text in (clarify.render_assess("LL-1", {"verdict": "not_ready", "reasons": [{"id": "x", "detail": bad}],
                                                       "questions": []}),
                             clarify.render_assess("LL-1", {"verdict": "not_ready", "reasons": [], "questions": [bad]}),
                             clarify.render_round("LL-1", 2, 3, [], [], reasons=[{"id": "x", "detail": bad}])):
                    self.assertIn("link or image outside a code block", checks.post_findings(text, 30000))
                spec = clarify.render_spec("LL-1", "openspec", "Label sdd-openspec", "add-tags", clarify.READINESS_PASSED,
                                      f"=== a.md ===\nSiehe {bad}\n")
                self.assertEqual(checks.post_findings(spec, 30000), [])  # inside the fence: code, never a link
                self.assertEqual(checks.post_findings(clarify.render_spec_questions("LL-1", bad), 30000), [])

    def test_post_findings_collects_scan_findings(self):
        f = checks.post_findings("[KI] a\u200b <!-- x --> ghp_" + "c" * 30, 1000)
        self.assertEqual(len(f), 3)
        self.assertTrue(f[0].startswith("\\bgh"))


class ClarifyContract(unittest.TestCase):
    IDS = ["missing_detail", "unclear_scope"]

    def good(self, status="questions"):
        d = {"status": status, "questions": [], "assumptions": [], "description": ""}
        if status == "questions":
            d["questions"] = [{"id": "1", "text": "Welches Formular?", "suggestion": "Das Profil", "criterion": "missing_detail"},
                              {"id": "2", "text": "Auch alte Tags?", "suggestion": "Nein", "criterion": "unclear_scope"}]
            d["assumptions"] = [{"id": "A1", "text": "Nur das Formular"}]
        elif status == "confirm":
            d["assumptions"] = [{"id": "A1", "text": "Nur das Formular"}]
        else:
            d["description"] = "Beim Speichern werden Tags klein geschrieben.\n\nNur im Formular."
        return d

    def run_check(self, d, max_desc=2000, raw=None):
        p = Path(tempfile.mkdtemp()) / checks.CLARIFY
        p.write_text(raw if raw is not None else json.dumps(d), encoding="utf-8")
        return checks.check_clarify(p, self.IDS, max_desc)

    def fails(self, d, text, **kw):
        with self.assertRaises(config.Stop) as cm:
            self.run_check(d, **kw)
        self.assertTrue(str(cm.exception).startswith("FACTORY-CLARIFY.json"), str(cm.exception))
        self.assertIn(text, str(cm.exception))

    def test_constants(self):
        self.assertEqual((checks.CLARIFY, checks.MAX_ITEMS, checks.MAX_ITEM_CHARS, checks.MAX_CLARIFY_FILE),
                         ("FACTORY-CLARIFY.json", 10, 500, 30000))

    def test_passes_questions(self):
        d = self.good("questions")
        self.assertEqual(self.run_check(d), d)

    def test_passes_confirm(self):
        d = self.good("confirm")
        self.assertEqual(self.run_check(d), d)

    def test_passes_ready(self):
        d = self.good("ready")
        self.assertEqual(self.run_check(d), d)

    def test_passes_without_assumptions(self):
        d = self.good("confirm")
        d["assumptions"] = []
        self.assertEqual(self.run_check(d), d)

    def test_missing_file(self):
        with self.assertRaises(config.Stop) as cm:
            checks.check_clarify(Path(tempfile.mkdtemp()) / checks.CLARIFY, self.IDS, 2000)
        self.assertTrue(str(cm.exception).startswith("FACTORY-CLARIFY.json"))

    def test_file_too_big(self):
        d = self.good("ready")
        self.fails(d, "30000", raw=" " * 30001 + json.dumps(d))

    def test_invalid_json(self):
        self.fails(None, "not valid JSON", raw="{nope")

    def test_deeply_nested_json_stops(self):
        raw = "[" * 29000
        self.assertLessEqual(len(raw), checks.MAX_CLARIFY_FILE)
        self.fails(None, "not valid JSON", raw=raw)

    def test_directory_at_the_path_stops(self):
        d = Path(tempfile.mkdtemp())
        with self.assertRaises(config.Stop) as cm:
            checks.check_clarify(d, self.IDS, 2000)
        self.assertTrue(str(cm.exception).startswith("FACTORY-CLARIFY.json"))

    def test_unreadable_file_stops(self):
        p = Path(tempfile.mkdtemp()) / checks.CLARIFY
        p.write_bytes(b"\xff\xfe not utf-8")
        with self.assertRaises(config.Stop) as cm:
            checks.check_clarify(p, self.IDS, 2000)
        self.assertTrue(str(cm.exception).startswith("FACTORY-CLARIFY.json"))

    def test_whitespace_only_description_counts_as_empty(self):
        for status in ("questions", "confirm"):
            with self.subTest(status=status):
                d = self.good(status)
                d["description"] = " \n\t "
                self.assertEqual(self.run_check(d)["description"], "")

    def test_not_an_object(self):
        self.fails(None, "exactly the keys", raw="[]")

    def test_top_level_keys(self):
        d = self.good("confirm")
        del d["description"]
        self.fails(d, "exactly the keys status, questions, assumptions, description")
        d = self.good("confirm")
        d["extra"] = 1
        self.fails(d, "exactly the keys status, questions, assumptions, description")

    def test_bad_status(self):
        d = self.good("confirm")
        d["status"] = "done"
        self.fails(d, "status 'done'")

    def test_lists_must_be_lists(self):
        d = self.good("confirm")
        d["assumptions"] = "x"
        self.fails(d, "must be lists")

    def test_question_keys(self):
        d = self.good("questions")
        del d["questions"][0]["suggestion"]
        self.fails(d, "question 1 must have exactly the keys id, text, suggestion, criterion")
        d = self.good("questions")
        d["questions"][0]["more"] = "x"
        self.fails(d, "question 1 must have exactly the keys")
        d = self.good("questions")
        d["questions"][0] = "text"
        self.fails(d, "question 1 must have exactly the keys")

    def test_question_ids(self):
        d = self.good("questions")
        d["questions"][1]["id"] = "3"
        self.fails(d, "question 2 has id '3', expected '2'")
        d = self.good("questions")
        d["questions"][0]["id"] = 1
        self.fails(d, "question 1 has id 1, expected '1'")

    def test_assumption_keys(self):
        d = self.good("confirm")
        d["assumptions"][0]["extra"] = "x"
        self.fails(d, "assumption 1 must have exactly the keys id, text")
        d = self.good("confirm")
        del d["assumptions"][0]["text"]
        self.fails(d, "assumption 1 must have exactly the keys id, text")

    def test_assumption_ids(self):
        d = self.good("confirm")
        d["assumptions"] = [{"id": "A1", "text": "a"}, {"id": "A3", "text": "b"}]
        self.fails(d, "assumption 2 has id 'A3', expected 'A2'")
        d["assumptions"] = [{"id": "1", "text": "a"}]
        self.fails(d, "assumption 1 has id '1', expected 'A1'")

    def test_unknown_criterion(self):
        d = self.good("questions")
        d["questions"][0]["criterion"] = "made_up"
        self.fails(d, "question 1 names criterion 'made_up'")

    def test_too_many_questions(self):
        d = self.good("questions")
        d["questions"] = [{"id": str(i), "text": "t", "suggestion": "s", "criterion": "missing_detail"} for i in range(1, 12)]
        self.fails(d, "more than 10 questions")

    def test_ten_questions_pass(self):
        d = self.good("questions")
        d["questions"] = [{"id": str(i), "text": "t", "suggestion": "s", "criterion": "missing_detail"} for i in range(1, 11)]
        self.assertEqual(self.run_check(d), d)

    def test_too_many_assumptions(self):
        d = self.good("confirm")
        d["assumptions"] = [{"id": f"A{i}", "text": "t"} for i in range(1, 12)]
        self.fails(d, "more than 10 assumptions")

    def test_empty_strings(self):
        for path, edit in (("question 1 text", lambda d: d["questions"][0].update(text="")),
                           ("question 1 suggestion", lambda d: d["questions"][0].update(suggestion="  \n ")),
                           ("assumption 1 text", lambda d: d["assumptions"][0].update(text=""))):
            with self.subTest(path=path):
                d = self.good("questions")
                edit(d)
                self.fails(d, f"{path} is empty")

    def test_non_string(self):
        d = self.good("questions")
        d["questions"][0]["text"] = 5
        self.fails(d, "question 1 text must be a string")
        d = self.good("ready")
        d["description"] = None
        self.fails(d, "description must be a string")

    def test_too_long_strings(self):
        d = self.good("questions")
        d["questions"][0]["text"] = "a" * 501
        self.fails(d, "question 1 text is longer than 500 characters")
        d = self.good("questions")
        d["assumptions"][0]["text"] = "a" * 501
        self.fails(d, "assumption 1 text is longer than 500 characters")
        d = self.good("questions")
        d["questions"][0]["text"] = "a" * 500
        self.run_check(d)

    def test_scan_findings(self):
        for bad, what in (("a\u200bb", "invisible"), ("a <!-- x --> b", "HTML comment"), ("a\n[x]: y", "link or footnote"),
                          ("ghp_" + "c" * 30, "gh")):
            with self.subTest(what=what):
                d = self.good("questions")
                d["questions"][0]["suggestion"] = bad
                self.fails(d, "question 1 suggestion")
                d = self.good("confirm")
                d["assumptions"][0]["text"] = bad
                self.fails(d, "assumption 1 text")
        d = self.good("ready")
        d["description"] = "ok\n<!-- hidden -->"
        self.fails(d, "description: HTML comment")

    def test_links_and_images_refused(self):  # M2
        for bad in ("siehe [hier](https://x.example)", "![](https://x.example/p?d=1)", "[hier|http://x.example]",
                    "!http://x.example/p.png!", "[hier|HTTPS://x.example]", "[hier| http://x.example]", "!httpx!"):
            with self.subTest(bad=bad):
                d = self.good("questions")
                d["questions"][0]["text"] = "Welches? " + bad
                self.fails(d, "question 1 text: would become a link or image in Jira")
                d = self.good("questions")
                d["questions"][0]["suggestion"] = bad
                self.fails(d, "question 1 suggestion: would become a link or image in Jira")
                d = self.good("confirm")
                d["assumptions"][0]["text"] = bad
                self.fails(d, "assumption 1 text: would become a link or image in Jira")
                d = self.good("ready")
                d["description"] = "## Ziel\n" + bad
                self.fails(d, "description: would become a link or image in Jira")
        d = self.good("ready")
        d["description"] = "## Hinweise\n- Route `/tags` (siehe TagController), Ausruf! [x] http ok"
        self.run_check(d)

    def test_scans_run_on_the_raw_string(self):
        d = self.good("questions")
        d["questions"][0]["text"] = "a\u200b\n\nb"
        self.fails(d, "invisible or bidi-control")

    def test_questions_status_needs_questions(self):
        d = self.good("questions")
        d["questions"] = []
        self.fails(d, "status questions needs at least one question")

    def test_confirm_and_ready_have_no_questions(self):
        for status in ("confirm", "ready"):
            with self.subTest(status=status):
                d = self.good(status)
                d["questions"] = self.good("questions")["questions"]
                self.fails(d, f"status {status} must not have questions")

    def test_description_only_for_ready(self):
        for status in ("questions", "confirm"):
            with self.subTest(status=status):
                d = self.good(status)
                d["description"] = "etwas"
                self.fails(d, f"status {status} must have an empty description")

    def test_ready_needs_description(self):
        d = self.good("ready")
        d["description"] = " \n"
        self.fails(d, "status ready needs a description")

    def test_description_too_long(self):
        d = self.good("ready")
        d["description"] = "a" * 51
        self.fails(d, "description is longer than 50 characters", max_desc=50)
        d["description"] = "a" * 50
        self.run_check(d, max_desc=50)

    def test_items_are_neutralized_and_collapsed(self):
        d = self.good("questions")
        d["questions"][0]["text"] = "Siehe FACTORY-QUESTIONS.md\n\n  und   weiter\t "
        d["questions"][0]["suggestion"] = "  a\nb  "
        d["assumptions"][0]["text"] = "FACTORY-X\ny"
        out = self.run_check(d)
        self.assertEqual(out["questions"][0]["text"], "Siehe FACTORY_QUESTIONS.md und weiter")
        self.assertEqual(out["questions"][0]["suggestion"], "a b")
        self.assertEqual(out["assumptions"][0]["text"], "FACTORY_X y")
        self.assertEqual(out["questions"][0]["id"], "1")
        self.assertEqual(out["questions"][0]["criterion"], "missing_detail")

    def test_description_keeps_line_breaks_but_is_neutralized(self):
        d = self.good("ready")
        d["description"] = "Zeile 1\n\nZeile 2 FACTORY-CLARIFY.json"
        out = self.run_check(d)
        self.assertEqual(out["description"], "Zeile 1\n\nZeile 2 FACTORY_CLARIFY.json")
