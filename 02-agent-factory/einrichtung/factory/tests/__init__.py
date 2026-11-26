"""Tests for agentic-factory.py and agentic_factory/. From the folder above:
python3 -I -B -m unittest discover -s tests -t .
"""
import sys
from pathlib import Path

TEMPLATE = str(Path(__file__).resolve().parent.parent)
if TEMPLATE not in sys.path:
    sys.path.append(TEMPLATE)  # as agentic-factory.py does: appended, so stdlib names win
