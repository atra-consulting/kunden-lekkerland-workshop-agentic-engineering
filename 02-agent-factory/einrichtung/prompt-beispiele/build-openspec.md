# Bauen mit OpenSpec

Ticket [FLAB-41](../../../01-erstworkshop/tag-2/demo-durchlauf.md), Ausgabe von `local.py --print-only` (heute `agentic-factory.py`). Die Flags erklärt die [README](README.md#die-parameter-für-copilot). Die rohe Ausgabe: [`roh/build-openspec.txt`](roh/build-openspec.txt).

```text
[local] FLAB-41: mode build, framework openspec (from --framework), project <projekt>
[local] building change post-reading-time (5 spec files)
# 1 copilot call(s), build, openspec, run in <projekt>
# environment: COPILOT_AUTO_UPDATE=false SPECKIT_COPILOT_ALLOW_ALL_TOOLS=0 DO_NOT_TRACK=1 OPENSPEC_TELEMETRY=0
```

Gebaut wird die echte Spec aus dem Factory-Lauf zu FLAB-41: `openspec/changes/post-reading-time/` vom Branch `factory/FLAB-41`.

## Aufruf 1 von 1

- Erlaubte Werkzeuge: `read`, `write`, `shell(openspec:*)`, `shell(mkdir:*)`, `shell(./bin/phpunit:*)`
- Credit-Grenze: 150

Prompt:

```text
/openspec-apply-change post-reading-time

Factory rules: Implement exactly the approved spec. Edit files with your file tools, not with shell scripts. Run the tests with exactly: ./bin/phpunit. Don't change the spec except for checking off tasks.
```
