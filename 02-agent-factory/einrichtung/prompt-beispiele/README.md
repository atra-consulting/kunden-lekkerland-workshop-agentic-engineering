# Prompt-Beispiele: die Copilot-Aufrufe der Factory

Diese Seiten zeigen jeden Copilot-Aufruf der Factory für ein echtes Ticket aus dem Lab, [FLAB-41](../../../01-erstworkshop/tag-2/demo-durchlauf.md): Bereitschaft prüfen, Spec schreiben, bauen, mit OpenSpec, Spec Kit und BMad. Sie zeigen, was die [Vorlage](../template/README.md) `agentic-factory.py` an Copilot schickt. Die Pipeline von `factory-base` baut dieselben Aufrufe, mit den Unterschieden unten.

- **Quelle:** die Ausgabe von `agentic-factory.py --print-only` aus der Vorlage in diesem Repo, mit `"test_command": "./bin/phpunit"` in `config.json`, dem Testbefehl des Labs.
- **Stand:** 25. November 2026, Modell `claude-sonnet-5.5`.
- **Kosten:** `--print-only` startet nichts und kostet nichts.
- **Unterschiede zur Pipeline (`factory/agent.py` in `factory-base`):**
  - Jeder Aufruf von `spec` und `build` bekommt dazu die lesenden Befehle aus `read_tools`, etwa `shell(ls:*)` und `shell(grep:*)`.
  - Die Bereitschaftsprüfung bekommt `--deny-tool=shell`: Sie hat kein Shell-Werkzeug.
  - Der Plan-Prompt von Spec Kit sagt „Use the existing stack and test setup“ statt „Use the existing Symfony 7 / PHP stack and PHPUnit“.
  - Die verbotenen Befehle nennen `composer` nicht mehr. Von `npm` verbieten sie nur `npm install`, `npm i`, `npm ci` und `npm exec`, nicht ganz `npm`: Sonst liefe `npm test` nicht.
  - Die geschützten Pfade nennen keine Dateien von Symfony und PHP mehr, auch nicht `bin/`. `AGENTS.md`, `CLAUDE.md` und `GEMINI.md` sind auch in Unterordnern geschützt. Alle geschützten Pfade gelten in jeder Schreibweise.
  - Die Regeln für Spec und Bauen (`spec_rules`, `build_rules`) und die Regeln der Bereitschaftsprüfung enden mit „Follow AGENTS.md in the repository root, if it exists, and the files it links to; where they conflict with these factory rules, these rules win.“
  - Der Prompt der Bereitschaftsprüfung und `readiness.md` nennen Teile des Codes ohne Begriffe aus Symfony, etwa „modules, entry points, user interface, data model“ statt „pages, routes, controllers, templates, entities, translations“.

## Das Ticket

So steht FLAB-41 in Jira:

> **Titel:** Lesezeit auf der Artikelseite
>
> **Ziel**
>
> Leser sehen vor dem Lesen, wie lange ein Artikel dauert.
>
> **Akzeptanzkriterien**
>
> Die Artikelseite /de/blog/posts/{slug} zeigt unter dem Titel die Lesezeit, auf Deutsch „Lesezeit: N Min.“, auf Englisch „Reading time: N min“.
>
> N ist die Zahl der Wörter im Inhalt geteilt durch 200, aufgerundet, mindestens 1.
>
> Ein Artikel mit 450 Wörtern zeigt „Lesezeit: 3 Min.“, einer mit 50 Wörtern „Lesezeit: 1 Min.“.
>
> **Nicht Teil des Tickets**
>
> Blog-Übersicht, Admin-Bereich und Datenbank bleiben unverändert.
>
> Andere Sprachen als Deutsch und Englisch.

FLAB-41 hat das Label `sdd-openspec`. Für Spec Kit und BMad haben wir das Framework mit `--framework` gewählt. `agentic-factory.py` liest das Ticket als JSON, eine Zeile je Absatz. Die Datei: [`ticket-FLAB-41.json`](ticket-FLAB-41.json).

```json
{
  "key": "FLAB-41",
  "summary": "Lesezeit auf der Artikelseite",
  "description": "Ziel\nLeser sehen vor dem Lesen, wie lange ein Artikel dauert.\nAkzeptanzkriterien\nDie Artikelseite /de/blog/posts/{slug} zeigt unter dem Titel die Lesezeit, auf Deutsch „Lesezeit: N Min.“, auf Englisch „Reading time: N min“.\nN ist die Zahl der Wörter im Inhalt geteilt durch 200, aufgerundet, mindestens 1.\nEin Artikel mit 450 Wörtern zeigt „Lesezeit: 3 Min.“, einer mit 50 Wörtern „Lesezeit: 1 Min.“.\nNicht Teil des Tickets\nBlog-Übersicht, Admin-Bereich und Datenbank bleiben unverändert.\nAndere Sprachen als Deutsch und Englisch.",
  "labels": ["sdd-openspec"]
}
```

## Übersicht

| Schritt | OpenSpec | Spec Kit | BMad |
|---|---|---|---|
| Bereitschaft prüfen | [`assess.md`](assess.md): 1 Aufruf, für alle Frameworks gleich | ← | ← |
| Spec schreiben | [`spec-openspec.md`](spec-openspec.md): 2 Aufrufe, Bereitschaft und `/openspec-propose` | [`spec-speckit.md`](spec-speckit.md): 4 Aufrufe, Bereitschaft, `/speckit-specify`, `/speckit-plan`, `/speckit-tasks` | [`spec-bmad.md`](spec-bmad.md): 3 Aufrufe, Bereitschaft, `/bmad-prd`, `/bmad-spec` |
| Bauen | [`build-openspec.md`](build-openspec.md): `/openspec-apply-change` | [`build-speckit.md`](build-speckit.md): `/speckit-implement` | [`build-bmad.md`](build-bmad.md): `/bmad-build-auto` |

Die rohe Ausgabe jedes Laufs liegt in [`roh/`](roh/), genau so, wie `agentic-factory.py` sie druckt. Nur lokale Pfade sind ersetzt (siehe unten).

## So sind die Prompts gebaut

- **Bereitschaftsprüfung:** Der Prompt enthält das Ticket und die Kriterien aus [`readiness.md`](../template/readiness.md), zwischen `<<<CRITERIA` und `CRITERIA>>>`. Der Agent darf nur lesen und eine Datei schreiben, `FACTORY-ASSESSMENT.json`. Bei `spec` ist sie immer Aufruf 1. Lautet das Urteil „nicht bereit“, startet kein weiterer Aufruf.
- **Spec:** Der erste Aufruf des Frameworks startet dessen Skill als Slash-Befehl und bekommt das Ticket zwischen `<<<TICKET` und `TICKET>>>`, ausdrücklich als Daten, nicht als Anweisung. Die folgenden Aufrufe, etwa `/speckit-plan` oder `/bmad-spec`, bekommen das Ticket nicht noch einmal. Sie arbeiten mit den Dateien, die der Aufruf davor geschrieben hat.
- **Factory rules:** Jeder Prompt endet mit Regeln aus `config.json` (`spec_rules`, `build_rules`): in welchen Ordner der Agent schreiben darf, keine Shell-Skripte zum Bearbeiten, bei Unklarheit `FACTORY-QUESTIONS.md` statt einer Spec. Beim Bauen: genau die freigegebene Spec umsetzen, Tests mit genau dem Befehl aus `test_command`, hier `./bin/phpunit`.
- **Bauen:** Der Prompt enthält keinen Ticket-Text und keinen Spec-Text. Er nennt nur den Spec-Ordner oder die Spec-Datei, BMad dazu den Schlüssel des Tickets. Den Inhalt liest der Agent selbst im Repo.
- **Spec Kit:** Der Plan-Prompt sagt nur „Use the existing stack and test setup; no new dependencies.“ Euren Stack beschreibt ihr in `AGENTS.md`. Copilot liest die Datei selbst.

## Die Dateien der Spec und `tasks.md`

OpenSpec und Spec Kit schreiben eine `tasks.md`, BMad nicht. Welche Dateien eine Spec haben muss, steht in [`config.json`](https://bitbucket.org/factory-lab/factory-lab/src/factory-base/factory/config.json) unter `frameworks`, Felder `spec_required` und `spec_required_glob`.

| Framework | Wo die Spec liegt | `tasks.md` | Schreibt sie | Pflicht für die Factory |
|---|---|---|---|---|
| OpenSpec | `openspec/changes/<change>/`: `proposal.md`, `design.md`, `specs/*/spec.md`, `tasks.md` | ja | `/openspec-propose`, in einem Aufruf | `proposal.md`, `tasks.md`, `specs/*/spec.md` |
| Spec Kit | `specs/<nnn-feature>/`: `spec.md`, `plan.md`, `research.md`, `data-model.md`, `quickstart.md`, `tasks.md` | ja | `/speckit-tasks`, der dritte der drei Spec-Aufrufe | `spec.md`, `plan.md`, `tasks.md` |
| BMad | PRD in `_bmad-output/planning-artifacts/prds/<name>/prd.md`, Spec in `_bmad-output/specs/<slug>/SPEC.md` | nein | `/bmad-prd`, dann `/bmad-spec` | `prd.md`, `SPEC.md` |

Beispiele aus dem Lab: `openspec/changes/post-reading-time/tasks.md` auf dem Branch `factory/FLAB-41`, `specs/001-blog-reading-time/tasks.md` auf dem Branch `factory/FLAB-18`.

**In der Pipeline ist beim Bauen `tasks.md` die einzige Datei der Spec, die der Agent ändern darf** (Feld `run2_editable_re` in der `config.json` von `factory-base`). So hakt er die erledigten Aufgaben ab. Alles andere an der freigegebenen Spec bleibt, wie es ist. Bei BMad darf der Agent stattdessen in `_bmad-output/implementation-artifacts/` schreiben und die `.memlog.md`-Dateien ändern. Die Vorlage kennt das Feld nicht: Lokal prüft das niemand, ihr lest den Diff selbst.

## Die Parameter für Copilot

Jeder Aufruf hat diese Form, gekürzt:

```bash
copilot -p '<Prompt>' --no-ask-user --model claude-sonnet-5.5 --output-format json --no-auto-update \
  --disallow-temp-dir --disable-builtin-mcps --max-ai-credits 150 --secret-env-vars=COPILOT_GITHUB_TOKEN \
  --usage-output-file=<Datei> --allow-tool=read --allow-tool=write '--allow-tool=shell(openspec:*)' … \
  '--deny-tool=shell(git push:*)' …
```

| Flag | Wirkung |
|---|---|
| `-p '<Prompt>'` | Ein Aufruf ohne Dialog. Der Prompt startet meist den Skill des Frameworks, etwa `/openspec-propose` |
| `--no-ask-user` | Copilot fragt nie zurück. Was nicht freigegeben ist, lehnt er ab |
| `--model claude-sonnet-5.5` | Modell aus `config.json`. Lokal kann `model` in `local.json` es ersetzen |
| `--output-format json` | Ereignisse als JSON-Zeilen. Daraus liest die Factory die Werkzeug-Aufrufe und die letzte Antwort |
| `--no-auto-update` | Kein Update während des Laufs |
| `--disallow-temp-dir` | Das Temp-Verzeichnis ist nicht automatisch freigegeben |
| `--disable-builtin-mcps` | Keine eingebauten MCP-Server, etwa der von GitHub |
| `--max-ai-credits` | Obergrenze je Aufruf: 40 bei der Bereitschaftsprüfung, 150 bei den Aufrufen des Frameworks |
| `--secret-env-vars=COPILOT_GITHUB_TOKEN` | Copilot schwärzt diesen Wert in seinen Ausgaben |
| `--usage-output-file=…` | Verbrauch des Aufrufs. Daraus liest die Factory die Credits |
| `--allow-tool=…` | Erlaubte Werkzeuge, je Schritt und Framework verschieden (Tabelle unten) |
| `--deny-tool=…` | Verbotene Befehle, in allen Aufrufen gleich (Liste unten) |

### Erlaubte Werkzeuge

Alle Aufrufe dürfen `read` und `write`. Dazu:

| Schritt | OpenSpec | Spec Kit | BMad |
|---|---|---|---|
| Bereitschaft | nichts | nichts | nichts |
| Spec | `shell(openspec:*)`, `shell(mkdir:*)`, die `read_tools` | `shell(mkdir:*)` und die Skripte `create-new-feature.sh`, `setup-plan.sh`, `setup-tasks.sh`, `check-prerequisites.sh`, `resolve-template.sh` unter `.specify/scripts/bash/`, die `read_tools` | `shell(uv:*)`, `shell(mkdir:*)`, die `read_tools` |
| Bauen | `shell(openspec:*)`, `shell(mkdir:*)`, die `read_tools`, `shell(./bin/phpunit:*)` | `shell(mkdir:*)`, `check-prerequisites.sh`, `resolve-template.sh`, die `read_tools`, `shell(./bin/phpunit:*)` | `shell(uv:*)`, `shell(mkdir:*)`, `shell(git add:*)`, `shell(git commit:*)`, `shell(git status:*)`, `shell(git diff:*)`, die `read_tools`, `shell(./bin/phpunit:*)` |

- Die `read_tools` aus `config.json`: `shell(ls:*)`, `shell(cat:*)`, `shell(head:*)`, `shell(tail:*)`, `shell(wc:*)`, `shell(grep:*)`, `shell(pwd:*)`, `shell(diff:*)`, `shell(stat:*)`, `shell(cd:*)`. Warum genau diese, steht in der [Vorlage](../template/README.md#sicherheit-was-ihr-wissen-müsst).
- `shell(./bin/phpunit:*)` ist der Testbefehl aus `test_command` in `config.json`, als ganzer Befehl. Aus `make test` würde `shell(make test:*)`. In der Vorlage ist `test_command` leer: Dann stoppt `build`.
- `shell(uv:*)` erlaubt BMad, beliebigen Python-Code zu starten. BMad darf beim Bauen auch selbst committen.

### Verbotene Befehle

In allen 13 Aufrufen gleich:

`shell(git push:*)`, `shell(git remote:*)`, `shell(git config:*)`, `shell(curl:*)`, `shell(wget:*)`, `shell(ssh:*)`, `shell(scp:*)`, `shell(env:*)`, `shell(printenv:*)`, `shell(npm install:*)`, `shell(npm i:*)`, `shell(npm ci:*)`, `shell(npm exec:*)`, `shell(npx:*)`

Die vier Bereitschaftsprüfungen bekommen dazu `--deny-tool=shell`. Die Pipeline von `factory-base` verbietet stattdessen `shell(composer:*)` und ganz `shell(npm:*)`.

### Umgebungsvariablen

Die Pipeline setzt sie vor jedem Aufruf:

- `COPILOT_AUTO_UPDATE=false`, `SPECKIT_COPILOT_ALLOW_ALL_TOOLS=0`, `DO_NOT_TRACK=1`, `OPENSPEC_TELEMETRY=0`.
- Beim Bauen mit Spec Kit zusätzlich `SPECIFY_FEATURE_DIRECTORY=specs/<Spec-Ordner>`.
- Dazu kommt in der Pipeline das Copilot-Token als `COPILOT_GITHUB_TOKEN`. `--print-only` zeigt es nicht.

**Nur lokal:** Startet `agentic-factory.py` die Aufrufe selbst, hängt es für jeden MCP-Server aus `copilot mcp list` noch `--disable-mcp-server=<Name>` an. In der Pipeline ist kein MCP-Server eingerichtet.

## Wo der Branch entsteht

Copilot legt in Bitbucket keinen Branch an. Das macht erst der letzte Schritt der Pipeline, **publish**: `factory/publish.py` pusht mit dem Token des Bots. Nur dieser Schritt darf nach Bitbucket schreiben.

| Wo | Was passiert |
|---|---|
| [`bitbucket-pipelines.yml`](https://bitbucket.org/factory-lab/factory-lab/src/factory-base/bitbucket-pipelines.yml) | Schritt „4 publish (Jira and Bitbucket write)“ startet `publish.py spec` in der Pipeline `factory-spec`. Schritt „5 publish“ startet `publish.py build` in `factory-build` |
| [`publish.py`](https://bitbucket.org/factory-lab/factory-lab/src/factory-base/factory/publish.py), `spec()` | Prüft den Patch des Agenten und committet die Spec. Beim ersten Lauf gibt es den Branch noch nicht, also **legt dieser Push `factory/<KEY>` an** |
| `publish.py`, `commit_and_push()` | Committet als `factory-bot` und pusht `HEAD:refs/heads/factory/<KEY>`. Ab dem zweiten Lauf mit `--force-with-lease`: Der Push überschreibt den Branch nur, wenn ihn niemand sonst verändert hat |
| [`common.py`](https://bitbucket.org/factory-lab/factory-lab/src/factory-base/factory/common.py), `branch_name()` | Der Name: `branch_prefix` aus `config.json` (`"factory/"`) plus Schlüssel des Tickets |
| `publish.py`, `build()` | Der zweite Lauf hängt den Commit mit dem Code an **denselben** Branch und öffnet den Pull Request von `factory/<KEY>` nach `factory-base` |

- **Basis und Commits:** Der Branch beginnt bei dem Commit, auf dem der Lauf startete, also dem Stand von `factory-base`. Bei FLAB-41 sind das `a414237`, dann „FLAB-41: spec (openspec, factory run 97)“ und „FLAB-41: implementation (openspec, factory run 98)“.
- **Der Branch des Agenten bleibt lokal:** `agent.py` gibt dem Agenten ein Wegwerf-Repository mit `git init -b factory/<KEY>`. Das braucht BMad, um committen zu können. Es wird nie gepusht. Die Factory übernimmt nur die geänderten Dateien des Agenten als Patch, `publish.py` committet und pusht sie.
- **Der Push startet nichts:** Die Pipeline hat nur Custom-Pipelines. Ein Push auf `factory/*` startet also keinen Lauf.
- **Die anderen Schritte lesen den Branch nur:** Guard, Agent und Prüfung holen ihn als Daten nach `refs/factory/<KEY>`, ohne ihn auszuchecken.

## So sind die Beispiele entstanden

Erzeugt mit der Vorlage aus diesem Repo, Stand 25. November 2026, mit Python 3 und ohne Copilot-Aufruf: `--print-only` startet Copilot nicht. Wir haben ein Wegwerf-Repo angelegt:

- mit Git und den leeren Ordnern `openspec/`, `.specify/` und `_bmad/`, denn ohne sie stoppt das Skript mit „framework … is not installed in this project“,
- mit der Vorlage in `factory/`, ohne `local.json`, und in `factory/config.json` mit `"test_command": "./bin/phpunit"`,
- mit Platzhaltern für die Spec-Ordner, die `build` braucht. Der Prompt nennt nur deren Namen:
  - OpenSpec: `openspec/changes/post-reading-time/` mit `proposal.md`, `design.md`, `tasks.md` und `specs/blog-post/spec.md`. Den Namen hat der Factory-Lauf zu FLAB-41 vergeben.
  - Spec Kit: `specs/001-blog-reading-time/` mit `spec.md`, `plan.md` und `tasks.md`, benannt nach einer Spec aus dem Lab zu FLAB-18.
  - BMad: `_bmad-output/specs/lesezeit-artikelseite/SPEC.md`. Das Lab hat keine BMad-Spec zur Lesezeit.

Dann im Wurzelordner des Wegwerf-Repos:

```bash
T=~/workshop-agentic-engineering/02-agent-factory/einrichtung/prompt-beispiele/ticket-FLAB-41.json   # Pfad zu eurem Klon dieses Repos
python3 -I factory/agentic-factory.py assess --ticket-file "$T" --print-only
python3 -I factory/agentic-factory.py spec   --ticket-file "$T" --framework openspec --print-only   # ebenso speckit, bmad
python3 -I factory/agentic-factory.py build  --ticket-file "$T" --framework openspec --change post-reading-time --print-only
python3 -I factory/agentic-factory.py build  --ticket-file "$T" --framework speckit --print-only
python3 -I factory/agentic-factory.py build  --ticket-file "$T" --framework bmad --print-only
```

- **Keine `local.json`.** Mit einer `local.json` ändern sich nur `model` und der Befehl, der Copilot startet.
- **Rohe Ausgabe und Seiten.** Die Dateien in [`roh/`](roh/) sind die Ausgabe der Befehle. Die Seiten haben wir daraus gebaut: Kopfzeilen, Werkzeuge, Credit-Grenze und Prompt je Aufruf.
- **Ersetzte Pfade.** In den Dateien steht `<projekt>` für den Projektordner und `~/.factory-local/<projekt>/<zeit>-…` für die Protokoll-Dateien.

Neu erzeugen: dieselben Befehle mit eurer `config.json` und `readiness.md`. Ändert ihr Kriterien, Werkzeuge oder den Testbefehl, ändern sich die Prompts mit.
