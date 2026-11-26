# Änderungen und Umstieg

Diese Seite nennt die Änderungen an `agentic-factory.py` gegenüber `local.py` und der früheren Vorlage. Sie zeigt auch, wie ihr ein Projekt umstellt. Die Bedienung steht in der [README](README.md).

- **Stand:** 25. November 2026, Copilot CLI 1.0.115.
- **`local.py`:** `factory/local.py` im Lab-Repo [factory-lab](https://bitbucket.org/factory-lab/factory-lab/src/factory-base/factory/local.py), Branch `factory-base`, Commit `a414237`. Daneben liegen `config.json`, `local.example.json` und `readiness.md`.
- **Die frühere Vorlage:** dieser Ordner im Commit `414cf25` des Workshop-Repos, mit `regeln/` und `test_command` in `local.json`.

## Was sich gegenüber `local.py` geändert hat

`local.py` war eine Datei mit drei Modi: `assess`, `spec` und `build`. Es las Tickets per REST aus Jira und schrieb nie in Jira. `test_command`, `stack_hint`, `model` und `copilot` nahm es aus `local.json`.

### Aufbau

| Vorher | Jetzt |
|---|---|
| Eine Datei, `local.py`, 704 Zeilen | Starter `agentic-factory.py` und Paket `agentic_factory/`, ein Modul pro Teil. Fehlt das Paket, stoppt der Starter mit Exit-Code 2 |
| Tests in `test_local.py` | Tests in `tests/`, eine Datei pro Modul |
| – | Ordner `agentic-factory-plugin/` mit dem Hook für die Jira-Aufrufe |
| Ausgaben beginnen mit `[local]` | Ausgaben beginnen mit `[agentic-factory]` |

### Modi und Optionen

| Vorher | Jetzt |
|---|---|
| `assess`, `spec`, `build` | Neu: `clarify` klärt ein Ticket in Runden von Kommentaren. `init` schlägt aus der Doku des Projekts Änderungen an `config.json` und `readiness.md` vor |
| Jeder Lauf von `spec` und `build` startet wie der erste | Ein neuer Lauf überarbeitet Spec oder Code nach `[Mensch]`-Kommentaren und Änderungen von Hand, siehe [Feedback](#feedback). `--fresh` startet wie beim ersten Mal |
| `build --framework …` liest kein Ticket | `build` liest immer ein Ticket, aus Jira oder aus `--ticket-file` |
| Optionen `--key`, `--ticket-file`, `--framework`, `--change`, `--no-assess`, `--print-only`, `--config`, `--local`, `--readiness` | Bleiben. `--repo` ist weg: Das Projekt ist das Repository um `factory/`. Neu: `--jira`, `--comments-file`, `--no-post`, `--apply`, `--fresh`, `--step`, `--io-dir` |
| `--key LL-123` nennt das Ticket | Neu: Ticket direkt nach dem Modus, als Schlüssel oder Jira-URL: `spec LL-123` oder `spec https://example.atlassian.net/browse/LL-123`. Der Host der URL muss zu `jira_site` oder `JIRA_BASE_URL` passen. `--key` bleibt als lange Form |
| Exit-Codes 0, 2, 4 (nicht bereit) und 5 (Fragen) | Neu: 6, `clarify` hat seine Grenze an Runden erreicht |

### Jira

| Vorher | Jetzt |
|---|---|
| Liest Zusammenfassung, Beschreibung, Labels und Status | Liest auch alle Kommentare |
| Schreibt nie in Jira | Postet das Ergebnis als Kommentar mit `[KI]` am Anfang: `assess` bei „nicht bereit“, `clarify`, `spec` und `build`. `clarify --apply` setzt die Beschreibung. Mit `--ticket-file` oder `--no-post` landet der Kommentar nur in einer Datei |
| Ein Weg: REST mit `JIRA_BASE_URL`, `JIRA_API_TOKEN` und für Jira Cloud `JIRA_EMAIL` | Zwei Wege. `--jira mcp` (Standard außerhalb einer Pipeline): euer Jira-MCP-Server in Copilot, nur Jira Cloud. `--jira api` (Standard in einer Pipeline): REST mit denselben Variablen wie vorher |
| – | Über MCP ist jeder Jira-Aufruf ein eigener, kurzer Copilot-Aufruf mit genau einem Werkzeug. Danach prüft das Skript ihn in den Ereignissen von Copilot. Einen geposteten Kommentar liest es zurück. Der Hook in `agentic-factory-plugin/` soll nur den erwarteten Aufruf durchlassen. Copilot 1.0.115 führt ihn aber nicht aus |

### Pipeline

| Vorher | Jetzt |
|---|---|
| Nur lokal, ein Prozess | Drei Schritte: `fetch`, `agent` und `post`. Sie tauschen Daten über einen Ordner mit `in/` und `out/`. Lokal laufen sie in einem Prozess, in einer Pipeline getrennt: `fetch` und `post` mit den Jira-Daten, `agent` nur mit dem Copilot-Token. Sieht ein Schritt das Token des anderen, stoppt er |
| – | [`pipelines.example.yml`](pipelines.example.yml) mit den Pipelines `agentic-clarify` und `agentic-assess` |
| – | In einer Pipeline lehnt das Skript `build` und `init` ab |

### Konfiguration

| Vorher | Jetzt |
|---|---|
| Die `config.json` des Labs: Symfony und PHP, `./bin/phpunit` und die Schlüssel der Pipeline von factory-base | Ohne Annahmen über euren Stack. Die Schlüssel nur für die Pipeline sind weg. Die Tabelle in [A: von `local.py`](#a-von-localpy) nennt jeden |
| `test_command` in `config.json` als Liste `["./bin/phpunit"]`. `local.json` kann es als Text überschreiben | `test_command` steht nur in `config.json`, als Text, zum Start leer. Ohne ihn stoppt `build` |
| Die Freigabe für den Testbefehl ist sein erstes Wort: Aus `make test` wird `shell(make:*)` | Die Freigabe ist der ganze Befehl als Anfang. Der Befehl hat ein Wort, etwa `./run-tests`, oder zwei bei `npm`, `yarn` und `go`, etwa `npm test`. Längere Befehle passt Copilot nie. Für `make test` schreibt ihr ein Skript. Vor jedem Build prüft das Skript den Befehl, etwa auf `bash -c` oder `&&`. Siehe [Der Testbefehl](README.md#der-testbefehl) |
| `build_rules` und jede Liste `build_tools` nennen `./bin/phpunit` | `build_rules` hat den Platzhalter `{test_command}`. `build_tools` nennt keinen Testbefehl, das Skript hängt ihn an |
| `stack_hint` in `local.json` ersetzt „Use the existing Symfony 7 / PHP stack and PHPUnit“ im Plan-Prompt von Spec Kit | Der Plan-Prompt sagt „Use the existing stack and test setup; no new dependencies.“ Euren Stack beschreibt ihr in `AGENTS.md` |
| `local.json`: `test_command`, `stack_hint`, `model`, `copilot` | `local.json`: `model`, `copilot`, `jira_mcp_server`, `jira_site`. Ein alter Schlüssel stoppt das Skript |
| `deny_tools` verbietet `composer` und `npm` ganz | `deny_tools` verbietet `npm install`, `npm i`, `npm ci` und `npm exec`, sonst liefe `npm test` nicht. `composer` verbietet die Vorlage nicht mehr |
| `protected_paths` mit Pfaden von Symfony und PHP | Nur allgemeine Pfade. `init` schlägt Pfade für euren Stack vor |
| – | Neu: `read_tools` mit lesenden Befehlen wie `ls`, `cat` und `grep` für jeden Aufruf von `spec` und `build`. Die Blöcke `clarify`, `init`, je Framework `revise_prompt` und `amend_prompt` |
| `spec_rules` und `build_rules` nennen `AGENTS.md` nicht | Beide enden mit „Follow AGENTS.md in the repository root, if it exists, and the files it links to; where they conflict with these factory rules, these rules win.“ Das gilt auch für die Regeln der Bereitschaftsprüfung, von `clarify` und der amend-Aufrufe. Fehlt `spec_rules` oder `build_rules` in `config.json`, stoppt das Skript. Es nimmt nicht mehr die Regeln des Labs mit `./bin/phpunit` |
| `protected_paths`: `^AGENTS\.md$`, `^CLAUDE\.md$`, `^\.github/` | `(?i)(^\|/)(AGENTS\|CLAUDE\|GEMINI)\.md$` und `(?i)^\.github/`. Neu: `GEMINI.md` (Copilot lädt es auch), Unterordner und jede Schreibweise. Copilot lädt auch `agents.md`. Jedes Muster in `protected_paths` beginnt mit `(?i)`. Das Skript prüft alle Muster ohne Unterschied von Groß- und Kleinschreibung, auch die von `init`. Grund: Auf macOS ist `.Agents/` derselbe Ordner wie `.agents/` |
| `forbidden_flags` ohne `--no-custom-instructions` | `--no-custom-instructions` ist verboten, auch wenn eine alte `config.json` es nicht nennt |
| `readiness.md` mit Beispielen aus der Symfony-Demo, Status „Klärung nötig“ und Image | Dieselben Kriterien und IDs. Beispiele ohne Stack, ohne Status, ohne Image |

### Sicherheit

| Vorher | Jetzt |
|---|---|
| Die Bereitschaftsprüfung hat kein Shell-Werkzeug, verbietet die Shell aber nicht | Jeder Aufruf ohne Shell-Werkzeug bekommt `--deny-tool=shell`: Bereitschaftsprüfung, `clarify`, `init` und Jira-Aufrufe. Lief trotzdem ein Shell-Befehl, stoppt das Skript |
| Eure MCP-Server sind in jedem Aufruf aus | Wie vorher. Nur ein Jira-Aufruf über MCP lässt euren Jira-Server an |
| Das Skript prüft das Urteil der Bereitschaftsprüfung auf seine Form | Auch auf Länge, Anzahl und unsichtbare Zeichen, wie `assess.py` der Pipeline |
| – | Vor dem Posten prüft das Skript jeden Kommentar: Tokens, unsichtbare Zeichen, Links außerhalb von Code-Blöcken, Länge, `FACTORY-` und den Anfang `[KI]` |
| – | Vor dem ersten Aufruf prüft das Skript `test_command` und `read_tools`. Trifft ein Eintrag in `deny_tools` sie, stoppt es |
| – | `init` darf nur lesen. Seine Vorschläge dürfen nur hinzufügen oder verschärfen. Das Skript prüft jeden Vorschlag. `init --apply` schreibt das gespeicherte Ergebnis des letzten Laufs, ohne neuen Aufruf |
| `git status` nach jedem Aufruf mit der Konfiguration des Repos | Jeder `git`-Aufruf des Skripts läuft ohne fsmonitor, Hooks, externen Diff und Pager. Ändert ein Arbeitsaufruf `.git/config`, die Hooks oder eingebundene Dateien, stoppt das Skript vor dem nächsten `git`-Befehl |
| – | Vor jedem Lauf nennt das Skript Nummer und Konto der `[Mensch]`-Kommentare, die es liest. `blocked.jsonl` schwärzt bekannte Tokens. Sehen die Ereignisse von Copilot anders aus als bei 1.0.115, warnt das Skript |

### Feedback

Neu: `[Mensch]`-Kommentare im Ticket und Änderungen von Hand an den Spec-Dateien steuern einen neuen Lauf. Vor dem ersten Build überarbeitet `spec` die Spec. Danach macht `build` aus den Kommentaren neue Aufgaben und setzt sie um. `spec` lehnt dann ab. Mehr: [Feedback zu Spec und Build](README.md#feedback-zu-spec-und-build).

### Protokolle

| Vorher | Jetzt |
|---|---|
| Ein Ordner pro Lauf, `~/.factory-local/<repo>/<zeit>-<modus>-<key>/`, mit Ereignissen und Verbrauch jedes Aufrufs | Wie vorher, dazu `io/` mit `in/` und `out/` |
| Abgelehnte Aufrufe stehen nur in der Ausgabe, als `DENIED` | Dazu sammelt [`blocked.jsonl`](README.md#blockierte-aufrufe-blockedjsonl) sie für alle Läufe, in `~/.factory-local/<repo>/`. Jeder Lauf mit Copilot-Aufrufen endet mit einer Zeile dazu |
| – | In `~/.factory-local/<repo>/specs/` eine Kopie der Spec nach jedem Lauf von `spec` und `build`. Mit ihr berechnet das Skript den Diff eurer Änderungen von Hand |
| – | `init-result.json` im Ordner eines `init`-Laufs: das geprüfte Ergebnis für `init --apply` |

### Was gleich geblieben ist

- **Prompts und Flags** baut das Skript wie `agent.py` von factory-base. Tests vergleichen beides mit einer Konfiguration wie der des Labs, siehe [Tests](README.md#tests). Die `config.json` der Vorlage weicht nur hier ab:
  - der Plan-Prompt von Spec Kit,
  - `{test_command}` in `build_rules`,
  - der Satz zu `AGENTS.md` am Ende von `spec_rules`, `build_rules` und den Regeln der Bereitschaftsprüfung,
  - die Freigabe für den Testbefehl, `read_tools` und `deny_tools`,
  - die geschützten Pfade im Prompt der Bereitschaftsprüfung,
  - die Wörter für Teile des Codes in diesem Prompt und in `readiness.md`: „modules, entry points, user interface, data model“ statt Begriffe aus Symfony.

  Neu sind die Prompts von `clarify`, `init`, `revise_prompt` und `amend_prompt`. `--deny-tool=shell` und `--disable-mcp-server` hängt das Skript nur hinten an.
- **Unverändert aus factory-base:** der Prompt der Bereitschaftsprüfung und `readiness.md`, bis auf die Wörter und den Satz zu `AGENTS.md` oben. Die IDs der Kriterien sind gleich. Dazu `spec_rules` bis auf den Satz zu `AGENTS.md`, `forbidden_flags` bis auf `--no-custom-instructions`, und `forbidden_env`. Das Modell `claude-sonnet-5.5`, 150 Credits pro Aufruf, 40 für die Bereitschaftsprüfung, 1200 Sekunden pro Aufruf.
- **Das Framework:** erst `--framework`, dann genau ein Label `sdd-*`, dann `default_framework`. Fehlt sein Ordner im Projekt, stoppt das Skript.
- **Die Bereitschaftsprüfung** läuft vor `spec`, wenn `assess.enabled` gilt. `--no-assess` überspringt sie.
- **Die Umgebung:** Copilot bekommt eure Umgebungsvariablen ohne die drei Jira-Variablen, dazu dieselben Sicherheits-Variablen.
- **Nach dem Lauf:** die Liste der Änderungen und Warnungen bei geschützten Pfaden und bei Dateien außerhalb des Spec-Ordners. Kein Container, kein eigener Benutzer, kein Prüfschritt. `git diff` lest ihr selbst.
- **Die Dateien** `config.json`, `readiness.md` und `local.json` liest das Skript neben sich. Das Skript muss in `factory/` im Wurzelordner des Repos liegen. Starten könnt ihr es aus jedem Ordner.

### Gegenüber der früheren Vorlage

Die frühere `agentic-factory.py` hatte schon Kommentare in Jira, `clarify`, die drei Schritte und `--deny-tool=shell`. Neu seitdem:

- **Keine Regeln des Teams mehr:** `regeln/`, der Block `rules` in `config.json` und das Kriterium `team_rules` sind weg. Ein Block `rules` stoppt das Skript. Die Hinweise gehören in `AGENTS.md`.
- **`local.json` hat nur noch die Einstellungen eures Rechners:** `test_command` steht in `config.json`, den Stack beschreibt `AGENTS.md`.
- **`config.json` ohne Stack:** siehe [Konfiguration](#konfiguration). Die frühere Vorlage hatte noch die `config.json` des Labs.
- **Neu:** `init`, `blocked.jsonl`, `read_tools`, das Überarbeiten von Spec und Build, `--fresh`.
- **Die `[KI]`-Kommentare von `spec` und `build`** haben neue Zeilen: `Spec-Prüfsumme`, bei `build` auch `Start-Commit`, bei Überarbeitungen `Bearbeitet`. Neue Marker: `spec überarbeitung=<n>` und `build überarbeitung=<n>`.

### Nach dem OroCommerce-Test (26. November 2026)

Ein Test auf OroCommerce 7.0.4 mit echten Jira-Tickets zeigte Fehler. Die Folgen:

- **Der Ordner heißt `factory/`,** im Workshop-Repo und in eurem Projekt. Liegt das Skript nicht in `factory/` im Wurzelordner des Repos, stoppt es vor jedem Aufruf. `--repo` ist weg.
- **Der Testbefehl hat ein Wort, oder zwei bei `npm`, `yarn` und `go`.** Copilot CLI 1.0.115 passt `shell(make test:*)` nie. Im Test lief deshalb kein Test, aber der Build lief weiter. Jetzt stoppt `build` vor dem Aufruf. Für `make test` oder `uv run pytest` schreibt ein Skript wie `./run-tests`. `init` schlägt solche Befehle und Werkzeuge nicht mehr vor.
- **Abgelehnte Tests heißen so.** Lehnt Copilot den Testbefehl ab, sagt der Kommentar `abgelehnt, nicht ausgeführt` statt `fehlgeschlagen`. Das Skript warnt dann.
- **Die Marker von `clarify` zählen nur, wenn sie unbearbeitet sind und vom Konto der Runde 1 kommen.** Im Test hielt ein bearbeiteter Übergabe-Kommentar die Klärung an.
- **`build` nimmt den Change aus dem Spec-Kommentar,** wenn es mehrere Spec-Ordner gibt.
- **Eine abgelaufene Jira-Anmeldung** nennt das Skript jetzt beim Namen, statt `no result`.
- **`agent_timeout_s` beendet den ganzen Aufruf,** auch Prozesse, die Copilot gestartet hat. Im Test lief ein Aufruf 1.699 statt 1.200 Sekunden.
- **Die Doku nennt die Kosten:** `--print-only` und „nichts Neues“ kosten über den Jira-MCP die Jira-Aufrufe.


## Umsteigen

Beide Wege enden gleich: `factory/` hat die Dateien dieser Vorlage und eure Werte. `init` ist einmal gelaufen. Ein Testlauf ohne Jira hat geklappt. `<dieser Ordner>` steht für diesen Ordner im Workshop-Repo. Für den Testlauf braucht ihr eine Ticket-Datei, etwa `~/factory-tickets/LL-123.json`:

```json
{"key": "LL-123", "summary": "Tags klein schreiben", "description": "Beim Speichern sollen Tags klein geschrieben werden.", "labels": ["sdd-openspec"]}
```

### A: von `local.py`

Ihr habt `local.py` mit `config.json`, `readiness.md` und vielleicht `local.json` aus factory-base in `factory/` kopiert.

1. Committet alles. `git status` zeigt danach nichts mehr.
2. Notiert, was ihr übernehmt: `test_command` und `stack_hint` aus `factory/local.json` und eure Änderungen an `factory/config.json`. Das Original zeigt `git show a414237:factory/config.json` in einem Klon von factory-lab. Speichert es, etwa als `config-alt.json`, und vergleicht: `diff config-alt.json factory/config.json`.
3. Entfernt `local.py` und kopiert die Vorlage:

   ```bash
   rm factory/local.py                    # und factory/test_local.py, falls ihr es kopiert habt
   cp -R <dieser Ordner>/{agentic_factory,agentic-factory-plugin} factory/
   cp <dieser Ordner>/{agentic-factory.py,config.json,local.example.json} factory/
   ```

   Damit ersetzt ihr `config.json`. `readiness.md` der Vorlage hat dieselben Kriterien und IDs wie in factory-base, nur Beispiele ohne Symfony. Habt ihr eure Datei nicht geändert, kopiert die neue: `cp <dieser Ordner>/readiness.md factory/`. Sonst behaltet eure. Liegen in `factory/tests/` schon die Tests von factory-base, kopiert die Tests der Vorlage nicht dorthin: `test_readiness.py` gibt es in beiden.
4. Startet das Skript einmal ohne Copilot-Aufruf: `python3 -I factory/agentic-factory.py init --print-only`. Steht in `local.json` noch `test_command` oder `stack_hint`, stoppt es mit Exit-Code 2. Es sagt, wohin der Wert gehört, etwa so:

   ```text
   [agentic-factory] STOP: …/factory/local.json: stack_hint moved to AGENTS.md (describe the stack there), test_command moved to config.json (key test_command); remove it from local.json
   ```

5. Tragt die Werte um, wie die Tabelle unten sagt. `test_command` kommt als Text in `config.json`, etwa `"test_command": "./run-tests"`. Für `make test` schreibt ihr ein Skript, siehe [Der Testbefehl](README.md#der-testbefehl). Den Text von `stack_hint` schreibt ihr in `AGENTS.md`. Dann löscht ihr beide Schlüssel aus `local.json`. Eure Änderungen an `config.json` übertragt ihr von Hand in die neue Datei.
6. Startet `python3 -I factory/agentic-factory.py init --print-only` noch einmal. Jetzt zeigt es den Copilot-Befehl und endet mit Exit-Code 0.
7. Startet `init` ohne `--print-only` und lest den Bericht. Passt er, startet `init --apply`. Es schreibt genau diese Vorschläge in `config.json` und `readiness.md`, ohne neuen Aufruf. Der Lauf ohne `--apply` kostet bis zu 40 Credits, `--apply` kostet nichts. Dann `git diff factory/`. Mehr: [Erste Einrichtung mit `init`](README.md#erste-einrichtung-mit-init).
8. Richtet den Jira-MCP ein, einmal pro Rechner. Das ist neu für euch, `local.py` kannte nur REST:

   ```bash
   copilot mcp add --transport http atlassian https://mcp.atlassian.com/v1/mcp
   copilot          # dann /mcp, atlassian, „Authenticate“, im Browser anmelden, /exit
   ```

   Tragt eure Jira-Cloud-Adresse in `factory/local.json` ein, etwa `"jira_site": "https://example.atlassian.net"`. Bei Jira Data Center nehmt ihr `--jira api`, mit denselben Variablen wie bei `local.py`.

   Habt ihr den Server in Übung 1 mit einer Liste von Werkzeugen angelegt (`"tools": [...]` in `~/.copilot/mcp-config.json`)? Dann fehlen dort Werkzeuge für das Skript: `addCommentToJiraIssue` zum Posten, `editJiraIssue` für `clarify --apply` und `atlassianUserInfo` für `clarify --apply` und jeden weiteren Lauf von `spec` und `build`. Ergänzt sie. Oder löscht den Server mit `copilot mcp remove atlassian` und legt ihn mit dem Befehl oben neu an. Sonst kostet der erste Lauf Credits und stoppt erst beim Posten.
9. Prüft ohne Jira. Das Projekt braucht den Ordner des Frameworks aus dem Label der Ticket-Datei, hier `openspec/`. Sonst gebt ihr `--framework` an. Startet erst `python3 -I factory/agentic-factory.py spec --ticket-file ~/factory-tickets/LL-123.json --print-only`. Das zeigt die Copilot-Befehle und kostet nichts. Dann denselben Befehl ohne `--print-only`. Das kostet Credits. Das Skript fragt Jira nicht und postet nichts. Den Kommentar schreibt es in eine Datei, die letzte Zeile nennt sie. Danach liegt die Spec uncommittet im Projekt. Braucht ihr sie nicht, verwerft sie.
10. Committet `factory/` und `AGENTS.md`.

Läuft in eurem Repo die Pipeline von factory-base aus demselben Ordner `factory/`? Dann ersetzt `config.json` nicht. Die Pipeline nimmt die Datei in ihr Image auf und braucht ihre Schlüssel, etwa `project_key`, `bitbucket` und `test_command` als Liste. Mit dieser Liste stoppen `build` und `init` von `agentic-factory.py` aber vor dem ersten Copilot-Aufruf: `config.json: test_command must be a string such as "make test"; an old config has a list — write it as one string`. Legt die Vorlage dann in einen eigenen Ordner. Aber: Der Skill [`schreibe-ticket`](../../werkzeuge/schreibe-ticket/README.md) sucht sie in `factory/`.

| Alter Schlüssel | Neuer Ort |
|---|---|
| `local.json` `test_command`, etwa `"make test"` | `config.json` `test_command` als Text: ein Skript wie `./run-tests`, das `make test` startet. Freigabe: `shell(./run-tests:*)` statt `shell(make:*)` |
| `local.json` `stack_hint` | `AGENTS.md` |
| `local.json` `model`, `copilot` | Bleiben in `local.json` |
| – | `local.json` `jira_mcp_server` (Standard `atlassian`) und `jira_site`, für `--jira mcp` |
| `JIRA_BASE_URL`, `JIRA_API_TOKEN`, `JIRA_EMAIL` in der Umgebung | Bleiben, für `--jira api`. Fehlt `jira_site`, gilt `JIRA_BASE_URL` auch für `--jira mcp` |
| `config.json` `test_command`: `["./bin/phpunit"]` | `config.json` `test_command` als Text, zum Start leer |
| `./bin/phpunit` in `build_rules` | Der Platzhalter `{test_command}` |
| `shell(./bin/phpunit:*)` in jeder Liste `build_tools` | Entfällt: Das Skript hängt den Testbefehl an |
| Symfony und PHPUnit im Plan-Prompt von Spec Kit | `AGENTS.md` |
| Die Pfade von Symfony und PHP in `protected_paths` | Entfallen. Für ein Symfony-Projekt tragt sie wieder ein, von Hand oder per `init`. Die Liste steht unten |
| `shell(composer:*)` in `deny_tools` | Entfällt. Für ein PHP-Projekt tragt es wieder ein, wenn der Agent `composer` nie starten soll |
| `shell(npm:*)` in `deny_tools` | `shell(npm install:*)`, `shell(npm i:*)`, `shell(npm ci:*)`, `shell(npm exec:*)` |
| `project_key`, `jira.approver_account_ids`, `jira.factory_account_id`, `jira.status`, `jira.transition`, `bitbucket`, `composer_install`, `workspace_exclude`, `max_patch_bytes`, `run2_editable_re` je Framework | Entfallen. `local.py` las sie nie, `agentic-factory.py` auch nicht. Nur die Pipeline von factory-base braucht sie |
| – | Neu in `config.json`: `read_tools`, die Blöcke `clarify` und `init`, je Framework `revise_prompt` und `amend_prompt` |
| `readiness.md` | Bleibt. Die Vorlage hat dieselben Kriterien, mit Beispielen ohne Stack |

Die Pfade von Symfony und PHP aus factory-base, zum Einfügen in `protected_paths`:

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

Ihr habt die frühere Vorlage in `factory/` kopiert, mit `regeln/` und `test_command` in `local.json`. Der Weg zu Jira bleibt gleich.

1. Committet alles. `git status` zeigt danach nichts mehr.
2. Notiert, was ihr übernehmt: `test_command` und `stack_hint` aus `factory/local.json`, den Text der Dateien in `factory/regeln/` und eure Änderungen an `factory/config.json`. Die frühere Vorlage zeigt `git show 414cf25:02-agent-factory/einrichtung/factory/config.json` im Workshop-Repo. Speichert sie, etwa als `config-alt.json`, und vergleicht: `diff config-alt.json factory/config.json`.
3. Entfernt den alten Code und die Regeln, dann kopiert die Vorlage. Löscht `agentic_factory/` vorher, sonst bleibt das alte `rules.py` liegen. Die Befehle tun das:

   ```bash
   rm -rf factory/agentic_factory factory/regeln factory/tests
   cp -R <dieser Ordner>/{agentic_factory,agentic-factory-plugin} factory/
   cp <dieser Ordner>/{agentic-factory.py,config.json,local.example.json} factory/
   cp -R <dieser Ordner>/tests factory/     # optional
   ```

   Damit ersetzt ihr `config.json`. Für `readiness.md` gilt A, Schritt 3.
4. Startet das Skript einmal ohne Copilot-Aufruf: `python3 -I factory/agentic-factory.py init --print-only`. Mit der alten `local.json` stoppt es mit Exit-Code 2 und der Meldung aus A, Schritt 4.

   Habt ihr die alte `config.json` behalten, stoppt es danach mit `config.json has a rules block: team rules were removed; move them to AGENTS.md`. Löscht ihr nur den Block `rules`, stoppen `build` und `init` danach mit `test_command must be a string such as "make test"`. Denn die alte Datei hat `test_command` als Liste. Nehmt deshalb die neue `config.json`.
5. Tragt die Werte um, wie die Tabelle unten sagt. `test_command` kommt als Text in `config.json`. Den Text von `stack_hint`, `regeln/code.md` und `regeln/stil.md` schreibt ihr in `AGENTS.md`. `regeln/ticket.md` ging als Kriterium `team_rules` in die Bereitschaftsprüfung und in `clarify`. Soll eine Regel ein Ticket weiter „nicht bereit“ machen, schreibt sie als Kriterium mit eigener ID in `readiness.md`. Sonst gehört sie in `AGENTS.md`. Löscht `test_command` und `stack_hint` aus `local.json`. Eure Änderungen an `config.json` übertragt ihr von Hand in die neue Datei.
6. Startet `python3 -I factory/agentic-factory.py init --print-only` noch einmal. Jetzt zeigt es den Copilot-Befehl und endet mit Exit-Code 0.
7. Startet `init`, lest den Bericht, dann `init --apply` und `git diff factory/`. Wie in A, Schritt 7.
8. Prüft ohne Jira, wie in A, Schritt 9: erst mit `--print-only`, dann ohne.
9. Committet `factory/` und `AGENTS.md`.

| Alter Schlüssel | Neuer Ort |
|---|---|
| `local.json` `test_command` | `config.json` `test_command` als Text. Die Freigabe ist jetzt der ganze Befehl, nicht nur sein erstes Wort |
| `local.json` `stack_hint` | `AGENTS.md` |
| `local.json` `model`, `copilot`, `jira_mcp_server`, `jira_site` | Bleiben in `local.json` |
| `regeln/code.md`, `regeln/stil.md` | `AGENTS.md` |
| `regeln/ticket.md` | `readiness.md` als Kriterium, wenn sie ein Ticket „nicht bereit“ machen soll. Sonst `AGENTS.md` |
| `config.json` Block `rules` | Entfällt. Steht er noch da, stoppt das Skript |
| `config.json` `test_command`: `["./bin/phpunit"]` | `config.json` `test_command` als Text, zum Start leer |
| `./bin/phpunit` in `build_rules` und `build_tools` | Der Platzhalter `{test_command}`. Die Freigabe hängt das Skript an |
| Die Pfade von Symfony und PHP in `protected_paths`, `shell(composer:*)` und `shell(npm:*)` in `deny_tools` | Wie in A |
| Die Schlüssel der Pipeline, `project_key` bis `run2_editable_re`, wie in A | Entfallen. Die frühere Vorlage las sie nie |
| – | Neu in `config.json`: `read_tools`, der Block `init`, je Framework `revise_prompt` und `amend_prompt` |
| `readiness.md` | Bleibt, wie in A |

### Was danach anders läuft

- **Das Skript postet (A),** unter eurem Konto, siehe [Jira](#jira). Nur lesen: `--no-post`. Ganz ohne Jira: `--ticket-file`.
- **Der Standardweg ist der Jira-MCP (A).** Für REST wie bei `local.py` gebt `--jira api` an.
- **Ein neuer Lauf überarbeitet,** siehe [Feedback](#feedback). Gibt es keine neuen `[Mensch]`-Kommentare und keine Änderungen an der Spec, meldet es `nothing new since comment …`, postet nichts und endet mit Exit-Code 0. Neu anfangen: `--fresh`.
- **`spec` lehnt nach einem Build ab:** `a build exists for LL-123 (comment …); give feedback through build, or run spec --fresh`.
- **Tickets aus der früheren Vorlage (B).** Ein alter Spec-Kommentar hat keine `Spec-Prüfsumme`. Eine Überarbeitung klappt trotzdem. Aber Änderungen von Hand erkennt das Skript dann nicht: `note: comment … has no Spec-Prüfsumme, so hand edits since then can't be told`. Auch die Kopie der Spec fehlt. Der Kommentar zeigt dann die ganze Spec ohne Diff. Ein alter Build-Kommentar hat keinen `Start-Commit`. Ein neuer `build` stoppt deshalb: `the build comment … names no Start-Commit, so the first build can't be found; run build --fresh`.
- **Alte Schlüssel stoppen jeden Lauf:** `test_command` oder `stack_hint` in `local.json` (Schritt 4), ein Block `rules` in `config.json` (B).
- **`build` braucht `test_command`.** Ohne ihn stoppt er mit `set test_command in config.json (or run init)`.
- **Die Freigabe für den Testbefehl ist enger:** `shell(./run-tests:*)` statt `shell(make:*)`. Zur Länge des Befehls siehe [Konfiguration](#konfiguration). Die Freigabe endet auf `:*`, also darf der Agent Argumente anhängen. Euer Skript ignoriert sie.
- **`spec` und `build` dürfen lesende Befehle starten:** die `read_tools`, also `ls`, `cat`, `head`, `tail`, `wc`, `grep`, `pwd`, `diff`, `stat` und `cd`.
- **`npm test` geht jetzt.** `npm install` bleibt verboten. Zu `composer` siehe [Konfiguration](#konfiguration).
- **Abgelehnte Aufrufe sammeln sich** in `~/.factory-local/<repo>/blocked.jsonl`. Gebt die Datei an `init` oder an die Person, die `config.json` pflegt.
