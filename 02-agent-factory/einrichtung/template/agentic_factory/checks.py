"""The checks on what the model wrote: the readiness verdict, FACTORY-CLARIFY.json, and every comment before it is
posted."""
import json
import re
from pathlib import Path

from . import copied, config, copilot, jira_rest, clarify, rules
from . import ticket as ticket_mod


# --- the readiness verdict: FACTORY-ASSESSMENT.json against its contract ----------------------------------------------

VERDICT_MAX_ITEMS, MAX_DETAIL_CHARS, MAX_QUESTION_CHARS = 10, 1000, 500  # factory/assess.py


def verdict_text(s, limit, what):
    """One reason detail or question, as factory/assess.py _text_ok checks it."""
    if not isinstance(s, str) or not s.strip():
        raise config.Stop(f"{config.ASSESSMENT}: every {what} must be a non-empty string")
    if len(s) > limit:
        raise config.Stop(f"{config.ASSESSMENT}: a {what} is longer than {limit} characters")
    bad = copied.invisible_findings(s)
    if bad:
        raise config.Stop(f"{config.ASSESSMENT}: a {what} contains {bad}")


def check_verdict(path, ids):
    """The verdict file against the contract (the checks of factory/assess.py parse_verdict)."""
    if not path.exists():
        raise config.Stop(f"the readiness check wrote no {config.ASSESSMENT}")
    return verdict_fields(config.read_json(path), ids)


def verdict_fields(v, ids):
    """The parsed verdict against the contract. Returns it unchanged."""
    if not isinstance(v, dict) or set(v) != {"verdict", "reasons", "questions"}:
        raise config.Stop(f"{config.ASSESSMENT} must have exactly the keys verdict, reasons, questions")
    if v["verdict"] not in ("ready", "not_ready"):
        raise config.Stop(f"{config.ASSESSMENT}: verdict {str(v['verdict'])[:40]!r} is neither ready nor not_ready")
    if not isinstance(v["reasons"], list) or not isinstance(v["questions"], list):
        raise config.Stop(f"{config.ASSESSMENT}: reasons and questions must be lists")
    if len(v["reasons"]) > VERDICT_MAX_ITEMS or len(v["questions"]) > VERDICT_MAX_ITEMS:
        raise config.Stop(f"{config.ASSESSMENT}: at most {VERDICT_MAX_ITEMS} reasons and {VERDICT_MAX_ITEMS} questions")
    for r in v["reasons"]:
        if not isinstance(r, dict) or set(r) != {"id", "detail"} or r["id"] not in ids:
            raise config.Stop(f"{config.ASSESSMENT}: bad reason {str(r)[:120]}; ids allowed: {ids}")
        verdict_text(r["detail"], MAX_DETAIL_CHARS, "reason detail")
    for q in v["questions"]:
        verdict_text(q, MAX_QUESTION_CHARS, "question")
    if v["verdict"] == "ready" and (v["reasons"] or v["questions"]):
        raise config.Stop(f"{config.ASSESSMENT}: a ready verdict has no reasons and no questions")
    if v["verdict"] == "not_ready" and not v["reasons"]:
        raise config.Stop(f"{config.ASSESSMENT}: a not_ready verdict needs at least one reason")
    return v


# --- clarify output: FACTORY-CLARIFY.json and the checks before a comment is posted ---------------------------------

CLARIFY = "FACTORY-CLARIFY.json"
MAX_ITEMS = 10
MAX_ITEM_CHARS = 500
MAX_CLARIFY_FILE = 30000
CLARIFY_STATUSES = ("questions", "confirm", "ready")


# Model text that Jira would show as a live link or image: Markdown [x](url) and ![](url) (the MCP route sends
# Markdown), Jira wiki [x|http…] and !http…! (als_wiki, the Data Center description, doesn't escape), and the wiki
# forms with any other scheme or none: [x|ftp:…], [x|//…], [x|mailto:…], !ftp:…!. Inside a fenced block it stays code.
# The other schemes count after "|" only inside "[", and right after "!" (an image starts without a space), so text
# such as "| Hinweis: x |" or "Wichtig! Hinweis: x" stays plain text. The link text may hold escapes such as \] or \|;
# an escaped "[" ends the scan there, and the match starts again at that "[", so the scan stays linear. live_link also
# checks the text with every whitespace run made one space: a line break inside a link doesn't hide it.
URI_START = r"(?:[a-z][a-z0-9+.-]*:|//)"
WIKI_LINK_TEXT = r"\[(?:\\[^\[]|[^\[\]|\\])*\|"
LIVE_LINK = re.compile(r"\]\(|!\[|[|!][ \t]*http|" + WIKI_LINK_TEXT + r"[ \t]*" + URI_START + "|!" + URI_START, re.I)


def live_link(text):
    return bool(LIVE_LINK.search(text) or LIVE_LINK.search(" ".join(text.split())))


def link_findings(text):
    return ["would become a link or image in Jira"] if live_link(text) else []


def post_findings(text, limit):
    """Why a comment must not be posted. Empty list: it may be."""
    out = copied.token_findings(text) + copied.invisible_findings(text)  # invisible_findings also covers HTML comments, link definitions
    if any(live_link(t) for kind, t in jira_rest.segments(text) if kind == "p"):
        out.append("link or image outside a code block")
    if len(text) > limit:
        out.append(f"longer than {limit} characters")
    if "FACTORY-" in text:
        out.append("contains FACTORY-")
    if not text.startswith("[KI]"):
        out.append("does not start with [KI]")
    return out


def clarify_text(s, where, limit, source=CLARIFY):
    """One string of the clarify file: a string, not empty, not too long, no scan finding. Returns it unchanged.
    source: where the string comes from, for the messages (the proposal comment on the --apply path)."""
    if not isinstance(s, str):
        raise config.Stop(f"{source}: {where} must be a string")
    if not s.strip():
        raise config.Stop(f"{source}: {where} is empty")
    if len(s) > limit:
        raise config.Stop(f"{source}: {where} is longer than {limit} characters")
    found = copied.token_findings(s) + copied.invisible_findings(s) + link_findings(s)  # on the raw string, before neutralizing
    if found:
        raise config.Stop(f"{source}: {where}: {'; '.join(found)}")
    return s


def check_clarify(path, ids, max_desc):
    """The clarify file against its contract. Returns it with every item on one line and neutralized."""
    path = Path(path)
    if not path.exists():
        raise config.Stop(f"{CLARIFY}: the clarify call wrote no such file")
    try:
        size = path.stat().st_size
        if size > MAX_CLARIFY_FILE:
            raise config.Stop(f"{CLARIFY}: {size} bytes, the limit is {MAX_CLARIFY_FILE}")
        d = json.loads(path.read_text(encoding="utf-8"))
    except OSError as e:  # a directory at the path, an unreadable file
        raise config.Stop(f"{CLARIFY} cannot be read: {e}")
    except (ValueError, RecursionError) as e:  # ValueError includes UnicodeDecodeError; deep nesting is RecursionError
        raise config.Stop(f"{CLARIFY} is not valid JSON: {type(e).__name__}: {str(e)[:200]}")
    return clarify_fields(d, ids, max_desc)


def clarify_fields(d, ids, max_desc):
    """The parsed clarify file against its contract (check_clarify's checks after reading). The post step runs it
    again on the copy in out/clarify.json."""
    if not isinstance(d, dict) or set(d) != {"status", "questions", "assumptions", "description"}:
        raise config.Stop(f"{CLARIFY} must have exactly the keys status, questions, assumptions, description")
    status, qs, ass, desc = d["status"], d["questions"], d["assumptions"], d["description"]
    if status not in CLARIFY_STATUSES:
        raise config.Stop(f"{CLARIFY}: status {str(status)[:40]!r} is not one of {', '.join(CLARIFY_STATUSES)}")
    if not isinstance(qs, list) or not isinstance(ass, list):
        raise config.Stop(f"{CLARIFY}: questions and assumptions must be lists")
    if len(qs) > MAX_ITEMS:
        raise config.Stop(f"{CLARIFY}: more than {MAX_ITEMS} questions")
    if len(ass) > MAX_ITEMS:
        raise config.Stop(f"{CLARIFY}: more than {MAX_ITEMS} assumptions")
    out_q, out_a = [], []
    for n, q in enumerate(qs, 1):
        if not isinstance(q, dict) or set(q) != {"id", "text", "suggestion", "criterion"}:
            raise config.Stop(f"{CLARIFY}: question {n} must have exactly the keys id, text, suggestion, criterion")
        if q["id"] != str(n):
            raise config.Stop(f"{CLARIFY}: question {n} has id {repr(q['id'])[:20]}, expected {str(n)!r}")
        if q["criterion"] not in ids:
            raise config.Stop(f"{CLARIFY}: question {n} names criterion {str(q['criterion'])[:40]!r}, not one of {ids}")
        out_q.append({"id": q["id"], "criterion": q["criterion"],
                      "text": clarify.one_line(clarify_text(q["text"], f"question {n} text", MAX_ITEM_CHARS)),
                      "suggestion": clarify.one_line(clarify_text(q["suggestion"], f"question {n} suggestion", MAX_ITEM_CHARS))})
    for n, a in enumerate(ass, 1):
        if not isinstance(a, dict) or set(a) != {"id", "text"}:
            raise config.Stop(f"{CLARIFY}: assumption {n} must have exactly the keys id, text")
        if a["id"] != f"A{n}":
            raise config.Stop(f"{CLARIFY}: assumption {n} has id {repr(a['id'])[:20]}, expected {f'A{n}'!r}")
        out_a.append({"id": a["id"], "text": clarify.one_line(clarify_text(a["text"], f"assumption {n} text", MAX_ITEM_CHARS))})
    if status == "questions" and not qs:
        raise config.Stop(f"{CLARIFY}: status questions needs at least one question")
    if status != "questions" and qs:
        raise config.Stop(f"{CLARIFY}: status {status} must not have questions")
    if not isinstance(desc, str):
        raise config.Stop(f"{CLARIFY}: description must be a string")
    if status != "ready":
        if desc.strip():
            raise config.Stop(f"{CLARIFY}: status {status} must have an empty description")
        desc = ""
    else:
        if not desc.strip():
            raise config.Stop(f"{CLARIFY}: status ready needs a description")
        clarify_text(desc, "description", max_desc)
        desc = clarify.neutral(desc)
    return {"status": status, "questions": out_q, "assumptions": out_a, "description": desc}


MAX_ROUNDS = 99


def clarify_config(cfg):
    """(the clarify block, its round cap). clarify needs the assess block too: the readiness check runs on the
    proposed description."""
    C = cfg.get("clarify")
    if not C or not cfg.get("assess"):
        raise config.Stop("clarify is not available in this config: config.json needs a \"clarify\" and an \"assess\" block")
    rounds = C.get("max_rounds", 3)
    if type(rounds) is not int or not 1 <= rounds <= MAX_ROUNDS:
        raise config.Stop(f"config.json: clarify.max_rounds must be a whole number from 1 to {MAX_ROUNDS}")
    return C, rounds


def clarify_call(cfg, ticket, comments_block, crit, team_rules=""):
    """The clarify call's prompt, tools, and credit cap, built like assess_call. comments_block: the tagged comments,
    wrapped by comments_block(). team_rules: the block of the team's rules for clarify (rules.block); "" adds nothing."""
    C = cfg["clarify"]
    text, ids = crit
    vals = {"ticket_block": ticket_mod.ticket_block(ticket), "comments_block": comments_block, "criteria": text,
            "ids": ", ".join(ids), "output_file": CLARIFY, "max_items": MAX_ITEMS,
            "protected_paths": "\n".join("- " + p for p in cfg["protected_paths"])}
    prompt = rules.append(copilot.fill(C["prompt"], vals, "the clarify prompt"), team_rules)
    return prompt, list(C.get("tools", [])), C.get("max_ai_credits", 40)
