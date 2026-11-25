# Vorlage: die Factory-Schritte lokal mit `agentic-factory.py`

Mit diesen Dateien startet ihr die Copilot-Aufrufe der Factory im eigenen Projekt. `agentic-factory.py` hieß früher `local.py`. Es kennt vier Modi:

| Modus | Was er tut |
|---|---|
| `assess` | Bereitschaft prüfen |
| `clarify` | Ein Ticket in Runden von Kommentaren klären, bis es bereit ist |
| `spec` | Bereitschaft prüfen, dann die Spec schreiben |
| `build` | Die Spec umsetzen |

Neu gegenüber `local.py`: Das Skript liest die Kommentare des Tickets und schreibt selbst Kommentare. Jeder beginnt mit `[KI]`. Lokal geht es über euren Jira-MCP-Server (`--jira mcp`), in einer Pipeline per API-Token (`--jira api`). Die Anleitung: [Factory-Schritte lokal ausführen](../../bedienung/lokal-ausfuehren.md) und [Übung 1](../../../01-erstworkshop/tag-2/uebung-factory-lokal.md).

- **Quelle:** angepasst aus `local.py` im Lab-Repo [factory-lab](https://bitbucket.org/factory-lab/factory-lab/src/factory-base/factory/), Branch `factory-base`, Commit `a414237`, Ordner `factory/`. Es ist keine unveränderte Kopie mehr.
- **Stand:** 25. November 2026, Copilot CLI 1.0.115, Modell `claude-sonnet-5.5`.

| Datei | Wozu | Nötig? |
|---|---|---|
| [`agentic-factory.py`](agentic-factory.py) | Das Programm, nur ein Starter: Es lädt den Code aus `agentic_factory/` neben sich. Nur Python-Standardbibliothek. Außer seinem Paket `agentic_factory/` importiert es nichts aus der Factory | Ja |
| [`agentic_factory/`](agentic_factory/) | Der Code, ein Modul pro Teil: Jira, Copilot-Aufrufe, Prüfungen, Klärung und die Schritte `fetch`, `agent`, `post`. Der Ordner muss **neben dem Skript** liegen | Ja |
| [`config.json`](config.json) | Prompts, Werkzeug-Freigaben, verbotene Befehle, Modell und Credit-Grenzen, für OpenSpec, Spec Kit und BMad. Neu ist der Block `clarify`: Prompt, Werkzeuge, Credit-Grenze und `max_rounds` für die Klärung. Neu ist auch der Block `rules`: welche Regeln des Teams in welche Prompts kommen | Ja |
| [`readiness.md`](readiness.md) | Die Kriterien der Bereitschaftsprüfung. `clarify` nutzt sie auch | Für `assess`, `clarify` und `spec` mit Bereitschaftsprüfung |
| [`regeln/`](regeln/) | Die Regeln des Teams als Markdown-Dateien, siehe [Regeln des Teams](#regeln-des-teams) | Solange `config.json` sie im Block `rules` nennt |
| [`local.example.json`](local.example.json) | Vorlage für `local.json`: euer Testbefehl, Stack-Satz für Spec Kit, Modell, Copilot-Befehl. Neu: `jira_mcp_server` und `jira_site` für den Weg über den Jira-MCP | Nein. Ohne `local.json` gelten die Werte aus `config.json`, auch der Testbefehl `./bin/phpunit`. Für `--jira mcp` braucht ihr `jira_site` oder `JIRA_BASE_URL` |
| [`agentic-factory-plugin/`](agentic-factory-plugin/) | Der Hook für die Jira-Aufrufe über MCP: Er lässt nur den einen erwarteten Aufruf durch. Der Ordner muss **neben dem Skript** liegen. Das Skript lädt ihn von dort, nie aus `.github/` | Für `--jira mcp`. Copilot 1.0.115 führt ihn nicht aus, siehe [Sicherheit](#sicherheit-was-ihr-wissen-müsst) |
| [`pipelines.example.yml`](pipelines.example.yml) | Beispiel für Bitbucket Pipelines: `agentic-clarify` und `agentic-assess`, je mit den Schritten `fetch`, `agent` und `post` | Nein. Nur für die Pipeline |
| [`tests/`](tests/) | Die Tests, eine Datei pro Modul, siehe [Tests](#tests) | Nein |

## So nutzt ihr sie

Im Wurzelordner eures Repos:

```bash
mkdir -p factory
cp -R <dieser Ordner>/{agentic_factory,agentic-factory-plugin,regeln} factory/
cp <dieser Ordner>/{agentic-factory.py,config.json,readiness.md,local.example.json} factory/
cp -R <dieser Ordner>/tests factory/     # optional
cp factory/local.example.json factory/local.json
python3 -I factory/agentic-factory.py spec --ticket-file ~/factory-tickets/LL-123.json --print-only
```

- Die Tests in `tests/` prüfen die Dateien der Vorlage. Ändert ihr `config.json` oder `regeln/`, schlagen einige fehl.
- `agentic-factory.py` liest `config.json`, `readiness.md` und `local.json` **neben sich**, nicht im aktuellen Ordner. Die Ordner `agentic_factory/`, `agentic-factory-plugin/` und `regeln/` auch. Fehlt `agentic_factory/`, stoppt das Skript mit Exit-Code 2.
- Der Ordner heißt `factory/`, denn dort sucht der Skill [`schreibe-ticket`](../../werkzeuge/schreibe-ticket/README.md) `agentic-factory.py` und `readiness.md`.
- In `local.json` tragt ihr euren echten Testbefehl ein. Aus `make test` wird die Erlaubnis `shell(make:*)`: Der Agent darf dann **jedes** Make-Ziel starten.
- `--ticket-file` heißt offline: Das Skript fragt Jira nie und postet nichts. Der erste Lauf mit `--print-only` startet keinen Copilot-Aufruf und kostet nichts.
- Jira-Zugangsdaten gehören nie in `local.json`, nur in die Umgebung: `JIRA_BASE_URL`, `JIRA_API_TOKEN` und für Jira Cloud `JIRA_EMAIL`. Die braucht nur `--jira api`.

Für den Weg über den Jira-MCP, einmal pro Rechner:

```bash
copilot mcp add --transport http atlassian https://mcp.atlassian.com/v1/mcp
copilot          # dann /mcp, atlassian, „Authenticate“, im Browser anmelden, /exit
```

Dann in `factory/local.json` eure Jira-Cloud-Adresse eintragen, etwa `"jira_site": "https://example.atlassian.net"`. Fehlt `jira_site`, nimmt das Skript `JIRA_BASE_URL`. Jira Data Center hat keinen MCP-Weg: Nehmt dort `--jira api`. Alles Weitere steht in [Factory-Schritte lokal ausführen](../../bedienung/lokal-ausfuehren.md#jira-über-den-mcp-server).

Was `agentic-factory.py` mit diesen Dateien an Copilot schickt, zeigen die [Prompt-Beispiele](../prompt-beispiele/README.md).

## Regeln des Teams

Eigene Regeln schreibt ihr als Markdown-Dateien in den Ordner `regeln/`. Das Skript hängt sie an die Prompts an. Welche Datei in welchen Aufruf kommt, steht in `config.json` im Block `rules`:

| Datei | Aufrufe | Inhalt zum Start |
|---|---|---|
| [`regeln/stil.md`](regeln/stil.md) | `clarify`, `spec` | So kurz wie möglich, kurze Sätze, kein Passiv |
| [`regeln/ticket.md`](regeln/ticket.md) | `assess`, `clarify` | Nie mehr als 10 Akzeptanzkriterien, keine Hinweise, die nicht unbedingt nötig sind |
| [`regeln/code.md`](regeln/code.md) | `build` | Always read and follow the AGENTS.md, make minimal code changes, no additional refactoring, bug-fixing, or nice-to-have changes |

- `assess` heißt: jede Bereitschaftsprüfung. Also der Modus `assess`, die Prüfung vor `spec` und die Prüfung in `clarify`. `spec` und `build` heißen: jeder Prompt des Frameworks. Die kurzen Jira-Aufrufe bekommen keine Regeln.
- Das Skript hängt die Dateien als Block `<<<TEAM RULES … TEAM RULES>>>` ans Ende des Prompts, nach einer Leerzeile. Die Regeln der Factory gehen vor: Die Regeln des Teams machen nie ein Ticket bereit, das die Kriterien aus `readiness.md` nicht bereit finden.
- Jede Datei, die die Bereitschaftsprüfung bekommt, ist ein Kriterium: Verstößt ein Ticket gegen sie, ist es „nicht bereit“, mit dem Grund `team_rules`. Stilregeln tragt ihr deshalb nur bei `clarify`, `spec` und `build` ein, nie bei `assess`. In `clarify` darf eine Frage das Kriterium `team_rules` nennen.
- Vor jedem Copilot-Aufruf prüft das Skript die Dateien, auch mit `--print-only`. Es stoppt, wenn eine fehlt, wenn eine länger als 4.000 Zeichen ist und wenn es Tokens, unsichtbare Zeichen, HTML-Kommentare oder Link-Definitionen findet. Leere Dateien lässt es weg.
- Ohne Block `rules` bleiben die Prompts wie vorher.

So fügt ihr eine Regel hinzu:

1. Legt die Datei an, etwa `regeln/tests.md`.
2. Tragt sie unter `files` ein: `"tests": "regeln/tests.md"`. Der Pfad gilt ab dem Ordner von `config.json`.
3. Nennt ihren Namen unter `calls` bei jedem Aufruf, der sie bekommen soll, etwa `"build": ["code", "tests"]`. Die Reihenfolge dort ist die Reihenfolge im Prompt.

Die Schritte `fetch`, `agent` und `post` lesen dieselben Dateien. Die Pipeline von `factory-base` kennt sie noch nicht: Ihre Prompts haben keine Regeln des Teams.

## Sicherheit: Was ihr wissen müsst

`agentic-factory.py` hat lokal nicht den Schutz der Pipeline: keinen eigenen Benutzer, keinen Container, keinen Prüfschritt vor dem Commit. Der Agent läuft als ihr.

- **Eure Umgebung:** Copilot bekommt alle eure Umgebungsvariablen, nur die drei Jira-Variablen nicht. Startet das Skript in einer Shell ohne andere Tokens, etwa für Cloud, Datenbank oder Registry.
- **BMad darf beliebigen Code starten:** `shell(uv:*)` gilt beim Spec schreiben und beim Bauen. Mit `uv` startet der Agent jedes Python-Programm. Beim Bauen darf BMad außerdem selbst committen. OpenSpec und Spec Kit haben keinen solchen Freibrief.
- **Der Agent kann ändern, was er starten darf:** Er darf Dateien schreiben, also auch `./bin/phpunit`, die Skripte unter `.specify/` oder euer `Makefile`, und sie danach starten. Ein Ticket-Text, der ihn dazu bringt, führt so eigenen Code aus. Das Skript warnt erst nach dem Lauf, mit `WARNING: protected paths changed`, wenn sich `bin/` oder `.specify/` geändert haben. Ein geändertes `Makefile` meldet es nicht.
- **Euer Testbefehl wird zur Erlaubnis:** Aus `make test` wird `shell(make:*)`, also jedes Make-Ziel. Über Make kann der Agent beliebige Befehle ausführen.
- **In `spec` und `build` bleiben lesende Befehle möglich.** Diese Schritte brauchen Shell-Werkzeuge, etwa `shell(openspec:*)`. Ein Verbot von `shell` würde sie mit abschalten. Copilot kann dort also auch lesende Befehle außerhalb der Freigabe ausführen, etwa `ls` oder `grep`.
- **Die Kontrolle nach dem Lauf sieht nicht alles:** Das Skript vergleicht nur, was `git status` zeigt. Änderungen in `.git/`, etwa ein neuer Hook, und in ignorierten Dateien, etwa `.env`, sieht es nicht. Ein Hook liefe beim nächsten `git commit`.

Neu, seit das Skript in Jira schreibt:

- **Kommentare erscheinen unter eurem eigenen Jira-Konto.** Lokal postet das Skript mit eurer Anmeldung beim Jira-MCP. Jeder Kommentar beginnt mit `[KI]` und sagt, dass `agentic-factory.py` ihn geschrieben hat. Ein `[KI]`-Kommentar ist nie eine Freigabe.
- **Ein Werkzeug pro Jira-Aufruf.** Jeder Jira-Aufruf ist ein eigener, kurzer Copilot-Aufruf. Freigegeben ist nur ein Werkzeug des MCP-Servers, etwa `atlassian(getJiraIssue)`. Alle anderen MCP-Server sind aus, Lesen und Schreiben von Dateien auch. Er läuft in einem Ordner außerhalb des Projekts. Die Arbeitsaufrufe (`assess`, `clarify`, `spec`, `build`) haben keinen Jira-Zugang. Die kurzen Jira-Aufrufe sehen dagegen Ticket- oder Kommentartext, etwa das Ergebnis von `getJiraIssue` oder den Text, den sie posten sollen. Was sie tatsächlich getan haben, prüft das Skript danach.
- **Shell-Befehle ohne Freigabe.** Copilot 1.0.115 führt Shell-Befehle aus, die es für nur lesend hält, auch wenn sie nicht freigegeben sind. Das Skript verbietet deshalb `shell` in jedem Aufruf ohne Shell-Werkzeuge: in der Bereitschaftsprüfung, in `clarify` und in den Jira-Aufrufen. Lief trotzdem einer, stoppt es. Nach der Bereitschaftsprüfung oder `clarify` postet es dann nichts.
- **Der Hook läuft mit Copilot 1.0.115 nicht.** Copilot CLI 1.0.115 führt in `-p`-Läufen keine Hooks aus `--plugin-dir` aus. 1.0.114 hat es getan. Das Skript liefert den Hook trotzdem mit und prüft jeden Jira-Aufruf danach aus den Ereignissen von Copilot: welches Werkzeug, welches Ticket, welche Argumente, welcher Text. Danach liest es den gespeicherten Kommentar zurück. Passt etwas nicht, stoppt es und nennt den Kommentar, den ihr von Hand löschen müsst. Ohne Hook verhindert diese Prüfung nichts, sie bemerkt es nur hinterher.

Was ihr tut:

- Nur Tickets durchschicken, deren Text ihr kennt. Der Text landet im Prompt.
- Vor dem Lauf alles committen, damit der Diff nur die Arbeit des Agenten zeigt.
- Jede `WARNING` des Skripts ernst nehmen.
- Nach jedem Lauf prüfen:

```bash
git status --ignored
git diff
ls -la .git/hooks
git config --local --list
```

## Was fehlt

- **Die Prüf- und Veröffentlichungsschritte der Pipeline:** `check.py`, `publish.py` und `guard.py` der Pipeline (factory-base). Lokal prüft niemand den Diff auf geschützte Pfade, Secrets oder unsichtbare Zeichen. Ihr lest ihn selbst. Auch `pipelines.example.yml` hat diese Schritte nicht.
- **Übergänge, Labels und Freigaben.** Das Skript schreibt nur Kommentare und, bei `clarify --apply`, die Beschreibung. Es setzt keinen Status, kein Label, keinen Branch und keinen Pull Request. Das bleibt so.
- **`build` in der Pipeline.** Das Skript lehnt es dort ab: Der Code ginge mit dem Schritt verloren.

## Tests

Die Tests brauchen nur die Python-Standardbibliothek. Sie rufen weder Jira noch Copilot auf: Ein Ersatz-`copilot` und ein lokaler Test-Server stehen dafür. Im Workshop-Repo:

```bash
python3 -I -B -m unittest discover -s 02-agent-factory/einrichtung/template/tests -t 02-agent-factory/einrichtung/template
```

Ein Teil der Tests vergleicht den Code mit `factory-base`: Prompts und Flags mit `agent.py`, die kopierten Prüfungen mit `common.py` und die eigenen Kommentare mit dem Marker von `guard.py`. Diese Tests brauchen einen Klon des Lab-Repos. Ohne `FACTORY_BASE` überspringen sie sich:

```bash
git clone --depth 1 --branch factory-base https://bitbucket.org/factory-lab/factory-lab.git /tmp/factory-lab
FACTORY_BASE=/tmp/factory-lab/factory python3 -I -B -m unittest discover -s 02-agent-factory/einrichtung/template/tests -t 02-agent-factory/einrichtung/template
```

## Aktualisieren

`factory-base` ist nur noch die Referenz. Kopiert die Dateien von dort nicht mehr über diese hier.

- **Kopierte Blöcke** stehen alle in `agentic_factory/copied.py`, markiert etwa mit `# --- copied from factory/common.py`. Ändert sich `factory-base`, schlagen die Tests mit `FACTORY_BASE` fehl. Dann übernehmt ihr die Änderung von Hand.
- **Die Umwandlung der Beschreibung** steht auch dort. Sie ist aus `jira_ticket.py` des Skills [`schreibe-ticket`](../../werkzeuge/schreibe-ticket/README.md) kopiert. Ein Test vergleicht beide, auch ohne `FACTORY_BASE`.
- **Alles andere** pflegt ihr hier.
