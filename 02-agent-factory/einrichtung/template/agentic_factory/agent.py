"""Step agent: the work calls for one request, and their raw results in out/."""
import shlex
import time

from . import blocked, copied, config, copilot, readiness, checks, clarify, feedback, fetch, revise
from . import ticket as ticket_mod


# --- step agent -----------------------------------------------------------------------------------------------------

def work_plan(run, req, ticket, comments=()):
    """The work calls for one request, built the way factory/agent.py builds them. clarify: the clarify call; the
    readiness check on the proposed description follows only when the result calls for it (clarify_agent)."""
    cfg, local, repo = run.cfg, run.local, run.repo
    mode, key = req["mode"], req["key"]
    # spec and build: what the comments say; a refused or untrusted rerun stops here
    fb = revise.decide(run, req, comments) if mode in fetch.FEEDBACK_MODES else None
    p = {"calls": [], "env_extra": {}, "fw": None, "source": None, "F": None, "change": None, "crit": None, "fb": fb,
         # a revision has no readiness check: the ticket passed it the first time
         "with_assess": fetch.assesses(cfg, mode, req["no_assess"]) and (fb is None or fb["kind"] == "first")}
    calls = p["calls"]  # (tag, prompt, tools, credit cap)
    if p["with_assess"]:
        p["crit"] = run.criteria()
        prompt, tools, cap = readiness.assess_call(cfg, ticket, p["crit"])
        calls.append(("assess", prompt, tools, cap))
        if mode == "assess" and not run.A.get("enabled"):
            config.say("note: assess.enabled is false in config.json, so the factory skips this check; running it anyway")
    if mode == "clarify":
        checks.clarify_config(cfg)
        state = clarify.clarify_state(comments, key)
        applying = fetch.apply_wanted(run) and fetch.can_post(run, req)
        p.update(state=state, pause=fetch.clarify_pause_of(run, req, state), crit=run.criteria("clarify"), proposal=None)
        if clarify.applies_proposal(state, applying):  # --apply on a posted proposal: only the readiness check on its text
            # the free chain checks first: a foreign or edited chain stops before any account call. Then, in one
            # process, the layer fetch made also checks the running account (api: GET /myself; mcp:
            # atlassianUserInfo, one short Copilot call, cached for the post step). Not with --print-only, which sets
            # nothing; the split agent step has no Jira. The post step checks the account before setting.
            fetch.proposal_trust(state, None, req["route"])
            me = (run.layers[req["route"]].myself()
                  if req["route"] in run.layers and not run.a.print_only else None)
            p["proposal"] = fetch.proposal_description(state, ticket["summary"], req["route"], me)
            prompt, tools, cap = readiness.assess_call(cfg, {**ticket, "description": p["proposal"][1]}, run.criteria())
            calls.append(("assess", prompt, tools, cap))
            config.say(f"{key}: clarify --apply, the proposal in comment {p['proposal'][0]}, project {repo}")
        else:
            prompt, tools, cap = checks.clarify_call(cfg, ticket, clarify.comments_block(key, state["tagged"]), p["crit"])
            calls.append(("clarify", prompt, tools, cap))
            config.say(f"{key}: clarify, project {repo}")
    elif mode != "assess":
        fw, source = ticket_mod.choose_framework(cfg, req["framework"], ticket["labels"])
        ticket_mod.check_installed(repo, fw)
        F = cfg["frameworks"][fw]
        p.update(fw=fw, source=source, F=F)
        config.say(f"{key}: mode {mode}, framework {fw} (from {source}), project {repo}")
        spec_file = None
        if mode == "spec" and (repo / config.QUESTIONS).exists():
            raise config.Stop(f"{config.QUESTIONS} exists from an earlier run: answer the questions in the ticket, delete it, "
                       "run again")
        if mode == "build":
            if fb["kind"] == "revision":  # the change the previous build built, still there, and what is new since
                p["fb"] = fb = revise.plan_build(run, req, F, fb)
                change, files = fb["change"], ticket_mod.repo_files(repo)
                config.say(revise.describe(fb))
            else:
                change, files = ticket_mod.find_change(repo, F, req["change"])
            paths = ticket_mod.spec_paths_for(F, change, files)
            specs = [x for x in paths if x.endswith("SPEC.md")]
            specs = [x for x in specs if f"/{change}/" in x] or specs
            spec_file = specs[0] if specs else paths[0] if paths else F["spec_root"].format(change=change)
            p["change"] = change
            config.say(f"building change {change} ({len(paths)} spec files)")
        if mode == "spec" and fb["kind"] == "revision":  # the spec rerun: a revise call (new comments), or none
            p["fb"] = fb = revise.plan(run, req, F, fb)
            p["change"] = fb["change"]
            config.say(revise.describe(fb))
            prompts, tools = [], []
            if fb["kind"] == "revise":
                prompt, tools, p["env_extra"] = copilot.revise_plan(cfg, key, fw, ticket, fb["change"],
                                                                    clarify.comments_block(key, fb["new"]))
                prompts = [("revise", prompt)]
        elif mode == "build" and fb["kind"] == "nothing":
            prompts, tools = [], []
        else:
            if mode == "build" and fb["new"]:  # the amend call first: the new comments become new, unchecked tasks
                fb["task_file"] = feedback.task_file(fw, F, p["change"], spec_file)
                fb["amend_paths"] = feedback.amend_paths(fw, F, p["change"], spec_file)
                prompt, amend_tools, _ = copilot.amend_plan(cfg, key, fw, ticket, p["change"],
                                                            clarify.comments_block(key, fb["new"]), fb["task_file"],
                                                            fb["revision"])
                if fw == "speckit":
                    amend_tools = ticket_mod.speckit_tool_map(repo, amend_tools)
                calls.append(("amend", prompt, amend_tools, None))
            prompts, tools, p["env_extra"] = copilot.plan(cfg, mode, key, fw, ticket, p["change"], spec_file,
                                                          revise.answers_block(key, fb) if mode == "spec" else "",
                                                          revise.spec_changes(fb) if mode == "build" else "")
            prompts = [(str(i), x) for i, x in enumerate(prompts, 1)]
        if fw == "speckit" and prompts:
            tools = ticket_mod.speckit_tool_map(repo, tools)
        calls += [(tag, x, tools, None) for tag, x in prompts]
    else:
        config.say(f"{key}: readiness check, project {repo}")
    if local:
        config.say(f"overrides from {run.a.local}: {sorted(local)}")
    return p


def print_calls(run, req, p):
    calls, logdir = p["calls"], run.log(req["key"])
    print(f"# {len(calls)} copilot call(s), {req['mode']}, {p['fw'] or 'no framework'}, run in {run.repo}")
    print("# environment: " + " ".join(f"{k}={v}" for k, v in {**copied.SAFE_ENV, **p['env_extra']}.items()))
    for n, (tag, prompt, tools, cap) in enumerate(calls, 1):
        argv = copilot.copilot_argv(run.cfg, run.local, prompt, tools, (logdir / f"usage-{tag}.json").as_posix(), cap=cap)
        print(f"\n# call {n}/{len(calls)}{' (readiness check)' if tag == 'assess' else ''}"
              f"\n{shlex.join(argv)}")
    if p.get("fb"):
        for line in revise.print_lines(p["fb"]):
            print(line)
    if req["mode"] == "clarify" and p["proposal"]:
        print(f"\n# no clarify call: this run sets the text of the proposal in comment {p['proposal'][0]} when the "
              "readiness check says ready")
    elif req["mode"] == "clarify":
        print("\n# a ready result with confirmed assumptions adds the readiness check on the proposed description")
        if p["pause"]:
            print(f"# this run makes no call now: {p['pause'][1]}")
    print("\n# a local run also adds --disable-mcp-server=NAME for each server `copilot mcp list` shows")


class Work:
    """Where a run's work calls happen: your Copilot with every MCP server it would start switched off, an
    environment without the Jira secrets, snapshots of the project that leave out the io folder when it lies inside
    (it isn't the agent's), and the credit total."""

    def __init__(self, run, key, env_extra, ctx):
        self.cfg, self.local, self.repo, self.io = run.cfg, run.local, run.repo, run.io
        try:
            self.prefix = self.io.relative_to(self.repo.resolve()).as_posix() + "/"
        except ValueError:
            self.prefix = None
        self.logdir = run.log(key)
        self.exe = copilot.resolve_copilot(self.local)
        self.env = copilot.child_env(self.cfg, env_extra)
        self.mcp_off = copilot.mcp_servers(self.exe, self.repo, self.env)
        config.say(f"MCP servers switched off for this run: {self.mcp_off}" if self.mcp_off
            else "no MCP servers to switch off")
        self.logdir.mkdir(parents=True, exist_ok=True)
        self.total = 0.0
        self.ctx, self.blocked = ctx, 0  # ctx: mode, framework, key, run; blocked: the calls logged to blocked.jsonl

    def report(self):
        """The run's last line about blocked calls."""
        config.say(blocked.summary(self.blocked, blocked.log_path(self.repo)))

    def snap(self):
        return {k: v for k, v in copilot.snapshot(self.repo).items() if not (self.prefix and k.startswith(self.prefix))}

    def call(self, tag, label, prompt, tools, cap, file_tools=("read", "write")):
        """One work call; returns its final message. file_tools: the file tools the call gets (init: read only). Stops
        when Copilot fails or when the call changed the io folder."""
        io_before = fetch.folder_digest(self.io)
        usage = self.logdir / f"usage-{tag}.json"
        argv = copilot.copilot_argv(self.cfg, self.local, prompt, tools, str(usage), self.exe, cap=cap, mcp_off=self.mcp_off,
                                  file_tools=file_tools)
        allowed = [*file_tools, *tools]
        config.say(f"copilot {label}: tools {allowed}")
        t0 = time.time()
        git_before = ticket_mod.git_dir_files(self.repo)
        rc, final, denied = copilot.run_call(argv, self.repo, self.env, self.logdir / f"events-{tag}.jsonl",
                                     self.cfg["agent_timeout_s"])
        cr = copilot.credits_of(usage)
        self.total += cr or 0
        config.say(f"copilot {label}: exit={rc} credits={cr} denied={denied} seconds={int(time.time() - t0)}")
        print("  final message: " + final[:1500].replace("\n", "\n    "))
        self.blocked += blocked.record(self.repo, {**self.ctx, "call": tag}, self.logdir / f"events-{tag}.jsonl", allowed)
        ticket_mod.check_git_dir(self.repo, git_before)  # before any git command: git could run code from there
        if rc != 0:
            raise config.Stop(f"copilot exited with {rc}; events: {self.logdir}")
        if fetch.folder_digest(self.io) != io_before:
            raise config.Stop(f"a work call changed the io folder {self.io}; nothing is posted")
        if not copilot.has_shell_tool(allowed):
            ran = copilot.shell_ran(self.logdir / f"events-{tag}.jsonl")
            if ran:
                raise config.Stop(f"the {label} ran the shell tool {ran[0]} although it may not run shell commands; "
                           f"nothing was posted. Events: {self.logdir / f'events-{tag}.jsonl'}")
        return final


def run_agent(run, req, p):
    """The work calls, then their raw results in out/. Returns the mode's exit code."""
    cfg, local, repo, io = run.cfg, run.local, run.repo, run.io
    mode, key, calls = req["mode"], req["key"], p["calls"]
    out = io / "out"
    fetch.clear_out(out)
    out.mkdir(parents=True, exist_ok=True)
    fb = p.get("fb")
    if fb and fb["kind"] == "nothing":  # before any Copilot process: no credits
        reason = revise.nothing_reason(fb)
        revise.write_nothing_new(out, mode, reason)
        config.say(f"{key}: {reason}")
        return 0
    if fb and fb["kind"] == "hand":
        return revise.hand_out(run, req, p)
    work = Work(run, key, p["env_extra"], {"mode": mode, "framework": p["fw"], "key": key, "run": run.log(key).name})
    try:  # the blocked-calls line ends every run, a stopped one too
        return _run_calls(run, req, p, work)
    finally:
        work.report()


def _amend_done(repo, fb, at, now, head):
    """After the amend call: it may change only what feedback.amend_paths allows, and make no commit, else Stop. Sets
    fb["amended"]. Returns True when the build calls should not run: nothing amended and no hand edits."""
    allowed = fb["amend_paths"]
    if ticket_mod.head_commit(repo) != head:
        raise config.Stop(f"the amend call may change only {', '.join(allowed)}, but it made a commit; nothing is "
                          "posted")
    changed = copilot.changed_paths(at, now)
    other = feedback.outside_amend([x[3:] for x in changed], allowed)
    if other:
        raise config.Stop(f"the amend call changed more than {', '.join(allowed)}: {other[:10]}; nothing is posted")
    fb["amended"] = bool(changed)
    if changed:
        return False
    config.say(f"note: the amend call changed nothing in {', '.join(allowed)}: no new tasks from the comments")
    if fb["diff"]:
        return False
    config.say("no hand edits of the spec either: no build call")
    return True


def _run_calls(run, req, p, work):
    cfg, repo, io = run.cfg, run.repo, run.io
    mode, key, calls = req["mode"], req["key"], p["calls"]
    out = io / "out"
    if p["with_assess"] and (repo / config.ASSESSMENT).exists():
        (repo / config.ASSESSMENT).unlink()
        config.say(f"removed the old {config.ASSESSMENT}")
    before = work.snap()
    head = ticket_mod.head_commit(repo)
    if before:
        config.say(f"note: the working tree already has {len(before)} uncommitted change(s)")
    t_all = time.time()
    ran = 0
    for n, (tag, prompt, tools, cap) in enumerate(calls, 1):
        at = work.snap() if tag == "amend" else None
        work.call(tag, "readiness check" if tag == "assess" else f"call {n}/{len(calls)}", prompt, tools, cap)
        ran = n
        if tag == "amend" and _amend_done(repo, p["fb"], at, work.snap(), head):
            break  # nothing amended and no hand edits: nothing to build, no build call
        if tag == "assess":
            other = [x for x in copilot.changed_paths(before, work.snap()) if x[3:] != config.ASSESSMENT]
            if other or ticket_mod.head_commit(repo) != head:
                raise config.Stop(f"the readiness check changed more than {config.ASSESSMENT}: {other[:10]}")
            v = checks.check_verdict(repo / config.ASSESSMENT, p["crit"][1])
            readiness.show_verdict(v)
            (out / "assessment.json").write_bytes((repo / config.ASSESSMENT).read_bytes())
            if v["verdict"] == "not_ready":
                config.say(f"not ready: no spec calls. Credits {work.total:.2f}. The verdict is in {config.ASSESSMENT}; "
                    "don't commit it")
                return config.EXIT_NOT_READY
            (repo / config.ASSESSMENT).unlink()
            if mode == "assess":
                config.say(f"ready. Credits {work.total:.2f}, {int(time.time() - t_all)} s, logs in {work.logdir}")
                return 0
            config.say("ready: the spec calls start")
        if mode == "spec" and (repo / config.QUESTIONS).exists():
            text = (repo / config.QUESTIONS).read_bytes().decode("utf-8", errors="replace")
            print(text[:4000])
            (out / "spec-questions.md").write_bytes(text.encode("utf-8"))
            config.say(f"the agent wrote {config.QUESTIONS} instead of a spec. Answer the questions in the ticket, delete the file, "
                f"run again. Credits {work.total:.2f}")
            return config.EXIT_QUESTIONS

    changed = copilot.changed_paths(before, work.snap())
    config.say(f"done: {ran} call(s), credits {work.total:.2f}, {int(time.time() - t_all)} s, logs in {work.logdir}")
    config.say(f"uncommitted changes ({len(changed)}):")
    for l in changed[:80]:
        print("    " + l)
    paths = [l[3:] for l in changed]
    now = ticket_mod.head_commit(repo)
    if now and now != head:
        commits = ticket_mod.git(repo, "log", "--oneline", f"{head}..HEAD" if head else "HEAD").splitlines()
        files = ticket_mod.git(repo, "diff", "--name-status", "--no-renames", head or ticket_mod.EMPTY_TREE, "HEAD").splitlines()
        config.say(f"the agent made {len(commits)} commit(s) on your branch, with {len(files)} file(s):")
        for l in commits[:20] + files[:80]:
            print("    " + l)
        paths += [x for x in (l.split("\t", 1)[-1] for l in files) if not (work.prefix and x.startswith(work.prefix))]
    for w in copilot.warnings_for(cfg, mode, p["fw"], paths):
        config.say("WARNING: " + w)
    if mode == "spec" and p["fb"]["kind"] == "revise":
        revise.revise_out(run, req, p, paths)
    elif mode == "spec":
        revise.first_out(run, req, p, paths)
    elif mode == "build":
        events = [work.logdir / f"events-{tag}.jsonl" for tag, *_ in calls[:ran] if tag not in ("assess", "amend")]
        revise.build_out(run, req, p, paths, fetch.test_line(events, fetch.test_command(cfg)), head)
    config.say("next: review `git diff`, run the tests yourself, and commit by hand")
    return 0


def clarify_agent(run, req, ticket, p):
    """One clarify run's work calls: the clarify call, and for a ready result with confirmed assumptions the
    unchanged readiness check on the proposed description. Writes out/clarify.json ({"result": FACTORY-CLARIFY.json
    as the call wrote it, "assessment": the verdict, when the check ran}) and out/description.md. --apply on a posted
    proposal: only the readiness check on the proposal's text, and out/clarify.json is {"proposal": the comment's
    id, "assessment": the verdict}. Returns the run's exit code; the post step decides again from in/ and out/."""
    cfg, repo, key = run.cfg, run.repo, req["key"]
    _, max_rounds = checks.clarify_config(cfg)
    out = run.io / "out"
    fetch.clear_out(out)
    out.mkdir(parents=True, exist_ok=True)
    state = p["state"]
    config.say(clarify.skip_note(state))
    if p["pause"]:
        config.say(p["pause"][1])
        return p["pause"][0]
    work = Work(run, key, {}, {"mode": "clarify", "framework": None, "key": key, "run": run.log(key).name})
    try:  # the blocked-calls line ends every run, a stopped one too
        return _clarify_calls(run, req, ticket, p, work)
    finally:
        work.report()


def _clarify_calls(run, req, ticket, p, work):
    cfg, repo, key = run.cfg, run.repo, req["key"]
    _, max_rounds = checks.clarify_config(cfg)
    out = run.io / "out"
    state = p["state"]
    assess_crit = run.criteria()
    for name in (checks.CLARIFY, config.ASSESSMENT):
        if (repo / name).exists():
            (repo / name).unlink()
            config.say(f"removed the old {name}")
    head, t_all = ticket_mod.head_commit(repo), time.time()

    def call(tag, label, prompt, tools, cap, name):
        """One call that may write only `name`."""
        before = work.snap()
        work.call(tag, label, prompt, tools, cap)
        other = [x for x in copilot.changed_paths(before, work.snap()) if x[3:] != name]
        if other or ticket_mod.head_commit(repo) != head:
            raise config.Stop(f"the {label} changed more than {name}: {other[:10]}")

    def check_readiness(prompt, tools, cap):
        call("assess", "readiness check", prompt, tools, cap, config.ASSESSMENT)
        v = checks.check_verdict(repo / config.ASSESSMENT, assess_crit[1])
        readiness.show_verdict(v)
        written = config.read_json(repo / config.ASSESSMENT)
        (repo / config.ASSESSMENT).unlink()
        return v, written

    dirty = work.snap()
    if dirty:
        config.say(f"note: the working tree already has {len(dirty)} uncommitted change(s)")
    _, prompt, tools, cap = p["calls"][0]
    if p["proposal"]:
        cid, text = p["proposal"]
        (out / "description.md").write_bytes(text.encode("utf-8"))
        config.say(f"--apply: no clarify call; the readiness check runs on the proposal's text from comment {cid}, in "
            f"{out / 'description.md'}")
        v, written = check_readiness(prompt, tools, cap)
        d = clarify.decide_proposal(state, v, max_rounds, clarify.round_assumptions(state), text)
        fetch.write_json(out / "clarify.json", {"proposal": cid, "assessment": written})
        config.say(f"{key}: {fetch.clarify_what(d, max_rounds, True)}. Credits {work.total:.2f}, {int(time.time() - t_all)} s, "
            f"logs in {work.logdir}")
        return d["exit"]
    call("clarify", "clarify call", prompt, tools, cap, checks.CLARIFY)
    result = checks.check_clarify(repo / checks.CLARIFY, p["crit"][1], copied.MAX_CHARS - len(ticket["summary"]))
    saved = {"result": config.read_json(repo / checks.CLARIFY)}
    (repo / checks.CLARIFY).unlink()
    d = clarify.decide(result, state, None, max_rounds)
    if d["kind"] == "needs_assess":
        (out / "description.md").write_bytes(result["description"].encode("utf-8"))
        config.say(f"ready, every assumption confirmed: the readiness check runs on {out / 'description.md'}")
        prompt, tools, cap = readiness.assess_call(cfg, {**ticket, "description": result["description"]}, assess_crit)
        v, saved["assessment"] = check_readiness(prompt, tools, cap)
        d = clarify.decide(result, state, v, max_rounds, fetch.apply_wanted(run) and fetch.can_post(run, req))
    fetch.write_json(out / "clarify.json", saved)
    config.say(f"{key}: {fetch.clarify_what(d, max_rounds)}. Credits {work.total:.2f}, {int(time.time() - t_all)} s, "
        f"logs in {work.logdir}")
    return d["exit"]
