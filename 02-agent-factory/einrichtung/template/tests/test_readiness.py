"""Tests for agentic_factory/readiness.py: the readiness check equals factory/assess.py's (needs FACTORY_BASE)."""
import builtins
import contextlib
import io
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from agentic_factory import copilot, readiness
from agentic_factory import ticket as ticket_mod
from .fakes import CFG, FACTORY_BASE, FULL_CFG, HAVE_PWD, HERE, KEY, LAB_CFG, READINESS, TICKET, drop_usage


def agent_assess_call():
    """factory/agent.py's run_assessment (session A's readiness gate) with side effects stubbed: its argv."""
    import agent
    calls, tmp = [], tempfile.mkdtemp(prefix="parity-assess-")
    real_open = builtins.open
    out = Path(tmp) / agent.assess.OUTPUT
    out.write_text('{"verdict": "ready", "reasons": [], "questions": []}', encoding="utf-8")

    def fake_as_agent(cmd, env, timeout, cwd=None, stdout=None):
        calls.append(list(cmd))
        return SimpleNamespace(returncode=0, stdout=b"")

    fake_sub = SimpleNamespace(run=lambda *a, **k: SimpleNamespace(returncode=0, stdout=b""), PIPE=-1, DEVNULL=-3,
                               STDOUT=-2, TimeoutExpired=subprocess.TimeoutExpired)
    with contextlib.ExitStack() as st, contextlib.redirect_stdout(io.StringIO()):
        for n, v in {"as_agent": fake_as_agent, "kill_agent": lambda: None, "summarize_events": lambda p: ([], 0, "", {}),
                     "make_patch": lambda b, o: [f"A\t{agent.assess.OUTPUT}"], "write_json": lambda p, o: None,
                     "WS": tmp, "subprocess": fake_sub}.items():
            st.enter_context(mock.patch.object(agent, n, v))
        st.enter_context(mock.patch.object(agent, "open", lambda p, *a, **k: real_open(
            os.path.join(tmp, os.path.basename(str(p))), *a, **k), create=True))
        env = {**agent.base_env(), "COPILOT_GITHUB_TOKEN": "x" * 20}
        agent.run_assessment(KEY, "b" * 40, ticket_mod.ticket_block(dict(TICKET)), env, CFG["frameworks"]["openspec"], tmp)
    return [c for c in calls if c[0] == "copilot"]


@unittest.skipUnless(FACTORY_BASE, "set FACTORY_BASE to the factory/ folder to run the parity tests")
@unittest.skipUnless(HAVE_PWD, "factory/agent.py needs the pwd module (not on Windows)")
class AssessParity(unittest.TestCase):
    def test_assess_call_matches_the_factory(self):
        import agent
        if not hasattr(agent, "run_assessment") or not CFG.get("assess"):
            self.skipTest("this agent.py has no readiness check (session A's branch lab/t2-30-readiness adds it)")
        theirs = agent_assess_call()
        crit = readiness.criteria(HERE / CFG["assess"].get("criteria_file", "readiness.md"))
        prompt, tools, cap = readiness.assess_call(LAB_CFG, dict(TICKET), crit)
        ours = copilot.copilot_argv(LAB_CFG, {}, prompt, tools, "/x/usage-assess.json", cap=cap)
        self.assertEqual(len(theirs), 1)
        self.assertEqual(drop_usage(ours), drop_usage(theirs[0]) + ["--deny-tool=shell"])  # only appends (I1)

    def test_criteria_ids_match_the_factory(self):
        try:
            import assess
        except ImportError:
            self.skipTest("no factory/assess.py on this branch")
        p = Path(tempfile.mkdtemp()) / "readiness.md"
        p.write_text(READINESS, encoding="utf-8")
        self.assertEqual(readiness.criteria(p), assess.criteria(str(p)))
