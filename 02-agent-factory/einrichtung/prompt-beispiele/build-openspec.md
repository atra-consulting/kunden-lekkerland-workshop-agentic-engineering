# Bauen mit OpenSpec

Ticket [FLAB-41](../../../01-erstworkshop/tag-2/demo-durchlauf.md), Ausgabe von `agentic-factory.py --print-only`. Die Flags erklärt die [README](README.md#die-parameter-für-copilot). Die rohe Ausgabe: [`roh/build-openspec.txt`](roh/build-openspec.txt).

```text
[agentic-factory] Jira route: offline (offline input)
[agentic-factory] FLAB-41: mode build, framework openspec (from --framework), project <projekt>
[agentic-factory] building change post-reading-time (4 spec files)
# 1 copilot call(s), build, openspec, run in <projekt>
# environment: COPILOT_AUTO_UPDATE=false SPECKIT_COPILOT_ALLOW_ALL_TOOLS=0 DO_NOT_TRACK=1 OPENSPEC_TELEMETRY=0
```

Gebaut wird ein Platzhalter: `openspec/changes/post-reading-time/` mit vier Dateien. Den Namen hat der Factory-Lauf zu FLAB-41 vergeben, auf dem Branch `factory/FLAB-41`. Der Prompt nennt nur den Namen, den Inhalt liest erst der Agent.

## Aufruf 1 von 1

- Erlaubte Werkzeuge: `read`, `write`, `shell(openspec:*)`, `shell(mkdir:*)`, `shell(ls:*)`, `shell(cat:*)`, `shell(head:*)`, `shell(tail:*)`, `shell(wc:*)`, `shell(grep:*)`, `shell(pwd:*)`, `shell(diff:*)`, `shell(stat:*)`, `shell(cd:*)`, `shell(./bin/phpunit:*)`
- Credit-Grenze: 150

Prompt:

```text
/openspec-apply-change post-reading-time

Factory rules: Implement exactly the approved spec. Edit files with your file tools, not with shell scripts. Run the tests with exactly: ./bin/phpunit. Don't change the spec except for checking off tasks. Follow AGENTS.md in the repository root, if it exists, and the files it links to; where they conflict with these factory rules, these rules win.
```
