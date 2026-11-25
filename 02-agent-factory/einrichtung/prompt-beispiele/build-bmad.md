# Bauen mit BMad

Ticket [FLAB-41](../../../01-erstworkshop/tag-2/demo-durchlauf.md), Ausgabe von `local.py --print-only` (heute `agentic-factory.py`). Die Flags erklärt die [README](README.md#die-parameter-für-copilot). Die rohe Ausgabe: [`roh/build-bmad.txt`](roh/build-bmad.txt).

```text
[local] FLAB-41: mode build, framework bmad (from --framework), project <projekt>
[local] building change lesezeit-artikelseite (1 spec files)
# 1 copilot call(s), build, bmad, run in <projekt>
# environment: COPILOT_AUTO_UPDATE=false SPECKIT_COPILOT_ALLOW_ALL_TOOLS=0 DO_NOT_TRACK=1 OPENSPEC_TELEMETRY=0
```

Gebaut wird ein Platzhalter: `_bmad-output/specs/lesezeit-artikelseite/SPEC.md`. Das Lab hat keine BMad-Spec zur Lesezeit. Der Prompt nennt nur den Pfad, den Inhalt liest erst der Agent.

## Aufruf 1 von 1

- Erlaubte Werkzeuge: `read`, `write`, `shell(uv:*)`, `shell(mkdir:*)`, `shell(git add:*)`, `shell(git commit:*)`, `shell(git status:*)`, `shell(git diff:*)`, `shell(./bin/phpunit:*)`
- Credit-Grenze: 150

Prompt:

```text
/bmad-build-auto Ticket FLAB-41. The approved spec is _bmad-output/specs/lesezeit-artikelseite/SPEC.md. Follow every step file of the workflow in order, including the spec file, the review subagents, and the final status write-back.

Factory rules: Implement exactly the approved spec. Edit files with your file tools, not with shell scripts. Run the tests with exactly: ./bin/phpunit. Don't change the spec except for checking off tasks.
```
