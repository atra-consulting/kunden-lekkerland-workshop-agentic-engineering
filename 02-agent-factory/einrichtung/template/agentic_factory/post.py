"""Step post: checks out/ against in/ again, renders the comment, and posts it."""
import difflib

from . import copied, config, checks, clarify, fetch
from . import ticket as ticket_mod


# --- step post ------------------------------------------------------------------------------------------------------

def read_out_text(path):
    try:
        return path.read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError) as e:
        raise config.Stop(f"{path} cannot be read as UTF-8: {type(e).__name__}")


def checked_verdict(path, ids):
    """check_verdict (which also scans for invisible characters), plus the token scan. FACTORY- in model text isn't
    refused: the renderers replace it with FACTORY_, as factory/assess.py neutral() does."""
    try:
        v = checks.check_verdict(path, ids)
    except config.Stop as e:  # its messages quote the file, which may be tampered
        raise config.Stop(copied.redact(str(e)))
    return verdict_tokens(v, path.name)


def verdict_tokens(v, where):
    for s in [r["detail"] for r in v["reasons"]] + list(v["questions"]):
        found = copied.token_findings(s)
        if found:
            raise config.Stop(f"{where}: {'; '.join(found)}")
    return v


def checked_spec(run, req, ticket, path):
    d = config.read_json(path)
    if not isinstance(d, dict) or sorted(d) != sorted(fetch.SPEC_OUT_KEYS) or not all(isinstance(v, str) for v in d.values()):
        raise config.Stop(f"{path.name} must have exactly the string keys {', '.join(fetch.SPEC_OUT_KEYS)}")
    fw, source = ticket_mod.choose_framework(run.cfg, req["framework"], ticket["labels"])
    want = {"fw": fw, "source": fetch.source_label(run.cfg, fw, source),
            "readiness_line": fetch.readiness_line(run.cfg, req["no_assess"])}
    for k, v in want.items():
        if d[k] != v:
            raise config.Stop(f"{path.name}: {k} is not {v!r}, which in/ gives")
    if not ticket_mod.CHANGE_NAME.fullmatch(d["change"]) or len(d["change"]) > 100:
        raise config.Stop(f"{path.name}: change is not a valid change name")
    if not d["spec_text"].strip():
        raise config.Stop(f"{path.name}: spec_text is empty")
    return d


def checked_build(run, path):
    d = config.read_json(path)
    if not isinstance(d, dict) or sorted(d) != sorted(fetch.BUILD_OUT_KEYS):
        raise config.Stop(f"{path.name} must have exactly the keys {', '.join(fetch.BUILD_OUT_KEYS)}")
    if not isinstance(d["change"], str) or not ticket_mod.CHANGE_NAME.fullmatch(d["change"]) or len(d["change"]) > 100:
        raise config.Stop(f"{path.name}: change is not a valid change name")
    if not isinstance(d["changed"], list) or not all(isinstance(x, str) and x.strip() for x in d["changed"]):
        raise config.Stop(f"{path.name}: changed must be a list of paths")
    if d["test_line"] not in fetch.test_lines(fetch.test_command(run.cfg)):
        raise config.Stop(f"{path.name}: test_line is not one of {list(fetch.test_lines(fetch.test_command(run.cfg)))}")
    return d


def outcome(run, req, ticket):
    """(comment text or None, exit code, what happened), derived again from out/ and checked against in/."""
    cfg, out = run.cfg, run.io / "out"
    mode, key = req["mode"], req["key"]
    found = [n for n in fetch.OUT_FILES if (out / n).exists()]

    def only(*names):
        extra = [n for n in found if n not in names]
        if extra:
            raise config.Stop(f"{out} holds results that a {mode} run doesn't make: {extra}; nothing is posted")

    with_assess = fetch.assesses(cfg, mode, req["no_assess"])
    if mode in ("assess", "spec"):
        if (out / "assessment.json").exists():
            if not with_assess:
                raise config.Stop(f"{out / 'assessment.json'} exists, but this {mode} run has no readiness check")
            v = checked_verdict(out / "assessment.json", run.criteria()[1])
            if v["verdict"] == "not_ready":
                only("assessment.json")
                return clarify.render_assess(key, v), config.EXIT_NOT_READY, "not ready"
        elif with_assess:
            raise config.Stop(f"{out / 'assessment.json'} is missing: did the agent step run?")
    if mode == "assess":
        only("assessment.json")
        return None, 0, "ready"
    if mode == "spec":
        only("assessment.json", "spec.json", "spec-questions.md")
        has_q, has_s = (out / "spec-questions.md").exists(), (out / "spec.json").exists()
        if has_q == has_s:
            raise config.Stop(f"{out} must hold exactly one of spec.json and spec-questions.md: did the agent step run?")
        if has_q:
            text = read_out_text(out / "spec-questions.md")
            if not text.strip():
                raise config.Stop(f"{out / 'spec-questions.md'} is empty")
            return clarify.render_spec_questions(key, text), config.EXIT_QUESTIONS, "questions"
        return clarify.render_spec(key, **checked_spec(run, req, ticket, out / "spec.json")), 0, "spec written"
    if mode == "build":
        only("build.json")
        if "build.json" not in found:
            raise config.Stop(f"{out / 'build.json'} is missing: did the agent step run?")
        return clarify.render_build(key, **checked_build(run, out / "build.json")), 0, "build done"
    raise config.Stop(f"mode {mode} has nothing to post")


def render_decision(key, d, max_rounds):
    kind = d["kind"]
    if kind in ("round", "assess_round"):
        return clarify.render_round(key, d["round"], max_rounds, d["questions"], d["assumptions"], d["reasons"])
    if kind == "handover":
        return clarify.render_handover(key, max_rounds)
    if kind == "proposal":
        return clarify.render_proposal(key, d["description"])
    return clarify.render_ready(key)


def clarify_outcome(run, req, ticket, comments):
    """(comment text or None, exit code, what happened, the new description or None, set it?), derived again from
    in/ (the comments) and out/clarify.json, which is checked as the agent step checked it."""
    out, key = run.io / "out", req["key"]
    _, max_rounds = checks.clarify_config(run.cfg)
    found = [n for n in fetch.OUT_FILES if (out / n).exists()]
    state = clarify.clarify_state(comments, key)
    apply, posting = fetch.apply_wanted(run), fetch.can_post(run, req)
    pause = fetch.clarify_pause_of(run, req, state)
    if pause:
        if found:
            raise config.Stop(f"{out} holds results {found}, but in/ says this run makes no call; nothing is posted")
        return None, pause[0], pause[1], None, False
    if clarify.applies_proposal(state, apply and posting):
        return proposal_outcome(run, req, ticket, state, found, max_rounds)
    extra = [n for n in found if n not in ("clarify.json", "description.md")]
    if extra:
        raise config.Stop(f"{out} holds results that a clarify run doesn't make: {extra}; nothing is posted")
    if "clarify.json" not in found:
        raise config.Stop(f"{out / 'clarify.json'} is missing: did the agent step run?")
    saved = config.read_json(out / "clarify.json")
    if not isinstance(saved, dict) or set(saved) not in ({"result"}, {"result", "assessment"}):
        raise config.Stop(f"{out / 'clarify.json'} must have the key result, and may have the key assessment")
    try:  # the messages may quote the file, which may be tampered
        result = checks.clarify_fields(saved["result"], run.criteria("clarify")[1], copied.MAX_CHARS - len(ticket["summary"]))
        v = checks.verdict_fields(saved["assessment"], run.criteria()[1]) if "assessment" in saved else None
    except config.Stop as e:
        raise config.Stop(copied.redact(str(e)))
    if v is not None:
        verdict_tokens(v, "clarify.json assessment")
    d = clarify.decide(result, state, None, max_rounds)
    needs = d["kind"] == "needs_assess"
    if needs != (v is not None) or needs != ("description.md" in found):
        raise config.Stop(f"{out}: the readiness verdict and description.md must be there exactly when the clarify result is "
                   "ready with confirmed assumptions; nothing is posted")
    if needs:
        if (out / "description.md").read_bytes() != result["description"].encode("utf-8"):
            raise config.Stop(f"{out / 'description.md'} differs from the description in clarify.json; nothing is posted")
        if apply and not posting:
            config.say("description not set (offline or --no-post): the comment file holds the proposal")
        d = clarify.decide(result, state, v, max_rounds, apply and posting)
    kind = d["kind"]
    desc = d["description"] if kind in ("proposal", "ready") else None
    return render_decision(key, d, max_rounds), d["exit"], fetch.clarify_what(d, max_rounds), desc, kind == "ready"


def proposal_outcome(run, req, ticket, state, found, max_rounds):
    """clarify_outcome for --apply on a posted proposal: out/ holds exactly clarify.json ({"proposal", "assessment"})
    and description.md, which must be the proposal's text as in/ gives it, byte for byte."""
    out, key = run.io / "out", req["key"]
    if sorted(found) != ["clarify.json", "description.md"]:
        raise config.Stop(f"{out} must hold exactly clarify.json and description.md for --apply on a posted proposal, not "
                   f"{found}; nothing is posted")
    saved = config.read_json(out / "clarify.json")
    if not isinstance(saved, dict) or set(saved) != {"proposal", "assessment"}:
        raise config.Stop(f"{out / 'clarify.json'} must have exactly the keys proposal and assessment for --apply on a posted "
                   "proposal; nothing is posted")
    cid, text = fetch.proposal_description(state, ticket["summary"], req["route"])
    if saved["proposal"] != cid:
        raise config.Stop(f"{out / 'clarify.json'} names another comment than the proposal {cid} in in/; nothing is posted")
    if (out / "description.md").read_bytes() != text.encode("utf-8"):
        raise config.Stop(f"{out / 'description.md'} differs from the proposal in comment {cid}; nothing is posted")
    try:  # the messages may quote the file, which may be tampered
        v = checks.verdict_fields(saved["assessment"], run.criteria()[1])
    except config.Stop as e:
        raise config.Stop(copied.redact(str(e)))
    verdict_tokens(v, "clarify.json assessment")
    d = clarify.decide_proposal(state, v, max_rounds, clarify.round_assumptions(state), text)
    desc = d["description"] if d["kind"] == "ready" else None
    return render_decision(key, d, max_rounds), d["exit"], fetch.clarify_what(d, max_rounds, True), desc, d["kind"] == "ready"


def show_diff(old, new):
    lines = list(difflib.unified_diff(old.splitlines(), new.splitlines(), "description in Jira", "proposed description",
                                      lineterm=""))
    print("\n".join(lines) if lines else "  (the proposed description equals the current one)")


def comment_order(c):
    """Comments in time order; at the same time, by id (numbers as numbers)."""
    i = c["id"]
    return c["created"], (0, int(i), "") if i.isdigit() else (1, 0, i)


def marker_for(body, key):
    """Whether the comment starts with one of this script's markers for key."""
    if clarify.tag_of(body) != "KI":
        return False
    line = clarify.first_line(body)
    m = clarify.ROUND_RE.fullmatch(line)
    return bool(m and m.group(2) == key) or line in {clarify.marker(k, key) for k in clarify.MARKERS if k != "round"}


def newer_run_check(now, before, key):
    """Stops when Jira now has a [KI] marker comment for key that is newer than every comment fetch saw: another run
    posted between this run's fetch and post (two answers close together start two pipeline runs)."""
    seen = {c["id"] for c in before}
    newest = max((comment_order(c) for c in before), default=None)
    for c in now:
        if c["id"] not in seen and marker_for(c["body"], key) and (newest is None or comment_order(c) > newest):
            raise config.Stop(f"another run posted meanwhile; nothing posted (comment {c['id']} on {key} is newer than what "
                       "this run fetched; run again)")


def newer_answer_check(now, before, key):
    """--apply on a posted proposal: stops when Jira now has a [Mensch] comment that is newer than every comment fetch
    saw. Someone answered the proposal while this run checked it, so it may no longer be what people want."""
    seen = {c["id"] for c in before}
    newest = max((comment_order(c) for c in before), default=None)
    for c in now:
        if c["id"] not in seen and clarify.tag_of(c["body"]) == "Mensch" and (newest is None or comment_order(c) > newest):
            raise config.Stop(f"a [Mensch] comment came in after this run fetched the ticket (comment {c['id']}); nothing is "
                              f"set or posted; run again: the next run reads the answer and clarifies {key} again")


def step_post(run, req, ticket, comments=()):
    """Checks out/ against in/, renders, and posts through the route. Offline or --no-post: only the files.
    clarify with --apply (APPLY=1 in a pipeline): sets the description first, then posts."""
    route, key = req["route"], req["key"]
    desc, set_desc = None, False
    if req["mode"] == "clarify":
        text, code, what, desc, set_desc = clarify_outcome(run, req, ticket, comments)
    else:
        text, code, what = outcome(run, req, ticket)
    if text is None:
        config.say(f"{key}: {what}, nothing to post")
        return code
    found = checks.post_findings(text, (run.cfg.get("jira") or {}).get("max_comment_chars", 30000))
    if found:
        raise config.Stop(f"refusing to post the comment for {key}: {'; '.join(found)}")
    path, dpath = run.io / "out" / "comment-1.txt", run.io / "out" / "description.md"
    try:
        path.write_bytes(text.encode("utf-8"))
        if desc is not None:
            dpath.write_bytes(desc.encode("utf-8"))
    except OSError as e:
        raise config.Stop(f"can't write {path.parent}: {e.strerror or e}")
    if desc is not None:
        show_diff(ticket["description"], desc)
    if route == "offline" or req["no_post"] or run.a.no_post:
        config.say(f"{key}: {what}; comment not posted ({'offline input' if route == 'offline' else '--no-post'}), "
            f"written to {path}")
        return code
    layer = run.jira(route, key)
    if req["mode"] == "clarify":
        state = clarify.clarify_state(comments, key)
        proposal = clarify.applies_proposal(state, fetch.apply_wanted(run))  # the proposal path, decided again from in/
        if route == "api":  # free over REST; over MCP a read costs credits, so not there
            now = layer.comments(key)
            newer_run_check(now, comments, key)
            if proposal:
                newer_answer_check(now, comments, key)
        if proposal:  # the free chain checks first (proposal_outcome ran them too), then the running account (api:
            # GET /myself; mcp: atlassianUserInfo, cached from the agent step)
            fetch.proposal_trust(state, None, route)
            fetch.proposal_trust(state, layer.myself(), route)
    if set_desc:
        layer.set_description(key, desc)
        config.say(f"{key}: description set")
    cid = layer.add_comment(key, text)
    config.say(f"{key}: {what}; comment {cid} posted, its text is in {path}")
    return code
