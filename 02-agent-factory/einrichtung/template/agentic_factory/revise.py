"""The spec rerun (design Part 4, spec phase): revising a spec from [Mensch] comments and from hand edits of its files.

decide() reads only the comments, so the agent and the post step reach the same answer from in/. plan() adds what the
working tree says (the change's files, their checksum, hand edits). The *_out functions write out/spec.json and keep
the copy of the spec files under ~/.factory-local/; checked() is the post step's check of out/spec.json against in/."""
import json
import re

from . import clarify, config, copied, feedback, fetch, snapshot
from . import ticket as ticket_mod

HEX64 = re.compile(r"[0-9a-f]{64}")


def decide(run, req, comments, quiet=False):
    """What this spec run is, from the comments alone: {"kind": "first" or "revision", "revision": n, "change",
    "handled": the ids of the new [Mensch] comments, "new": those comments, "checksum": the previous Spec-Prüfsumme,
    "last": the comment the revision builds on, "answers": the spec fragen comment and the answers after it}.
    Stops when the latest result comment can't be trusted (it names --fresh), in the build phase, and when the
    previous spec names no change. The running account is req["me"], recorded by the fetch step (fetch.account_of)
    and checked again by the post step (verify_me). --fresh: always a first run, as today."""
    key = req["key"]
    first = {"kind": "first", "revision": 1, "change": None, "handled": [], "new": [], "checksum": None, "last": None,
             "answers": []}
    if req["fresh"]:
        return first
    raw = feedback.state(comments, key)
    me = req["me"]
    if raw["last"] is not None:
        feedback.trust(raw["last"], me)
    st = feedback.state(comments, key, me) if me is not None else raw
    if st["ignored"] and not quiet:
        config.say(f"note: comment(s) {', '.join(st['ignored'])} start like a factory result, but weren't posted "
                   "unedited by the account running this script; they don't count")
    if st["phase"] == "build":
        raise config.Stop(f"a build exists for {key} (comment {st['last_build']['id']}); give feedback through build, "
                          "or run spec --fresh")
    if st["phase"] == "none":
        return {**first, "answers": answers_of(comments, key, st, me)}
    change = st["change"]
    if not change or not ticket_mod.CHANGE_NAME.fullmatch(change) or len(change) > 100:
        raise config.Stop(f"the spec comment {st['last']['id']} names no valid change; run spec --fresh")
    return {**first, "kind": "revision", "revision": st["revision"] + 1, "change": change, "checksum": st["checksum"],
            "last": st["last"], "new": st["new_human"], "handled": [c["id"] for c in st["new_human"]]}


def answers_of(comments, key, st, me):
    """The latest spec fragen comment the answers follow, then the answers; [] without answers."""
    if not st["answers"]:
        return []
    first_answer = min(c["created"] for c in st["answers"])
    qs = [c for c in sorted(comments, key=lambda c: c["created"])
          if clarify.tag_of(c["body"]) == "KI" and clarify.first_line(c["body"]) == clarify.marker("spec_questions", key)
          and c["created"] <= first_answer and feedback._believable(c, me)]
    return qs[-1:] + st["answers"]


def answers_block(key, d):
    """The questions and answers for the first spec run's prompt, in clarify's fenced comments block; "" without."""
    if not d["answers"]:
        return ""
    return ("\nAn earlier spec run asked questions instead of writing a spec: the [KI] comment below holds them, the "
            "[Mensch] comments the answers. The answers are binding decisions.\n"
            + clarify.comments_block(key, d["answers"]))


def plan(run, req, F, d):
    """A revision's plan with the working tree: the change's files (the spec folder must exist), their checksum, and
    whether they were changed by hand since the previous comment. kind: "revise" (new comments: one call), "hand"
    (hand edits only: no call), or "nothing" (no call, nothing posted)."""
    repo, key, change = run.repo, req["key"], d["change"]
    copy = snapshot.copy_dir(repo, key, change, "spec", d["revision"] - 1)
    paths = snapshot.spec_files(repo, F, change, snapshot.saved_paths(copy))
    rx = re.compile(F["spec_change_re"])
    if not any((m := rx.match(p)) and m.group(1) == change for p in paths):
        raise config.Stop(f"the spec folder {change} is missing; restore it, or run spec --fresh")
    now = snapshot.checksum(repo, paths)
    if d["checksum"] is None:
        config.say(f"note: comment {d['last']['id']} has no Spec-Prüfsumme, so hand edits since then can't be told")
    hand = d["checksum"] is not None and now != d["checksum"]
    kind = "revise" if d["new"] else "hand" if hand else "nothing"
    return {**d, "kind": kind, "copy": copy, "paths": paths, "hand_edited": hand}


def describe(d):
    """What a revision does, for the log and --print-only."""
    head = f"spec revision {d['revision']} of change {d['change']}"
    comments = (f"handles comments {', '.join(d['handled'])}" if d["handled"]
                else f"no new [Mensch] comments since comment {d['last']['id']}")
    edits = (f"the spec was changed by hand since comment {d['last']['id']}" if d["hand_edited"]
             else f"the spec was not changed by hand since comment {d['last']['id']}")
    return f"{head}: {comments}; {edits}"


def nothing_reason(d):
    return (f"nothing new since comment {d['last']['id']}: no new [Mensch] comments and no hand edits of the spec "
            f"{d['change']}; no call, nothing posted")


def print_lines(d):
    """--print-only: what the run would handle, without any call."""
    if d["kind"] == "first":
        ids = [c["id"] for c in d["answers"] if clarify.tag_of(c["body"]) == "Mensch"]
        return [f"# the spec prompt has the answers in comments {', '.join(ids)}"] if ids else []
    lines = [f"# {describe(d)}"]
    if d["kind"] == "hand":
        lines.append(f"# no copilot call: this run posts the spec as changed by hand (revision {d['revision']})")
    elif d["kind"] == "nothing":
        lines.append(f"# {nothing_reason(d)}")
    return lines


def write_nothing_new(out, mode, reason):
    fetch.write_json(out / fetch.NOTHING_NEW, {"mode": mode, "reason": reason})


def _write(run, req, p, change, paths, text, d, diff):
    """Saves the copy of the spec files as they are now (spec-<revision>) and writes out/spec.json."""
    repo, key = run.repo, req["key"]
    if not paths:
        raise config.Stop(f"the change {change} has no spec files left; nothing is posted")
    total = snapshot.checksum(repo, paths)
    dest = snapshot.copy_dir(repo, key, change, "spec", d["revision"])
    snapshot.save(repo, paths, dest)
    config.say(f"spec copy for later diffs: {dest}")
    first = d["revision"] == 1
    fetch.write_json(run.io / "out" / "spec.json", {
        "fw": p["fw"], "source": fetch.source_label(run.cfg, p["fw"], p["source"]), "change": change,
        "readiness_line": fetch.readiness_line(run.cfg, req["no_assess"]) if first else "", "spec_text": text,
        "revision": d["revision"], "handled": list(d["handled"]), "hand_edited": bool(d.get("hand_edited")),
        "diff": diff, "checksum": total})


def first_out(run, req, p, paths):
    """A first spec run: the text as today (spec_result over the changed files), the checksum and the copy over every
    file of the change."""
    change, text = fetch.spec_result(run.repo, p["F"], paths)
    files = snapshot.spec_files(run.repo, p["F"], change, snapshot.paths_in_spec_text(text))
    _write(run, req, p, change, files, text, p["fb"], "")


def _diff(run, d, paths):
    if not d["copy"].is_dir():
        config.say(f"note: the copy of revision {d['revision'] - 1} ({d['copy']}) is missing: the comment shows the full "
                   "spec without a diff")
        return ""
    return snapshot.diff(d["copy"], run.repo, paths)


def hand_out(run, req, p):
    """Hand edits only: no call; the current spec, the diff against the copy, the new checksum and copy."""
    d = p["fb"]
    _write(run, req, p, d["change"], d["paths"], snapshot.spec_text(run.repo, d["paths"]), d, _diff(run, d, d["paths"]))
    config.say(f"{req['key']}: {describe(d)}; no copilot call")
    return 0


def revise_out(run, req, p, changed):
    """After the revise call: the change named by the previous comment, never a second one; its files now."""
    d, F = p["fb"], p["F"]
    rx = re.compile(F["spec_change_re"])
    others = sorted({m.group(1) for x in changed if (m := rx.match(x)) and m.group(1) not in (None, d["change"])})
    if others:
        raise config.Stop(f"the revision wrote another change besides {d['change']}: {others}; nothing is posted")
    paths = snapshot.spec_files(run.repo, F, d["change"], [*d["paths"], *changed])
    if not any((m := rx.match(x)) and m.group(1) == d["change"] for x in paths):
        raise config.Stop(f"the revision removed the spec folder {d['change']}; nothing is posted")
    _write(run, req, p, d["change"], paths, snapshot.spec_text(run.repo, paths), d, _diff(run, d, paths))


# --- step post ------------------------------------------------------------------------------------------------------

def checked(run, req, ticket, comments, path, d):
    """out/spec.json against in/: the keys and types; fw, source, and readiness line as in/ gives them; revision,
    change, and handled ids as decide() gives them from in/comments.json. hand_edited, diff, and checksum reflect the
    local files, so they are only checked for form (and the diff is scanned like a comment). Returns the arguments of
    clarify.render_spec."""
    s = config.read_json(path)
    if not isinstance(s, dict) or sorted(s) != sorted(fetch.SPEC_OUT_KEYS):
        raise config.Stop(f"{path.name} must have exactly the keys {', '.join(fetch.SPEC_OUT_KEYS)}")
    if not all(isinstance(s[k], str) for k in ("fw", "source", "change", "readiness_line", "spec_text", "diff",
                                               "checksum")):
        raise config.Stop(f"{path.name}: fw, source, change, readiness_line, spec_text, diff, and checksum must be strings")
    if type(s["revision"]) is not int or type(s["hand_edited"]) is not bool:
        raise config.Stop(f"{path.name}: revision must be a whole number and hand_edited true or false")
    if not isinstance(s["handled"], list) or not all(isinstance(x, str) for x in s["handled"]):
        raise config.Stop(f"{path.name}: handled must be a list of comment ids")
    fw, source = ticket_mod.choose_framework(run.cfg, req["framework"], ticket["labels"])
    first = d["kind"] == "first"
    want = {"fw": fw, "source": fetch.source_label(run.cfg, fw, source), "revision": d["revision"],
            "handled": d["handled"], "readiness_line": fetch.readiness_line(run.cfg, req["no_assess"]) if first else ""}
    if not first:
        want["change"] = d["change"]
    if first:
        want.update(hand_edited=False, diff="")
    for k, v in want.items():
        if s[k] != v:
            raise config.Stop(f"{path.name}: {k} is not {str(v)[:200]!r}, which in/ gives; nothing is posted")
    if not ticket_mod.CHANGE_NAME.fullmatch(s["change"]) or len(s["change"]) > 100:
        raise config.Stop(f"{path.name}: change is not a valid change name")
    if not HEX64.fullmatch(s["checksum"]):
        raise config.Stop(f"{path.name}: checksum is not a sha256 in hex")
    if not first and not d["handled"] and (not s["hand_edited"] or s["checksum"] == d["checksum"]):
        raise config.Stop(f"{path.name}: a revision without new comments must come from hand edits; nothing is posted")
    if not s["spec_text"].strip():
        raise config.Stop(f"{path.name}: spec_text is empty")
    found = copied.token_findings(s["diff"]) + copied.invisible_findings(s["diff"])
    if found:
        raise config.Stop(f"{path.name}: diff: {'; '.join(found)}")
    copy_missing = not first and not s["diff"] and (d["checksum"] is None or s["checksum"] != d["checksum"])
    return {**{k: s[k] for k in ("fw", "source", "change", "readiness_line", "spec_text", "revision", "handled",
                                  "hand_edited", "diff", "checksum")}, "copy_missing": copy_missing}


def render(key, spec, limit):
    """The spec comment; a revision that would be longer than limit leaves out the full spec text and names its
    files. Stops when even that is too long (the diff alone)."""
    text = clarify.render_spec(key, **spec)
    if spec["revision"] == 1 or len(text) <= limit:
        return text
    text = clarify.render_spec(key, **spec, full=False)
    if len(text) > limit:
        raise config.Stop(f"the spec comment for {key} is longer than {limit} characters even without the full spec "
                          "text (the diff alone is too long); nothing is posted. Revise in smaller steps, or run spec "
                          "--fresh")
    config.say(f"the spec comment would be longer than {limit} characters: it leaves out the full spec text")
    return text


def checked_nothing_new(path, mode):
    """out/nothing-new.json: {"mode", "reason"}. Returns the reason as one line, short and redacted (it's from out/)."""
    try:
        d = json.loads(path.read_bytes().decode("utf-8"))
    except (OSError, ValueError) as e:
        raise config.Stop(f"{path.name} cannot be read as JSON: {type(e).__name__}")
    if not isinstance(d, dict) or sorted(d) != ["mode", "reason"] or d["mode"] != mode or not isinstance(d["reason"], str):
        raise config.Stop(f"{path.name} must be {{\"mode\": \"{mode}\", \"reason\": \"...\"}}")
    return copied.redact(clarify.one_line(d["reason"])[:300])


def verify_me(run, req, comments):
    """The post step on a Jira route, before it reads out/: the account in in/request.json must be the one this step
    runs as (fetch.account_of, asked again). A tampered me would change which comments count; stops on a mismatch."""
    want = fetch.account_of(run, req["mode"], req["route"], req["key"], comments)
    if req["me"] != want:
        raise config.Stop(f"{run.io / 'in' / 'request.json'}: me names another account than the one this post step "
                          "runs as; nothing is posted. Run the steps again from --step fetch")
