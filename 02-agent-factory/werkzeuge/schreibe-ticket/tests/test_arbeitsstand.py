"""Tests für arbeitsstand.py in einem frischen Git-Repo pro Test. Kein Netz nötig."""

import contextlib
import io
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import arbeitsstand as ast  # noqa: E402


def git(root, *args):
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


def schreibe(root, pfad, text="x\n"):
    voll = os.path.join(root, pfad)
    os.makedirs(os.path.dirname(voll), exist_ok=True)
    with open(voll, "w", encoding="utf-8") as f:
        f.write(text)


class ArbeitsstandTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = os.path.realpath(self.tmp.name)
        git(self.root, "init", "-q", "-b", "main")
        git(self.root, "config", "user.email", "t@example.com")
        git(self.root, "config", "user.name", "Test")
        git(self.root, "config", "core.hooksPath", "/dev/null")
        schreibe(self.root, "src/App.php", "alt\n")
        schreibe(self.root, ".specify/memory/constitution.md", "regeln\n")
        schreibe(self.root, ".gitignore", ".specify/feature.json\n_bmad-output/\n")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "start")
        self.alt_cwd = os.getcwd()
        os.chdir(self.root)
        self.addCleanup(os.chdir, self.alt_cwd)

    def lauf(self, *argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            code = ast.main(list(argv))
        return code, out.getvalue()

    def status(self):
        return subprocess.run(["git", "status", "--porcelain", "--ignored"], cwd=self.root,
                              capture_output=True, text=True).stdout

    def test_framework_dateien_werden_entfernt(self):
        self.assertEqual(self.lauf("merken")[0], 0)
        schreibe(self.root, "specs/001-lesezeit/spec.md")
        schreibe(self.root, "specs/001-lesezeit/checklists/requirements.md")
        schreibe(self.root, ".specify/feature.json", "{}")          # ignoriert
        schreibe(self.root, "_bmad-output/specs/spec-x/SPEC.md")    # ignoriert
        schreibe(self.root, "openspec/changes/x/proposal.md")
        schreibe(self.root, "ticket-entwurf.md")
        schreibe(self.root, "src/App.php", "geändert\n")
        os.remove(os.path.join(self.root, ".specify/memory/constitution.md"))
        code, out = self.lauf("zeigen")
        self.assertEqual(code, 0)
        self.assertIn("Löschen: specs/001-lesezeit/spec.md", out)
        self.assertIn("Löschen: .specify/feature.json", out)
        self.assertIn("Löschen: _bmad-output/specs/spec-x/SPEC.md", out)
        self.assertIn("Zurücksetzen: src/App.php", out)
        self.assertTrue(os.path.exists(os.path.join(self.root, "specs/001-lesezeit/spec.md")), "zeigen ändert nichts")
        code, out = self.lauf("aufraeumen", "--ja")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.status(), "")
        self.assertFalse(os.path.exists(os.path.join(self.root, "specs")))
        self.assertFalse(os.path.exists(os.path.join(self.root, "_bmad-output")))
        with open(os.path.join(self.root, "src/App.php"), encoding="utf-8") as f:
            self.assertEqual(f.read(), "alt\n")

    def test_neue_leere_ordner_werden_entfernt(self):
        os.makedirs(os.path.join(self.root, ".specify/leer-vorher"))
        self.lauf("merken")
        os.makedirs(os.path.join(self.root, "specs/001-x/checklists"))   # nur Ordner, keine Datei
        schreibe(self.root, "specs/001-x/spec.md")
        code, out = self.lauf("aufraeumen", "--ja")
        self.assertEqual(code, 0, out)
        self.assertFalse(os.path.exists(os.path.join(self.root, "specs")))
        self.assertTrue(os.path.isdir(os.path.join(self.root, ".specify/leer-vorher")), "alte leere Ordner bleiben")

    def test_ohne_ja_nur_zeigen(self):
        self.lauf("merken")
        schreibe(self.root, "specs/001/spec.md")
        code, out = self.lauf("aufraeumen")
        self.assertEqual(code, 0)
        self.assertTrue(os.path.exists(os.path.join(self.root, "specs/001/spec.md")))

    def test_vorher_vorhandene_aenderungen_bleiben(self):
        schreibe(self.root, "notizen.txt", "meins\n")
        schreibe(self.root, "src/App.php", "meine Arbeit\n")
        code, out = self.lauf("merken")
        self.assertEqual(code, 3)
        self.assertIn("schon geändert oder neu", out)
        schreibe(self.root, "specs/001/spec.md")
        code, out = self.lauf("aufraeumen", "--ja")
        self.assertEqual(code, 0, out)
        self.assertTrue(os.path.exists(os.path.join(self.root, "notizen.txt")))
        with open(os.path.join(self.root, "src/App.php"), encoding="utf-8") as f:
            self.assertEqual(f.read(), "meine Arbeit\n")
        self.assertFalse(os.path.exists(os.path.join(self.root, "specs")))

    def test_neuer_branch_und_gestagte_datei(self):
        self.lauf("merken")
        git(self.root, "switch", "-q", "-c", "001-lesezeit")
        schreibe(self.root, "specs/001/spec.md")
        git(self.root, "add", "specs/001/spec.md")
        code, out = self.lauf("aufraeumen", "--ja")
        self.assertEqual(code, 0, out)
        self.assertIn("Zurück auf Branch: main", out)
        self.assertIn("Branch gelöscht: 001-lesezeit", out)
        self.assertEqual(self.status(), "")
        branches = subprocess.run(["git", "branch", "--format=%(refname:short)"], cwd=self.root,
                                  capture_output=True, text=True).stdout.split()
        self.assertEqual(branches, ["main"])

    def test_neue_commits_werden_gemeldet_nicht_entfernt(self):
        self.lauf("merken")
        schreibe(self.root, "specs/001/spec.md")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "framework commit")
        code, out = self.lauf("aufraeumen", "--ja")
        self.assertEqual(code, 1)
        self.assertIn("neue Commits", out)
        self.assertTrue(os.path.exists(os.path.join(self.root, "specs/001/spec.md")))

    def test_ohne_merken(self):
        code, out = self.lauf("zeigen")
        self.assertEqual(code, 2)
        self.assertIn("zuerst 'merken'", out)

    def test_stand_liegt_nicht_im_arbeitsbaum(self):
        self.lauf("merken")
        self.assertEqual(self.status(), "")

    def stand_datei(self, name):
        return os.path.join(self.root, ".git", name)

    def test_stand_heisst_schreibe_ticket_stand(self):
        self.lauf("merken")
        self.assertTrue(os.path.exists(self.stand_datei("schreibe-ticket-stand.json")))
        self.assertFalse(os.path.exists(self.stand_datei("ticket-schreiben-stand.json")))

    def test_alter_stand_wird_gelesen_und_aufgeraeumt(self):
        self.lauf("merken")
        os.rename(self.stand_datei("schreibe-ticket-stand.json"), self.stand_datei("ticket-schreiben-stand.json"))
        schreibe(self.root, "specs/001/spec.md")
        code, out = self.lauf("zeigen")
        self.assertEqual(code, 0, out)
        self.assertIn("Löschen: specs/001/spec.md", out)
        code, out = self.lauf("aufraeumen", "--ja")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.status(), "")
        self.assertFalse(os.path.exists(self.stand_datei("ticket-schreiben-stand.json")))
        self.assertEqual(self.lauf("zeigen")[0], 2, "kein Stand mehr")

    def test_neuer_stand_gewinnt_und_alter_stand_bleibt_nicht_liegen(self):
        with open(self.stand_datei("ticket-schreiben-stand.json"), "w", encoding="utf-8") as f:
            f.write("kaputt")
        self.lauf("merken")
        self.assertFalse(os.path.exists(self.stand_datei("ticket-schreiben-stand.json")))
        self.assertEqual(self.lauf("aufraeumen", "--ja")[0], 0)
        self.assertEqual(self.lauf("zeigen")[0], 2)


if __name__ == "__main__":
    unittest.main()
