"""Tests for agentic_factory/feedback.py: the spec and build feedback state, read from the ticket's comments."""
import unittest

from agentic_factory import clarify, config, feedback

KEY = "LL-1"
SHA = "a" * 64
COMMIT = "b" * 40
FILES = ["src/Tags.php", "tests/TagsTest.php"]


def comment(cid, body, created, author="bot", updated=""):
    return {"author": author, "body": body, "created": created, "id": str(cid), "updated": updated}


def spec_body(key=KEY, change="add-tags", checksum=SHA):
    body = clarify.render_spec(key, "openspec", "Label sdd-openspec", change, clarify.READINESS_PASSED,
                               "=== openspec/changes/add-tags/proposal.md ===\nChange: fake.\nText")
    return body + (f"\n\nSpec-Prüfsumme: {checksum}" if checksum else "")


def build_body(key=KEY, change="add-tags", files=FILES, checksum=SHA, commit=COMMIT):
    body = clarify.render_build(key, change, files, "Testbefehl make test: bestanden.")
    return (body + (f"\n\nStart-Commit: {commit}" if commit else "")
            + (f"\n\nSpec-Prüfsumme: {checksum}" if checksum else ""))


def revision_body(kind, rnd, handled=(), key=KEY, change="add-tags", files=FILES):
    parts = [clarify.marker(kind, key, rnd), f"Change: {change}. Überarbeitet."]
    if handled:
        parts.append(feedback.handled_line(list(handled)))
    if kind == "build_revision":
        parts += ["Geänderte Dateien:", clarify.fence("\n".join(files))]
    parts += [f"Start-Commit: {COMMIT}", f"Spec-Prüfsumme: {SHA}"]
    return "\n\n".join(parts)


def human(cid, created, text="Bitte ändern", **kw):
    return comment(cid, f"[Mensch] {text}", created, author="anna", **kw)


class State(unittest.TestCase):
    def test_no_results_phase_none(self):
        s = feedback.state([human(1, "2026-01-01T10:00")], KEY)
        self.assertEqual(s["phase"], "none")
        self.assertIsNone(s["last"])
        self.assertIsNone(s["last_spec"])
        self.assertIsNone(s["last_build"])
        self.assertEqual((s["revision"], s["change"], s["checksum"], s["start_commit"], s["files"]),
                         (0, None, None, None, []))
        self.assertEqual((s["new_human"], s["answers"], s["handled"]), ([], [], set()))
        self.assertEqual(feedback.state([], KEY)["phase"], "none")

    def test_spec_phase_human_after_spec(self):
        cs = [human(1, "2026-01-01T09:00"), comment(2, spec_body(), "2026-01-01T10:00"),
              human(3, "2026-01-01T11:00")]
        s = feedback.state(cs, KEY)
        self.assertEqual(s["phase"], "spec")
        self.assertEqual(s["last"]["id"], "2")
        self.assertEqual(s["last_spec"]["id"], "2")
        self.assertIsNone(s["last_build"])
        self.assertEqual([c["id"] for c in s["new_human"]], ["3"])
        self.assertEqual((s["revision"], s["change"], s["checksum"], s["start_commit"], s["files"]),
                         (1, "add-tags", SHA, None, []))

    def test_build_phase_after_build(self):
        cs = [comment(1, spec_body(), "2026-01-01T10:00"), human(2, "2026-01-01T11:00"),
              comment(3, build_body(), "2026-01-01T12:00"), human(4, "2026-01-01T13:00")]
        s = feedback.state(cs, KEY)
        self.assertEqual(s["phase"], "build")
        self.assertEqual((s["last"]["id"], s["last_spec"]["id"], s["last_build"]["id"]), ("3", "1", "3"))
        self.assertEqual([c["id"] for c in s["new_human"]], ["4"])
        self.assertEqual((s["revision"], s["change"], s["checksum"], s["start_commit"], s["files"]),
                         (1, "add-tags", SHA, COMMIT, FILES))

    def test_handled_not_repeated(self):
        cs = [comment(1, spec_body(), "2026-01-01T10:00"), human(2, "2026-01-01T11:00"),
              human(3, "2026-01-01T11:30"),
              comment(4, revision_body("spec_revision", 2, ["2"]), "2026-01-01T12:00"),
              human(5, "2026-01-01T13:00")]
        s = feedback.state(cs, KEY)
        self.assertEqual(s["handled"], {"2"})
        self.assertEqual([c["id"] for c in s["new_human"]], ["5"])
        # a handled comment stays handled, even when it is newer than the last result
        cs2 = [comment(1, spec_body(), "2026-01-01T10:00"), human(2, "2026-01-01T12:30"),
               comment(3, revision_body("spec_revision", 2, ["2", "9"]), "2026-01-01T12:00")]
        s2 = feedback.state(cs2, KEY)
        self.assertEqual(s2["handled"], {"2", "9"})
        self.assertEqual(s2["new_human"], [])

    def test_edited_human_after_handled_not_repeated(self):
        cs = [comment(1, spec_body(), "2026-01-01T10:00"),
              human(2, "2026-01-01T11:00", updated="2026-01-01T14:00"),
              comment(3, revision_body("spec_revision", 2, ["2"]), "2026-01-01T12:00")]
        self.assertEqual(feedback.state(cs, KEY)["new_human"], [])

    def test_plain_spec_after_build_ends_build_phase(self):
        cs = [comment(1, spec_body(), "2026-01-01T10:00"), comment(2, build_body(), "2026-01-01T11:00"),
              comment(3, spec_body(change="add-labels"), "2026-01-01T12:00"), human(4, "2026-01-01T13:00")]
        s = feedback.state(cs, KEY)
        self.assertEqual(s["phase"], "spec")
        self.assertEqual((s["last"]["id"], s["last_spec"]["id"], s["last_build"]["id"]), ("3", "3", "2"))
        self.assertEqual((s["revision"], s["change"], s["files"]), (1, "add-labels", []))
        self.assertEqual([c["id"] for c in s["new_human"]], ["4"])
        # a build after the fresh spec starts the build phase again
        cs.append(comment(5, build_body(change="add-labels"), "2026-01-01T14:00"))
        self.assertEqual(feedback.state(cs, KEY)["phase"], "build")

    def test_spec_questions_answers(self):
        q = clarify.render_spec_questions(KEY, "1. Welches Formular?")
        cs = [human(1, "2026-01-01T09:00"), comment(2, q, "2026-01-01T10:00"),
              human(3, "2026-01-01T11:00", "Das Profil"), human(4, "2026-01-01T12:00", "Ja")]
        s = feedback.state(cs, KEY)
        self.assertEqual(s["phase"], "none")
        self.assertEqual([c["id"] for c in s["answers"]], ["3", "4"])
        # a spec result after the questions ends them
        cs.append(comment(5, spec_body(), "2026-01-01T13:00"))
        s = feedback.state(cs, KEY)
        self.assertEqual(s["answers"], [])
        self.assertEqual(s["phase"], "spec")
        # a later questions comment starts a new answer list
        cs += [comment(6, q, "2026-01-01T14:00"), human(7, "2026-01-01T15:00")]
        self.assertEqual([c["id"] for c in feedback.state(cs, KEY)["answers"]], ["7"])

    def test_questions_and_assess_are_not_results(self):
        cs = [comment(1, clarify.render_spec_questions(KEY, "Frage"), "2026-01-01T10:00"),
              comment(2, clarify.render_assess(KEY, {"verdict": "not_ready", "reasons": [], "questions": []}),
                      "2026-01-01T11:00"),
              human(3, "2026-01-01T12:00")]
        s = feedback.state(cs, KEY)
        self.assertEqual((s["phase"], s["last"], s["last_spec"], s["last_build"]), ("none", None, None, None))
        self.assertEqual(s["new_human"], [])
        cs.insert(0, comment(0, spec_body(), "2026-01-01T09:00"))
        s = feedback.state(cs, KEY)
        self.assertEqual((s["phase"], s["last"]["id"]), ("spec", "0"))  # they don't replace the spec

    def test_untrusted_author_stops_with_fresh_hint(self):
        c = comment(7, spec_body(), "2026-01-01T10:00", author="mallory")
        with self.assertRaises(config.Stop) as cm:
            feedback.trust(c, "bot")
        self.assertIn("7", str(cm.exception))
        self.assertIn("--fresh", str(cm.exception))
        feedback.trust(comment(7, spec_body(), "2026-01-01T10:00", author="bot"), "bot")
        feedback.trust(c, None)  # no account known: the author isn't checked
        with self.assertRaises(config.Stop):
            feedback.trust(comment(7, spec_body(), "2026-01-01T10:00", author=""), "bot")
        feedback.trust(comment(7, spec_body(), "2026-01-01T10:00", author=""), None)

    def test_edited_result_stops(self):
        c = comment(8, build_body(), "2026-01-01T10:00", updated="2026-01-01T10:05")
        for me in ("bot", None):
            with self.assertRaises(config.Stop) as cm:
                feedback.trust(c, me)
            self.assertIn("8", str(cm.exception))
            self.assertIn("--fresh", str(cm.exception))
        feedback.trust(comment(8, build_body(), "2026-01-01T10:00", updated="2026-01-01T10:00"), "bot")
        feedback.trust(comment(8, build_body(), "2026-01-01T10:00", updated=""), "bot")  # offline: no updated

    def test_other_ticket_markers_ignored(self):
        cs = [comment(1, spec_body(key="LL-2"), "2026-01-01T10:00"),
              comment(2, build_body(key="LL-2"), "2026-01-01T11:00"),
              comment(3, revision_body("spec_revision", 2, ["4"], key="LL-2"), "2026-01-01T12:00"),
              comment(4, clarify.render_spec_questions("LL-2", "Frage"), "2026-01-01T12:30"),
              human(5, "2026-01-01T13:00"), human(6, "2026-01-01T09:00")]
        s = feedback.state(cs, KEY)
        self.assertEqual((s["phase"], s["last"], s["new_human"], s["answers"], s["handled"]),
                         ("none", None, [], [], set()))
        self.assertEqual(feedback.state(cs, "LL-2")["phase"], "build")
        self.assertEqual(feedback.state(cs, "LL")["phase"], "none")  # a key prefix is another key

    def test_mensch_comment_quoting_a_marker_is_no_result(self):
        cs = [human(1, "2026-01-01T10:00", clarify.marker("build", KEY)),
              comment(2, "Vorwort\n" + spec_body(), "2026-01-01T11:00"),
              comment(3, "[Mensch] " + spec_body(), "2026-01-01T12:00", author="anna")]
        self.assertEqual(feedback.state(cs, KEY)["phase"], "none")

    def test_revision_numbers(self):
        cs = [comment(1, spec_body(), "2026-01-01T10:00"),
              comment(2, revision_body("spec_revision", 2), "2026-01-01T11:00"),
              comment(3, revision_body("spec_revision", 3), "2026-01-01T12:00")]
        s = feedback.state(cs, KEY)
        self.assertEqual((s["phase"], s["revision"], s["last"]["id"], s["last_spec"]["id"]), ("spec", 3, "3", "3"))
        cs += [comment(4, build_body(), "2026-01-01T13:00"),
               comment(5, revision_body("build_revision", 2, ["9"], files=["a.php", "b.php", "c.php"]),
                       "2026-01-01T14:00")]
        s = feedback.state(cs, KEY)
        self.assertEqual((s["phase"], s["revision"], s["last"]["id"], s["last_build"]["id"], s["last_spec"]["id"]),
                         ("build", 2, "5", "5", "3"))
        self.assertEqual(s["files"], ["a.php", "b.php", "c.php"])
        self.assertEqual(s["handled"], {"9"})
        self.assertEqual(feedback.state(cs[:4], KEY)["revision"], 1)  # a plain build is revision 1

    def test_sorted_by_created_and_old_comments_without_lines(self):
        cs = [human(3, "2026-01-01T13:00"), comment(2, build_body(checksum=None, commit=None), "2026-01-01T12:00"),
              comment(1, spec_body(checksum=None), "2026-01-01T10:00")]
        s = feedback.state(cs, KEY)
        self.assertEqual((s["phase"], s["checksum"], s["start_commit"], s["files"]), ("build", None, None, FILES))
        self.assertEqual([c["id"] for c in s["new_human"]], ["3"])

    def test_lines_in_fences_are_text(self):
        body = spec_body(checksum=None).replace("Text", f"Spec-Prüfsumme: {SHA}\nBearbeitet: Kommentar 99.")
        s = feedback.state([comment(1, body, "2026-01-01T10:00")], KEY)
        self.assertEqual((s["checksum"], s["handled"], s["change"]), (None, set(), "add-tags"))


class Lines(unittest.TestCase):
    def test_handled_line(self):
        self.assertEqual(feedback.handled_line(["10234", "10240"]), "Bearbeitet: Kommentar 10234, 10240.")
        self.assertEqual(feedback.handled_line(["5"]), "Bearbeitet: Kommentar 5.")
        with self.assertRaises(ValueError):
            feedback.handled_line([])

    def test_markers(self):
        self.assertEqual(clarify.marker("spec_revision", "LL-1", 2), "[KI] agentic-factory spec überarbeitung=2 key=LL-1")
        self.assertEqual(clarify.marker("build_revision", "LL-1", 3),
                         "[KI] agentic-factory build überarbeitung=3 key=LL-1")


if __name__ == "__main__":
    unittest.main()
