"""Tests for agentic_factory/main.py and the starter agentic-factory.py: exit codes, and pipelines.example.yml."""
import contextlib
import io
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from agentic_factory import config, main
from .fakes import HERE


class Entry(unittest.TestCase):
    """M4: every stop is exit code 2, also an unexpected error."""

    def run_entry(self, exc):
        out = io.StringIO()
        with mock.patch.object(main, "main", side_effect=exc), contextlib.redirect_stdout(out), \
                self.assertRaises(SystemExit) as cm:
            main.entry()
        return cm.exception.code, out.getvalue()

    def test_stop(self):
        self.assertEqual(self.run_entry(config.Stop("halt")), (2, "[agentic-factory] STOP: halt\n"))

    def test_unexpected_error_exits_2_redacted(self):
        code, out = self.run_entry(OSError(28, "No space left on device ghp_" + "a" * 36))
        self.assertEqual(code, 2)
        self.assertEqual(out, "[agentic-factory] STOP: unexpected OSError: [Errno 28] No space left on device "
                              "[REDACTED-PATTERN]\n")

    def test_interrupt(self):
        self.assertEqual(self.run_entry(KeyboardInterrupt()), (130, "[agentic-factory] interrupted\n"))

    def test_exit_code_passes_through(self):
        with mock.patch.object(main, "main", return_value=5), contextlib.redirect_stdout(io.StringIO()), \
                self.assertRaises(SystemExit) as cm:
            main.entry()
        self.assertEqual(cm.exception.code, 5)

    def test_script_uses_entry(self):
        r = subprocess.run([sys.executable, "-I", str(HERE / "agentic-factory.py"), "assess", "--config",
                            str(HERE / "no-such-config.json")], capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertIn("STOP: ", r.stdout)
        self.assertNotIn("Traceback", r.stderr)


class Starter(unittest.TestCase):
    """agentic-factory.py only loads agentic_factory/ from its own folder and runs main.entry()."""

    def copy(self, with_package):
        d = Path(tempfile.mkdtemp(prefix="af-starter-"))
        self.addCleanup(shutil.rmtree, d, True)
        shutil.copy2(HERE / "agentic-factory.py", d)
        if with_package:
            shutil.copytree(HERE / "agentic_factory", d / "agentic_factory",
                            ignore=shutil.ignore_patterns("__pycache__"))
        return d

    def test_missing_package_stops(self):
        d = self.copy(with_package=False)
        r = subprocess.run([sys.executable, "-I", str(d / "agentic-factory.py"), "-h"], capture_output=True, text=True,
                           timeout=60)
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertTrue(r.stdout.startswith("[agentic-factory] STOP: "), r.stdout)
        self.assertIn("copy agentic_factory/ next to agentic-factory.py", r.stdout)
        self.assertNotIn("Traceback", r.stderr)

    def test_writes_no_pycache(self):  # without -B: the check after each run would count __pycache__ in the project
        d = self.copy(with_package=True)
        r = subprocess.run([sys.executable, "-I", str(d / "agentic-factory.py"), "-h"], capture_output=True, text=True,
                           timeout=60)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("usage: agentic-factory.py", r.stdout)
        self.assertEqual(sorted(p.relative_to(d).as_posix() for p in d.rglob("__pycache__")), [])


class PipelineExample(unittest.TestCase):
    """pipelines.example.yml: text checks only, the tests use no YAML library."""

    @classmethod
    def setUpClass(cls):
        cls.text = (HERE / "pipelines.example.yml").read_text(encoding="utf-8")
        cls.code = "\n".join(l for l in cls.text.splitlines() if not l.lstrip().startswith("#"))
        cls.pipes = {m.group(1): m.group(2) for m in re.finditer(
            r"^    (agentic-[a-z]+):\n(.*?)(?=^    agentic-|\Z)", cls.code, re.S | re.M)}

    def test_steps_and_secrets(self):
        self.assertEqual(sorted(self.pipes), ["agentic-assess", "agentic-clarify"])
        for name, body in self.pipes.items():
            with self.subTest(pipeline=name):
                self.assertEqual(len(re.findall(r"^\s+deployment: ", body, re.M)), 3)
                self.assertEqual(re.findall(r"--step (\w+)", body), ["fetch", "agent", "post"])
                self.assertEqual(re.findall(r"deployment: (\S+)", body), ["agentic-jira", "agentic-agent", "agentic-post"])
                self.assertEqual(len(re.findall(r"^\s+concurrency-group: agentic$", body, re.M)), 3)
                self.assertEqual(len(re.findall(r"^\s+max-time: ", body, re.M)), 3)
                self.assertEqual(len(re.findall(r"scopes: \[read:git:bitbucket\]", body)), 3)
                self.assertEqual(re.findall(r"^\s+- (agentic-io/\S+)$", body, re.M), ["agentic-io/in/**", "agentic-io/out/**"])
                self.assertEqual(len(re.findall(r'--key "\$JIRA_KEY"', body)), 3)
                self.assertIn(f"python3 -I factory/agentic-factory.py {name.split('-')[1]} ", body)
        self.assertEqual(re.findall(r"^\s+- name: (\w+)", self.pipes["agentic-clarify"], re.M), ["JIRA_KEY", "APPLY"])
        self.assertEqual(re.findall(r"^\s+- name: (\w+)", self.pipes["agentic-assess"], re.M), ["JIRA_KEY"])
        for bad in ("--jira mcp", "--step all", "--apply", "build", "COPILOT_GITHUB_TOKEN", "JIRA_API_TOKEN"):
            self.assertNotIn(bad, self.code)

    def test_header_says_it(self):
        for word in ("/proc", "working tree", "build"):
            self.assertIn(word, self.text.split("\nimage:")[0].split("\npipelines:")[0])
