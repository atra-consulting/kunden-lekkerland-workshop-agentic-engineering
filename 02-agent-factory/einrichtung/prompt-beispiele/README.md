# Prompt-Beispiele: die Copilot-Aufrufe der Factory

Diese Seiten zeigen jeden Copilot-Aufruf der Factory für ein echtes Ticket aus dem Lab, [FLAB-41](../../../01-erstworkshop/tag-2/demo-durchlauf.md): Bereitschaft prüfen, Spec schreiben, bauen, mit OpenSpec, Spec Kit und BMad. Sie sind die Vorlage für den Agent-Schritt in Bitbucket Pipelines.

- **Quelle:** die Ausgabe von `local.py --print-only`. Dieselben Prompts, Flags und dieselbe Reihenfolge nutzt `factory/agent.py` in der Pipeline. Ein Test im Lab-Repo prüft, dass beide dieselben Befehle bauen.
- **Stand:** 24. November 2026, Lab-Repo Branch `factory-base`, Commit `a414237`, Modell `claude-sonnet-5.5`.
- **Kosten:** `--print-only` startet nichts und kostet nichts.

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

FLAB-41 hat das Label `sdd-openspec`. Für Spec Kit und BMad haben wir das Framework mit `--framework` gewählt. `local.py` liest das Ticket als JSON, eine Zeile je Absatz. Die Datei: [`ticket-FLAB-41.json`](ticket-FLAB-41.json).

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

Die rohe Ausgabe jedes Laufs liegt in [`roh/`](roh/), genau so, wie `local.py` sie druckt. Nur lokale Pfade sind ersetzt (siehe unten).

## So sind die Prompts gebaut

- **Bereitschaftsprüfung:** Der Prompt enthält das Ticket und die Kriterien aus `factory/readiness.md`, zwischen `<<<CRITERIA` und `CRITERIA>>>`. Der Agent darf nur lesen und eine Datei schreiben, `FACTORY-ASSESSMENT.json`. Bei `spec` ist sie immer Aufruf 1. Lautet das Urteil „nicht bereit“, startet kein weiterer Aufruf.
- **Spec:** Der erste Aufruf des Frameworks startet dessen Skill als Slash-Befehl und bekommt das Ticket zwischen `<<<TICKET` und `TICKET>>>`, ausdrücklich als Daten, nicht als Anweisung. Die folgenden Aufrufe, etwa `/speckit-plan` oder `/bmad-spec`, bekommen das Ticket nicht noch einmal. Sie arbeiten mit den Dateien, die der Aufruf davor geschrieben hat.
- **Factory rules:** Jeder Prompt endet mit Regeln aus `config.json` (`spec_rules`, `build_rules`): in welchen Ordner der Agent schreiben darf, keine Shell-Skripte zum Bearbeiten, bei Unklarheit `FACTORY-QUESTIONS.md` statt einer Spec. Beim Bauen: genau die freigegebene Spec umsetzen, Tests mit genau `./bin/phpunit`.
- **Bauen:** Der Prompt enthält keinen Ticket-Text und keinen Spec-Text. Er nennt nur den Spec-Ordner oder die Spec-Datei, BMad dazu den Schlüssel des Tickets. Den Inhalt liest der Agent selbst im Repo.
- **Spec Kit:** Der Plan-Prompt enthält den Satz „Use the existing Symfony 7 / PHP stack and PHPUnit“. In eurem Projekt ersetzt ihr ihn über `stack_hint` in `local.json`.

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
| Spec | `shell(openspec:*)`, `shell(mkdir:*)` | `shell(mkdir:*)` und die Skripte `create-new-feature.sh`, `setup-plan.sh`, `setup-tasks.sh`, `check-prerequisites.sh`, `resolve-template.sh` unter `.specify/scripts/bash/` | `shell(uv:*)`, `shell(mkdir:*)` |
| Bauen | `shell(openspec:*)`, `shell(mkdir:*)`, `shell(./bin/phpunit:*)` | `shell(mkdir:*)`, `check-prerequisites.sh`, `resolve-template.sh`, `shell(./bin/phpunit:*)` | `shell(uv:*)`, `shell(mkdir:*)`, `shell(git add:*)`, `shell(git commit:*)`, `shell(git status:*)`, `shell(git diff:*)`, `shell(./bin/phpunit:*)` |

- `shell(./bin/phpunit:*)` ist der Testbefehl aus `config.json`. Lokal ersetzt `test_command` aus `local.json` ihn, etwa durch `shell(make:*)`.
- `shell(uv:*)` erlaubt BMad, beliebigen Python-Code zu starten. BMad darf beim Bauen auch selbst committen.

### Verbotene Befehle

In allen 13 Aufrufen gleich:

`shell(git push:*)`, `shell(git remote:*)`, `shell(git config:*)`, `shell(curl:*)`, `shell(wget:*)`, `shell(ssh:*)`, `shell(scp:*)`, `shell(env:*)`, `shell(printenv:*)`, `shell(composer:*)`, `shell(npm:*)`, `shell(npx:*)`

### Umgebungsvariablen

Die Pipeline setzt sie vor jedem Aufruf:

- `COPILOT_AUTO_UPDATE=false`, `SPECKIT_COPILOT_ALLOW_ALL_TOOLS=0`, `DO_NOT_TRACK=1`, `OPENSPEC_TELEMETRY=0`.
- Beim Bauen mit Spec Kit zusätzlich `SPECIFY_FEATURE_DIRECTORY=specs/<Spec-Ordner>`.
- Dazu kommt in der Pipeline das Copilot-Token als `COPILOT_GITHUB_TOKEN`. `--print-only` zeigt es nicht.

**Nur lokal:** Startet `local.py` die Aufrufe selbst, hängt es für jeden MCP-Server aus `copilot mcp list` noch `--disable-mcp-server=<Name>` an. In der Pipeline ist kein MCP-Server eingerichtet.

## So sind die Beispiele entstanden

In einem frischen Klon des Lab-Repos, Branch `factory-base`, mit Python 3.13 und Copilot CLI 1.0.114:

```bash
git clone --branch factory-base https://bitbucket.org/factory-lab/factory-lab.git projekt
cd projekt
python3 -I factory/local.py assess --ticket-file ../FLAB-41.json --print-only
python3 -I factory/local.py spec   --ticket-file ../FLAB-41.json --framework openspec --print-only   # ebenso speckit, bmad
python3 -I factory/local.py build  --ticket-file ../FLAB-41.json --framework openspec --change post-reading-time --print-only
python3 -I factory/local.py build  --ticket-file ../FLAB-41.json --framework speckit --print-only
python3 -I factory/local.py build  --ticket-file ../FLAB-41.json --framework bmad --print-only
```

- **Keine `local.json`.** Prompts und Flags sind also genau die der Pipeline: Testbefehl `./bin/phpunit`, Stack-Satz für Symfony. Mit einer `local.json` ändern sich nur `test_command`, `stack_hint`, `model` und der Befehl, der Copilot startet.
- **Spec-Ordner für das Bauen.** `build` braucht einen Spec-Ordner. Der Prompt nennt aber nur dessen Namen. Wir haben genommen:
  - OpenSpec: die echte Spec aus dem Factory-Lauf zu FLAB-41, `openspec/changes/post-reading-time/` vom Branch `factory/FLAB-41`.
  - Spec Kit: eine echte Spec aus dem Lab, ebenfalls zur Lesezeit, `specs/001-blog-reading-time/` vom Branch `factory/FLAB-18`.
  - BMad: einen Platzhalter, `_bmad-output/specs/lesezeit-artikelseite/SPEC.md`. Das Lab hat keine BMad-Spec zur Lesezeit.
- **Ersetzte Pfade.** In den Dateien steht `<projekt>` für den Projektordner und `~/.factory-local/<projekt>/<zeit>-…` für die Protokoll-Dateien.

Neu erzeugen: dieselben Befehle mit eurer `config.json` und `readiness.md`. Ändert ihr Kriterien oder Regeln, ändern sich die Prompts mit.
