# Generic agentic-factory template Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the `agentic-factory.py` template stack-neutral, drop team rules, and add a blocked-tools log, an `init`
mode, human feedback for `spec` and `build`, and German docs with a change log and migration guide.

**Architecture:** Changes stay inside the existing package `agentic_factory/` and its fetch → agent → post split. New
pure modules (`blocked.py`, `init.py`, `feedback.py`, `snapshot.py`) hold the logic; `agent.py`, `post.py`, `fetch.py`,
`main.py` wire it in. All state for feedback lives in `[KI]` comments plus copies under `~/.factory-local/`.

**Tech Stack:** Python standard library only, `unittest`, GitHub Copilot CLI 1.0.115 (faked in tests), Jira (faked in
tests).

**Spec:** `docs/superpowers/specs/2026-11-25-agentic-factory-template-design.md`

## Global Constraints

- Template root `T` = `02-agent-factory/einrichtung/template/`. All code paths below are relative to `T` unless they
  start with `02-` or `01-`.
- Test command (from `T`): `python3 -I -B -m unittest discover -s tests -t .` — must pass at the end of every task.
- Python standard library only; no new dependencies.
- Copilot runs unattended: `-p`, `--no-ask-user`; every tool the agent uses must be on the allow list.
- Comment markers stay German and start with `[KI]`; human comments start with `[Mensch]`.
- Logs and copies live under `~/.factory-local/<repo>/`, never inside the project.
- Docs are German, short sentences, no passive; the design doc and code comments stay English.
- `init` and feedback may never loosen `deny_tools`, `protected_paths`, `forbidden_flags`, `forbidden_env`.
- Commits end with the attribution lines from the session's system reminder.

## Review Focus

- A spec revision comment (diff + full text) longer than `jira.max_comment_chars` (30000): drop the full text, keep the
  diff, say where the files are; stop only if the diff alone is too long. Test in Task 10.
- `test_command` with quotes or a leading env assignment (`pytest -k "a b"`, `CI=1 npm test`): refused with a message
  that names the problem. Test in Task 1.
- `blocked.jsonl` can't be written (path is a folder, HOME read-only): one warning line, the run goes on. Test in Task 4.
- A `[Mensch]` comment edited after a `[KI]` comment named it as handled: not handled again. Test in Task 8.
- `init` in a repo with no `AGENTS.md` and no README: the call still runs; no suggestions → "keine Vorschläge", exit 0.
  Test in Task 6.

---

## Phase 1: cleanup

### Task 1: Stack-neutral `config.json` and the derived test tool

**Files:**
- Modify: `config.json`, `agentic_factory/copilot.py` (`test_override`, `plan`), `agentic_factory/fetch.py`
  (`test_command`), `agentic_factory/post.py` (`checked_build`), `agentic_factory/agent.py` (callers of
  `fetch.test_command`), `agentic_factory/clarify.py` (`RENDER_SAMPLES`: use `make test`)
- Modify: `tests/fakes.py` (add `LAB_CFG`), `tests/test_copilot.py` (Parity uses `LAB_CFG`)
- Test: `tests/test_copilot.py` (new class `TestCommand`), `tests/test_config.py`

**Interfaces:**
- Produces:
  - `copilot.check_test_command(cmd: str) -> None` — raises `config.Stop`.
  - `copilot.test_tool(cmd: str) -> str` — returns `f"shell({cmd}:*)"`.
  - `copilot.denied_by(cmd: str, deny_tools: list[str]) -> str | None` — the first entry `shell(X:*)` with
    `cmd == X` or `cmd.startswith(X + " ")`.
  - `copilot.plan(cfg, local, mode, key, fw, ticket=None, change=None, spec_file=None, team_rules="")` keeps its
    signature in this task; `local` is no longer read for the test command or stack hint (Task 2 removes `local`).
  - `fetch.test_command(cfg) -> str` (was `(cfg, local)`): `cfg["test_command"]`, a string, may be `""`.
  - `config.json`: `"test_command": ""`; `build_rules` contains `{test_command}`; no `build_tools` list names a test
    tool.
  - `tests/fakes.py`: `LAB_CFG` = template config plus `"test_command": "./bin/phpunit"` and the Spec Kit plan prompt
    `"/speckit-plan Use the existing Symfony 7 / PHP stack and PHPUnit; no new dependencies.\n\n{spec_rules}"`.

- [ ] **Step 1: Write the failing tests** in `tests/test_copilot.py`, class `TestCommand`:
  - `test_build_tool_is_whole_command`: `plan({**FULL_CFG, "test_command": "make test"}, {}, "build", KEY,
    "openspec", TICKET, "c", "x")` → `tools[-1] == "shell(make test:*)"` and `"Run the tests with exactly: make test."`
    in `prompts[0]`.
  - `test_empty_test_command_stops_build`: `FULL_CFG` as is → `Stop` whose text contains
    `"set test_command in config.json (or run init)"`.
  - `test_spec_needs_no_test_command`: `plan(FULL_CFG, {}, "spec", …)` returns without `Stop`.
  - `test_inline_code_refused`: each of `"bash -c x"`, `"sh -c x"`, `"python3 -c 1"`, `"node -e 1"` → `Stop`.
  - `test_shell_syntax_refused`: each of `"make test && rm x"`, `"a; b"`, `"a | b"`, `"$(x)"`, `` "`x`" ``,
    `'pytest -k "a b"'`, `"CI=1 npm test"` → `Stop`.
  - `test_denied_test_tool_stops`: `{**FULL_CFG, "test_command": "npx jest"}` → `Stop` naming `npx jest` and
    `shell(npx:*)`.
  - `test_npm_test_passes_template_deny_list`: `{**FULL_CFG, "test_command": "npm test"}` → no `Stop`;
    `"shell(npm install:*)"` in `FULL_CFG["deny_tools"]`; `"shell(npm:*)"` not in it.
  - `test_lab_build_rules_equal_factory`: `copilot.fill(FULL_CFG["build_rules"], {"test_command": "./bin/phpunit"},
    "x") == copied.BUILD_RULES`.
- [ ] **Step 2: Write the failing test** `tests/test_config.py::test_template_config_is_stack_neutral`:
  `json.dumps(FULL_CFG)` contains none of `phpunit`, `Symfony`, `composer`, `symfony.lock`; none of the keys
  `project_key`, `bitbucket`, `composer_install`, `workspace_exclude`, `max_patch_bytes` at top level; `jira` has only
  `max_comment_chars`; no framework has `run2_editable_re`.
- [ ] **Step 3: Run tests, confirm they fail.** Run the test command. Expected: the new tests FAIL.
- [ ] **Step 4: Edit `config.json`** exactly as the spec's Part 1 "keeps"/"loses" lists say. Spec Kit plan prompt:
  `"/speckit-plan Use the existing stack and test setup; no new dependencies.\n\n{spec_rules}"`. `build_rules`: today's
  text with `./bin/phpunit` replaced by `{test_command}`. `deny_tools`: drop `shell(composer:*)` and `shell(npm:*)`,
  add `shell(npm install:*)`, `shell(npm i:*)`, `shell(npm ci:*)`, `shell(npm exec:*)`; keep `shell(npx:*)`.
- [ ] **Step 5: Implement** `check_test_command`, `test_tool`, `denied_by` in `copilot.py`; in `plan` for `build`:
  read `cfg["test_command"]`, stop if empty, `check_test_command`, stop if `denied_by`, fill `build_rules` with
  `{"test_command": cmd}` via `fill`, append `test_tool(cmd)` to the tools. Delete `test_override`.
  `check_test_command`: words split on single spaces; every char in `[A-Za-z0-9_./:@+,%-]` or space; first word has
  no `=`; first word (basename) in `{bash, sh, zsh, dash, python, python3, node, ruby, perl, pwsh, powershell}`
  followed by `-c`, `-e`, `--eval` or `-Command` → refused. Each refusal message names the reason.
- [ ] **Step 6: Switch callers** to `fetch.test_command(cfg)`; set `LAB_CFG` in `tests/fakes.py` and use it in
  `Parity.check` and the parity helpers instead of `CFG`.
- [ ] **Step 7: Run the test command.** Expected: all PASS (Parity skipped without `FACTORY_BASE`). Then run once with
  `FACTORY_BASE=<scratch clone>/factory` if a clone is at hand; Expected: Parity PASS.
- [ ] **Step 8: Commit** `config.json agentic_factory/ tests/` — "Make config.json stack-neutral and derive the test
  tool from test_command".

### Task 1b: Default read-only tools for spec and build

**Files:**
- Modify: `config.json` (new key `read_tools`), `agentic_factory/copilot.py` (`plan`), `tests/fakes.py`
  (`LAB_CFG["read_tools"] = []`)
- Test: `tests/test_copilot.py` (new class `ReadTools`)

**Interfaces:**
- Consumes: Task 1's `plan`, `denied_by`.
- Produces: `cfg["read_tools"]` (list of `shell(...)` strings); `copilot.check_read_tools(cfg) -> list[str]`
  (stops on a non-`shell(...)` entry or one that matches `deny_tools`, naming it). `plan` returns tools in the order
  framework tools, `read_tools`, test tool (build only).

- [ ] **Step 1: Write the failing tests:** `test_spec_and_build_get_read_tools` (for each framework, every default
  entry is in the tools of `spec` and `build`); `test_default_list` (`FULL_CFG["read_tools"]` equals exactly
  `["shell(ls:*)", "shell(cat:*)", "shell(head:*)", "shell(tail:*)", "shell(wc:*)", "shell(grep:*)", "shell(pwd:*)",
  "shell(diff:*)", "shell(stat:*)", "shell(cd:*)", "shell(git status:*)", "shell(git diff:*)", "shell(git log:*)",
  "shell(git show:*)", "shell(git ls-files:*)"]`); `test_dangerous_ones_absent` (none of `find`, `sed`, `awk`, `xargs`,
  `rg`, `git grep`, `tree`, `sort` appears); `test_order_test_tool_last`; `test_non_shell_entry_stops`;
  `test_denied_entry_stops`; `test_assess_and_clarify_unchanged` (their tools stay `[]`).
- [ ] **Step 2: Run, confirm FAIL.**
- [ ] **Step 3: Implement** `check_read_tools` and the append in `plan`; add `read_tools` to `config.json`; set
  `LAB_CFG["read_tools"] = []` so Parity still matches.
- [ ] **Step 4: Run the test command** (and once with `FACTORY_BASE`). Expected: PASS.
- [ ] **Step 5: Commit** — "Allow standard read-only commands in spec and build calls".

### Task 2: `local.json` keeps machine settings only

**Files:**
- Modify: `agentic_factory/config.py` (`LOCAL_KEYS`, `load_local`), `agentic_factory/copilot.py` (remove
  `STACK_DEFAULT`, `stack_override`, the `local` parameter of `plan`), `agentic_factory/agent.py`, `local.example.json`,
  `agentic_factory/main.py` (module docstring)
- Test: `tests/test_copilot.py` (replace `test_test_command*`, `test_stack_hint*`), `tests/test_config.py`

**Interfaces:**
- Consumes: Task 1's `plan`.
- Produces:
  - `config.LOCAL_KEYS = {"model", "copilot", "jira_mcp_server", "jira_site"}`.
  - `config.MOVED_KEYS = {"test_command": "config.json (key test_command)", "stack_hint": "AGENTS.md (describe the
    stack there)"}`.
  - `copilot.plan(cfg, mode, key, fw, ticket=None, change=None, spec_file=None, team_rules="")`.

- [ ] **Step 1: Write the failing tests:** `test_moved_key_stops` (a `local.json` with `test_command`, and one with
  `stack_hint`, each → `Stop` containing `"moved to"` and the new place); `test_example_file_loads`
  (`load_local(HERE / "local.example.json")` works and has no moved key).
- [ ] **Step 2: Run, confirm FAIL.**
- [ ] **Step 3: Implement** the key sets; `load_local` stops on a moved key before the unknown-key check; drop `local`
  from `plan` and update every caller; rewrite `local.example.json` without `test_command`/`stack_hint` and their
  comments.
- [ ] **Step 4: Run the test command.** Expected: PASS.
- [ ] **Step 5: Commit** — "Keep only machine settings in local.json".

### Task 3: Remove team rules

**Files:**
- Delete: `regeln/`, `agentic_factory/rules.py`, `tests/test_rules.py`
- Modify: `config.json` (drop `rules`), `agentic_factory/fetch.py` (`Run.rules`, `Run.criteria`),
  `agentic_factory/readiness.py` (`assess_call`), `agentic_factory/checks.py` (`clarify_call`),
  `agentic_factory/copilot.py` (`plan`), `agentic_factory/agent.py` (`work_plan`, `print_calls`, `clarify_agent`),
  `agentic_factory/config.py`, `tests/fakes.py` (`CFG = FULL_CFG`), `tests/test_copilot.py` (drop
  `test_team_rules_only_append_to_the_prompts`)
- Test: `tests/test_config.py`

**Interfaces:**
- Produces:
  - `readiness.assess_call(cfg, ticket, crit) -> (prompt, tools, cap)`.
  - `checks.clarify_call(cfg, ticket, comments_block, crit) -> (prompt, tools, cap)`.
  - `copilot.plan(cfg, mode, key, fw, ticket=None, change=None, spec_file=None) -> (prompts, tools, env_extra)`.
  - `fetch.Run.criteria(call="assess") -> (text, ids)` — the ids of `readiness.md` only.
  - `config.check_config(cfg) -> None` — stops when `cfg` has `"rules"`: "team rules were removed; move them to
    AGENTS.md". Called in `fetch.Run.__init__`.

- [ ] **Step 1: Write the failing tests** in `tests/test_config.py`: `test_no_team_rules_left` (`"rules"` not in
  `FULL_CFG`; `(HERE / "regeln").exists()` is false; no file in `agentic_factory/` contains `TEAM RULES` or
  `team_rules`); `test_rules_block_stops` (`config.check_config({**FULL_CFG, "rules": {}})` → `Stop` containing
  `AGENTS.md`).
- [ ] **Step 2: Run, confirm FAIL.**
- [ ] **Step 3: Delete and edit** as listed; remove every `rules.` call site and parameter.
- [ ] **Step 4: Run the test command.** Expected: PASS.
- [ ] **Step 5: Commit** — "Remove team rules; AGENTS.md carries team guidance".

## Phase 2: blocked-tools log

### Task 4: `blocked.jsonl`

**Files:**
- Create: `agentic_factory/blocked.py`, `tests/test_blocked.py`
- Modify: `agentic_factory/agent.py` (`Work.__init__`, `Work.call`, end of `run_agent` and `clarify_agent`),
  `tests/fakes.py` (`FAKE_COPILOT`: when the repo has a file `fake-denied`, emit one denied `bash` call with command
  `cat x | python3 y` before its normal work)

**Interfaces:**
- Produces:
  - `blocked.entries(events_path: Path) -> list[dict]` — `{"tool", "command", "kind", "message"}`; kind `"denied"`
    (error code `denied`) or `"blocked"` (message starts with `"Command blocked"`); other failures skipped. `command`:
    `arguments["command"]` when present, else `json.dumps(arguments)`.
  - `blocked.final_message(events_path: Path) -> str` — the last `assistant.message` content.
  - `blocked.log_path(repo: Path) -> Path` — `Path.home() / ".factory-local" / repo.name / "blocked.jsonl"`.
  - `blocked.record(repo: Path, ctx: dict, events_path: Path, allowed: list[str]) -> int` — appends one line per entry
    with `{"at", "run", "mode", "framework", "key", "call", "tool", "command", "kind", "message", "allowed"}`, plus
    `{"kind": "final", "call", "text"}` when there was an entry. Returns the number of entries. On `OSError`:
    `config.say("WARNING: can't write …")`, returns the count.
  - `blocked.summary(n: int, path: Path) -> str` — `f"{n} blocked call(s), see {path}"` or `"no blocked calls"`.
  - `agent.Work.blocked: int` — running total; `Work.__init__(run, key, env_extra, ctx)` with
    `ctx = {"mode", "framework", "key", "run"}`.

- [ ] **Step 1: Write the failing tests** in `tests/test_blocked.py`: `test_denied_and_blocked_kept_failures_skipped`
  (events with a denied, a "Command blocked: …" and a "Parent directory does not exist" complete → 2 entries, kinds
  `denied`, `blocked`); `test_final_line_only_when_blocked`; `test_appends_across_runs` (two `record` calls → lines of
  both); `test_write_error_warns_and_continues` (make `log_path` a folder → returns count, prints `WARNING`);
  E2E `test_spec_run_logs_denied_call` (`fake-denied` present → `blocked.jsonl` under the test `HOME` has a line with
  `mode` `spec`, `kind` `denied`, `command` `cat x | python3 y`; output contains `1 blocked call(s)`).
- [ ] **Step 2: Run, confirm FAIL.**
- [ ] **Step 3: Implement** `blocked.py`; call `record` in `Work.call` after `run_call`; print `summary` at the end of
  each run. Jira calls (`jira_mcp.py`) don't call it.
- [ ] **Step 4: Run the test command.** Expected: PASS.
- [ ] **Step 5: Commit** — "Log blocked tool calls to blocked.jsonl".

## Phase 3: `init`

### Task 5: Suggestion checks (pure)

**Files:**
- Create: `agentic_factory/init.py`, `tests/test_init.py`
- Modify: `config.json` (block `"init": {"max_ai_credits": 40, "prompt": "…"}`; prompt placeholders `{config}`,
  `{readiness}`, `{installed}`, `{blocked}`, `{output_file}`)

**Interfaces:**
- Consumes: `copilot.check_test_command`, `copilot.denied_by`, `copilot.test_tool`, `readiness.criteria`.
- Produces:
  - `init.OUT = "FACTORY-INIT.json"`.
  - `init.SUGGESTION_KEYS = ("test_command", "add_tools", "add_protected_paths", "add_deny_tools",
    "enabled_frameworks", "readiness_md")`. Each suggestion is `{"value", "reason", "source"}`; `add_tools` is
    `{"<fw>": {"spec": [s…], "build": [s…]}}`, the others lists of suggestions or one suggestion.
  - `init.check_suggestions(d: dict, cfg: dict, readiness_text: str, installed: list[str]) -> dict` —
    `{"accepted": [(key, path, suggestion)], "refused": [(key, path, suggestion, reason)], "notes": [str]}`. Unknown
    top-level keys → refused with reason "unknown key".
  - `init.refusal(tool: str, cfg: dict) -> str | None`.
  - `init.broad_note(tool: str) -> str | None` — single-word `shell(x:*)` → `f"allows every {x} command"`;
    `shell(make:*)` → `"allows every Make target"`.
  - `init.apply(cfg: dict, accepted) -> dict` — a new config; additions deduplicated, existing order kept, never a
    removal.
  - `init.blocked_summary(path: Path, limit=50) -> str` — counts per `(mode, framework, tool, command)`, most first.
  - `init.render_report(result: dict) -> str` and `init.diff(old: str, new: str, name: str) -> str`
    (`difflib.unified_diff`).

- [ ] **Step 1: Write the failing tests:** `test_refuses_interpreters_and_network` (`shell`, `shell(bash:*)`,
  `shell(python3:*)`, `shell(uv:*)`, `shell(npx:*)`, `shell(env:*)`, `shell(curl:*)`, `shell(ssh:*)`,
  `shell(git push:*)` all refused); `test_refuses_deny_list_match`; `test_refuses_non_shell_tools`
  (`github(create_issue)`); `test_unknown_key_refused` (`remove_deny_tools`); `test_apply_only_adds` (apply keeps
  every old `deny_tools`/`protected_paths` entry and order, appends new ones once); `test_test_command_checked`
  (`"bash -c x"` refused; `"uv run pytest"` accepted); `test_broad_tool_noted` (`shell(make:*)` →
  `"allows every Make target"` in notes); `test_readiness_must_keep_ids` (new text without an old id → refused);
  `test_bad_regex_protected_path_refused`; `test_blocked_summary_counts`.
- [ ] **Step 2: Run, confirm FAIL.**
- [ ] **Step 3: Implement** `init.py` (pure functions only; no Copilot call yet) and the `init` block in `config.json`.
- [ ] **Step 4: Run the test command.** Expected: PASS.
- [ ] **Step 5: Commit** — "Add init's suggestion checks".

### Task 6: `init` mode

**Files:**
- Modify: `agentic_factory/init.py` (`run_init`), `agentic_factory/main.py` (mode `init`), `agentic_factory/fetch.py`
  (`MODES`, `step_checks`), `tests/fakes.py` (`FAKE_COPILOT` mode `init`: writes the content of `fake-init.json` to
  `FACTORY-INIT.json`)
- Test: `tests/test_init.py` (E2E class)

**Interfaces:**
- Consumes: Task 5's functions, `agent.Work` (Task 4), `ticket_mod.FRAMEWORK_MARKERS`.
- Produces: `init.run_init(run, apply: bool, print_only: bool) -> int`; `agentic-factory.py init [--apply]
  [--print-only]` with no `--key`, no Jira, `--step all` only, refused in a pipeline.

- [ ] **Step 1: Write the failing tests:** `test_init_without_apply_changes_nothing` (report and diff printed;
  `config.json` and `readiness.md` bytes unchanged; `FACTORY-INIT.json` removed); `test_init_apply_writes_both`
  (accepted suggestions in `config.json`, two-space indent, trailing newline; new `readiness.md`);
  `test_init_refused_in_pipeline`; `test_init_call_writing_other_files_stops`; `test_init_without_docs_no_suggestions`
  (fake writes `{}` → output contains `keine Vorschläge`, exit 0); `test_init_print_only_runs_no_call`.
- [ ] **Step 2: Run, confirm FAIL.**
- [ ] **Step 3: Implement** `run_init`: build the prompt, one `Work.call` with tools `[]` (file tools only; shell is
  denied by `copilot_argv`), check only `FACTORY-INIT.json` changed, read and remove it, `check_suggestions`, print
  `render_report` and the diffs, write on `--apply`. Wire the mode in `main.py`.
- [ ] **Step 4: Run the test command.** Expected: PASS.
- [ ] **Step 5: Commit** — "Add the init mode".

## Phase 4: feedback for `spec` and `build`

### Task 7: Spike — framework re-entry (throwaway, manual, costs credits)

**Ask the user before running: it starts real Copilot calls.**

- [ ] **Step 1:** In a scratch clone of factory-lab (`factory-base`, frameworks installed), copy the template from
  Task 6 into `factory/`, set `test_command` to `./bin/phpunit`.
- [ ] **Step 2:** For each of `openspec`, `speckit`, `bmad`: `spec` and `build` offline with
  `--ticket-file 02-agent-factory/einrichtung/prompt-beispiele/ticket-FLAB-41.json --framework <fw>`; add one unchecked
  task by hand (BMad: a `## Änderungen nach Review` section in `SPEC.md`); `build` again; note whether the new task is
  implemented and checked off.
- [ ] **Step 3:** Once per framework, edit a spec sentence by hand and run the printed build command
  (`--print-only`) with a `<<<SPEC CHANGES` block appended to the prompt; note whether the code follows.
- [ ] **Step 4:** Write the results into the design doc under "Spike first", with the decision per framework (normal
  build prompt, or `frameworks.<fw>.rebuild_prompt`). If any framework needs `rebuild_prompt`, stop and show the user
  before Task 11.
- [ ] **Step 5: Commit** the design doc update — "Record the framework re-entry spike".

### Task 8: Feedback state from comments (pure)

**Files:**
- Create: `agentic_factory/feedback.py`, `tests/test_feedback.py`
- Modify: `agentic_factory/clarify.py` (`MARKERS`: `"spec_revision": "[KI] agentic-factory spec überarbeitung={rnd}
  key={key}"`, `"build_revision": "[KI] agentic-factory build überarbeitung={rnd} key={key}"`)

**Interfaces:**
- Produces:
  - Line formats (exact): `Bearbeitet: Kommentar <id>, <id>.`, `Start-Commit: <40 hex>`,
    `Spec-Prüfsumme: <64 hex>`, and today's `Change: <name>.` from `render_spec`/`render_build`.
  - `feedback.state(comments: list[dict], key: str) -> dict` with keys `phase` (`"none"|"spec"|"build"`), `last`
    (latest spec or build result comment or `None`), `last_spec`, `last_build`, `revision` (int, of `last`), `change`,
    `checksum`, `start_commit`, `files` (changed files listed in `last_build`), `new_human` (list of `[Mensch]`
    comments newer than `last` and not handled), `answers` (`[Mensch]` comments after the latest `spec fragen` when no
    spec result follows it), `handled` (set of ids).
    Phase rule: `build` when the latest build or build-revision comment is newer than the latest plain `spec` comment;
    `spec` when a spec result exists otherwise; else `none`. A plain marker counts as revision 1.
  - `feedback.trust(comment: dict, me: str | None) -> None` — stops when `me` is set and the author differs, or when
    `created != updated`; the message names the comment id and `--fresh`.
  - `feedback.handled_line(ids: list[str]) -> str`.

- [ ] **Step 1: Write the failing tests:** `test_no_results_phase_none`; `test_spec_phase_human_after_spec`;
  `test_build_phase_after_build`; `test_handled_not_repeated`; `test_edited_human_after_handled_not_repeated`
  (same id, new `updated`); `test_plain_spec_after_build_ends_build_phase`; `test_spec_questions_answers`;
  `test_questions_and_assess_are_not_results`; `test_untrusted_author_stops_with_fresh_hint`;
  `test_edited_result_stops`; `test_other_ticket_markers_ignored`; `test_revision_numbers`.
- [ ] **Step 2: Run, confirm FAIL.**
- [ ] **Step 3: Implement** `feedback.py` and the two markers.
- [ ] **Step 4: Run the test command.** Expected: PASS.
- [ ] **Step 5: Commit** — "Read spec and build feedback state from comments".

### Task 9: Spec checksum and copies (pure + files)

**Files:**
- Create: `agentic_factory/snapshot.py`, `tests/test_snapshot.py`

**Interfaces:**
- Produces:
  - `snapshot.spec_files(repo: Path, F: dict, change: str, known: list[str]) -> list[str]` — sorted repo-relative
    files that match `F["spec_change_re"]` with group 1 == `change`, plus files under the folder of any `known` path
    that matches `F["spec_any_under"]` (BMad PRD folders).
  - `snapshot.paths_in_spec_text(text: str) -> list[str]` — the `=== path ===` headers.
  - `snapshot.checksum(repo: Path, paths: list[str]) -> str` — sha256 over `path + "\0" + bytes + "\0"` in sorted order.
  - `snapshot.copy_dir(repo: Path, key: str, change: str, mode: str, n: int) -> Path` —
    `Path.home()/".factory-local"/repo.name/"specs"/key/change/f"{mode}-{n}"`.
  - `snapshot.save(repo: Path, paths: list[str], dest: Path) -> None` — replaces `dest`.
  - `snapshot.diff(dest: Path, repo: Path, paths: list[str]) -> str` — unified diff, added and removed files included;
    `""` when equal.

- [ ] **Step 1: Write the failing tests:** `test_checksum_order_independent`; `test_checksum_changes_on_edit`;
  `test_checksum_counts_crlf`; `test_save_then_diff_shows_edit_add_remove`; `test_diff_empty_when_equal`;
  `test_bmad_includes_prd_folder_from_known`; `test_copy_dir_outside_repo`.
- [ ] **Step 2: Run, confirm FAIL.**
- [ ] **Step 3: Implement** `snapshot.py`.
- [ ] **Step 4: Run the test command.** Expected: PASS.
- [ ] **Step 5: Commit** — "Add spec checksums and copies".

### Task 10: Spec rerun

**Files:**
- Modify: `agentic_factory/agent.py` (`work_plan`, `run_agent`), `agentic_factory/fetch.py` (`REQUEST_KEYS` + `fresh`;
  `SPEC_OUT_KEYS` + `revision`, `handled`, `hand_edited`, `diff`, `checksum`; `OUT_FILES` + `nothing-new.json`),
  `agentic_factory/post.py` (`checked_spec`, `outcome`), `agentic_factory/clarify.py` (`render_spec`),
  `agentic_factory/main.py` (`--fresh`), `config.json` (`frameworks.<fw>.revise_prompt` with `{ticket_block}`,
  `{comments_block}`, `{change}`, `{spec_root}`, `{spec_rules}`)
- Test: `tests/test_feedback_spec.py` (E2E; offline route with `--comments-file`, comment text from
  `out/comment-1.txt`; trust cases on the api route with `JiraE2E`)

**Interfaces:**
- Consumes: `feedback.state`, `feedback.trust`, `feedback.handled_line`, all of `snapshot`.
- Produces:
  - `clarify.render_spec(key, fw, source, change, readiness_line, spec_text, revision=1, handled=(),
    hand_edited=False, diff="", checksum="")` — marker `spec` for revision 1, `spec_revision` otherwise; adds the
    `Bearbeitet`, "von Hand geändert", diff block and `Spec-Prüfsumme` lines.
  - `fetch.Run.a.fresh: bool`; `req["fresh"]`.
  - `out/nothing-new.json` = `{"mode": "spec"|"build", "reason": str}` → post prints the reason, posts nothing, exit 0.

- [ ] **Step 1: Write the failing tests:** `test_first_spec_comment_has_checksum` (and a copy `spec-1` exists);
  `test_revision_with_human_comment` (one call with tag `revise`; comment starts with the `spec überarbeitung=2`
  marker, has `Bearbeitet: Kommentar 11.` and a `Spec-Prüfsumme`); `test_hand_edit_only_posts_without_call` (fake
  copilot records zero calls; `von Hand geändert`; the diff shows the edited line); `test_nothing_new_exit_0`;
  `test_refused_in_build_phase` (Stop text contains `spec --fresh`); `test_fresh_in_build_phase_is_first_spec`;
  `test_spec_folder_missing_stops`; `test_answers_after_questions_in_prompt`; `test_second_change_stops`;
  `test_long_comment_drops_full_text` (keeps the diff, says where the files are); `test_untrusted_spec_comment_stops`;
  `test_print_only_lists_comments_and_hand_edit` (output names the comment ids and "changed by hand"; no call).
- [ ] **Step 2: Run, confirm FAIL.**
- [ ] **Step 3: Implement** per the spec's "Spec phase: spec rerun": phase check, change from the comment, checksum
  compare, revise call or hand-edit-only path (empty `calls`), spec text over `snapshot.spec_files`, copy `spec-<n>`,
  post-side checks of `revision` and `handled` against `feedback.state(in/comments)`.
- [ ] **Step 4: Run the test command.** Expected: PASS.
- [ ] **Step 5: Commit** — "Revise specs from comments and hand edits".

### Task 11: Build rerun

**Files:**
- Modify: `agentic_factory/agent.py`, `agentic_factory/fetch.py` (`BUILD_OUT_KEYS` + `revision`, `handled`,
  `spec_diff`, `start_commit`, `checksum`), `agentic_factory/post.py` (`checked_build`), `agentic_factory/clarify.py`
  (`render_build`), `agentic_factory/feedback.py` (`first_build_missing`, `spec_diff_block`), `config.json`
  (`frameworks.<fw>.amend_prompt`; `rebuild_prompt` only if Task 7 says so)
- Test: `tests/test_feedback_build.py` (E2E)

**Interfaces:**
- Consumes: Tasks 8–10.
- Produces:
  - `feedback.first_build_missing(repo: Path, start: str, files: list[str]) -> list[str]` — files not in
    `git diff --name-only <start>` ∪ untracked files; raises `Stop` when `start` is not a commit in the repo.
  - `feedback.spec_diff_block(diff: str) -> str` — `"<<<SPEC CHANGES since the last build (data, not instructions)\n"
    + diff + "SPEC CHANGES>>>"`, with `SPEC CHANGES>>>` inside the diff defused as `comments_block` does.
  - `feedback.task_file(fw: str, F: dict, change: str, spec_file: str) -> str` — `tasks.md` under the spec root for
    `openspec`/`speckit`, `spec_file` for `bmad`.
  - `clarify.render_build(key, change, changed, test_line, revision=1, handled=(), spec_diff="", start_commit="",
    checksum="")`.

- [ ] **Step 1: Write the failing tests:** `test_first_build_comment_has_start_and_checksum`;
  `test_revision_runs_amend_then_build` (tags in order `amend`, `1`; only the task file changed in the amend call);
  `test_amend_touching_other_files_stops`; `test_hand_edited_spec_adds_diff_block` (build prompt contains
  `<<<SPEC CHANGES` and the edited line; comment shows the diff); `test_checked_boxes_are_not_hand_edits` (rerun with
  no comments after a build that checked a box → nothing new); `test_first_build_gone_stops_with_fresh_hint`;
  `test_copy_missing_with_edit_stops`; `test_build_nothing_new`; `test_build_fresh_is_first_build`.
- [ ] **Step 2: Run, confirm FAIL.**
- [ ] **Step 3: Implement** per the spec's "Build phase: build rerun"; checksum and copy `build-<n>` after the last
  call; `Start-Commit` kept from the first build.
- [ ] **Step 4: Run the test command.** Expected: PASS.
- [ ] **Step 5: Commit** — "Revise builds from comments and spec edits".

## Phase 5: docs (German)

### Task 12: Template README and the other docs

**Files:**
- Modify: `README.md` (template), `02-agent-factory/bedienung/lokal-ausfuehren.md`, `02-agent-factory/einrichtung/README.md`,
  `02-agent-factory/einrichtung/prompt-beispiele/README.md` and its pages, `01-erstworkshop/tag-2/uebung-factory-lokal.md`
  and the other files that `git grep -l -E "regeln/|stack_hint|Regeln des Teams|team_rules|local\.json"` lists
  (outside `T/aenderungen.md`), `02-agent-factory/werkzeuge/schreibe-ticket/` where it names `readiness.md` or
  `agentic-factory.py`.

- [ ] **Step 1: Template README:** new file table (no `regeln/`, new modules, `blocked.jsonl`), sections „Erste
  Einrichtung mit `init`", „Blockierte Aufrufe: `blocked.jsonl`", „Feedback zu Spec und Build" (the two-channel,
  two-phase table; step-by-step; when `spec` refuses; `--fresh`; every stop and what to do; the lines `Bearbeitet`,
  `Start-Commit`, `Spec-Prüfsumme`), the note that team guidance belongs in `AGENTS.md`, the updated safety section
  (test tool is the whole command; `npm` installs denied; the default `read_tools`, what is left out and why, and that
  `cat`/`grep` can read outside the project).
- [ ] **Step 2: Regenerate the prompt examples** from `agentic-factory.py --print-only` with the FLAB-41 ticket file and
  a config with `test_command` `./bin/phpunit`; say so in the examples' README.
- [ ] **Step 3: Update the other files** from the `git grep` list.
- [ ] **Step 4: Verify:** `git grep -n -E "regeln/|stack_hint|Regeln des Teams|team_rules"` lists only
  `T/aenderungen.md` (after Task 13) and the design/plan docs. Every command in the docs matches `main.py --help`.
- [ ] **Step 5: Commit** — "Document init, blocked.jsonl, and feedback; drop team rules from the docs".

### Task 13: Change log and migration

**Files:**
- Create: `aenderungen.md` (template), linked from the template README's intro

- [ ] **Step 1: „Was sich gegenüber `local.py` geändert hat"**, per the spec's Part 5, checked line by line against
  `factory/local.py` at `a414237` (clone factory-lab, branch `factory-base`) and the finished code.
- [ ] **Step 2: „Migration für bestehende Projekte"**, starting points A (`local.py`) and B (earlier
  `agentic-factory.py`), numbered steps and the table „alter Schlüssel → neuer Ort".
- [ ] **Step 3: Verify:** follow migration B in a scratch copy of the template as it was on `origin/main`
  (`git show origin/main:<T>`), with a `local.json` that has `test_command` and a `regeln/` folder; every step works;
  the moved-key stop appears where the page says.
- [ ] **Step 4: Commit** — "Add change log and migration guide".
