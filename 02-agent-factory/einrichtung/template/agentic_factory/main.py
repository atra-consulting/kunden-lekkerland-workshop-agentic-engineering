"""agentic-factory.py: run the factory's Copilot calls for one Jira ticket, in your own project, and post the result
on the ticket as a comment that starts with [KI].

Usage (from anywhere inside the project's git repository; the ticket is its key or its Jira URL, such as
https://example.atlassian.net/browse/LL-123; --key LL-123 is the long form):
  python3 agentic-factory.py assess  LL-123                readiness check (needs an "assess" block in config.json)
  python3 agentic-factory.py spec    LL-123 [--framework speckit] [--no-assess]
  python3 agentic-factory.py build   LL-123 [--change <name>] [--framework speckit]
  python3 agentic-factory.py clarify LL-123 [--apply]      clarify the ticket in rounds of comments
  python3 agentic-factory.py spec    LL-123 [--fresh]      again: revise the spec from [Mensch] comments and hand edits;
                                                           --fresh starts over as a first spec
  python3 agentic-factory.py build   LL-123 [--fresh]      again: revise the build from [Mensch] comments and spec edits
  python3 agentic-factory.py spec    LL-123 --print-only   read the ticket, print the work calls, run none of them
  python3 agentic-factory.py init    [--apply]             suggest config.json and readiness.md changes from the project's docs
                                                           (local only; no ticket, no Jira; --apply writes the last checked result)

Options:
  --jira mcp|api         how to reach Jira. mcp: your Copilot's Atlassian MCP server (local.json jira_mcp_server,
                         default "atlassian", and jira_site); the default outside a pipeline. api: REST with
                         JIRA_BASE_URL, JIRA_API_TOKEN, and JIRA_EMAIL for Jira Cloud; the default in a pipeline.
  --ticket-file t.json   offline: the ticket from a file, never Jira, never a post; --comments-file c.json adds comments
  --no-post              write each comment to <io>/out/comment-<n>.txt instead of posting it
  --apply                clarify: set the clarified description on the ticket (in a pipeline: the variable APPLY=1)
  --step fetch|agent|post|all
                         all (the default) runs the three steps in one process. A pipeline runs them as separate steps
                         (fetch and post with the Jira secrets, agent with the Copilot token) that hand over through
                         --io-dir (default ./agentic-io): in/ holds the request, ticket, and comments; out/ the results.
                         post checks out/ against in/ again before it posts. build is refused in a pipeline.

Exit codes for --step all: 0 done or ready, 4 not ready, 5 questions posted (clarify: or waiting for answers), 6 round
cap (clarify), 2 error. The split steps exit 0 unless there is an error.

Same prompts, flags, and order as factory/agent.py. Prompts, tools, deny_tools, and the model come from config.json
next to agentic-factory.py, with the test command in config.json (test_command). local.json there holds this
machine's settings: model, copilot (the command that starts Copilot CLI), jira_mcp_server, and jira_site. Logs go to ~/.factory-local/<project>/, outside the project.

What agentic-factory.py doesn't do: no separate user, no container, no check step (protected paths, secrets, invisible
characters) on the work, no approval gate between spec and build, no status transitions. Review `git diff` yourself.

Python standard library only. Mac, Linux, and Windows (Windows untested). The code is the package agentic_factory/
next to agentic-factory.py; this module is the command line.
"""
import argparse
import os
import sys

from . import copied, config, checks, fetch, agent, init, post
from . import ticket as ticket_mod


# --- main -------------------------------------------------------------------------------------------------------------

def parse(argv):
    ap = argparse.ArgumentParser(prog="agentic-factory.py",
                                 description="Run the factory's Copilot calls for a Jira ticket and post the result.")
    ap.add_argument("mode", choices=list(fetch.MODES))
    ap.add_argument("ticket", nargs="?", help="the ticket: its key, such as LL-123, or its Jira URL, such as "
                    "https://example.atlassian.net/browse/LL-123 (not for init)")
    ap.add_argument("--key", help="Jira ticket key, such as LL-123 (the long form of the ticket argument)")
    ap.add_argument("--jira", choices=["mcp", "api"], help="how to reach Jira: mcp (your Copilot's Atlassian MCP "
                    "server; default outside a pipeline) or api (REST; default in a pipeline)")
    ap.add_argument("--ticket-file", help="JSON with key, summary, description, labels; offline: no Jira, no posts")
    ap.add_argument("--comments-file", help="with --ticket-file: JSON list of comments {body, created?, id?}")
    ap.add_argument("--framework", help="speckit, openspec, or bmad; else the ticket's sdd-* label")
    ap.add_argument("--change", help="build: the spec folder's name, if there is more than one")
    ap.add_argument("--no-assess", action="store_true", help="spec: skip the readiness check before the spec calls")
    ap.add_argument("--fresh", action="store_true", help="spec and build: ignore the earlier [KI] results of the mode and "
                    "run as a first run (after a discarded build, a deleted spec folder, or an untrusted comment)")
    ap.add_argument("--no-post", action="store_true", help="write the comments to out/comment-<n>.txt, post nothing")
    ap.add_argument("--apply", action="store_true", help="clarify: set the clarified description; init: write the last init run's checked result to config.json and readiness.md, without a Copilot call")
    ap.add_argument("--print-only", action="store_true",
                    help="read the ticket (over MCP: one Jira call), print the copilot commands of the work calls, "
                    "run none of them and set or post nothing")
    ap.add_argument("--step", choices=list(fetch.STEPS), default="all",
                    help="all (default) runs fetch, agent, and post in one process; a pipeline runs them one by one")
    ap.add_argument("--io-dir", help=f"the hand-over folder with in/ and out/ (default: <log folder>/io for --step "
                    f"all, ./{fetch.IO_DEFAULT} for the other steps)")
    ap.add_argument("--config", default=str(config.HERE / "config.json"))
    ap.add_argument("--local", default=str(config.HERE / "local.json"), help="this machine's settings (default: local.json here)")
    ap.add_argument("--readiness", help="the criteria file for both assess and clarify (default: their "
                    "criteria_file next to config.json)")
    ap.add_argument("--repo", default=".", help="the project (default: the git repository around the current folder)")
    return ap.parse_args(argv)


def main(argv=None):
    a = parse(sys.argv[1:] if argv is None else argv)
    fetch.step_checks(a.step, a.mode, os.environ)
    if a.print_only and a.step not in ("all", "agent"):
        raise config.Stop("--print-only works with --step all or --step agent")
    if a.mode == "init" and a.ticket is not None:
        raise config.Stop("init takes no ticket: it reads the project's docs, not Jira")
    run = fetch.Run(a)
    if a.ticket is not None:  # the short form of --key: a key or a ticket URL, before any call (ruling R33)
        key = ticket_mod.key_from_arg(a.ticket, run.cfg, run.local, os.environ)
        if a.key and a.key != key:
            raise config.Stop(f"the ticket {key} differs from --key {a.key}")
        a.key = key
    if a.mode == "init":  # no ticket, no Jira, no route
        return init.run_init(run, a.apply, a.print_only)
    if a.mode == "assess" and not run.A:
        raise config.Stop("assess is not available in this config: config.json has no \"assess\" block")
    if a.mode == "clarify":
        checks.clarify_config(run.cfg)

    def agent_step(req, ticket, p):
        return agent.clarify_agent(run, req, ticket, p) if req["mode"] == "clarify" else agent.run_agent(run, req, p)

    if a.step == "all":
        req, ticket, comments = fetch.fetch(run)
        if a.print_only:
            agent.print_calls(run, req, agent.work_plan(run, req, ticket, comments))
            return 0
        run.set_io(a.io_dir or run.log(req["key"]) / "io")
        fetch.write_in(run.io, req, ticket, comments)
        req, ticket, comments = fetch.read_in(run)
        agent_step(req, ticket, agent.work_plan(run, req, ticket, comments))
        return post.step_post(run, req, ticket, comments)

    # split steps (decision 2): 0 for every outcome that isn't an error; an error stops with 2
    run.set_io(a.io_dir or fetch.IO_DEFAULT)
    if a.step == "fetch":
        req, ticket, comments = fetch.fetch(run)
        fetch.write_in(run.io, req, ticket, comments)
        config.say(f"{req['key']}: fetched {len(comments)} comment(s); in/ is in {run.io}")
        return 0
    req, ticket, comments = fetch.read_in(run)
    if a.step == "agent":
        config.say(f"Jira route: {req['route']} (from in/request.json; the agent step doesn't talk to Jira)")
        p = agent.work_plan(run, req, ticket, comments)
        if a.print_only:
            agent.print_calls(run, req, p)
            return 0
        code = agent_step(req, ticket, p)
        config.say(f"{req['key']}: agent step done (exit code {code} as one run); out/ is in {run.io}")
        return 0
    if a.jira and a.jira != req["route"]:
        raise config.Stop(f"--jira {a.jira} differs from the route {req['route']} in in/request.json")
    offline = req["route"] == "offline"
    config.choose_route(None if offline else req["route"], os.environ, offline)  # the pipeline and api checks, again
    config.say(f"Jira route: {req['route']} (from in/request.json)")
    post.step_post(run, req, ticket, comments)
    return 0


def entry():
    """The command line: every stop is exit code 2, an unexpected error too (without a traceback)."""
    try:
        sys.exit(main())
    except config.Stop as e:
        config.say(f"STOP: {e}")
        sys.exit(2)
    except KeyboardInterrupt:
        config.say("interrupted")
        sys.exit(130)
    except Exception as e:  # noqa: BLE001 - an OSError writing out/, a bug: exit 2 as every stop
        config.say(copied.redact(f"STOP: unexpected {type(e).__name__}: {e}"))
        sys.exit(2)
