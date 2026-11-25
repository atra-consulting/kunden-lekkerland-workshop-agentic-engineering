"""The steps fetch -> agent -> post: what they share (Run, in/ and out/, the outcome helpers), and step fetch."""
import hashlib
import json
import os
import re
import time
from pathlib import Path

from . import copied, config, copilot, readiness, jira_rest, jira_mcp, checks, clarify, feedback
from . import ticket as ticket_mod


# --- steps: fetch -> agent -> post ------------------------------------------------------------------------------------
# A run is three steps that hand over through a folder (--io-dir). fetch reads the ticket and its comments over the
# route and writes in/. agent makes the work calls and writes their raw results to out/. post checks out/ against in/
# again, renders the comment, and posts it. Locally (--step all) the three run in one process. In a pipeline they run
# as separate steps, each with only the secrets it needs (decision 6), so post trusts nothing in out/.

MODES = ("assess", "spec", "build", "clarify", "init")
STEPS = ("fetch", "agent", "post", "all")
ROUTES = ("offline", "mcp", "api")
REQUEST_KEYS = ("mode", "key", "route", "framework", "change", "no_assess", "no_post", "fresh", "me")
FEEDBACK_MODES = ("spec", "build")  # the modes whose reruns read [KI] results and [Mensch] comments
TICKET_KEYS = ("key", "summary", "description", "labels")
COMMENT_KEYS = ["author", "body", "created", "id", "updated"]  # jira_rest.make_comment, sorted
NOTHING_NEW = "nothing-new.json"  # spec and build reruns without new comments or hand edits: {"mode", "reason"}
OUT_FILES = ("assessment.json", "clarify.json", "description.md", "spec.json", "spec-questions.md", "build.json",
             NOTHING_NEW)
SPEC_OUT_KEYS = ("fw", "source", "change", "readiness_line", "spec_text", "revision", "handled", "hand_edited", "diff",
                 "checksum")
BUILD_OUT_KEYS = ("change", "changed", "test_line", "revision", "handled", "spec_diff", "start_commit", "checksum")
IO_DEFAULT = "agentic-io"  # split steps: inside the pipeline's clone
NO_TEST_RUN = "Der Agent hat den Testbefehl nicht ausgeführt."


def step_checks(step, mode, env):
    """Stops before anything runs: --step all in a pipeline, build in a pipeline (decision 3), and a pipeline step
    that sees a secret it must not have (decision 6). Outside a pipeline, the split steps may see both. init is local
    only: no pipeline, and no split steps (it has no Jira to separate from the Copilot call)."""
    if mode == "init":
        if config.in_pipeline(env):
            raise config.Stop("init is refused in a pipeline: it suggests changes to config.json for a person to review; "
                              "run it locally")
        if step != "all":
            raise config.Stop(f"init runs as --step all only, not --step {step}")
    if config.in_pipeline(env) and step == "all":
        raise config.Stop("in a pipeline, run --step fetch, --step agent, and --step post as separate pipeline steps")
    if config.in_pipeline(env) and mode == "build":
        raise config.Stop("build is refused in a pipeline: its code would vanish with the step; run build locally")
    if config.in_pipeline(env) and step in ("fetch", "post") and env.get("COPILOT_GITHUB_TOKEN"):
        raise config.Stop(f"--step {step} must not see COPILOT_GITHUB_TOKEN: give it to the agent step only")
    if config.in_pipeline(env) and step == "agent" and env.get("JIRA_API_TOKEN"):
        raise config.Stop("--step agent must not see JIRA_API_TOKEN: give it to the fetch and post steps only")


def assesses(cfg, mode, no_assess):
    """The factory's spec run starts with the readiness check when assess.enabled is true (factory/agent.py)."""
    A = cfg.get("assess") or {}
    return mode == "assess" or (mode == "spec" and bool(A.get("enabled")) and not no_assess)


def readiness_line(cfg, no_assess):
    if not (cfg.get("assess") or {}).get("enabled"):
        return clarify.READINESS_OFF
    return clarify.READINESS_SKIPPED if no_assess else clarify.READINESS_PASSED


def source_label(cfg, fw, source):
    """choose_framework's source, as the spec comment names it."""
    return {"--framework": "--framework", "label": f"Label {cfg['framework_label_prefix']}{fw}",
            "default": "Standard"}[source]


def test_command(cfg):
    return cfg["test_command"]


def test_lines(cmd):
    return (f"Testbefehl {cmd}: bestanden.", f"Testbefehl {cmd}: fehlgeschlagen.", NO_TEST_RUN)


def test_line(events_paths, cmd):
    """From the build calls' events: the last tool call whose command is the test command (or starts with it and a
    space), and the success of its matching tool.execution_complete (toolCallId)."""
    last, ok = None, {}
    for path in events_paths:
        try:
            lines = Path(path).read_bytes().splitlines()
        except OSError:
            continue
        for raw in lines:
            try:
                e = json.loads(raw)
            except ValueError:
                continue
            d = e.get("data") if isinstance(e, dict) else None
            if not isinstance(d, dict):
                continue
            cid = (str(path), d.get("toolCallId"))
            if e.get("type") == "tool.execution_start":
                args = d.get("arguments")
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except ValueError:
                        args = None
                c = args.get("command") if isinstance(args, dict) else None
                if isinstance(c, str) and (c.strip() == cmd or c.strip().startswith(cmd + " ")):
                    last = cid
            elif e.get("type") == "tool.execution_complete":
                ok[cid] = d.get("success") is True
    if last is None:
        return NO_TEST_RUN
    good, bad, _ = test_lines(cmd)
    return good if last[1] is not None and ok.get(last) else bad


def spec_result(repo, F, paths):
    """(change, spec text) of a spec run: the changed files under the framework's spec folders, in the format of
    factory/common.py spec_text. Exactly one change."""
    rx = re.compile(F["spec_change_re"])
    files = sorted({p for p in paths if rx.match(p) and (repo / p).is_file()})
    names = sorted({m.group(1) for p in files for m in [rx.match(p)] if m.group(1)})
    if len(names) != 1:
        raise config.Stop(f"the spec calls must write exactly one change; found {names or 'none'}, so nothing is posted")
    parts = []
    for p in files:
        body = (repo / p).read_bytes().decode("utf-8", errors="replace")
        parts.append(f"=== {p} ===\n{body.rstrip(chr(10))}\n")
    return names[0], "\n".join(parts)


def write_json(path, obj):
    try:
        path.write_bytes((json.dumps(obj, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))
    except OSError as e:
        raise config.Stop(f"can't write {path}: {e.strerror or e}")


def clear_out(out):
    """out/ of an earlier run must never be posted for this one. Removes only the files this script writes."""
    try:
        if not out.is_dir():
            return
        for p in [out / n for n in OUT_FILES] + sorted(out.glob("comment-*.txt")):
            if p.is_file():
                p.unlink()
    except OSError as e:
        raise config.Stop(f"can't clear {out}: {e.strerror or e}")


def folder_digest(folder):
    try:
        if not folder.is_dir():
            return {}
        return {p.relative_to(folder).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(folder.rglob("*")) if p.is_file()}
    except OSError as e:
        raise config.Stop(f"can't read {folder}: {e.strerror or e}")


class Run:
    """What every step needs: the options, the config, the project, the folders, and the Jira layer."""

    def __init__(self, a):
        self.a = a
        self.cfg = config.read_json(a.config)
        self.local = config.load_local(a.local)
        self.repo = Path(ticket_mod.git(Path(a.repo), "rev-parse", "--show-toplevel").strip())
        self.A = self.cfg.get("assess") or {}
        config.check_config(self.cfg)  # every step, before any Copilot call
        self.io = None
        self.logdir = None
        self.layers = {}

    def log(self, key):
        """~/.factory-local/<repo>/<stamp>-<mode>-<key>/, outside the project: a Jira call's Copilot must never load
        the project's .github/. Not created here."""
        if self.logdir is None:
            stamp = time.strftime("%Y%m%d-%H%M%S")
            logdir = Path.home() / ".factory-local" / self.repo.name / f"{stamp}-{self.a.mode}-{key}"
            try:
                logdir.resolve().relative_to(self.repo.resolve())
            except ValueError:
                self.logdir = logdir
            else:
                raise config.Stop(f"the log folder {logdir} lies inside the project {self.repo}: a Jira call there would "
                           "load the project's .github/; run from a home folder outside the project")
        return self.logdir

    def set_io(self, path):
        self.io = Path(path).resolve()
        if self.io == self.repo.resolve():
            raise config.Stop("--io-dir must be a folder of its own, not the project")

    def criteria(self, call="assess"):
        """(text, ids) of readiness.md as the call's block (assess or clarify) names it."""
        name = (self.A if call == "assess" else self.cfg["clarify"]).get("criteria_file", "readiness.md")
        return readiness.criteria(self.a.readiness or Path(self.a.config).resolve().parent / name)

    def jira(self, route, key):
        """The Jira layer of the route, made once per process. None when offline."""
        if route == "offline":
            return None
        if route not in self.layers:
            if route == "api":
                self.layers[route] = jira_rest.JiraRest(os.environ)
            else:
                if not (jira_mcp.PLUGIN_DIR / "hooks" / "guard.py").is_file():
                    raise config.Stop(f"{jira_mcp.PLUGIN_DIR / 'hooks' / 'guard.py'} is missing: copy the folder agentic-factory-plugin "
                               "next to agentic-factory.py (the mcp route needs its guard hook)")
                logdir = self.log(key)
                logdir.mkdir(parents=True, exist_ok=True)
                exe = copilot.resolve_copilot(self.local)
                env = copilot.child_env(self.cfg, {})
                jira_mcp.mcp_check(exe, jira_mcp.jira_server(self.local), logdir, env)  # fail closed before anything else
                self.layers[route] = jira_mcp.JiraMcp(self.cfg, self.local, exe, env, logdir, jira_mcp.PLUGIN_DIR)
        return self.layers[route]


# --- shared by the agent and post steps: --apply, posting, the proposal, the log line ---------------------------------

def clarify_what(d, max_rounds, from_proposal=False):
    """What a clarify decision does, for the log. from_proposal: --apply on a posted proposal (decide_proposal)."""
    if from_proposal and d["kind"] == "ready":
        return "ready: the proposal's text is set"
    return {"round": f"round {d['round']}: {len(d['questions'])} question(s), {len(d['assumptions'])} assumption(s)",
            "assess_round": f"the readiness check says not ready: round {d['round']} with its reasons",
            "handover": f"the round cap of {max_rounds} is reached: a person takes over",
            "proposal": "ready: the new description is proposed",
            "ready": "ready: the new description is set",
            "needs_assess": "ready: the readiness check is next"}[d["kind"]]


def apply_wanted(run):
    """--apply, or in a pipeline the variable APPLY=1 that a person sets when starting the run."""
    return bool(run.a.apply) or (config.in_pipeline(os.environ) and os.environ.get("APPLY") == "1")


def can_post(run, req):
    """Whether this run reaches Jira at all: not offline, no --no-post (in in/ or on this step)."""
    return req["route"] != "offline" and not req["no_post"] and not run.a.no_post


def clarify_pause_of(run, req, state):
    """clarify_pause for this run. --apply that can't set anything (offline, --no-post) pauses on a posted proposal
    like a run without --apply: no call, no credits."""
    apply = apply_wanted(run)
    pause = clarify.clarify_pause(state, apply and can_post(run, req))
    if pause and apply and clarify.clarify_pause(state, True) is None:
        return pause[0], "proposal already posted; --apply sets nothing offline or with --no-post"
    return pause


def proposal_trust(state, me=None, route=None):
    """Stops unless the proposal can be trusted. Anyone may comment, so a comment that merely starts with the marker
    proves nothing: every proposal comment after the last round must have that round's author (the script's account;
    --apply sets the last one), the proposal must not have been edited (created and updated differ; a route that
    doesn't send updated skips this), and with me, the account running this script (api: GET /myself; mcp:
    atlassianUserInfo), that account must have written them. route: "mcp" words that stop for the MCP route."""
    c, n = state["proposal"], state["rounds"]
    theirs = (state["last_round"] or {}).get("author") or ""
    foreign = [p["id"] for p in state["proposals"] if (p.get("author") or "") != theirs]
    why, kind = None, "mixed"  # kind: what helps. mixed: a new proposal, or by hand; foreign: not a new one; edited: a new one
    if not theirs or not all(p.get("author") for p in state["proposals"]):
        why = f"the author of a proposal or of round {n} is unknown"
    elif c["id"] in foreign:
        why, kind = f"another account wrote it than round {n}", "foreign"
    elif foreign:
        why, kind = f"another account than round {n}'s wrote the proposal in comment {', '.join(foreign)}", "foreign"
    elif me is not None and theirs != me and route == "mcp":
        why, kind = "it wasn't posted by the account running this script", "account"
    elif me is not None and theirs != me:
        why = f"it and round {n} were written by another account than the one this run uses"
    elif c.get("created") and c.get("updated") and c["created"] != c["updated"]:
        why, kind = "it was edited after it was posted", "edited"
    if why:
        head = f"the proposal in comment {c['id']} can't be trusted: {why}; nothing is set or posted; "
        if kind == "foreign":  # the foreign comment stays after a [Mensch] answer, so a new proposal can't help
            raise config.Stop(head + f"delete comment{'s' if len(foreign) > 1 else ''} {', '.join(foreign)} in Jira, "
                              "or set the description by hand")
        if kind == "account":
            raise config.Stop(head + "run --apply as the account that posted the proposal, or set the description by "
                              "hand")
        raise config.Stop(head + "answer it with a [Mensch] comment to get a new proposal"
                          + (f"; if round {n} came from another account than the one running now (say, the round was "
                             "posted locally and this run is in the pipeline), set the description by hand"
                             if kind == "mixed" else ""))


def proposal_description(state, summary, route, me=None):
    """(comment id, text) of the unanswered proposal: trusted (proposal_trust, with me, the running account, when the
    run has a Jira layer), its text as proposal_text reads it on this route, checked as the clarify result's
    description is (length, scans, links, FACTORY-)."""
    proposal_trust(state, me, route)
    c = state["proposal"]
    text = clarify.proposal_text(c["body"], route, c["id"])
    checks.clarify_text(text, "description", copied.MAX_CHARS - len(summary), f"the proposal in comment {c['id']}")
    return c["id"], clarify.neutral(text)


def account_of(run, mode, route, key, comments):
    """The account running this script, as in/request.json records it (me): over the route's Jira layer (api: GET
    /myself; mcp: atlassianUserInfo, one short Copilot call, cached), for spec and build only, and only when the
    comments hold a result or answers (feedback.needs_account). None offline, with --print-only, and otherwise. The
    fetch step records it, so the split agent step, which has no Jira, judges the comments as the post step does;
    the post step asks again and stops when in/ says otherwise."""
    if (route == "offline" or mode not in FEEDBACK_MODES or run.a.print_only
            or not feedback.needs_account(comments, key)):
        return None
    return run.jira(route, key).myself()


# --- step fetch -----------------------------------------------------------------------------------------------------

def fetch(run):
    """(request, ticket, comments) over the route. --ticket-file means offline (decision 1)."""
    a = run.a
    offline = bool(a.ticket_file)
    if a.comments_file and not offline:
        raise config.Stop("--comments-file needs --ticket-file: with Jira, the comments come from the ticket")
    route = config.choose_route(a.jira, os.environ, offline)
    config.say(f"Jira route: {route} ({config.route_reason(a.jira, os.environ, offline)})")
    ticket = ticket_mod.load_ticket_file(a.ticket_file, a.key) if offline else None
    key = ticket["key"] if offline else a.key
    if not key:
        raise config.Stop("--key is missing")
    ticket_mod.check_key(run.cfg, key)
    if offline:
        comments = jira_rest.load_comments_file(a.comments_file) if a.comments_file else []
    else:
        ticket, comments = run.jira(route, key).read(key)
    request = {"mode": a.mode, "key": key, "route": route, "framework": a.framework, "change": a.change,
               "no_assess": a.no_assess, "no_post": a.no_post, "fresh": a.fresh,
               "me": account_of(run, a.mode, route, key, comments)}
    return request, ticket, comments


def write_in(io, request, ticket, comments):
    d = io / "in"
    d.mkdir(parents=True, exist_ok=True)
    clear_out(io / "out")
    write_json(d / "request.json", request)
    write_json(d / "ticket.json", ticket)
    write_json(d / "comments.json", comments)


def read_in(run):
    """in/ as fetch wrote it, checked: the agent and post steps take mode, key, route, and the options from here."""
    d = run.io / "in"
    req = config.read_json(d / "request.json")
    if not isinstance(req, dict) or sorted(req) != sorted(REQUEST_KEYS):
        raise config.Stop(f"{d / 'request.json'} must have exactly the keys {', '.join(REQUEST_KEYS)}")
    if req["mode"] != run.a.mode:
        raise config.Stop(f"this is mode {run.a.mode}, but {d / 'request.json'} is for mode {str(req['mode'])[:20]}")
    if not isinstance(req["key"], str):
        raise config.Stop(f"{d / 'request.json'}: key must be a string")
    ticket_mod.check_key(run.cfg, req["key"])
    if run.a.key and run.a.key != req["key"]:
        raise config.Stop(f"--key {run.a.key} differs from {req['key']} in {d / 'request.json'}")
    if req["route"] not in ROUTES:
        raise config.Stop(f"{d / 'request.json'}: route must be one of {', '.join(ROUTES)}")
    for k in ("framework", "change"):
        if req[k] is not None and not isinstance(req[k], str):
            raise config.Stop(f"{d / 'request.json'}: {k} must be a string or null")
    for k in ("no_assess", "no_post", "fresh"):
        if not isinstance(req[k], bool):
            raise config.Stop(f"{d / 'request.json'}: {k} must be true or false")
    if req["me"] is not None and not (isinstance(req["me"], str) and req["me"].strip() and len(req["me"]) <= 200):
        raise config.Stop(f"{d / 'request.json'}: me must be an account id or null")
    if req["route"] == "offline" and req["me"] is not None:
        raise config.Stop(f"{d / 'request.json'}: me must be null on the offline route")
    t = config.read_json(d / "ticket.json")
    if (not isinstance(t, dict) or sorted(t) != sorted(TICKET_KEYS) or t["key"] != req["key"]
            or not all(isinstance(t[k], str) for k in ("summary", "description"))
            or not isinstance(t["labels"], list) or not all(isinstance(x, str) for x in t["labels"])):
        raise config.Stop(f"{d / 'ticket.json'} must have the strings key ({req['key']}), summary, description, and a list "
                   "of labels")
    comments = config.read_json(d / "comments.json")
    if not isinstance(comments, list) or not all(isinstance(c, dict) and sorted(c) == COMMENT_KEYS
                                                  and all(isinstance(v, str) for v in c.values()) for c in comments):
        raise config.Stop(f"{d / 'comments.json'} must be a list of comments with the strings id, created, updated, author, "
                          "body")
    return req, t, comments
