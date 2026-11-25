"""The readiness check (factory/assess.py): the criteria in readiness.md, the check's prompt, the verdict on screen."""
import re
from pathlib import Path

from . import config, copilot
from . import ticket as ticket_mod


# --- readiness check (factory/assess.py) ---------------------------------------------------------------------------

CRITERION = re.compile(r"(?m)^### `([a-z][a-z0-9_]{1,40})`[ \t]*$")


def criteria(path):
    """(text, ids) of readiness.md. The IDs are the level-3 headings with the ID in backticks."""
    try:
        text = Path(path).read_text(encoding="utf-8")
    except FileNotFoundError:
        raise config.Stop(f"{path} not found: copy readiness.md next to agentic-factory.py")
    ids = CRITERION.findall(text)
    if not ids:
        raise config.Stop(f"{path} defines no criteria (headings like ### `missing_detail`)")
    if len(ids) != len(set(ids)):
        raise config.Stop(f"{path} defines a criterion ID twice: {sorted(ids)}")
    return text, ids


def assess_call(cfg, ticket, crit):
    """The readiness check's prompt, tools, and credit cap, as factory/assess.py and agent.py build them."""
    A = cfg["assess"]
    text, ids = crit
    vals = {"ticket_block": ticket_mod.ticket_block(ticket), "criteria": text, "ids": ", ".join(ids), "output_file": config.ASSESSMENT,
            "protected_paths": "\n".join("- " + p for p in cfg["protected_paths"])}
    prompt = copilot.fill(A["prompt"], vals, "the assess prompt")
    return prompt, list(A.get("tools", [])), A.get("max_ai_credits", 40)


def show_verdict(v):
    print(f"\n  verdict: {v['verdict']}")
    for r in v["reasons"]:
        print(f"  - {r['id']}: {r['detail']}")
    for q in v["questions"]:
        print(f"  ? {q}")
    print()
