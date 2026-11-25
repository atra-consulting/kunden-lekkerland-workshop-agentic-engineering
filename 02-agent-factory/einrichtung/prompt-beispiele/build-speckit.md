# Bauen mit Spec Kit

Ticket [FLAB-41](../../../01-erstworkshop/tag-2/demo-durchlauf.md), Ausgabe von `local.py --print-only` (heute `agentic-factory.py`). Die Flags erklärt die [README](README.md#die-parameter-für-copilot). Die rohe Ausgabe: [`roh/build-speckit.txt`](roh/build-speckit.txt).

```text
[local] FLAB-41: mode build, framework speckit (from --framework), project <projekt>
[local] building change 001-blog-reading-time (7 spec files)
# 1 copilot call(s), build, speckit, run in <projekt>
# environment: COPILOT_AUTO_UPDATE=false SPECKIT_COPILOT_ALLOW_ALL_TOOLS=0 DO_NOT_TRACK=1 OPENSPEC_TELEMETRY=0 SPECIFY_FEATURE_DIRECTORY=specs/001-blog-reading-time
```

Gebaut wird eine echte Spec Kit-Spec aus dem Lab: `specs/001-blog-reading-time/` vom Branch `factory/FLAB-18`, ebenfalls zur Lesezeit.

## Aufruf 1 von 1

- Erlaubte Werkzeuge: `read`, `write`, `shell(mkdir:*)`, `shell(.specify/scripts/bash/check-prerequisites.sh:*)`, `shell(.specify/scripts/bash/resolve-template.sh:*)`, `shell(./bin/phpunit:*)`
- Credit-Grenze: 150

Prompt:

```text
/speckit-implement

Factory rules: Implement exactly the approved spec. Edit files with your file tools, not with shell scripts. Run the tests with exactly: ./bin/phpunit. Don't change the spec except for checking off tasks.
```
