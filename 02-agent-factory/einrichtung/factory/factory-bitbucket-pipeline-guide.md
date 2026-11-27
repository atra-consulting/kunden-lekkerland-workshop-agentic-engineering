# Run the Agentic Factory in a Bitbucket Pipeline, Started by Jira Automation

**Status.** The `agentic-*` pipelines never ran in Bitbucket. The Automation rule is an untested sketch. Nobody read the FLAB rules page. Lab details come from `02-agent-factory/einrichtung/jira.md`, Part B. Secret isolation per step is unverified: no record says a step without a deployment can't see that deployment's variables.
The blueprint is the lab's `factory-base` in `factory-lab/factory-lab`, with Jira space `FLAB` on `betterprojectsfaster.atlassian.net`. The full version with the reasoning, and the records behind each S-ID, are in the Almanach repository: [factory-bitbucket-pipeline-guide-long.md](https://github.com/atra-consulting/almanach/blob/main/briefs/factory-bitbucket-pipeline-guide-long.md) and its `records/` folder.

Tags: (S-nnnn) is a vendor record. S-7113 is a forum post. (internal) is the factory's code or the workshop docs. (lab) is what the lab did or saw. (untested) is a choice nobody has tried.

## Prerequisites

1. **Bitbucket Cloud repository with Pipelines on.** From the repository admin. No documented path.
2. **A runner.** Atlassian's runners, or a self-hosted runner and its labels, from the repository admin.
3. **An image, and the Dockerfile you write for it.** It needs `python3` 3.9 or newer, `git`, and Copilot CLI, tested with 1.0.115 (internal). No Dockerfile exists. The predecessor's `factory/image/Dockerfile` is a starting point (lab).
4. **A registry** the runner pulls from without credentials, or with a pull-only credential (untested). No documented way to authenticate a private registry.
5. **A technical Jira user,** `<bot-email>`, from the Jira admin. Role: view and "Add comments", no edit (lab). Adding a comment needs "Browse projects and Add comments project permission" (S-7123).
6. **A Jira API token** for that user, with scopes `read:jira-work` and `write:jira-work` (lab). "Once you create an API token, you can't modify its scopes." (S-7534, service-account tokens). No documented path for a regular user's token.
7. **The cloud ID** of your Jira site. S-7534 says: "Locate the string after /s/ in your admin URL or response". Don't use the Organization ID (S-7534).
8. **A Copilot fine-grained PAT** from the Copilot seat holder. It "Must be owned by your personal account (not an organization) with the Copilot Requests account permission" (S-7538). "Classic personal access tokens (ghp_) are not supported." (S-7540).
9. **Bitbucket repository access tokens** with "Pipelines: Write" only (S-7527). You need one trigger token for the rule and one start token per starter. No documented path.
10. **Three deployment environments,** `agentic-jira`, `agentic-agent` and `agentic-post`, and their deployment permissions. No documented path for custom environments. The records don't confirm how deployment permissions behave for branches or token-started runs.
11. **An opt-in label,** `<opt-in-label>`, such as `agentic`. The Jira admin picks it.
12. **Named people:**
    - a repository admin
    - a Jira admin and a backup admin
    - starters, who already have repository write access
    - a first responder, who holds a start token
    - a token coordinator

## Installation Steps

`assess` checks whether a ticket is ready for a spec. It comments only when the ticket isn't ready. `clarify` posts one round of questions and assumptions per run. People answer in a comment that starts with `[Mensch]`, and the factory's comments start with `[KI]`. The texts are German (internal).

### 1. Check the Repository

- If `bitbucket-pipelines.yml` exists, you merge into it in step 7.
- Look at "Workspace Settings → Pipelines → Workspace variables" and "Repository Settings → Pipelines → Repository variables" (S-7114). They reach every step, the agent too (internal). Move what an existing build needs into a deployment the agent doesn't use.
- List the custom pipelines on all branches and tags. The trigger token can start each of them (lab). Protect the ones that use deployment secrets with deployment permissions, or move them out (untested).

```bash
git fetch origin --tags
for b in $(git for-each-ref --format='%(refname:short)' refs/remotes/origin refs/tags); do
  echo "== $b"; git show "$b:bitbucket-pipelines.yml" 2>/dev/null | grep -nE 'custom:|deployment:'
done
```

### 2. Protect the Start Branch

Pick `<start-branch>`. Allow no direct push, and merges only through a pull request by named people. Forbid deletion and history rewrites (lab). Check that a direct push fails. Do this before you store any secret.

Branch protection doesn't protect the secrets. Anyone with write access may use the deployments from another branch (untested). Limit all three deployments to `<start-branch>` with deployment permissions (untested). The records don't confirm that this works.

### 3. Copy `factory/`

The script runs only from `factory/agentic-factory.py` at the top of the git clone (internal). A pipeline refuses `build` and `init` (internal). Open one pull request now, and merge it in step 7. From your repository's top folder:

```bash
F=<workshop>/02-agent-factory/einrichtung/factory
mkdir -p factory
cp -R "$F/agentic_factory" factory/
cp "$F"/{agentic-factory.py,config.json,readiness.md,.gitignore} factory/
if [ -e bitbucket-pipelines.yml ]; then
  cp "$F/pipelines.example.yml" pipelines.agentic.yml   # merge by hand in step 7, then delete it
else
  cp "$F/pipelines.example.yml" bitbucket-pipelines.yml
fi
```

Adapt `config.json` and `readiness.md` to your project. To do so, run `init` locally (internal).

### 4. Set the Runner and Build the Image

- **Atlassian's runners:** delete every `runs-on:` line in step 7, and build for amd64 (lab).
- **A self-hosted runner:** use its labels. "A runs-on parameter must contain a self.hosted label." (S-7520). The records don't confirm `linux.arm64` as a label.
- Build the image, push it to `<registry>`, and pin it as `<registry>/<image>@sha256:<digest>` (lab).
- Check that `copilot --version` runs inside the image.

### 5. Create the Tokens

- Create the Jira token and the Copilot token. Store them only in deployments (step 6).
- Create the trigger token. Store it only as the rule's hidden header (step 9).
- Give start tokens only to starters, who already have write access (untested). A start request may override deployment variables: "Pipeline > Deployment > Repository > Workspace" (S-7114). The records don't say whether that works for undeclared names such as `JIRA_BASE_URL`.
- Never start runs with a personal or admin token (lab).
- Hand tokens over through a password manager, never through a ticket or a chat.

### 6. Create the Deployments and Their Variables

Create the environments under "Repository Settings → Pipelines → Deployments" (S-7114). Never use repository or workspace variables for these (internal).

| Environment | Secured | Not secured |
|---|---|---|
| `agentic-jira` | `JIRA_API_TOKEN` | `JIRA_BASE_URL`, `JIRA_EMAIL` |
| `agentic-agent` | `COPILOT_GITHUB_TOKEN` | – |
| `agentic-post` | `JIRA_API_TOKEN` | `JIRA_BASE_URL`, `JIRA_EMAIL` |

`JIRA_BASE_URL` is `https://api.atlassian.com/ex/jira/<cloud-id>` (lab). S-7534 shows this form for service-account tokens. `JIRA_EMAIL` is `<bot-email>`. The script stops if `fetch` or `post` sees the Copilot token, or if `agent` sees the Jira token (internal).

### 7. Finish `bitbucket-pipelines.yml` and Merge

Add `agentic-assess-dryrun` to the file (untested). It is `agentic-assess` with `--no-post` on fetch and post. `agentic-assess` from the example stays as it is, apart from the image and `runs-on` edits. Its agent step keeps `max-time: 25`, because assess makes one call (internal).

```yaml
image:
  name: <registry>/<image>@sha256:<digest>
options:
  max-time: 45                                # example: 30 (untested)
pipelines:
  custom:
    agentic-clarify:
      - variables:
          - name: JIRA_KEY
          - name: APPLY                       # set only by hand, never in the rule
      - step:
          name: fetch (Jira token only)
          runs-on: [self.hosted, linux.arm64] # your labels, or delete for Atlassian's runners
          deployment: agentic-jira
          concurrency-group: agentic
          max-time: 5
          auth: { system: { scopes: [read:git:bitbucket] } }
          script:
            - python3 -I factory/agentic-factory.py clarify --key "$JIRA_KEY" --step fetch
          artifacts: [agentic-io/in/**]
      - step:
          name: agent (Copilot token only)
          runs-on: [self.hosted, linux.arm64]
          deployment: agentic-agent
          concurrency-group: agentic
          max-time: 45                        # example: 25 (untested)
          auth: { system: { scopes: [read:git:bitbucket] } }
          script:
            - python3 -I factory/agentic-factory.py clarify --key "$JIRA_KEY" --step agent
          artifacts: [agentic-io/out/**]
      - step:
          name: post (Jira token only)
          runs-on: [self.hosted, linux.arm64]
          deployment: agentic-post
          concurrency-group: agentic
          max-time: 5
          auth: { system: { scopes: [read:git:bitbucket] } }
          script:
            - python3 -I factory/agentic-factory.py clarify --key "$JIRA_KEY" --step post
    agentic-assess-dryrun:                    # untested; delete after run 1 passes
      - variables:
          - name: JIRA_KEY
      - step:
          name: fetch (Jira token only)
          runs-on: [self.hosted, linux.arm64]
          deployment: agentic-jira
          concurrency-group: agentic
          max-time: 5
          auth: { system: { scopes: [read:git:bitbucket] } }
          script:
            - python3 -I factory/agentic-factory.py assess --key "$JIRA_KEY" --step fetch --no-post
          artifacts: [agentic-io/in/**]
      - step:
          name: agent (Copilot token only)
          runs-on: [self.hosted, linux.arm64]
          deployment: agentic-agent
          concurrency-group: agentic
          max-time: 25
          auth: { system: { scopes: [read:git:bitbucket] } }
          script:
            - python3 -I factory/agentic-factory.py assess --key "$JIRA_KEY" --step agent
          artifacts: [agentic-io/out/**]
      - step:
          name: post (Jira token only)
          runs-on: [self.hosted, linux.arm64]
          deployment: agentic-post
          concurrency-group: agentic
          max-time: 5
          auth: { system: { scopes: [read:git:bitbucket] } }
          script:
            - python3 -I factory/agentic-factory.py assess --key "$JIRA_KEY" --step post --no-post
          artifacts: [agentic-io/out/**]      # keeps comment-1.txt
```

**`max-time`.** Each Copilot call may run 20 minutes (`agent_timeout_s` 1200, internal). A `clarify` run can make two calls. So the agent step gets 45: two calls plus 5 minutes of margin (untested). Allowed values: "A positive integer between 1 and 720" (S-7117).

**Merge case.** If the file already existed, follow this checklist (untested):

- Don't copy `image` or `options`.
- Check that any existing global `max-time` is at least 45.
- On every agentic step, add `image: name: <registry>/<image>@sha256:<digest>`. The records don't confirm a step-level `image`.
- Keep each step's own `max-time`.

Merge after step 6 is done, and re-check against other edits to the file.

### 8. Test by Hand

Use a test ticket `PROJ-123` that isn't ready and holds no personal or customer data. It needs no opt-in label. Start runs with "Run pipeline" in Bitbucket (internal), or with a start token and the API (lab):

```bash
printf 'Token: '; read -rs TOKEN; echo
printf 'header = "Authorization: Bearer %s"\n' "$TOKEN" | curl -sS -w '\nHTTP %{http_code}\n' -K - -X POST \
  -H "Content-Type: application/json" \
  "https://api.bitbucket.org/2.0/repositories/<workspace>/<repo>/pipelines" \
  -d '{"target":{"type":"pipeline_ref_target","ref_type":"branch","ref_name":"<start-branch>","selector":{"type":"custom","pattern":"agentic-assess-dryrun"}},"variables":[{"key":"JIRA_KEY","value":"PROJ-123"}]}'
unset TOKEN
```

Expect `HTTP 201`. S-7529 lists 201, 400 and 404 for this call. Run in order (untested):

| # | Pipeline | Expected line or result (internal) |
|---|---|---|
| 1 | `agentic-assess-dryrun` | post: `comment not posted (--no-post)`. The text is in the run's artifacts |
| 2 | `agentic-assess` | A `[KI] agentic-factory assess` comment in the ticket |
| 3 | `agentic-clarify` | `[KI] agentic-factory klärung runde=1 key=PROJ-123` |
| 4 | Optional: `agentic-clarify` with `{"key":"APPLY","value":"1"}`, after a proposal | `PROJ-123: description set`. It likely stops, because the lab role can't edit (untested) |

A green pipeline doesn't mean "ready". The steps exit 0 unless they hit an error. Read the agent line: `exit code 0` means ready, 4 not ready, 5 questions or waiting for answers (internal).

### 9. Create the Automation Rule

The rule starts the next `clarify` round when someone answers with `[Mensch]`. Round 1 is a hand start (step 8). The starter adds `<opt-in-label>` first.

| Setting | Value |
|---|---|
| Trigger | Comment added. "Editing a comment will not trigger this flow." (S-7533) |
| Action | "Send web request", `POST https://api.bitbucket.org/2.0/repositories/<workspace>/<repo>/pipelines` (lab) |
| Headers | Hidden `Authorization: Bearer <trigger-token>`, normal `Content-Type: application/json` (lab) |
| Body | `{"target": {"type": "pipeline_ref_target", "ref_type": "branch", "ref_name": "<start-branch>", "selector": {"type": "custom", "pattern": "agentic-clarify"}}, "variables": [{"key": "JIRA_KEY", "value": "{{issue.key}}"}]}`. Never `APPLY` |
| Scope and actor | This project only, "Automation for Jira" (lab) |
| Trigger and edit | "Only user actions can trigger this flow", "Private" (lab) |
| Response | Wait for the response, stop on an error response. Email the first responder on errors (lab) |

Conditions (untested; no record gives the syntax):

1. The comment starts with `[Mensch]`. The sketch: `{{comment.body.trim().startsWith("[Mensch]")}}` equals `true` (internal).
2. The ticket has `<opt-in-label>`.
3. The comment's author is in a named group or project role.
4. The comment's author is not `<bot-email>`.

Treat everyone who can edit the rule as holding the trigger token (untested).

Validate with "Validate your web request configuration" on a ticket that has a `[KI]` round and no newer `[Mensch]` answer. That starts a real run (lab), which ends with `waiting for answers` and no Copilot call (internal). Create each rule fresh, without copying. After any edit, re-enter the hidden header (lab).

**Loop test.** Answer the round once with `[Mensch] …`. Confirm that exactly one run starts. If more start, the first responder alerts the Jira admin, who turns the rule off. A loop, repeated `[Mensch]` comments, or unwanted rounds start unwanted runs, post unwanted comments, and send ticket text to Copilot. Conditions 2 and 3 limit who can start them.

### 10. Go Live on a Pilot Ticket

1. Turn the rule on for one pilot ticket with `<opt-in-label>`.
2. Check that runs 1 to 3 passed and the loop test passed.
3. Read the rule's audit log after each change. Rules fail silently (lab).
4. Delete `agentic-assess-dryrun` in a pull request.

**Rotation and rollback** (untested):

- **Rotate** the Jira, Copilot and trigger tokens:
  1. Pause the rule, and wait until no run is active or queued.
  2. Put in the new token, and run step 8 run 2 as a smoke test.
  3. Revoke the old token. Then resume the rule.
- **Roll back:**
  1. The Jira admin turns the rule off.
  2. The repository admin revokes the trigger and start tokens and deletes the deployment variables.
  3. The token coordinator has the Jira and Copilot tokens revoked.

## If Something Fails

| Message or symptom | Fix |
|---|---|
| `… not in a folder named factory/` or `… is not the top folder of a git repository` | Put `factory/` at the top of the clone (step 3, internal) |
| `--step agent must not see JIRA_API_TOKEN`, or `--step fetch must not see COPILOT_GITHUB_TOKEN` | Keep each token only in its own deployment (step 6, internal) |
| `the api route needs JIRA_BASE_URL and JIRA_API_TOKEN` | Add the variables to `agentic-jira` and `agentic-post` (internal) |
| `Jira … HTTP 401` | Check `JIRA_EMAIL` and `JIRA_API_TOKEN` (internal) |
| `Jira … HTTP 404` | Check `JIRA_BASE_URL`: use the cloud ID, not the Organization ID (S-7534) |
| `copilot exited with timeout`, or the agent step hit `max-time` | Raise `agent_timeout_s` in `config.json`, and `max-time` with it (internal) |
| Step fails at start: no runner | Fix `runs-on`. "If you don't have any online runners in your repository that match all your labels, the step will fail." (S-7520) |
| "The system scopes provided contains unsupported scopes." (S-7521) | Check the scope spelling. For a first test only, delete the `auth` block. Until 2027-04-30 the step then gets wider scopes (S-7118) |
| Copilot refuses to start | Use a fine-grained PAT, not a classic `ghp_` token (S-7539, S-7540) |
| Start request returns 404, or the rule ran but no pipeline started | Check the token, then the URL. Re-enter the hidden header (lab) |

## Open Gaps

- Secret isolation per deployment is unverified (step 6).
- A forum report says starts with custom variables returned HTTP 400 (S-7113, unverified). Your first API start shows it.
- The records don't say whether a start request can override deployment variables (step 5).
- The records give no path for custom deployment environments, or for limiting them to a branch.
- No Dockerfile exists, and the records don't cover installing Copilot CLI or private-registry access.
- The example runs the script from the working tree. Moving it into the image fails the location check (internal).
- The records don't give the scope that `GET /myself` needs. `APPLY=1` uses it, and also needs edit rights.
- No Cloud record shows POST, a custom body, hidden headers or the condition syntax for "Send web request".
- The records don't say whether the factory's own comments fire the trigger.
- The records don't confirm `read:git:bitbucket`, the `auth` YAML nesting, or the `linux.arm64` label.
