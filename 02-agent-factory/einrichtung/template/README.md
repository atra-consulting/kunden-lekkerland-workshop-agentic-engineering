# Vorlage: die Factory-Schritte lokal mit `local.py`

Diese vier Dateien braucht ihr, um die Copilot-Aufrufe der Factory im eigenen Projekt zu starten: Bereitschaft prüfen, Spec schreiben, bauen. Die Anleitung: [Übung 1](../../../01-erstworkshop/tag-2/uebung-factory-lokal.md) und [Factory-Schritte lokal ausführen](../../bedienung/lokal-ausfuehren.md).

- **Quelle:** Lab-Repo [factory-lab](https://bitbucket.org/factory-lab/factory-lab/src/factory-base/factory/), Branch `factory-base`, Commit `a414237`, Ordner `factory/`. Die Dateien sind unverändert kopiert.
- **Stand:** 24. November 2026, Copilot CLI 1.0.114, Modell `claude-sonnet-5.5`.

| Datei | Wozu | Nötig? |
|---|---|---|
| [`local.py`](local.py) | Das Programm. Nur Python-Standardbibliothek, importiert keine anderen Dateien der Factory | Ja |
| [`config.json`](config.json) | Prompts, Werkzeug-Freigaben, verbotene Befehle, Modell und Credit-Grenzen, für OpenSpec, Spec Kit und BMad. Dieselbe Datei nutzt die Pipeline | Ja |
| [`readiness.md`](readiness.md) | Die Kriterien der Bereitschaftsprüfung | Für `assess` und für `spec` mit Bereitschaftsprüfung |
| [`local.example.json`](local.example.json) | Vorlage für `local.json`: euer Testbefehl, Stack-Satz für Spec Kit, Modell, Copilot-Befehl | Nein. Ohne `local.json` gelten die Werte aus `config.json`, auch der Testbefehl `./bin/phpunit` |

## So nutzt ihr sie

Im Wurzelordner eures Repos:

```bash
mkdir -p factory
cp <dieser Ordner>/{local.py,config.json,readiness.md,local.example.json} factory/
cp factory/local.example.json factory/local.json
python3 -I factory/local.py spec --ticket-file ~/factory-tickets/LL-123.json --print-only
```

- `local.py` liest `config.json`, `readiness.md` und `local.json` **neben sich**, nicht im aktuellen Ordner.
- Der Ordner heißt `factory/`, denn dort sucht der Skill [`ticket-schreiben`](../../werkzeuge/ticket-schreiben/README.md) `local.py` und `readiness.md`.
- In `local.json` tragt ihr euren echten Testbefehl ein. Aus `make test` wird die Erlaubnis `shell(make:*)`: Der Agent darf dann **jedes** Make-Ziel starten.
- Jira-Zugangsdaten gehören nie in `local.json`, nur in die Umgebung: `JIRA_BASE_URL`, `JIRA_API_TOKEN` und für Jira Cloud `JIRA_EMAIL`. Ohne Jira nehmt ihr `--ticket-file`.

Was `local.py` mit diesen Dateien an Copilot schickt, zeigen die [Prompt-Beispiele](../prompt-beispiele/README.md).

## Sicherheit: Was ihr wissen müsst

`local.py` hat nicht den Schutz der Pipeline: keinen eigenen Benutzer, keinen Container, keinen Prüfschritt vor dem Commit. Der Agent läuft als ihr.

- **Eure Umgebung:** Copilot bekommt alle eure Umgebungsvariablen, nur die drei Jira-Variablen nicht. Startet `local.py` in einer Shell ohne andere Tokens, etwa für Cloud, Datenbank oder Registry.
- **BMad darf beliebigen Code starten:** `shell(uv:*)` gilt beim Spec schreiben und beim Bauen. Mit `uv` startet der Agent jedes Python-Programm. Beim Bauen darf BMad außerdem selbst committen. OpenSpec und Spec Kit haben keinen solchen Freibrief.
- **Der Agent kann ändern, was er starten darf:** Er darf Dateien schreiben, also auch `./bin/phpunit`, die Skripte unter `.specify/` oder euer `Makefile`, und sie danach starten. Ein Ticket-Text, der ihn dazu bringt, führt so eigenen Code aus. `local.py` warnt erst nach dem Lauf, mit `WARNING: protected paths changed`, wenn sich `bin/` oder `.specify/` geändert haben. Ein geändertes `Makefile` meldet es nicht.
- **Euer Testbefehl wird zur Erlaubnis:** Aus `make test` wird `shell(make:*)`, also jedes Make-Ziel. Über Make kann der Agent beliebige Befehle ausführen.
- **Die Kontrolle nach dem Lauf sieht nicht alles:** `local.py` vergleicht nur, was `git status` zeigt. Änderungen in `.git/`, etwa ein neuer Hook, und in ignorierten Dateien, etwa `.env`, sieht es nicht. Ein Hook liefe beim nächsten `git commit`.

Was ihr tut:

- Nur Tickets durchschicken, deren Text ihr kennt. Der Text landet im Prompt.
- Vor dem Lauf alles committen, damit der Diff nur die Arbeit des Agenten zeigt.
- Jede `WARNING` von `local.py` ernst nehmen.
- Nach jedem Lauf prüfen:

```bash
git status --ignored
git diff
ls -la .git/hooks
git config --local --list
```

## Was fehlt

- **Die Pipeline-Dateien**, etwa `agent.py`, `check.py` und `publish.py`. Lokal braucht ihr sie nicht.
- **Die Tests** `test_local.py`: Ein Teil vergleicht `local.py` mit `agent.py` und braucht das ganze Lab-Repo. Dort startet ihr sie mit `python3 -I -B -m unittest discover -s factory -p 'test_local.py'`.

## Aktualisieren

Ändert sich `factory-base` im Lab-Repo, kopiert ihr die vier Dateien neu:

```bash
git clone --branch factory-base https://bitbucket.org/factory-lab/factory-lab.git /tmp/factory-lab
cp /tmp/factory-lab/factory/{local.py,config.json,readiness.md,local.example.json} 02-agent-factory/einrichtung/template/
```

Danach den Commit oben unter „Quelle“ anpassen.
