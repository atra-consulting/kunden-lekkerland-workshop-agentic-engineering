"""Tests for agentic_factory/snapshot.py: the spec checksum, the local copy of the spec files, and the diff against it."""
import hashlib
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from agentic_factory import config, fetch, snapshot
from .fakes import CFG, E2E

GIT_ENV = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}


class SnapshotTest(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp(prefix="local-snapshot-"))
        self.addCleanup(shutil.rmtree, self.d, True)
        self.repo = self.d / "proj"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=self.repo, check=True, env=GIT_ENV)
        patcher = mock.patch.dict(os.environ, {"HOME": str(self.d), "USERPROFILE": str(self.d)})
        patcher.start()
        self.addCleanup(patcher.stop)

    def write(self, path, text, raw=None):
        p = self.repo / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(raw if raw is not None else text.encode("utf-8"))

    def home_dest(self, name="x"):
        return Path.home() / ".factory-local" / "proj" / "specs" / "LL-1" / "c" / name


class Checksum(SnapshotTest):
    def test_checksum_order_independent(self):
        self.write("a.md", "one\n")
        self.write("b.md", "two\n")
        self.assertEqual(snapshot.checksum(self.repo, ["a.md", "b.md"]), snapshot.checksum(self.repo, ["b.md", "a.md"]))

    def test_checksum_is_sha256_over_path_and_bytes(self):
        self.write("a.md", "one\n")
        self.write("b.md", "two\n")
        want = hashlib.sha256(b"a.md\0one\n\0b.md\0two\n\0").hexdigest()
        self.assertEqual(snapshot.checksum(self.repo, ["b.md", "a.md"]), want)

    def test_checksum_changes_on_edit(self):
        self.write("a.md", "one\n")
        before = snapshot.checksum(self.repo, ["a.md"])
        self.write("a.md", "one!\n")
        self.assertNotEqual(snapshot.checksum(self.repo, ["a.md"]), before)

    def test_checksum_counts_crlf(self):
        self.write("a.md", "", raw=b"one\ntwo\n")
        lf = snapshot.checksum(self.repo, ["a.md"])
        self.write("a.md", "", raw=b"one\r\ntwo\r\n")
        self.assertNotEqual(snapshot.checksum(self.repo, ["a.md"]), lf)

    def test_checksum_counts_the_path(self):
        self.write("a.md", "same\n")
        self.write("b.md", "same\n")
        self.assertNotEqual(snapshot.checksum(self.repo, ["a.md"]), snapshot.checksum(self.repo, ["b.md"]))

    def test_checksum_of_a_missing_file_stops(self):
        with self.assertRaises(config.Stop):
            snapshot.checksum(self.repo, ["gone.md"])


class SaveAndDiff(SnapshotTest):
    def test_save_then_diff_shows_edit_add_remove(self):
        self.write("openspec/changes/c/proposal.md", "line1\nline2\n")
        self.write("openspec/changes/c/tasks.md", "- [ ] a\n")
        paths = ["openspec/changes/c/proposal.md", "openspec/changes/c/tasks.md"]
        dest = self.home_dest("spec-1")
        snapshot.save(self.repo, paths, dest)
        self.write("openspec/changes/c/proposal.md", "line1\nline2 edited\n")
        (self.repo / "openspec/changes/c/tasks.md").unlink()
        self.write("openspec/changes/c/design.md", "new\n")
        out = snapshot.diff(dest, self.repo, ["openspec/changes/c/design.md", "openspec/changes/c/proposal.md"])
        self.assertIn("--- a/openspec/changes/c/proposal.md\n+++ b/openspec/changes/c/proposal.md\n", out)
        self.assertIn("-line2\n+line2 edited\n", out)
        self.assertIn("--- a/openspec/changes/c/design.md\n+++ b/openspec/changes/c/design.md\n", out)
        self.assertIn("+new\n", out)
        self.assertIn("--- a/openspec/changes/c/tasks.md\n+++ b/openspec/changes/c/tasks.md\n", out)
        self.assertIn("-- [ ] a\n", out)
        heads = [l for l in out.splitlines() if l.startswith("--- ")]
        self.assertEqual([h[6:] for h in heads], sorted(h[6:] for h in heads))  # deterministic: sorted paths

    def test_diff_empty_when_equal(self):
        self.write("a.md", "one\n")
        self.write("sub/b.md", "two")
        dest = self.home_dest()
        snapshot.save(self.repo, ["a.md", "sub/b.md"], dest)
        self.assertEqual(snapshot.diff(dest, self.repo, ["a.md", "sub/b.md"]), "")

    def test_save_keeps_bytes_and_replaces_dest(self):
        self.write("a.md", "", raw=b"one\r\ntwo\r\n")
        self.write("b.md", "b\n")
        dest = self.home_dest()
        snapshot.save(self.repo, ["a.md", "b.md"], dest)
        self.assertEqual((dest / "a.md").read_bytes(), b"one\r\ntwo\r\n")
        snapshot.save(self.repo, ["a.md"], dest)
        self.assertFalse((dest / "b.md").exists())
        self.assertEqual((dest / "a.md").read_bytes(), b"one\r\ntwo\r\n")

    def test_diff_marks_a_missing_final_newline(self):
        self.write("a.md", "one")
        dest = self.home_dest()
        snapshot.save(self.repo, ["a.md"], dest)
        self.write("a.md", "one\n")
        out = snapshot.diff(dest, self.repo, ["a.md"])
        self.assertIn("-one\n\\ No newline at end of file\n+one\n", out)

    def test_diff_survives_invalid_utf8(self):
        self.write("a.md", "", raw=b"ok\n\xff\n")
        dest = self.home_dest()
        snapshot.save(self.repo, ["a.md"], dest)
        self.write("a.md", "", raw=b"ok2\n\xff\n")
        self.assertIn("�", snapshot.diff(dest, self.repo, ["a.md"]))

    def test_save_refuses_dest_outside_factory_local(self):
        self.write("a.md", "one\n")
        for dest in (self.d / "elsewhere", self.repo / "copy", Path.home() / ".factory-local", Path.home()):
            with self.subTest(dest=dest), self.assertRaises(config.Stop):
                snapshot.save(self.repo, ["a.md"], dest)
        self.assertFalse((self.d / "elsewhere").exists())

    def test_save_refuses_dest_dotdot_out_of_factory_local(self):
        self.write("a.md", "one\n")
        with self.assertRaises(config.Stop):
            snapshot.save(self.repo, ["a.md"], Path.home() / ".factory-local" / "proj" / ".." / ".." / "x")

    def test_save_refuses_unsafe_paths(self):
        for p in ("../x.md", "/etc/passwd"):
            with self.subTest(p=p), self.assertRaises(config.Stop):
                snapshot.save(self.repo, [p], self.home_dest())


class Unsafe(SnapshotTest):
    """Paths from Jira comments and symlinks must never reach files outside the repository."""
    def setUp(self):
        super().setUp()
        self.secret = self.d / "secret.txt"
        self.secret.write_text("secret\n", encoding="utf-8")
        self.write("openspec/changes/c/proposal.md", "p\n")
        (self.repo / "openspec/changes/c/link.md").symlink_to(self.secret)
        (self.repo / "openspec/changes/c/dirlink").symlink_to(self.d, target_is_directory=True)
        self.bad = ["../secret.txt", str(self.secret), "openspec/changes/c/link.md", "openspec/changes/c/dirlink/secret.txt"]

    def test_spec_files_skips_symlinks(self):
        F = CFG["frameworks"]["openspec"]
        self.assertEqual(snapshot.spec_files(self.repo, F, "c", []), ["openspec/changes/c/proposal.md"])
        self.assertEqual(snapshot.spec_files(self.repo, F, "c", ["../secret.txt", str(self.secret)]),
                         ["openspec/changes/c/proposal.md"])

    def test_checksum_stops(self):
        for p in self.bad:
            with self.subTest(p=p), self.assertRaises(config.Stop):
                snapshot.checksum(self.repo, ["openspec/changes/c/proposal.md", p])

    def test_save_stops_and_copies_nothing(self):
        dest = self.home_dest()
        for p in self.bad:
            with self.subTest(p=p), self.assertRaises(config.Stop):
                snapshot.save(self.repo, ["openspec/changes/c/proposal.md", p], dest)
            self.assertFalse(dest.exists())

    def test_diff_stops(self):
        dest = self.home_dest()
        snapshot.save(self.repo, ["openspec/changes/c/proposal.md"], dest)
        for p in self.bad:
            with self.subTest(p=p), self.assertRaises(config.Stop) as cm:
                snapshot.diff(dest, self.repo, ["openspec/changes/c/proposal.md", p])
            self.assertIn(p, str(cm.exception))


class SpecFiles(SnapshotTest):
    def commit_all(self):
        subprocess.run(["git", "add", "-A"], cwd=self.repo, check=True, env=GIT_ENV)
        subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "-q", "-m", "x"],
                       cwd=self.repo, check=True, env=GIT_ENV)

    def test_openspec_change_files_sorted_untracked_included(self):
        F = CFG["frameworks"]["openspec"]
        self.write("openspec/changes/c/proposal.md", "p\n")
        self.write("openspec/changes/c/specs/tags/spec.md", "s\n")
        self.write("openspec/changes/other/proposal.md", "o\n")
        self.write("openspec/changes/archive/c/proposal.md", "a\n")
        self.write("README.md", "r\n")
        self.commit_all()
        self.write("openspec/changes/c/tasks.md", "t\n")  # untracked
        self.assertEqual(snapshot.spec_files(self.repo, F, "c", []),
                         ["openspec/changes/c/proposal.md", "openspec/changes/c/specs/tags/spec.md",
                          "openspec/changes/c/tasks.md"])

    def test_speckit_files(self):
        F = CFG["frameworks"]["speckit"]
        self.write("specs/001-tags/spec.md", "s\n")
        self.write("specs/002-other/spec.md", "s\n")
        self.assertEqual(snapshot.spec_files(self.repo, F, "001-tags", []), ["specs/001-tags/spec.md"])

    def test_deleted_tracked_file_is_left_out(self):
        F = CFG["frameworks"]["openspec"]
        self.write("openspec/changes/c/proposal.md", "p\n")
        self.write("openspec/changes/c/tasks.md", "t\n")
        self.commit_all()
        (self.repo / "openspec/changes/c/tasks.md").unlink()
        self.assertEqual(snapshot.spec_files(self.repo, F, "c", []), ["openspec/changes/c/proposal.md"])

    def test_bmad_includes_prd_folder_from_known(self):
        F = CFG["frameworks"]["bmad"]
        prd = "_bmad-output/planning-artifacts/prds/prd-x/"
        self.write(prd + "prd.md", "prd\n")
        self.write(prd + "notes/n.md", "n\n")
        self.write("_bmad-output/planning-artifacts/prds/prd-y/prd.md", "other prd\n")
        self.write("_bmad-output/specs/c/SPEC.md", "spec\n")
        self.write("_bmad-output/specs/d/SPEC.md", "other change\n")
        self.write("_bmad-output/planning-artifacts/architecture.md", "tree\n")
        self.assertEqual(snapshot.spec_files(self.repo, F, "c", []), ["_bmad-output/specs/c/SPEC.md"])
        self.assertEqual(snapshot.spec_files(self.repo, F, "c", [prd + "prd.md", "_bmad-output/specs/c/SPEC.md"]),
                         [prd + "notes/n.md", prd + "prd.md", "_bmad-output/specs/c/SPEC.md"])

    def test_known_outside_spec_area_adds_nothing(self):
        F = CFG["frameworks"]["bmad"]
        self.write("src/a.php", "x\n")
        self.write("src/b.php", "y\n")
        self.write("_bmad-output/specs/c/SPEC.md", "spec\n")
        self.assertEqual(snapshot.spec_files(self.repo, F, "c", ["src/a.php"]), ["_bmad-output/specs/c/SPEC.md"])

    def test_known_of_another_change_adds_nothing(self):
        F = CFG["frameworks"]["bmad"]
        self.write("_bmad-output/specs/c/SPEC.md", "spec\n")
        self.write("_bmad-output/specs/d/SPEC.md", "other\n")
        self.assertEqual(snapshot.spec_files(self.repo, F, "c", ["_bmad-output/specs/d/SPEC.md"]),
                         ["_bmad-output/specs/c/SPEC.md"])


class PathsInSpecText(SnapshotTest):
    def test_paths_in_spec_text_of_spec_result(self):
        F = CFG["frameworks"]["openspec"]
        self.write("openspec/changes/c/proposal.md", "p\n=== not/a/header.md ===\nstill body\n")
        self.write("openspec/changes/c/tasks.md", "")
        self.write("openspec/changes/c/design.md", "d")
        paths = ["openspec/changes/c/tasks.md", "openspec/changes/c/proposal.md", "openspec/changes/c/design.md"]
        _, text = fetch.spec_result(self.repo, F, paths)
        self.assertEqual(snapshot.paths_in_spec_text(text),
                         ["openspec/changes/c/design.md", "openspec/changes/c/proposal.md", "openspec/changes/c/tasks.md"])

    def test_spec_result_skips_symlinks(self):
        F = CFG["frameworks"]["openspec"]
        self.write("openspec/changes/c/proposal.md", "p")
        secret = self.d / "secret.txt"
        secret.write_text("geheim", encoding="utf-8")
        (self.repo / "openspec/changes/c/leak.md").symlink_to(secret)
        _, text = fetch.spec_result(self.repo, F, ["openspec/changes/c/proposal.md", "openspec/changes/c/leak.md"])
        self.assertNotIn("geheim", text)
        self.assertEqual(snapshot.paths_in_spec_text(text), ["openspec/changes/c/proposal.md"])

    def test_no_headers(self):
        self.assertEqual(snapshot.paths_in_spec_text(""), [])
        self.assertEqual(snapshot.paths_in_spec_text("just text\n"), [])


class CopyDir(SnapshotTest):
    def test_copy_dir_outside_repo(self):
        got = snapshot.copy_dir(self.repo, "LL-1", "add-tags", "spec", 2)
        self.assertEqual(got, Path.home() / ".factory-local" / "proj" / "specs" / "LL-1" / "add-tags" / "spec-2")
        self.assertFalse(got.exists())  # not created here
        with self.assertRaises(ValueError):
            got.resolve().relative_to(self.repo.resolve())

    def test_copy_dir_rejects_path_parts(self):
        for key, change in (("../x", "c"), ("LL-1", "a/b"), ("", "c"), ("LL-1", "..")):
            with self.subTest(key=key, change=change), self.assertRaises(config.Stop):
                snapshot.copy_dir(self.repo, key, change, "spec", 1)

    def test_copy_dir_takes_any_plain_repo_folder_name(self):
        for name in ("Mein Projekt", "bestellübersicht", ".hidden", "_intern"):
            with self.subTest(name=name):
                got = snapshot.copy_dir(self.repo.parent / name, "LL-1", "c", "spec", 1)
                self.assertEqual(got, Path.home() / ".factory-local" / name / "specs" / "LL-1" / "c" / "spec-1")

    def test_repo_folder_name_check(self):
        for name in ("", ".", "..", "a/b", "a\\b", "bad\x07name", "zeile\nzwei"):
            with self.subTest(name=name), self.assertRaisesRegex(config.Stop, "can't be the folder name"):
                snapshot.repo_part(name)
        self.assertEqual(snapshot.repo_part("Mein Projekt"), "Mein Projekt")


class RepoNameBeforeCalls(E2E, unittest.TestCase):
    def test_bad_repo_folder_name_stops_before_any_call(self):
        bad = self.d / "bad\x07name"
        self.repo.rename(bad)
        self.repo = bad
        with self.assertRaisesRegex(config.Stop, "can't be the folder name"):
            self.run_main("spec", "--ticket-file", str(self.tf))
        self.assertFalse((self.d / "calls.jsonl").exists())


if __name__ == "__main__":
    unittest.main()
