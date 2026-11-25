#!/usr/bin/env python3
"""agentic-factory: runs the factory's Copilot calls for a Jira ticket. The code is in agentic_factory/ next to this
file; usage and options: python3 agentic-factory.py -h, and agentic_factory/main.py."""
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # no __pycache__ in the project: the check after each run would count it
sys.path.append(str(Path(__file__).resolve().parent))  # -I leaves this folder off sys.path; appended: stdlib names win
try:
    from agentic_factory import main
except ImportError as e:
    print(f"[agentic-factory] STOP: can't load agentic_factory/ ({e}): copy agentic_factory/ next to "
          f"{Path(__file__).name}", flush=True)
    sys.exit(2)
main.entry()
