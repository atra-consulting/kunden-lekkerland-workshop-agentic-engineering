# Design: a generic agentic-factory template, with init, a blocked-tools log, and human feedback for spec and build

Date: 2026-11-25. Scope: `02-agent-factory/einrichtung/template/` (the `agentic-factory.py` template) and the German
docs that describe it.

## Intent

The template still carries the lab project (Symfony/PHP, `./bin/phpunit`, factory-base pipeline keys) and a team-rules
mechanism. Lekkerland teams should be able to drop it into their own repos, whatever the stack, and tune it from real
runs. Five changes, built in this order, each on top of the one before:

1. **Cleanup:** a minimal, stack-neutral `config.json`; team rules removed.
2. **Blocked-tools log:** one file per project that collects what unattended Copilot was denied, so the developer can
   hand it over and `config.json` gets adapted.
3. **`init`:** a mode that reads the project's docs (and the blocked-tools log) and suggests changes to `config.json`
   and `readiness.md`.
4. **Human feedback for `spec` and `build`:** `[Mensch]` comments on the ticket change an existing spec or an existing
   implementation when the developer reruns `spec` or `build`.
5. **Change log and migration:** a German page on what changed compared to factory-base `local.py`, with migration
   steps for existing projects.

## Goals, non-goals, anti-goals

- Goals: works for any stack after `init`; all three SDD frameworks (OpenSpec, Spec Kit, BMad) stay; the developer
  steers spec and build revisions from the ticket; the safety properties of today's script stay intact.
- Non-goals: pipeline support for `build` (still refused in a pipeline); status transitions, labels, branches, PRs;
  changing the factory-base pipeline itself.
- Anti-goals: `init` or a feedback comment loosening the safety config (deny lists, protected paths, forbidden
  flags/env); a fake `[KI]` comment steering a revision; the spec and the code drifting apart after build feedback.

## Constraints

- Python standard library only, as today. Mac and Linux tested; Windows untested.
- Copilot CLI 1.0.115, unattended (`-p`, `--no-ask-user`). Every tool the agent may use has to be on the allow list.
  Copilot loads `AGENTS.md` on its own; the prompts don't need to name it.
- The three-step split (`fetch` → `agent` → `post`) and its hand-over through `in/` and `out/` stay. New modes and
  outcomes fit into it.
- Comment markers stay German and start with `[KI]`; human comments start with `[Mensch]` (as `clarify` does).
- The docs in the repo are German and follow the repo's style (short sentences, no passive).

## Approaches considered (feedback)

The only real fork was how build feedback gets in, given that the same developer who ran `build` comments after
reading `git diff`:

- **A. `[Mensch]` comment in Jira, then rerun `build` (chosen).** Same mechanism as spec feedback and `clarify`; the
  ticket keeps the whole history. Cost: a detour through Jira.
- B. `build --feedback "…"` on the command line. Faster, but a second input path and different behavior for spec and
  build.
- C. Either input, but the agent changes only the code. Simplest, but the spec drifts from the code, and a later run can
  undo the fix.

Chosen: A, with the spec amended first (see part 4), so the spec stays the source of truth.

Then for spec feedback after a build exists, three options: (1) after a build, all feedback goes through `build`;
(2) a comment belongs to the `[KI]` comment it follows, and `build` follows a newer spec; (3) the comment names its
target. Chosen: (1), extended by a second channel the user asked about: hand edits of the spec files count as feedback
too. In the spec phase `spec` picks them up; after a build `build` picks them up, so spec and code can't drift.

## Part 1: cleanup

### `config.json` keeps

- `key_pattern`, `default_framework`, `enabled_frameworks`, `label_frameworks`, `framework_label_prefix`, `model`,
  `agent_timeout_s`, `max_ai_credits`, `spec_rules`, `build_rules`, `test_command`, `deny_tools`, `forbidden_flags`,
  `forbidden_env`, `jira.max_comment_chars`.
- The `assess` and `clarify` blocks, and `readiness.md` as the Definition of Ready.
- `frameworks.openspec|speckit|bmad` with every key the script reads (`spec_change_re`, `spec_required`,
  `spec_required_glob`, `spec_tools`, `build_tools`, `spec_prompts`, `build_prompts`, `spec_rule_folder`, `spec_root`,
  `spec_any_under`, `env_feature_dir`).
- Generic `protected_paths`: `bitbucket-pipelines.yml`, `factory/`, `AGENTS.md`, `CLAUDE.md`, `.github/`, `.agents/`,
  `.specify/`, `_bmad/`, `openspec/config.yaml`, Dockerfiles, `.dockerignore`, `.gitattributes`, `.gitmodules`,
  `.gitignore`, `.env*`, `.devcontainer/`, `.vscode/`, `bin/`, `FACTORY-QUESTIONS.md`.

### `config.json` loses

- Keys the script never reads (factory-base pipeline only): `project_key`, `jira.approver_account_ids`,
  `jira.factory_account_id`, `jira.status`, `jira.transition`, `bitbucket`, `composer_install`, `workspace_exclude`,
  `max_patch_bytes`, `frameworks.*.run2_editable_re`.
- Symfony/PHP: the protected paths `composer.(json|lock)`, `symfony.lock`, `phpunit*.xml*`, `phpstan*.neon`,
  `.php-cs-fixer*`, `importmap.php`, `tests/bootstrap.php`, `config/packages/`, `config/bundles.php`,
  `package(-lock).json`; `shell(composer:*)` in `deny_tools`; "Symfony 7 / PHP stack and PHPUnit" in the Spec Kit plan
  prompt, which becomes "Use the existing stack and test setup; no new dependencies."
- `./bin/phpunit` everywhere: in `build_rules`, in `test_command`, and as `shell(./bin/phpunit:*)` in every
  `build_tools` list.

### Test command

- `test_command` stays, in `config.json` only, as a string such as `"make test"`. Default in the template: empty.
- A `build` run with an empty `test_command` stops: "set test_command in config.json (or run init)". `assess`,
  `clarify`, and `spec` don't need it.
- The script derives the rest from it, as `test_override` does today: `build_rules` gets the command through a
  placeholder (`Run the tests with exactly: {test_command}`), and every build call gets one tool added for it.
  `build_tools` in `config.json` no longer names a test tool.
- The added tool is the whole command as a prefix, not just its first word: `make test` gives `shell(make test:*)`,
  `npm test` gives `shell(npm test:*)`, `uv run pytest` gives `shell(uv run pytest:*)`. This is narrower than today's
  `shell(<first word>:*)` and lets interpreter-based test commands through without allowing the interpreter itself.
  (Copilot's tool patterns take multi-word prefixes, as `shell(git push:*)` in `deny_tools` shows.)
- `test_command` is refused when it starts with a shell or interpreter followed by an inline-code flag (`bash -c`,
  `sh -c`, `python -c`, `node -e`, and similar), or holds shell operators (`;`, `&&`, `|`, `$(`, backticks). That
  applies to a hand-set value and to an `init` suggestion alike.
- `deny_tools` drops `shell(npm:*)` (it would block `npm test`; a deny beats every allow) and denies the installing
  subcommands instead: `shell(npm install:*)`, `shell(npm i:*)`, `shell(npm ci:*)`, `shell(npm exec:*)`. It keeps
  `shell(npx:*)`. The script stops before any call when the derived test tool matches a `deny_tools` entry, naming both.
- The `[KI]` build comment's test line (`fetch.test_line`) keeps working with the configured command.

### Default read-only tools

Added at the user's request after runs where `ls`, `find`, or `grep` were denied.

- New key `read_tools` in `config.json`, a list the script appends to every `spec` and `build` call (and the spec and
  build revision calls), after the framework's tools and before the derived test tool. Default:
  `shell(ls:*)`, `shell(cat:*)`, `shell(head:*)`, `shell(tail:*)`, `shell(wc:*)`, `shell(grep:*)`, `shell(pwd:*)`,
  `shell(diff:*)`, `shell(stat:*)`, `shell(cd:*)`.
- Not included, because they can write files or run commands although they look read-only: `find` (`-delete`,
  `-exec`), `sed` (`-i`), `awk` (`system()`), `xargs`, `rg` (`--pre`), `git grep` (`-O`), `tree` (`-o`), `sort` (`-o`).
  No `git` command either: `git diff`/`log`/`show` write files with `--output=`, and `.git/config` (`core.fsmonitor`,
  diff drivers) can turn any git call, `git status` included, into code execution.
  Copilot's patterns match a prefix, so a tool can't be allowed with a dangerous option denied.
- `assess`, `clarify`, and `init` don't get them: they have no shell, and any shell tool would switch off the
  backstop that stops a run when Copilot ran a shell command anyway.
- Every `read_tools` entry must be `shell(...)` and must not match `deny_tools`; the script stops otherwise.
  `init` may add entries but never removes any.
- Risk, stated in the README's safety section: `cat` and `grep` can read files outside the project, which Copilot's
  own read tool can't. The token scan before posting is the only backstop for text copied into a spec.
- Parity: the lab fixture `LAB_CFG` sets `read_tools` to `[]`.

### `local.json`

Keeps only machine settings: `model`, `copilot`, `jira_mcp_server`, `jira_site`. `test_command` and `stack_hint` go
(they are facts about the project, not about one machine). A `local.json` that still has them stops with a message that
says where the value lives now.

### Team rules removed

- Delete `regeln/`, `agentic_factory/rules.py`, `tests/test_rules.py`, the `rules` block, the `team_rules` criterion and
  every call site (`fetch.Run.rules`, `Run.criteria`, `rules.block/line/with_ids` in agent, readiness, checks, clarify).
- Guidance such as "minimal changes, no refactoring" (from `regeln/code.md`) belongs in the team's `AGENTS.md`. The
  template README says so.

### Tests

- Tests that check the template's own files follow the new config.
- The factory-base comparison tests (with `FACTORY_BASE`) are limited to the parts that still match: flags, the copied
  checks in `copied.py`, the `guard.py` marker. Prompt comparisons drop the changed Spec Kit plan prompt and the build
  rules' test command.

### Docs (German)

Update every file that mentions team rules, `regeln/`, `local.json` keys, `./bin/phpunit` as the template's default, or
the removed keys: the template README, `bedienung/lokal-ausfuehren.md`, the exercises in `01-erstworkshop/tag-2/`, the
prompt examples in `einrichtung/prompt-beispiele/`, and `werkzeuge/schreibe-ticket/` where it names `readiness.md` or
`agentic-factory.py`. The prompt examples are regenerated from the script, not edited by hand.

## Part 2: blocked-tools log

- One append-only file per project: `~/.factory-local/<repo>/blocked.jsonl`, next to the per-run log folders.
- Every work call (`assess`, `clarify`, each `spec` and `build` call, `init`) appends one JSON line per blocked tool
  call, read from its `events-*.jsonl`:
  `{"at", "run" (log folder name), "mode", "framework", "key", "call" (tag), "tool", "command" (full arguments),
  "kind" ("denied" or "blocked"), "message", "allowed" (the call's allowed tools)}`.
  - `denied`: `tool.execution_complete` with error code `denied` (not on the allow list).
  - `blocked`: Copilot's own guard (error message starting "Command blocked"), such as "dangerous shell expansion".
  - Ordinary failures ("Parent directory does not exist") are not logged.
- When a call had at least one entry, one more line `{"kind": "final", "call", "text"}` holds that call's final
  message (the place where the agent says what it couldn't do). `--no-ask-user` leaves no event for questions the agent
  couldn't ask; the final message and `FACTORY-QUESTIONS.md` are the only traces.
- The short Jira calls over MCP are not logged here: a denial there is a security signal, already checked by the
  script, not a config gap.
- Each run ends with one line: `N blocked call(s), see ~/.factory-local/<repo>/blocked.jsonl` (or none). No flag.
- The file holds commands, which may contain paths and ticket text, but no secrets beyond what the events already have.
  It stays outside the project, as the logs do.

## Part 3: `init`

### How it runs

- `agentic-factory.py init [--apply] [--print-only]`. No ticket, no Jira, no `--key`. Local only: refused in a
  pipeline.
- One unattended Copilot call: tools `read` and `write` only, `shell` denied, every MCP server off, cap 40 credits
  (`init.max_ai_credits` in `config.json`, with `init.prompt`). It may write only `FACTORY-INIT.json` in the repo root;
  the script checks that afterwards (as it does for `FACTORY-ASSESSMENT.json`) and removes the file.
- It reads `AGENTS.md` and the files it links to, `README*`, `CONTRIBUTING*`, `.github/copilot-instructions.md`, and
  build files (`Makefile`, `package.json` scripts, `pom.xml`, `build.gradle*`, `pyproject.toml`, `go.mod`,
  `Cargo.toml`, and similar).
- The script adds to the prompt: the current `config.json` (the parts `init` may change) and `readiness.md`; which
  frameworks are installed (`ticket.FRAMEWORK_MARKERS`); and a summary of `blocked.jsonl` (counts per tool, command,
  mode, framework), because the agent can't read outside the repo.

### What it may suggest

`FACTORY-INIT.json`, each suggestion with `reason` and `source` (file and line, or "blocked.jsonl"):

- `test_command`: one string.
- `add_tools`: per framework and mode (`spec`, `build`), tools to add.
- `add_protected_paths`: regular expressions.
- `add_deny_tools`: such as the stack's package manager.
- `enabled_frameworks`: from what is installed.
- `readiness_md`: the full new text, or null.

### Safety

The docs go into the prompt and may carry a prompt injection, so the script checks every suggestion before showing it:

- Only add or tighten. It never removes from `deny_tools` or `protected_paths`, never touches `forbidden_flags`,
  `forbidden_env`, prompts, or credit caps. Loosening is a human edit.
- Refused tools: bare `shell`, any tool matching `deny_tools`, interpreters and wildcard shells (`shell(bash:*)`,
  `shell(sh:*)`, `shell(zsh:*)`, `shell(python*:*)`, `shell(node:*)`, `shell(uv:*)`, `shell(npx:*)`,
  `shell(env:*)`), network tools (`curl`, `wget`, `ssh`, `scp`, `nc`), `git push|remote|config`. BMad's existing
  `shell(uv:*)` stays as it is; `init` just can't add more like it.
- A `test_command` suggestion passes the same checks as a hand-set one (part 1); its derived tool is the whole
  command as a prefix, so `uv run pytest` is fine although `shell(uv:*)` is refused.
- A refused suggestion is shown as refused, with the reason, not silently dropped.
- Broad tools are flagged in the report, such as `shell(make:*)` ("allows every Make target").
- `readiness_md` passes the same checks as `readiness.md` today (`readiness.criteria`), and must keep every existing
  criterion id the clarify and assess checks rely on, unless a person removes it by hand.

### Output

- Without `--apply`: a readable report in the terminal (each suggestion, reason, source, flags) and a unified diff of
  `config.json` and `readiness.md`. Nothing changes. Exit 0.
- With `--apply`: the same report, then the script writes `config.json` (keys in their order, two-space indent as
  today) and `readiness.md`. It never writes anything else.
- `init` can run any time; it suggests against the current files.

## Part 4: human feedback for `spec` and `build`

Two channels, in two phases. Channels: a `[Mensch]` comment on the ticket (for anyone, and when the agent should do
the writing), or a hand edit of the spec files in the working tree (for the developer). Phases: the spec phase lasts
until the first trusted `[KI]` build comment for the change; after that, the build phase.

| | Spec phase (no build yet) | Build phase (a build exists) |
|---|---|---|
| `[Mensch]` comment, then rerun | `spec` revises the spec | `build` adds the comments as tasks, then builds |
| Hand edit of spec files, then rerun | `spec` posts the current spec ("von Hand geändert", with diff), no Copilot call | `build` brings the code in line with the spec diff |
| Both | `spec` revises, starting from the edited files | `build` does both |
| `spec` rerun | as above | refuses: "a build exists; give feedback through build, or run spec --fresh" |

### Shared rules

- Comments are already fetched for every mode (`fetch.fetch`), so `in/comments.json` has them.
- New markers: `[KI] agentic-factory spec überarbeitung={n} key=…` and
  `[KI] agentic-factory build überarbeitung={n} key=…`. The first `spec` or `build` comment counts as revision 1.
- Only the markers `spec`, `spec überarbeitung`, `build`, and `build überarbeitung` count as a mode's previous result.
  `spec fragen` and the not-ready `assess` comment don't (they name no change).
- Which `[Mensch]` comments a run handles: those newer than the latest spec or build `[KI]` comment for the ticket and
  not named as handled by any `[KI]` comment. In the spec phase they belong to `spec`, in the build phase to `build`.
  Each revision comment names the ids it handled (a line such as `Bearbeitet: Kommentar 10234, 10240.`).
- After a `spec fragen` comment, the next `spec` run is a fresh spec run (not a revision) and gets the `[Mensch]`
  comments after it in its prompt, as answers, in the same fenced block as `clarify` uses.
- Trust: the previous spec or build `[KI]` comment a run builds on only counts when the account running the script
  wrote it and it wasn't edited, as `proposal_trust` does for clarify proposals. Otherwise the run stops, says which
  comment, and points to `--fresh`. Other `[KI]` comments (clarify rounds, assess) are not checked: a ticket clarified
  in the pipeline can still get local spec and build revisions.
- `--fresh` (spec and build): ignore every earlier `[KI]` comment of the mode and run as a first run, as today.
  Its comment counts as revision 1 again; `[Mensch]` comments before it are treated as handled. `spec --fresh` in the
  build phase also ends the build phase (the next `build` is a first build). This is the way back after a discarded
  build, a deleted spec folder, an untrusted comment, or a spec posted by the pipeline or a teammate's account.
- `[Mensch]` comments are data and binding decisions, never instructions outside the allowed tools and paths; the same
  factory rules as in `clarify` apply. They go into the prompt as a fenced block, as `clarify.comments_block` does.
- No new `[Mensch]` comments and no hand edits since the last `[KI]` comment of the phase: the run stops before any
  call, "nothing new", exit 0, no credits.
- `--print-only` shows which comments the run would handle and whether the spec changed by hand.

### Detecting hand edits: checksum and snapshot

- Spec checksum: sha256 over the change's spec files as `fetch.spec_result` lists them (sorted paths and contents).
  For BMad: the PRD folder and `specs/<change>/`.
- Every spec and build `[KI]` comment gets a line `Spec-Prüfsumme: <sha256>`, taken after the run's last call. For a
  build that is after the agent checked off tasks, so checked boxes don't count as hand edits later. The trust check
  covers the line.
- Every spec and build run also keeps a copy of the spec files as they were at that point:
  `~/.factory-local/<repo>/specs/<key>/<change>/<mode>-<n>/`. The copy is the base for the diff.
- Hand edits: the current checksum differs from the one in the latest spec or build `[KI]` comment.
- Copy missing (another machine, cleaned folder) but checksum differs: the spec phase posts the full spec without a
  diff and says so; the build phase stops, "the spec changed since the last build, but the copy of the built spec is
  missing; run build --fresh".

### Spec phase: spec rerun

- No readiness check (the ticket passed it the first time).
- The change name comes from the previous spec comment; its spec folder must exist in the working tree (uncommitted or
  committed). If it's gone: stop, "the spec folder <name> is missing; restore it, or run spec --fresh".
- Hand edits only, no new comments: no Copilot call. Post a `[KI]` spec revision comment that says "von Hand
  geändert", with the diff against the copy and the full current spec text.
- New comments (with or without hand edits): one call with the framework's spec tools and a revise prompt per framework
  in `config.json` (`frameworks.<fw>.revise_prompt`). It gets the ticket, the comments, and works on the files as they
  are now, hand edits included. It may write only under the framework's spec area (`spec_any_under`);
  `copilot.warnings_for` checks that.
- The result names the change from the previous comment, not from the changed files: a BMad revision may change only
  the PRD folder (`planning-artifacts/prds/…`) or only `specs/<change>/`, and both are fine. A revision that creates a
  second change folder stops.
- Post: a new `[KI]` spec revision comment with revision n, the handled comment ids, whether hand edits were part of
  it, the diff against the previous copy, and the full updated spec text.
- In the split steps it works as `spec` does; the spec folder must be in the step's clone, so in practice locally.

### Build phase: build rerun

- Every `[KI]` build comment also gets a line `Start-Commit: <sha>`: the commit the first build started on (today's
  `ticket_mod.head_commit` before the calls). Revisions keep it.
- The first build must still be there: every file named in the previous `[KI]` build comment must show up in
  `git diff --name-only <start-commit>` (working tree against that commit, so committed and uncommitted work both
  count). If the start commit is unknown to the repo or files are missing: stop, "the first build is gone; run build
  --fresh".
- Triggers: new `[Mensch]` comments, hand edits of the spec since the last build, or both.
- Calls:
  1. **Amend** (only with new comments): spec tools, may write only the task file: `tasks.md` for OpenSpec and Spec
     Kit, `SPEC.md` for BMad (a section `## Änderungen nach Review`, revision n). It turns the comments into new,
     unchecked tasks. The script checks that only that file changed.
  2. **Build:** the framework's normal build prompt and tools. With hand edits, the prompt gets one more fenced block:
     the spec diff since the last build (against the copy), with the instruction to bring the code in line with it.
     OpenSpec apply and Spec Kit implement pick up the unchecked tasks; BMad's build reads the amended `SPEC.md`.
     Changes land as uncommitted changes on top of the earlier build; tests run again.
- Post: a new `[KI]` build revision comment with revision n, the handled comment ids, the spec diff from hand edits
  (if any), changed files, the test line, `Start-Commit`, and `Spec-Prüfsumme`.

### Spike first: does each framework pick up new tasks?

Not verified yet: that `/openspec-apply-change` and `/speckit-implement` work on new unchecked tasks after earlier ones
are checked off, and that `/bmad-build-auto` reworks a `SPEC.md` it already marked done. Before the build revision is
built, a throwaway spike runs each framework's build twice in the lab project (build, add a task by hand, build again)
and records what happens. It also runs one build with a hand-edited spec and the spec-diff block. If a framework
doesn't re-enter, its build revision uses a revise-style build prompt instead
of its normal one (`frameworks.<fw>.rebuild_prompt`), and the design is updated before planning that part.

### Not part of this

- No round cap: every run is started by the developer. Credit caps per call stay.
- No feedback for `assess` (that's `clarify`).

### Documentation in the template README

The template README (German) gets a section „Feedback zu Spec und Build" that a developer can work from without the
design: the two channels and two phases (the table above), the workflow step by step (comment or edit, rerun, read
the new `[KI]` comment), when `spec` refuses and why, `--fresh`, the stops and what to do about each, and what the
`[KI]` comments contain (`Bearbeitet`, `Start-Commit`, `Spec-Prüfsumme`). It also gets sections for `init` and for
`blocked.jsonl` (what is in it, how to hand it over), and its file table follows the new file set. Written against the
finished code.

## Part 5: change log and migration (German)

A new German page in the template folder: `02-agent-factory/einrichtung/template/aenderungen.md`, linked from the
template README. Written last, against the finished code. Two sections:

### „Was sich gegenüber `local.py` geändert hat"

- Baseline: `factory/local.py` in [factory-lab](https://bitbucket.org/factory-lab/factory-lab/src/factory-base/factory/local.py),
  branch `factory-base`, commit `a414237`. There, `local.py` is one file with the modes `assess`, `spec`, `build`; it
  reads Jira over REST only, never comments, and takes `test_command`, `stack_hint`, `model`, `copilot` from
  `local.json`.
- Grouped by topic, each with what was and what is now: structure (one file → starter `agentic-factory.py` plus package
  `agentic_factory/`; renamed), modes (`clarify` and `init` new), Jira (reads comments, posts `[KI]` comments; routes
  `mcp` and `api`; the guard plugin), pipeline (three steps `fetch`/`agent`/`post`, `pipelines.example.yml`),
  configuration (slimmed `config.json`, `test_command` only there, `local.json` reduced, new blocks `clarify`, `init`,
  `revise_prompt`), safety (shell denied in calls without shell tools, MCP servers switched off, checks of every Jira
  call), feedback (`[Mensch]` revisions of spec and build), logs (`blocked.jsonl`).
- What stayed the same: prompts and flags as in factory-base `agent.py`, apart from the listed deviations (Spec Kit
  plan prompt, test command placeholder, revise and amend prompts).
- Facts only from the code and the baseline; checked against both, not from memory.

### „Migration für bestehende Projekte"

Two starting points, each with numbered steps and a table „alter Schlüssel → neuer Ort":

- **A: from `local.py`** (a `factory/` folder copied from factory-base).
- **B: from the earlier `agentic-factory.py`** (this template before these changes, with `regeln/` and `test_command`
  in `local.json`).

The steps cover:

- Copy the new files; remove `local.py` (A) or `regeln/` (B).
- Carry over values:
  - `test_command` moves from `local.json` to `config.json`.
  - The content of `stack_hint` and of `regeln/*.md` moves to `AGENTS.md`.
  - `model` and `copilot` stay in `local.json`.
  - The project's own changes to `config.json` (prompts, tools, protected paths) are carried over by hand.
- Run `init`, read the report, then `init --apply`.
- Set up the Jira MCP route (A only: new).
- Check with `--print-only` and an offline run with `--ticket-file`.
- What runs differently afterwards:
  - The script now posts comments.
  - A rerun of `spec`/`build` with `[Mensch]` comments revises.
  - A `local.json` with old keys stops the script.

## Left to the builder

- Exact wording of the new prompts (`init.prompt`, `frameworks.<fw>.revise_prompt`, the amend prompt) and of the German
  comment texts, in the style of the existing ones.
- Module layout: likely `agentic_factory/init.py`, `agentic_factory/blocked.py`, `agentic_factory/feedback.py`.
- Exit codes for the new outcomes, consistent with today's (0, 2, 4, 5, 6).
- How `init` renders the diff (`difflib` unified diff is enough).
- Tests: one test file per new module, with the existing fake Copilot and fake Jira server.

## Calls made in this design (not discussed with the user)

- `test_command` empty by default; `build` stops without it.
- `test_command` and `stack_hint` leave `local.json`.
- `init` can only add or tighten; it can't add interpreter or network tools; BMad's `shell(uv:*)` stays.
- Jira calls are not in `blocked.jsonl`.
- Spec revision skips the readiness check.
- Build revision uses two calls (amend, then build) rather than one.
- Spec checksum and copy live in the `[KI]` comments and in `~/.factory-local/`, not in the repo.
- A hand edit alone in the spec phase posts without a Copilot call.
- `spec --fresh` in the build phase ends the build phase.
- No round cap for revisions.
- `[KI]` revision comments are trusted only from the running account, as clarify proposals are.
- The derived test tool is the whole test command as a prefix; `test_command` with inline code or shell operators is
  refused; `deny_tools` denies npm's installing subcommands instead of all of `npm`.
- `spec fragen` and not-ready `assess` comments don't count as a spec result; answers after `spec fragen` go into the
  next fresh spec run.
- The trust check covers only the spec or build comment a revision builds on.
- `--fresh` is the way back to a first run.
- The build's start commit goes into the `[KI]` build comment.
- A BMad revision may touch the PRD folder and `specs/<change>/`; the change name comes from the previous comment.
- A spike checks each framework's build re-entry before the build revision is built.
- `read_tools` is one list for all spec and build calls, not six copies in `frameworks`.
- The design doc is in English; the docs it changes stay German.
- The change log lives in `template/aenderungen.md`; migration covers two starting points (`local.py` and the earlier
  `agentic-factory.py`).
