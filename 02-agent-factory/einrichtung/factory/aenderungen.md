# Änderungen und Umstieg

Diese Seite sagt, was sich an `agentic-factory.py` gegenüber `local.py` und der früheren Vorlage geändert hat. Und wie ihr ein bestehendes Projekt umstellt. Die Bedienung steht in der [README der Vorlage](README.md).

- **Stand:** 25. November 2026, Copilot CLI 1.0.115.
- **`local.py`:** `factory/local.py` im Lab-Repo [factory-lab](https://bitbucket.org/factory-lab/factory-lab/src/factory-base/factory/local.py), Branch `factory-base`, Commit `a414237`, mit `config.json`, `local.example.json` und `readiness.md` daneben.
- **Die frühere Vorlage:** dieser Ordner im Commit `414cf25` des Workshop-Repos, mit `regeln/` und mit `test_command` in `local.json`.

## Was sich gegenüber `local.py` geändert hat

`local.py` war eine Datei mit drei Modi: `assess`, `spec` und `build`. Es las ein Ticket per REST aus Jira und schrieb nie in Jira. `test_command`, `stack_hint`, `model` und `copilot` nahm es aus `local.json`.

### Aufbau

| Vorher | Jetzt |
|---|---|
| Eine Datei, `local.py`, 704 Zeilen | Ein Starter, `agentic-factory.py`, und daneben das Paket `agentic_factory/` mit einem Modul pro Teil. Fehlt das Paket, stoppt der Starter mit Exit-Code 2 |
| Die Tests in `test_local.py` | Die Tests in `tests/`, eine Datei pro Modul |
| – | Der Ordner `agentic-factory-plugin/` mit dem Hook für die Jira-Aufrufe |
| Jede Ausgabe beginnt mit `[local]` | Jede Ausgabe beginnt mit `[agentic-factory]` |

### Modi und Optionen

| Vorher | Jetzt |
|---|---|
| `assess`, `spec`, `build` | Dazu `clarify`: ein Ticket in Runden von Kommentaren klären. Und `init`: aus der Doku des Projekts Änderungen an `config.json` und `readiness.md` vorschlagen |
| Jeder Lauf von `spec` und `build` startet wie der erste | Ein neuer Lauf überarbeitet Spec oder Code nach `[Mensch]`-Kommentaren und Änderungen von Hand, siehe [Feedback](#feedback). `--fresh` startet wie beim ersten Mal |
| `build --framework …` liest kein Ticket | `build` liest das Ticket immer, aus Jira oder aus `--ticket-file` |
| Die Optionen `--key`, `--ticket-file`, `--framework`, `--change`, `--no-assess`, `--print-only`, `--config`, `--local`, `--readiness` | Bleiben. `--repo` ist weg: Das Projekt ist das Repository um `factory/`. Neu: `--jira`, `--comments-file`, `--no-post`, `--apply`, `--fresh`, `--step`, `--io-dir` |
| `--key LL-123` nennt das Ticket | Neu: das Ticket direkt nach dem Modus, als Schlüssel oder Jira-URL: `spec LL-123` oder `spec https://example.atlassian.net/browse/LL-123`. Der Host der URL muss zu `jira_site` oder `JIRA_BASE_URL` passen. `--key` bleibt als lange Form |
| Exit-Codes 0, 2, 4 (nicht bereit) und 5 (Fragen) | Dazu 6: `clarify` hat seine Grenze an Runden erreicht |

### Jira

| Vorher | Jetzt |
|---|---|
| Liest Zusammenfassung, Beschreibung, Labels und Status | Liest dazu alle Kommentare |
| Schreibt nie in Jira | Postet das Ergebnis als Kommentar, der mit `[KI]` beginnt: `assess` bei „nicht bereit“, `clarify`, `spec` und `build`. `clarify --apply` setzt die Beschreibung. Mit `--ticket-file` oder `--no-post` landet der Kommentar nur in einer Datei |
| Ein Weg: REST mit `JIRA_BASE_URL`, `JIRA_API_TOKEN` und für Jira Cloud `JIRA_EMAIL` | Zwei Wege. `--jira mcp`, der Standard außerhalb einer Pipeline: über euren Jira-MCP-Server in Copilot, nur Jira Cloud. `--jira api`, der Standard in einer Pipeline: REST mit denselben Variablen wie vorher |
| – | Über MCP ist jeder Jira-Aufruf ein eigener, kurzer Copilot-Aufruf mit genau einem Werkzeug. Das Skript prüft ihn danach aus den Ereignissen von Copilot und liest einen geposteten Kommentar zurück. Der Hook in `agentic-factory-plugin/` soll nur den erwarteten Aufruf durchlassen. Copilot 1.0.115 führt ihn aber nicht aus |

### Pipeline

| Vorher | Jetzt |
|---|---|
| Nur lokal, ein Prozess | Drei Schritte: `fetch`, `agent` und `post`. Sie übergeben über einen Ordner mit `in/` und `out/`. Lokal laufen sie in einem Prozess. In einer Pipeline laufen sie getrennt: `fetch` und `post` mit den Jira-Daten, `agent` nur mit dem Copilot-Token. Sieht ein Schritt das Token des anderen, stoppt er |
| – | [`pipelines.example.yml`](pipelines.example.yml) mit den Pipelines `agentic-clarify` und `agentic-assess` |
| – | `build` und `init` lehnt das Skript in einer Pipeline ab |

### Konfiguration

| Vorher | Jetzt |
|---|---|
| Die `config.json` des Labs: Symfony und PHP, `./bin/phpunit` und die Schlüssel der Pipeline von factory-base | Ohne Annahmen über euren Stack. Die Schlüssel, die nur die Pipeline las, sind weg. Die Tabelle unter [A: von `local.py`](#a-von-localpy) nennt jeden |
| `test_command` in `config.json` als Liste `["./bin/phpunit"]`. `local.json` kann es als Text überschreiben | `test_command` steht nur in `config.json`, als Text, zum Start leer. Ohne ihn stoppt `build` |
| Die Freigabe für den Testbefehl ist sein erstes Wort: Aus `make test` wird `shell(make:*)` | Die Freigabe ist der ganze Befehl als Anfang: `shell(make test:*)`. Vor jedem Build prüft das Skript den Befehl, etwa auf `bash -c` oder `&&`, siehe [Der Testbefehl](README.md#der-testbefehl) |
| `build_rules` und jede Liste `build_tools` nennen `./bin/phpunit` | `build_rules` hat den Platzhalter `{test_command}`. `build_tools` nennt keinen Testbefehl: Das Skript hängt ihn an |
| `stack_hint` in `local.json` ersetzt „Use the existing Symfony 7 / PHP stack and PHPUnit“ im Plan-Prompt von Spec Kit | Der Plan-Prompt sagt „Use the existing stack and test setup; no new dependencies.“ Euren Stack beschreibt ihr in `AGENTS.md` |
| `local.json`: `test_command`, `stack_hint`, `model`, `copilot` | `local.json`: `model`, `copilot`, `jira_mcp_server`, `jira_site`. Ein alter Schlüssel stoppt das Skript |
| `deny_tools` verbietet `composer` und `npm` ganz | `deny_tools` verbietet `npm install`, `npm i`, `npm ci` und `npm exec`, sonst liefe `npm test` nicht. `composer` verbietet die Vorlage nicht mehr |
| `protected_paths` mit Pfaden von Symfony und PHP | Nur allgemeine Pfade. `init` schlägt Pfade für euren Stack vor |
| – | `read_tools`: lesende Befehle wie `ls`, `cat` und `grep` für jeden Aufruf von `spec` und `build` |
| – | Neue Blöcke: `clarify`, `init`, und je Framework `revise_prompt` und `amend_prompt` |
| `spec_rules` und `build_rules` nennen `AGENTS.md` nicht | Beide enden mit „Follow AGENTS.md in the repository root, if it exists, and the files it links to; where they conflict with these factory rules, these rules win.“ Die Regeln der Bereitschaftsprüfung, von `clarify` und der amend-Aufrufe auch. Fehlt `spec_rules` oder `build_rules` in `config.json`, stoppt das Skript, statt die Regeln des Labs mit `./bin/phpunit` zu nehmen |
| `protected_paths`: `^AGENTS\.md$`, `^CLAUDE\.md$`, `^\.github/` | `(?i)(^\|/)(AGENTS\|CLAUDE\|GEMINI)\.md$` und `(?i)^\.github/`: auch `GEMINI.md`, das Copilot ebenfalls lädt, auch in Unterordnern und in jeder Schreibweise. Copilot lädt auch `agents.md`. Jedes Muster in `protected_paths` beginnt mit `(?i)`, und das Skript prüft alle ohne Unterschied von Groß- und Kleinschreibung, auch die von `init`: Auf macOS ist `.Agents/` derselbe Ordner wie `.agents/` |
| `forbidden_flags` ohne `--no-custom-instructions` | `--no-custom-instructions` ist verboten, auch wenn eine alte `config.json` es nicht nennt |
| `readiness.md` mit Beispielen aus der Symfony-Demo, Status „Klärung nötig“ und Image | Dieselben Kriterien und IDs, Beispiele ohne Stack, ohne Status und ohne Image |

### Sicherheit

| Vorher | Jetzt |
|---|---|
| Die Bereitschaftsprüfung hat kein Shell-Werkzeug, verbietet die Shell aber nicht | Jeder Aufruf ohne Shell-Werkzeug bekommt `--deny-tool=shell`: die Bereitschaftsprüfung, `clarify`, `init` und die Jira-Aufrufe. Lief trotzdem ein Shell-Befehl, stoppt das Skript |
| Eure MCP-Server sind in jedem Aufruf aus | Wie vorher. Ein Jira-Aufruf über MCP lässt nur euren Jira-Server an |
| Das Urteil der Bereitschaftsprüfung prüft das Skript auf seine Form | Dazu auf Länge, Anzahl und unsichtbare Zeichen, wie `assess.py` der Pipeline |
| – | Vor dem Posten prüft das Skript jeden Kommentar: Tokens, unsichtbare Zeichen, Links außerhalb von Code-Blöcken, Länge, `FACTORY-` und den Anfang `[KI]` |
| – | `test_command` und `read_tools` prüft das Skript vor dem ersten Aufruf. Trifft sie ein Eintrag in `deny_tools`, stoppt es |
| – | `init` darf nur lesen. Seine Vorschläge dürfen nur hinzufügen oder verschärfen. Das Skript prüft jeden. `init --apply` schreibt das gespeicherte Ergebnis des letzten Laufs, ohne neuen Aufruf |
| `git status` nach jedem Aufruf mit der Konfiguration des Repos | Jeder `git`-Aufruf des Skripts läuft ohne fsmonitor, Hooks, externen Diff und Pager. Ändert ein Arbeitsaufruf `.git/config`, die Hooks oder eingebundene Dateien, stoppt das Skript vor dem nächsten `git`-Befehl |
| – | Vor jedem Lauf nennt das Skript Nummer und Konto der `[Mensch]`-Kommentare, die es liest. `blocked.jsonl` schwärzt bekannte Tokens. Sehen die Ereignisse von Copilot anders aus als bei 1.0.115, warnt das Skript |

### Feedback

Neu. `[Mensch]`-Kommentare im Ticket und Änderungen von Hand an den Spec-Dateien steuern einen neuen Lauf. Vor dem ersten Build überarbeitet `spec` die Spec. Danach macht `build` aus den Kommentaren neue Aufgaben und setzt sie um. `spec` lehnt dann ab. Alles Weitere: [Feedback zu Spec und Build](README.md#feedback-zu-spec-und-build).

### Protokolle

| Vorher | Jetzt |
|---|---|
| Ein Ordner pro Lauf, `~/.factory-local/<repo>/<zeit>-<modus>-<key>/`, mit Ereignissen und Verbrauch jedes Aufrufs | Wie vorher, dazu `io/` mit `in/` und `out/` |
| Abgelehnte Aufrufe stehen nur in der Ausgabe, als `DENIED` | Dazu sammelt [`blocked.jsonl`](README.md#blockierte-aufrufe-blockedjsonl) sie für alle Läufe, in `~/.factory-local/<repo>/`. Jeder Lauf mit Copilot-Aufrufen endet mit einer Zeile dazu |
| – | Unter `~/.factory-local/<repo>/specs/` eine Kopie der Spec nach jedem Lauf von `spec` und `build`. Gegen sie rechnet das Skript den Diff eurer Änderungen von Hand |
| – | `init-result.json` im Ordner eines `init`-Laufs: das geprüfte Ergebnis für `init --apply` |

### Was gleich geblieben ist

- **Prompts und Flags** baut das Skript wie `agent.py` von factory-base. Tests vergleichen beides, mit einer Konfiguration wie der des Labs, siehe [Tests](README.md#tests). Die `config.json` der Vorlage weicht an diesen Stellen ab: der Plan-Prompt von Spec Kit, `{test_command}` in `build_rules`, der Satz zu `AGENTS.md` am Ende von `spec_rules`, `build_rules` und der Regeln der Bereitschaftsprüfung, die Freigabe für den Testbefehl, `read_tools`, `deny_tools`, die geschützten Pfade, die der Prompt der Bereitschaftsprüfung nennt, und die Wörter für Teile des Codes in diesem Prompt und in `readiness.md`: „modules, entry points, user interface, data model“ statt Begriffe aus Symfony. Neu sind die Prompts von `clarify`, `init`, `revise_prompt` und `amend_prompt`. `--deny-tool=shell` und `--disable-mcp-server` hängt das Skript nur hinten an.
- **Unverändert aus factory-base:** der Prompt der Bereitschaftsprüfung und `readiness.md` bis auf die Wörter und den Satz zu `AGENTS.md` oben (die IDs der Kriterien sind gleich), `spec_rules` bis auf den Satz zu `AGENTS.md`, `forbidden_flags` bis auf `--no-custom-instructions`, und `forbidden_env`. Das Modell `claude-sonnet-5.5`, 150 Credits pro Aufruf, 40 für die Bereitschaftsprüfung, 1200 Sekunden pro Aufruf.
- **Das Framework:** erst `--framework`, dann genau ein Label `sdd-*`, dann `default_framework`. Fehlt sein Ordner im Projekt, stoppt das Skript.
- **Die Bereitschaftsprüfung** läuft vor `spec`, wenn `assess.enabled` gilt. `--no-assess` überspringt sie.
- **Die Umgebung:** Copilot bekommt eure Umgebungsvariablen ohne die drei Jira-Variablen, dazu dieselben Sicherheits-Variablen.
- **Nach dem Lauf:** die Liste der Änderungen und Warnungen bei geschützten Pfaden und bei Dateien außerhalb des Spec-Ordners. Kein Container, kein eigener Benutzer, kein Prüfschritt. `git diff` lest ihr selbst.
- **Die Dateien** `config.json`, `readiness.md` und `local.json` liest das Skript neben sich. Das Skript muss in `factory/` im Wurzelordner des Repos liegen. Starten könnt ihr es aus jedem Ordner.

### Gegenüber der früheren Vorlage

Die frühere `agentic-factory.py` hatte schon Kommentare in Jira, `clarify`, die drei Schritte und `--deny-tool=shell`. Seitdem neu:

- **Keine Regeln des Teams mehr:** `regeln/`, der Block `rules` in `config.json` und das Kriterium `team_rules` sind weg. Ein Block `rules` stoppt das Skript. Die Hinweise gehören in `AGENTS.md`.
- **`local.json` hat nur noch die Einstellungen eures Rechners:** `test_command` steht in `config.json`, den Stack beschreibt `AGENTS.md`.
- **`config.json` ohne Stack:** wie oben unter [Konfiguration](#konfiguration). Die frühere Vorlage hatte noch die `config.json` des Labs.
- **Neu:** `init`, `blocked.jsonl`, `read_tools`, das Überarbeiten von Spec und Build und `--fresh`.
- **Die `[KI]`-Kommentare von `spec` und `build`** haben neue Zeilen: `Spec-Prüfsumme`, bei `build` auch `Start-Commit`, bei Überarbeitungen `Bearbeitet`. Neue Marker: `spec überarbeitung=<n>` und `build überarbeitung=<n>`.

## Umsteigen

Beide Wege enden gleich: `factory/` hat die Dateien dieser Vorlage und eure Werte, `init` ist einmal gelaufen, ein Testlauf ohne Jira hat geklappt. `<dieser Ordner>` steht für diesen Ordner im Workshop-Repo. Für den Testlauf braucht ihr eine Ticket-Datei, etwa `~/factory-tickets/LL-123.json`:

```json
{"key": "LL-123", "summary": "Tags klein schreiben", "description": "Beim Speichern sollen Tags klein geschrieben werden.", "labels": ["sdd-openspec"]}
```

### A: von `local.py`

Ihr habt `local.py` mit `config.json`, `readiness.md` und vielleicht `local.json` aus factory-base in `factory/` kopiert.

1. Committet alles. `git status` zeigt danach nichts mehr.
2. Schreibt auf, was ihr übernehmt: `test_command` und `stack_hint` aus `factory/local.json`, dazu eure Änderungen an `factory/config.json`. Das Original zeigt `git show a414237:factory/config.json` in einem Klon von factory-lab. Speichert es, etwa als `config-alt.json`, und vergleicht: `diff config-alt.json factory/config.json`.
3. Entfernt `local.py` und kopiert die Vorlage:

   ```bash
   rm factory/local.py                    # und factory/test_local.py, falls ihr es kopiert habt
   cp -R <dieser Ordner>/{agentic_factory,agentic-factory-plugin} factory/
   cp <dieser Ordner>/{agentic-factory.py,config.json,local.example.json} factory/
   ```

   `config.json` ersetzt ihr damit. `readiness.md` hat in der Vorlage dieselben Kriterien und IDs wie in factory-base, nur mit Beispielen ohne Symfony. Habt ihr eure Datei nicht geändert, kopiert die neue: `cp <dieser Ordner>/readiness.md factory/`. Sonst behaltet eure. Die Tests der Vorlage kopiert ihr nicht nach `factory/tests/`, wenn dort schon die Tests von factory-base liegen: `test_readiness.py` gibt es in beiden.
4. Startet das Skript einmal ohne Copilot-Aufruf: `python3 -I factory/agentic-factory.py init --print-only`. Steht in `local.json` noch `test_command` oder `stack_hint`, stoppt es mit Exit-Code 2 und sagt, wohin der Wert gehört, etwa so:

   ```text
   [agentic-factory] STOP: …/factory/local.json: stack_hint moved to AGENTS.md (describe the stack there), test_command moved to config.json (key test_command); remove it from local.json
   ```

5. Tragt die Werte um, wie die Tabelle unten sagt. `test_command` kommt als Text in `config.json`, etwa `"test_command": "make test"`. Den Text von `stack_hint` schreibt ihr in `AGENTS.md`. Dann löscht ihr beide Schlüssel aus `local.json`. Eure Änderungen an `config.json` übertragt ihr von Hand in die neue Datei.
6. Startet `python3 -I factory/agentic-factory.py init --print-only` noch einmal. Jetzt zeigt es den Copilot-Befehl und endet mit Exit-Code 0.
7. Startet `init` ohne `--print-only` und lest den Bericht. Passt er, startet `init --apply`. Das schreibt genau diese Vorschläge in `config.json` und `readiness.md`, ohne neuen Aufruf. Der Lauf ohne `--apply` kostet bis zu 40 Credits, `--apply` kostet nichts. Dann `git diff factory/`. Mehr steht unter [Erste Einrichtung mit `init`](README.md#erste-einrichtung-mit-init).
8. Richtet den Jira-MCP ein, einmal pro Rechner. Das ist neu für euch, `local.py` kannte nur REST:

   ```bash
   copilot mcp add --transport http atlassian https://mcp.atlassian.com/v1/mcp
   copilot          # dann /mcp, atlassian, „Authenticate“, im Browser anmelden, /exit
   ```

   Tragt eure Jira-Cloud-Adresse in `factory/local.json` ein, etwa `"jira_site": "https://example.atlassian.net"`. Bei Jira Data Center nehmt ihr `--jira api`, mit denselben Variablen wie bei `local.py`.

   Habt ihr den Server in Übung 1 mit einer Werkzeug-Liste angelegt (`"tools": [...]` in `~/.copilot/mcp-config.json`), fehlen dort Werkzeuge, die das Skript braucht: `addCommentToJiraIssue` zum Posten, `editJiraIssue` für `clarify --apply` und `atlassianUserInfo` für `clarify --apply` und jeden weiteren Lauf von `spec` und `build`. Ergänzt sie, oder legt den Server mit `copilot mcp remove atlassian` und dem Befehl oben neu an. Sonst kostet der erste Lauf Credits und stoppt erst beim Posten.
9. Prüft ohne Jira. Das Projekt braucht den Ordner des Frameworks, das das Label der Ticket-Datei nennt, hier `openspec/`. Sonst gebt ihr `--framework` an. Erst `python3 -I factory/agentic-factory.py spec --ticket-file ~/factory-tickets/LL-123.json --print-only`: Das zeigt die Copilot-Befehle und kostet nichts. Dann derselbe Befehl ohne `--print-only`: Das kostet Credits. Das Skript fragt Jira nicht und postet nichts. Den Kommentar schreibt es in eine Datei, die letzte Zeile nennt sie. Die Spec liegt danach uncommittet im Projekt. Verwerft sie, wenn ihr sie nicht braucht.
10. Committet `factory/` und `AGENTS.md`.

Läuft in eurem Repo die Pipeline von factory-base aus demselben Ordner `factory/`, dann ersetzt ihr `config.json` nicht. Die Pipeline nimmt die Datei in ihr Image auf und braucht ihre Schlüssel, etwa `project_key`, `bitbucket` und `test_command` als Liste. Mit dieser Liste stoppen `build` und `init` von `agentic-factory.py` aber vor dem ersten Copilot-Aufruf mit `config.json: test_command must be a string such as "make test"; an old config has a list — write it as one string`. Legt die Vorlage dann in einen eigenen Ordner. Der Skill [`schreibe-ticket`](../../werkzeuge/schreibe-ticket/README.md) sucht sie allerdings in `factory/`.

| Alter Schlüssel | Neuer Ort |
|---|---|
| `local.json` `test_command`, etwa `"make test"` | `config.json` `test_command`, als Text. Die Freigabe wird `shell(make test:*)` statt `shell(make:*)` |
| `local.json` `stack_hint` | `AGENTS.md` |
| `local.json` `model`, `copilot` | Bleiben in `local.json` |
| – | `local.json` `jira_mcp_server` (Standard `atlassian`) und `jira_site`, für `--jira mcp` |
| `JIRA_BASE_URL`, `JIRA_API_TOKEN`, `JIRA_EMAIL` in der Umgebung | Bleiben, für `--jira api`. `JIRA_BASE_URL` gilt auch für `--jira mcp`, wenn `jira_site` fehlt |
| `config.json` `test_command`: `["./bin/phpunit"]` | `config.json` `test_command` als Text, zum Start leer |
| `./bin/phpunit` in `build_rules` | Der Platzhalter `{test_command}` |
| `shell(./bin/phpunit:*)` in jeder Liste `build_tools` | Entfällt: Das Skript hängt den Testbefehl an |
| Symfony und PHPUnit im Plan-Prompt von Spec Kit | `AGENTS.md` |
| Die Pfade von Symfony und PHP in `protected_paths` | Entfallen. Für ein Symfony-Projekt tragt ihr sie wieder ein, von Hand oder per `init`. Die Liste steht unten |
| `shell(composer:*)` in `deny_tools` | Entfällt. Tragt es für ein PHP-Projekt wieder ein, wenn der Agent `composer` nie starten soll |
| `shell(npm:*)` in `deny_tools` | `shell(npm install:*)`, `shell(npm i:*)`, `shell(npm ci:*)`, `shell(npm exec:*)` |
| `project_key`, `jira.approver_account_ids`, `jira.factory_account_id`, `jira.status`, `jira.transition`, `bitbucket`, `composer_install`, `workspace_exclude`, `max_patch_bytes`, `run2_editable_re` je Framework | Entfallen. `local.py` las sie nie, `agentic-factory.py` auch nicht. Nur die Pipeline von factory-base braucht sie |
| – | Neu in `config.json`: `read_tools`, die Blöcke `clarify` und `init`, je Framework `revise_prompt` und `amend_prompt` |
| `readiness.md` | Bleibt. Die Vorlage hat dieselben Kriterien, mit Beispielen ohne Stack |

Die Pfade von Symfony und PHP, wie factory-base sie hatte, zum Einfügen in `protected_paths`:

```json
"^bin/",
"^phpunit(\\.dist)?\\.xml(\\.dist)?$",
"^phpstan[^/]*\\.neon$",
"^\\.php-cs-fixer[^/]*$",
"^composer\\.(json|lock)$",
"^symfony\\.lock$",
"^package(-lock)?\\.json$",
"^importmap\\.php$",
"^tests/bootstrap\\.php$",
"^config/packages/",
"^config/bundles\\.php$"
```

### B: von der früheren `agentic-factory.py`

Ihr habt die frühere Vorlage in `factory/` kopiert, mit `regeln/` und mit `test_command` in `local.json`. Am Weg zu Jira ändert sich nichts.

1. Committet alles. `git status` zeigt danach nichts mehr.
2. Schreibt auf, was ihr übernehmt: `test_command` und `stack_hint` aus `factory/local.json`, den Text der Dateien in `factory/regeln/`, dazu eure Änderungen an `factory/config.json`. Die frühere Vorlage zeigt `git show 414cf25:02-agent-factory/einrichtung/factory/config.json` im Workshop-Repo. Speichert sie, etwa als `config-alt.json`, und vergleicht: `diff config-alt.json factory/config.json`.
3. Entfernt den alten Code und die Regeln, dann kopiert die Vorlage:

   Löscht `agentic_factory/` vorher, sonst bleibt das alte `rules.py` liegen. Die Befehle tun das:

   ```bash
   rm -rf factory/agentic_factory factory/regeln factory/tests
   cp -R <dieser Ordner>/{agentic_factory,agentic-factory-plugin} factory/
   cp <dieser Ordner>/{agentic-factory.py,config.json,local.example.json} factory/
   cp -R <dieser Ordner>/tests factory/     # optional
   ```

   `config.json` ersetzt ihr. Für `readiness.md` gilt dasselbe wie in A, Schritt 3.
4. Startet das Skript einmal ohne Copilot-Aufruf: `python3 -I factory/agentic-factory.py init --print-only`. Mit der alten `local.json` stoppt es mit Exit-Code 2, etwa so:

   ```text
   [agentic-factory] STOP: …/factory/local.json: stack_hint moved to AGENTS.md (describe the stack there), test_command moved to config.json (key test_command); remove it from local.json
   ```

   Habt ihr die alte `config.json` behalten, stoppt es danach mit `config.json has a rules block: team rules were removed; move them to AGENTS.md`. Löscht ihr nur den Block `rules`, stoppen `build` und `init` danach mit `test_command must be a string such as "make test"`: Die alte Datei hat `test_command` als Liste. Nehmt deshalb die neue `config.json`.
5. Tragt die Werte um, wie die Tabelle unten sagt. `test_command` kommt als Text in `config.json`. Den Text von `stack_hint`, `regeln/code.md` und `regeln/stil.md` schreibt ihr in `AGENTS.md`. `regeln/ticket.md` ging in die Bereitschaftsprüfung und in `clarify`, als Kriterium `team_rules`. Soll eine Regel ein Ticket weiter „nicht bereit“ machen, schreibt sie als Kriterium mit eigener ID in `readiness.md`. Sonst gehört sie in `AGENTS.md`. Löscht `test_command` und `stack_hint` aus `local.json`. Eure Änderungen an `config.json` übertragt ihr von Hand in die neue Datei.
6. Startet `python3 -I factory/agentic-factory.py init --print-only` noch einmal. Jetzt zeigt es den Copilot-Befehl und endet mit Exit-Code 0.
7. Startet `init`, lest den Bericht, dann `init --apply` und `git diff factory/`. Wie in A, Schritt 7.
8. Prüft ohne Jira, wie in A, Schritt 9: erst mit `--print-only`, dann ohne.
9. Committet `factory/` und `AGENTS.md`.

| Alter Schlüssel | Neuer Ort |
|---|---|
| `local.json` `test_command` | `config.json` `test_command`, als Text. Die Freigabe ist jetzt der ganze Befehl, nicht nur sein erstes Wort |
| `local.json` `stack_hint` | `AGENTS.md` |
| `local.json` `model`, `copilot`, `jira_mcp_server`, `jira_site` | Bleiben in `local.json` |
| `regeln/code.md`, `regeln/stil.md` | `AGENTS.md` |
| `regeln/ticket.md` | `readiness.md` als Kriterium, wenn sie ein Ticket „nicht bereit“ machen soll. Sonst `AGENTS.md` |
| `config.json` Block `rules` | Entfällt. Steht er noch da, stoppt das Skript |
| `config.json` `test_command`: `["./bin/phpunit"]` | `config.json` `test_command` als Text, zum Start leer |
| `./bin/phpunit` in `build_rules` und `build_tools` | Der Platzhalter `{test_command}`. Die Freigabe hängt das Skript an |
| Die Pfade von Symfony und PHP in `protected_paths`, `shell(composer:*)` und `shell(npm:*)` in `deny_tools` | Wie in A |
| `project_key`, `jira.approver_account_ids`, `jira.factory_account_id`, `jira.status`, `jira.transition`, `bitbucket`, `composer_install`, `workspace_exclude`, `max_patch_bytes`, `run2_editable_re` je Framework | Entfallen. Die frühere Vorlage las sie nie |
| – | Neu in `config.json`: `read_tools`, der Block `init`, je Framework `revise_prompt` und `amend_prompt` |
| `readiness.md` | Bleibt. Die Vorlage hat dieselben Kriterien, mit Beispielen ohne Stack |

### Was danach anders läuft

- **Das Skript postet (A).** Jeder Lauf mit einem Ticket aus Jira liest das Ticket mit allen Kommentaren. `spec`, `build` und `clarify` posten ihr Ergebnis als `[KI]`-Kommentar unter eurem Konto, `assess` nur bei „nicht bereit“. Wollt ihr nur lesen, nehmt `--no-post`. Ganz ohne Jira geht es mit `--ticket-file`.
- **Der Standardweg ist der Jira-MCP (A).** Wollt ihr REST wie bei `local.py`, gebt `--jira api` an.
- **Ein neuer Lauf überarbeitet.** Startet ihr `spec` oder `build` noch einmal, nimmt das Skript die neuen `[Mensch]`-Kommentare und eure Änderungen an der Spec. Gibt es beides nicht, meldet es `nothing new since comment …`, postet nichts und endet mit Exit-Code 0. Ganz neu anfangen: `--fresh`.
- **`spec` lehnt nach einem Build ab:** `a build exists for LL-123 (comment …); give feedback through build, or run spec --fresh`.
- **Tickets aus der früheren Vorlage (B).** Ein Spec-Kommentar von damals hat keine `Spec-Prüfsumme`. Eine Überarbeitung klappt trotzdem. Änderungen von Hand erkennt das Skript dann aber nicht: `note: comment … has no Spec-Prüfsumme, so hand edits since then can't be told`. Die Kopie der Spec fehlt auch, der Kommentar zeigt die ganze Spec ohne Diff. Ein Build-Kommentar von damals hat keinen `Start-Commit`. Ein neuer `build` stoppt deshalb: `the build comment … names no Start-Commit, so the first build can't be found; run build --fresh`.
- **Alte Schlüssel stoppen.** `test_command` oder `stack_hint` in `local.json` stoppen jeden Lauf, wie in Schritt 4. Ein Block `rules` in `config.json` auch (B).
- **`build` braucht `test_command`.** Ohne ihn stoppt er mit `set test_command in config.json (or run init)`.
- **Die Freigabe für den Testbefehl ist enger:** `shell(make test:*)` statt `shell(make:*)`. Weil sie auf `:*` endet, darf der Agent aber Argumente anhängen.
- **`spec` und `build` dürfen lesende Befehle starten:** die `read_tools`, also `ls`, `cat`, `head`, `tail`, `wc`, `grep`, `pwd`, `diff`, `stat` und `cd`.
- **`npm test` geht jetzt.** `npm install` bleibt verboten. `composer` verbietet die Vorlage nicht mehr.
- **Abgelehnte Aufrufe sammeln sich** in `~/.factory-local/<repo>/blocked.jsonl`. Gebt die Datei an `init` oder an die Person, die `config.json` pflegt.
