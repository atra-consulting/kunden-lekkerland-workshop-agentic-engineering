# Vorlage: die Factory-Schritte lokal mit `agentic-factory.py`

Mit diesen Dateien startet ihr die Copilot-Aufrufe der Factory im eigenen Projekt, mit jedem Stack. `agentic-factory.py` hieß früher `local.py`. Es kennt fünf Modi:

| Modus | Was er tut |
|---|---|
| `init` | Die Doku des Projekts lesen und Änderungen an `config.json` und `readiness.md` vorschlagen |
| `assess` | Bereitschaft prüfen |
| `clarify` | Ein Ticket in Runden von Kommentaren klären, bis es bereit ist |
| `spec` | Bereitschaft prüfen, dann die Spec schreiben. Noch einmal gestartet: die Spec nach Kommentaren und Änderungen von Hand überarbeiten |
| `build` | Die Spec umsetzen. Noch einmal gestartet: den Code nach Kommentaren und Änderungen an der Spec nachbessern |

Neu gegenüber `local.py`: Das Skript liest die Kommentare des Tickets und schreibt selbst Kommentare. Jeder beginnt mit `[KI]`. Lokal geht es über euren Jira-MCP-Server (`--jira mcp`), in einer Pipeline per API-Token (`--jira api`). Die Anleitung: [Factory-Schritte lokal ausführen](../../bedienung/lokal-ausfuehren.md) und [Übung 1](../../../01-erstworkshop/tag-2/uebung-factory-lokal.md). Was sich gegenüber `local.py` und der früheren Vorlage geändert hat und wie ihr umsteigt, steht in [`aenderungen.md`](aenderungen.md). Wie das Skript gebaut ist, welche Leitplanken es hat und welche Datei was tut, steht in [`aufbau.md`](aufbau.md).

- **Quelle:** angepasst aus `local.py` im Lab-Repo [factory-lab](https://bitbucket.org/factory-lab/factory-lab/src/factory-base/factory/), Branch `factory-base`, Commit `a414237`, Ordner `factory/`. Es ist keine unveränderte Kopie mehr.
- **Stand:** 25. November 2026, Copilot CLI 1.0.115, Modell `claude-sonnet-5.5`.

| Datei | Wozu | Nötig? |
|---|---|---|
| [`agentic-factory.py`](agentic-factory.py) | Das Programm, nur ein Starter: Es lädt den Code aus `agentic_factory/` neben sich. Nur Python-Standardbibliothek. Außer seinem Paket `agentic_factory/` importiert es nichts aus der Factory | Ja |
| [`agentic_factory/`](agentic_factory/) | Der Code, ein Modul pro Teil: Jira, Copilot-Aufrufe, Prüfungen, Klärung und die Schritte `fetch`, `agent`, `post`. Dazu `init.py` für `init`, `blocked.py` für `blocked.jsonl`, und `feedback.py`, `revise.py` und `snapshot.py` für das Überarbeiten von Spec und Build. Der Ordner muss **neben dem Skript** liegen | Ja |
| [`config.json`](config.json) | Prompts, Werkzeug-Freigaben, verbotene Befehle, Modell und Credit-Grenzen, für OpenSpec, Spec Kit und BMad. Ohne Annahmen über euren Stack. Darin auch: `test_command`, euer Testbefehl, zum Start leer; `read_tools`, die lesenden Befehle für `spec` und `build`; die Blöcke `clarify` und `init`; je Framework `revise_prompt` und `amend_prompt` für das Überarbeiten | Ja |
| [`readiness.md`](readiness.md) | Die Kriterien der Bereitschaftsprüfung. `clarify` nutzt sie auch. `init` kann Änderungen vorschlagen | Für `assess`, `clarify` und `spec` mit Bereitschaftsprüfung |
| [`local.example.json`](local.example.json) | Vorlage für `local.json`: nur die Einstellungen eures Rechners, also `model`, `copilot` (der Befehl, der Copilot startet), `jira_mcp_server` und `jira_site` | Nein. Ohne `local.json` gelten die Werte aus `config.json`. Für `--jira mcp` braucht ihr `jira_site` oder `JIRA_BASE_URL` |
| [`agentic-factory-plugin/`](agentic-factory-plugin/) | Der Hook für die Jira-Aufrufe über MCP: Er lässt nur den einen erwarteten Aufruf durch. Der Ordner muss **neben dem Skript** liegen. Das Skript lädt ihn von dort, nie aus `.github/` | Für `--jira mcp`. Copilot 1.0.115 führt ihn nicht aus, siehe [Sicherheit](#sicherheit-was-ihr-wissen-müsst) |
| [`pipelines.example.yml`](pipelines.example.yml) | Beispiel für Bitbucket Pipelines: `agentic-clarify` und `agentic-assess`, je mit den Schritten `fetch`, `agent` und `post` | Nein. Nur für die Pipeline |
| [`tests/`](tests/) | Die Tests, eine Datei pro Modul, siehe [Tests](#tests) | Nein |
| [`aenderungen.md`](aenderungen.md) | Was sich gegenüber `local.py` und der früheren Vorlage geändert hat, und wie ihr umsteigt | Nein |
| [`aufbau.md`](aufbau.md) | Ziel, Design, Leitplanken und Hooks der Vorlage, und welche Datei was tut | Nein |

Außerhalb des Projekts legt das Skript an, in `~/.factory-local/<repo>/`:

| Pfad | Was drin steht |
|---|---|
| `<zeit>-<modus>-<key>/` | Die Protokolle eines Laufs: Ereignisse und Verbrauch jedes Copilot-Aufrufs, dazu `io/` mit `in/` und `out/`. Bei `init` heißt der Ordner `<zeit>-init-INIT/` |
| `blocked.jsonl` | Was Copilot in allen Läufen abgelehnt hat, siehe [Blockierte Aufrufe](#blockierte-aufrufe-blockedjsonl) |
| `specs/<key>/<change>/<modus>-<n>/` | Eine Kopie der Spec-Dateien nach jedem Lauf von `spec` und `build`, siehe [Feedback zu Spec und Build](#feedback-zu-spec-und-build) |

## So nutzt ihr sie

Im Wurzelordner eures Repos:

```bash
mkdir -p factory
cp -R <dieser Ordner>/{agentic_factory,agentic-factory-plugin} factory/
cp <dieser Ordner>/{agentic-factory.py,config.json,readiness.md,local.example.json} factory/
cp -R <dieser Ordner>/tests factory/     # optional
cp factory/local.example.json factory/local.json
python3 -I factory/agentic-factory.py init     # Vorschläge lesen, dann mit --apply schreiben
python3 -I factory/agentic-factory.py spec --ticket-file ~/factory-tickets/LL-123.json --print-only
```

- Die Tests in `tests/` prüfen die Dateien der Vorlage. Ändert ihr `config.json`, schlagen einige fehl.
- `agentic-factory.py` liest `config.json`, `readiness.md` und `local.json` **neben sich**, nicht im aktuellen Ordner. Die Ordner `agentic_factory/` und `agentic-factory-plugin/` auch. Fehlt `agentic_factory/`, stoppt das Skript mit Exit-Code 2.
- Der Ordner heißt `factory/`, denn dort sucht der Skill [`schreibe-ticket`](../../werkzeuge/schreibe-ticket/README.md) `agentic-factory.py` und `readiness.md`.
- Euren Testbefehl tragt ihr in `config.json` ein, als `test_command`, etwa `"make test"`. `init` schlägt ihn vor. Ohne ihn stoppt `build` mit `set test_command in config.json (or run init)`. `assess`, `clarify` und `spec` brauchen ihn nicht. Was das Skript am Testbefehl prüft, steht unter [Der Testbefehl](#der-testbefehl).
- `local.json` hat nur noch die Einstellungen eures Rechners. Steht dort noch ein älterer Schlüssel, stoppt das Skript und sagt, wohin der Wert gehört, etwa `test_command moved to config.json (key test_command); remove it from local.json`.
- `--ticket-file` heißt offline: Das Skript fragt Jira nie und postet nichts. Der erste Lauf mit `--print-only` startet keinen Copilot-Aufruf und kostet nichts.
- Jira-Zugangsdaten gehören nie in `local.json`, nur in die Umgebung: `JIRA_BASE_URL`, `JIRA_API_TOKEN` und für Jira Cloud `JIRA_EMAIL`. Die braucht nur `--jira api`.

Für den Weg über den Jira-MCP, einmal pro Rechner:

```bash
copilot mcp add --transport http atlassian https://mcp.atlassian.com/v1/mcp
copilot          # dann /mcp, atlassian, „Authenticate“, im Browser anmelden, /exit
```

Dann in `factory/local.json` eure Jira-Cloud-Adresse eintragen, etwa `"jira_site": "https://example.atlassian.net"`. Fehlt `jira_site`, nimmt das Skript `JIRA_BASE_URL`. Jira Data Center hat keinen MCP-Weg: Nehmt dort `--jira api`. Alles Weitere steht in [Factory-Schritte lokal ausführen](../../bedienung/lokal-ausfuehren.md#jira-über-den-mcp-server).

Was `agentic-factory.py` mit diesen Dateien an Copilot schickt, zeigen die [Prompt-Beispiele](../prompt-beispiele/README.md).

### Der Testbefehl

`build` braucht `test_command` in `config.json`. Das Skript macht daraus zwei Dinge:

- **Die Regel im Prompt:** `Run the tests with exactly: make test.`
- **Eine Freigabe:** der ganze Befehl als Anfang, nicht nur das erste Wort. Aus `make test` wird `shell(make test:*)`, aus `npm test` wird `shell(npm test:*)`, aus `uv run pytest` wird `shell(uv run pytest:*)`. Das ist enger als `shell(make:*)` oder `shell(uv:*)`. Weil die Freigabe auf `:*` endet, darf der Agent aber Argumente anhängen, bei Make also auch weitere Ziele, etwa `make test deploy`.

Vor jedem Build-Aufruf prüft das Skript den Befehl. Es stoppt bei:

- Code direkt im Befehl, etwa `bash -c`, `sh -c`, `python3 -c` oder `node -e`,
- Zeichen der Shell, etwa `;`, `&&`, `|`, `$(`, `>`, und Anführungszeichen,
- einer Variablen davor, etwa `CI=1 make test`,
- einem Befehl ohne festes Ziel, etwa `python3` allein,
- Optionen eines Wrappers wie `timeout` oder `uv run`, die nicht die Form `--opt=value` haben,
- einem Befehl, den ein Eintrag in `deny_tools` trifft. Ein Verbot schlägt jede Freigabe.

Braucht euer Test mehr, schreibt ein Skript oder ein Make-Ziel und tragt das ein. Diese Prüfung fängt Fehler in der Konfiguration. Eine Sicherheitsgrenze ist sie nicht, siehe [Sicherheit](#sicherheit-was-ihr-wissen-müsst).

## Hinweise des Teams gehören in `AGENTS.md`

Regeln eures Teams, etwa „minimale Änderungen, kein Refactoring nebenbei“, schreibt ihr in `AGENTS.md` im Wurzelordner eures Repos. Copilot lädt die Datei in jedem Arbeitsaufruf selbst. Die Prompts der Factory nennen sie deshalb nicht. Dort beschreibt ihr auch euren Stack: Der Plan-Prompt von Spec Kit sagt nur noch „Use the existing stack and test setup; no new dependencies.“

- Einen Block `rules` in `config.json` gibt es nicht mehr. Hat eure `config.json` noch einen, stoppt das Skript: `config.json has a rules block: team rules were removed; move them to AGENTS.md`.
- `AGENTS.md` ist ein geschützter Pfad. Ändert der Agent die Datei, warnt das Skript nach dem Lauf.
- `init` liest `AGENTS.md` und die Dateien, auf die sie verlinkt.

## Erste Einrichtung mit `init`

`init` liest die Doku eures Projekts und schlägt Änderungen an `config.json` und `readiness.md` vor. Es braucht kein Ticket und kein Jira. Es läuft nur lokal: In einer Pipeline lehnt das Skript es ab.

```bash
python3 -I factory/agentic-factory.py init               # Bericht und Diff zeigen, nichts ändern
python3 -I factory/agentic-factory.py init --apply       # dasselbe, dann config.json und readiness.md schreiben
python3 -I factory/agentic-factory.py init --print-only  # nur den Copilot-Befehl zeigen, kein Aufruf
```

**Was der Aufruf liest.** Ein Copilot-Aufruf liest `AGENTS.md` und die Dateien, auf die sie verlinkt, `README*`, `CONTRIBUTING*`, `.github/copilot-instructions.md` und die Build-Dateien, etwa `Makefile`, `package.json`, `pom.xml`, `build.gradle*`, `pyproject.toml`, `go.mod` und `Cargo.toml`. Das Skript gibt ihm dazu mit:

- den Teil von `config.json`, den `init` ändern darf: Testbefehl, Frameworks, geschützte Pfade, verbotene Befehle und die Werkzeuge je Framework,
- `readiness.md`,
- die installierten Frameworks, also die Ordner `openspec/`, `.specify/` und `_bmad/`,
- eine Zusammenfassung von `blocked.jsonl`: wie oft welcher Befehl in welchem Modus abgelehnt wurde. Die Datei liegt außerhalb des Projekts, der Agent kann sie nicht selbst lesen.

**Wie der Aufruf läuft.** Er darf nur lesen: kein Schreiben, keine Shell, kein MCP-Server, höchstens 40 Credits (`init.max_ai_credits` in `config.json`). Er antwortet mit den Vorschlägen als JSON. Ändert er trotzdem eine Datei oder macht er einen Commit, stoppt das Skript und schlägt nichts vor.

**Was er vorschlagen kann.** Jeder Vorschlag hat einen Grund und eine Quelle, etwa `README.md:42` oder `blocked.jsonl`.

| Vorschlag | Was er ändert |
|---|---|
| `test_command` | Den Testbefehl |
| `add_tools` | Neue Werkzeuge je Framework, für `spec` oder `build` |
| `add_protected_paths` | Neue geschützte Pfade, als regulärer Ausdruck |
| `add_deny_tools` | Neue verbotene Befehle, etwa die Installationsbefehle eures Paketmanagers |
| `enabled_frameworks` | Die Frameworks, die ihr nutzt. Nur installierte |
| `readiness_md` | Den ganzen neuen Text von `readiness.md` |

**Was das Skript ablehnt.** Die Doku landet im Prompt und kann eine Prompt-Injection enthalten. Darum prüft das Skript jeden Vorschlag, bevor es ihn zeigt. `init` darf nur hinzufügen oder verschärfen:

- Es entfernt nie etwas aus `deny_tools` oder `protected_paths`. `forbidden_flags`, `forbidden_env`, `read_tools`, Prompts und Credit-Grenzen fasst es nicht an. Lockern ist Handarbeit.
- Diese Werkzeuge lehnt es ab: `shell` ohne Klammer, alles, was `deny_tools` verbietet, Shells und Interpreter (`bash`, `sh`, `python`, `node` und andere), Wrapper wie `env`, `timeout` oder `xargs`, Paket-Starter (`npx`, `uvx`, `npm exec` und andere), Netzwerk-Befehle (`curl`, `wget`, `ssh`, `scp`, `nc` und andere), jeden `git`-Befehl, und Befehle, die Dateien schreiben oder Befehle starten können: `find`, `sed`, `awk`, `rg`, `tree`, `sort`, `tar`, `docker`, `podman`.
- Paketmanager nimmt es nur mit Test- und Run-Befehlen an: `npm`, `pnpm`, `yarn`, `bun` mit `test`, `t`, `tst` oder `run`; `uv`, `poetry`, `pipenv`, `pdm`, `hatch`, `rye` mit `run`; `cargo` mit `test`, `build`, `check`, `clippy` oder `fmt`; `go` mit `test`, `build` oder `vet`; `composer` mit `test` oder `run-script`. Für `bundle`, `gem` und `pip` nichts. Davor stehen nur Optionen der Form `--opt=value`.
- Ein vorgeschlagener Testbefehl durchläuft dieselben Prüfungen wie einer von Hand, siehe [Der Testbefehl](#der-testbefehl). `uv run pytest` geht also, obwohl `shell(uv:*)` abgelehnt wäre.
- Geschützte Pfade: höchstens 200 Zeichen, ohne Leer- und Steuerzeichen, höchstens 20 neue pro Lauf.
- Ein neues Verbot darf keinen der `read_tools` und nicht den Testbefehl treffen.
- `readiness_md` muss jede bisherige Kriterium-ID behalten. Steuerzeichen und Zeichen für die Schreibrichtung lehnt das Skript ab.
- `enabled_frameworks` muss `default_framework` enthalten, wenn es gesetzt ist.

Abgelehnte Vorschläge zeigt der Bericht mit Grund. Er lässt sie nicht still weg. Breite Werkzeuge markiert er, etwa `shell(make:*)` mit „allows every Make target“.

**Was ihr seht.** Ohne `--apply`: den Bericht, dann einen Diff von `config.json` und `readiness.md`. Nichts ändert sich, Exit-Code 0. Mit `--apply` schreibt das Skript danach `config.json` und `readiness.md`, sonst nichts. Achtung: `--apply` startet einen neuen Aufruf. Seine Vorschläge können von denen des Laufs davor abweichen. Lest also den Bericht des Laufs mit `--apply`, dann `git diff`, und committet von Hand.

`init` läuft jederzeit wieder, etwa nachdem sich `blocked.jsonl` gefüllt hat. Es vergleicht immer mit den aktuellen Dateien.

## Blockierte Aufrufe: `blocked.jsonl`

Copilot läuft unbeaufsichtigt (`--no-ask-user`). Was nicht freigegeben ist, lehnt er ab. Der Agent sucht dann einen anderen Weg oder gibt auf. Das Skript sammelt diese Ablehnungen pro Projekt in einer Datei: `~/.factory-local/<repo>/blocked.jsonl`. Daraus passt ihr `config.json` an.

- **Was hineinkommt:** eine JSON-Zeile pro abgelehntem Werkzeug-Aufruf, aus jedem Arbeitsaufruf von `init`, `assess`, `clarify`, `spec` und `build`. `kind` ist `denied` (das Werkzeug steht nicht auf der Freigabe) oder `blocked` (Copilots eigener Schutz, die Meldung beginnt mit „Command blocked“). Normale Fehler, etwa „Parent directory does not exist“, kommen nicht hinein.
- **Was nicht hineinkommt:** die kurzen Jira-Aufrufe. Eine Ablehnung dort ist ein Sicherheitssignal, keine Lücke in der Konfiguration. Das Skript prüft diese Aufrufe selbst.
- **Die Felder:** `at`, `run` (der Protokoll-Ordner), `mode`, `framework`, `key`, `call` (der Aufruf), `tool`, `command` (der ganze Befehl), `kind`, `message` und `allowed` (die Freigabe des Aufrufs).
- **Die letzte Antwort:** Hatte ein Aufruf mindestens eine Ablehnung, folgt eine Zeile `{"kind": "final", "call": …, "text": …}` mit seiner letzten Antwort. Dort sagt der Agent meist, was er nicht tun konnte. Fragen, die er nicht stellen durfte, stehen nur dort oder in `FACTORY-QUESTIONS.md`.
- **Die Zeile am Ende jedes Laufs mit Copilot-Aufrufen:** etwa `[agentic-factory] 2 blocked call(s), see /home/anna/.factory-local/shop/blocked.jsonl`, sonst `[agentic-factory] no blocked calls`. Es gibt keinen Schalter dafür.

Ein Beispiel aus dem Lab, gekürzt:

```json
{"at": "2026-11-25T13:46:51+0100", "run": "20261125-134609-build-FLAB-41", "mode": "build", "framework": "openspec", "key": "FLAB-41", "call": "1", "tool": "bash", "command": "xmllint --noout translations/messages+intl-icu.de.xlf translations/messages+intl-icu.en.xlf && echo ok; ./bin/phpunit 2>&1 | tail -20", "kind": "denied", "message": "Permission denied because no interactive user response was available. …", "allowed": ["read", "write", "shell(openspec:*)", "…", "shell(./bin/phpunit:*)"]}
```

So gebt ihr die Datei weiter:

1. Lest sie durch. Sie enthält ganze Befehle, also Pfade und manchmal Text aus dem Ticket.
2. Startet `init`. Es bekommt eine Zusammenfassung der Datei und schlägt passende Werkzeuge vor.
3. Oder gebt die Datei der Person, die `config.json` pflegt. Sie entscheidet, welche Freigabe fehlt. Viele Ablehnungen sind gewollt. Im Lab waren es: `rm` eigener Hilfsdateien, `git diff` mit Umleitung, Ketten mit `cd … &&` und Bearbeiten per Shell (`sed -i`, Python). Die Agenten fanden jedes Mal einen anderen Weg.
4. Danach dürft ihr die Datei löschen. Der nächste Lauf legt sie neu an.

## Feedback zu Spec und Build

Ihr steuert eine Spec und einen Build vom Ticket aus. Es gibt zwei Wege:

- **Ein `[Mensch]`-Kommentar im Ticket.** Für alle, die Zugang zum Ticket haben, und wenn der Agent schreiben soll.
- **Eine Änderung der Spec-Dateien von Hand,** im Projekt auf eurem Rechner.

Was ein neuer Lauf damit macht, hängt davon ab, ob es schon einen Build gibt. „Nach dem ersten Build“ heißt: Im Ticket steht ein vertrauenswürdiger `[KI]`-Kommentar von `build`.

| | Vor dem ersten Build | Nach dem ersten Build |
|---|---|---|
| `[Mensch]`-Kommentar, dann neu starten | `spec` überarbeitet die Spec | `build` macht aus den Kommentaren neue Aufgaben und baut sie |
| Spec-Dateien von Hand geändert, dann neu starten | `spec` postet die Spec, wie sie jetzt ist, mit Diff. Kein Copilot-Aufruf | `build` passt den Code an die geänderte Spec an |
| Beides | `spec` überarbeitet, ausgehend von euren geänderten Dateien | `build` macht beides |
| `spec` neu starten | wie oben | lehnt ab, siehe unten |

### Schritt für Schritt: vor dem ersten Build

1. `spec` schreibt die Spec und postet `[KI] agentic-factory spec key=LL-123`.
2. Lest die Spec. Schreibt euer Feedback als Kommentar ins Ticket, der mit `[Mensch]` beginnt. Oder ändert die Spec-Dateien selbst. Oder beides.
3. Prüft, was der nächste Lauf tun würde: `python3 -I factory/agentic-factory.py spec --key LL-123 --print-only`. Die Ausgabe nennt die Kommentare, die er bearbeitet, und ob die Spec von Hand geändert ist.
4. Startet `spec` noch einmal, mit denselben Optionen wie beim ersten Mal, etwa `--framework`: `python3 -I factory/agentic-factory.py spec --key LL-123`.
5. Das Skript postet `[KI] agentic-factory spec überarbeitung=2 key=LL-123`: welche Kommentare bearbeitet sind, den Diff zur vorigen Fassung und die ganze Spec. Lest ihn.
6. Wiederholt das, bis die Spec passt. Dann startet ihr `build`.

Eine Überarbeitung hat keine Bereitschaftsprüfung: Das Ticket hat sie beim ersten Mal bestanden. Bei neuen Kommentaren startet ein Aufruf mit dem `revise_prompt` des Frameworks. Schreibt er außerhalb des Spec-Bereichs, warnt das Skript. Legt er einen zweiten Change an, stoppt es.

### Schritt für Schritt: nach dem ersten Build

1. `build` setzt die Spec um und postet `[KI] agentic-factory build key=LL-123`, mit den geänderten Dateien, der Testzeile, `Start-Commit` und `Spec-Prüfsumme`.
2. Lest `git diff` und startet die Tests. Schreibt euer Feedback als `[Mensch]`-Kommentar ins Ticket. Oder ändert die Spec-Dateien. Oder beides. Committen dürft ihr zwischendurch: Das Skript vergleicht mit dem `Start-Commit`, committete und uncommittete Änderungen zählen gleich.
3. Startet `build` noch einmal: `python3 -I factory/agentic-factory.py build --key LL-123`. Das passiert:
   - **Mit neuen Kommentaren** startet zuerst ein Aufruf „amend“. Er schreibt die Kommentare als neue, offene Aufgaben in die Spec, unter der Überschrift `## Änderungen nach Review (Überarbeitung <n>)`. Danach prüft das Skript, dass er nur die erlaubten Dateien geändert und nichts committet hat.
   - **Dann der Build-Aufruf** des Frameworks, mit dem normalen Prompt. Er setzt die offenen Aufgaben um. Habt ihr die Spec von Hand geändert, bekommt der Prompt dazu den Diff seit dem letzten Build, als Block `<<<SPEC CHANGES … SPEC CHANGES>>>`, mit dem Auftrag, den Code daran anzupassen. Die Tests laufen wieder.
   - Die Änderungen liegen danach uncommittet auf dem vorigen Build.
4. Das Skript postet `[KI] agentic-factory build überarbeitung=2 key=LL-123`. Lest ihn und `git diff`.

Wohin der amend-Aufruf schreibt:

| Framework | Was er ändern darf |
|---|---|
| OpenSpec | Den ganzen Change-Ordner: neue Aufgaben in `tasks.md`, dazu passt er `proposal.md`, die Specs unter `specs/` und `design.md` an |
| Spec Kit | Nur `tasks.md` |
| BMad | Nur die gebaute `SPEC.md` |

OpenSpec darf mehr, weil `/openspec-apply-change` eine Aufgabe ablehnt, die Proposal, Spec und Design nicht abdecken (siehe [Was der Spike gezeigt hat](#was-der-spike-gezeigt-hat)).

**Keine neue Aufgabe.** Macht der amend-Aufruf aus den Kommentaren keine Aufgabe, etwa weil sie nichts zu bauen verlangen, und habt ihr die Spec nicht von Hand geändert, startet kein Build-Aufruf. Der Kommentar sagt dann: „Der Agent hat aus den Kommentaren keine neue Aufgabe abgeleitet. Darum hat agentic-factory.py nichts gebaut.“ Die Kommentare gelten trotzdem als bearbeitet.

**Nichts Neues.** Keine neuen `[Mensch]`-Kommentare und keine Änderung von Hand seit dem letzten `[KI]`-Kommentar: Der Lauf stoppt vor jedem Aufruf mit `nothing new since comment …`. Er postet nichts, kostet nichts und endet mit Exit-Code 0.

### Wann `spec` ablehnt

Nach dem ersten Build stoppt `spec` mit `a build exists for LL-123 (comment …); give feedback through build, or run spec --fresh`. So laufen Spec und Code nicht auseinander: `build` ändert beide gemeinsam, erst die Spec, dann den Code.

### Neu anfangen mit `--fresh`

`spec --fresh` und `build --fresh` übergehen alle früheren `[KI]`-Kommentare des Modus und laufen wie beim ersten Mal. `spec --fresh` hat also wieder eine Bereitschaftsprüfung. Der neue Kommentar zählt wieder als Überarbeitung 1. `[Mensch]`-Kommentare davor gelten als bearbeitet. `spec --fresh` nach einem Build beendet die Zeit nach dem Build: Der nächste `build` ist wieder ein erster Build.

Nehmt `--fresh` nach einem verworfenen Build, einem gelöschten Spec-Ordner, einem Kommentar, dem das Skript nicht traut, und für eine Spec, die die Pipeline oder das Konto eines Kollegen gepostet hat.

### Wann das Skript stoppt

Jeder Stopp endet mit Exit-Code 2 und postet nichts.

| Meldung | Was passiert ist | Was ihr tut |
|---|---|---|
| `a build exists for … ; give feedback through build, or run spec --fresh` | `spec` nach dem ersten Build | Feedback über `build`. Oder `spec --fresh` |
| `the spec folder <name> is missing; restore it, or run spec --fresh` (bei `build`: `run build --fresh`) | Der Spec-Ordner aus dem vorigen Kommentar fehlt im Projekt | Den Ordner zurückholen, etwa per `git stash pop` oder Branch-Wechsel. Oder `--fresh` |
| `the first build is gone: … ; run build --fresh` | Die Dateien des vorigen Builds unterscheiden sich nicht mehr vom `Start-Commit`, oder das Repo kennt den `Start-Commit` nicht | Den Build zurückholen. Oder `build --fresh` |
| `the spec changed since the last build, but the copy of the built spec is missing; run build --fresh` | Die Spec ist von Hand geändert, aber die Kopie unter `~/.factory-local/` fehlt, etwa auf einem anderen Rechner | Auf dem Rechner des vorigen Laufs weitermachen. Oder `build --fresh` |
| `the comment … can't be trusted: it wasn't posted by the account running this script` oder `it was edited after it was posted` | Den letzten Ergebnis-Kommentar hat ein anderes Konto gepostet, oder jemand hat ihn bearbeitet | Mit dem Konto starten, das ihn gepostet hat. Oder `--fresh` |
| `the spec comment for … is longer than … characters even without the full spec text` | Schon der Diff ist zu lang für einen Jira-Kommentar (`jira.max_comment_chars`, 30.000 Zeichen) | In kleineren Schritten überarbeiten. Oder `spec --fresh` |
| `the build comment for … is longer than … characters even without the spec diff` | Schon die Liste der geänderten Dateien ist zu lang | In kleineren Schritten arbeiten |
| `the build comment … names no Start-Commit` oder `the … comment … names no valid change` | Der vorige Kommentar hat die Zeile `Start-Commit` oder `Change` nicht, etwa weil er älter ist | `--fresh` |
| `the latest result comment … is a spec posted after the build …; run build --fresh` | Nach dem letzten Build steht noch ein Spec-Ergebnis im Ticket | `build --fresh` |
| `--change … differs from the change … that comment … built; run build --fresh to build another change` | `--change` nennt einen anderen Change als der vorige Build | `--change` weglassen. Oder `build --fresh` |
| `the revision wrote another change besides …` oder `the amend call changed more than …` | Der Agent hat außerhalb seines Bereichs geschrieben | `git diff` lesen, die fremden Änderungen verwerfen, neu starten |

Ist ein Kommentar zu lang, kürzt das Skript ihn erst selbst: Eine Spec-Überarbeitung lässt dann den ganzen Spec-Text weg und nennt nur die Dateien. Eine Build-Überarbeitung lässt den Diff der Spec weg. Beides sagt der Kommentar.

### Was in den `[KI]`-Kommentaren steht

Ein Beispiel, eine Build-Überarbeitung:

~~~text
[KI] agentic-factory build überarbeitung=2 key=LL-123

Change: add-tags. Überarbeitung 2. Lokal umgesetzt mit agentic-factory.py, nicht geprüft und nicht gepusht.

Bearbeitet: Kommentar 10234, 10240.

agentic-factory.py hat die genannten [Mensch]-Kommentare als neue Aufgaben in die Spec übernommen und umgesetzt.

Geänderte Dateien:

```
src/Tags.php
tests/TagsTest.php
```

Testbefehl make test: bestanden.

Start-Commit: 3f93817…

Spec-Prüfsumme: 9c1e…
~~~

| Zeile | Was sie sagt |
|---|---|
| Erste Zeile | Der Marker: `spec`, `spec überarbeitung=<n>`, `build` oder `build überarbeitung=<n>`. Der erste Kommentar ohne Nummer zählt als Überarbeitung 1 |
| `Change: <name>.` | Der Spec-Ordner. Spätere Läufe nehmen ihn von hier, nicht aus den geänderten Dateien |
| `Bearbeitet: Kommentar 10234, 10240.` | Die `[Mensch]`-Kommentare, die dieser Lauf bearbeitet hat. Sie zählen danach nicht mehr als neu |
| `Start-Commit: <sha>` | Nur bei `build`: der Commit, auf dem der erste Build startete. Überarbeitungen behalten ihn |
| `Spec-Prüfsumme: <sha256>` | Eine Prüfsumme über die Spec-Dateien des Change nach dem letzten Aufruf. Bei `build` nach dem Abhaken der Aufgaben, abgehakte Kästchen zählen also nicht als Änderung von Hand. Weicht die Spec später davon ab, hat sie jemand von Hand geändert |

Eine Spec-Überarbeitung sagt außerdem, ob die Spec von Hand geändert war, zeigt den Diff zur vorigen Fassung und die ganze Spec. Eine Build-Überarbeitung zeigt die Änderungen von Hand an der Spec, die geänderten Dateien und die Testzeile. Bearbeitet diese Kommentare nicht: Einem bearbeiteten Kommentar traut das Skript nicht mehr.

### Welche Kommentare zählen

- **`[Mensch]`-Kommentare:** die nach dem letzten `[KI]`-Kommentar von `spec` oder `build`, die keine `Bearbeitet`-Zeile nennt. Vor dem ersten Build bearbeitet sie `spec`, danach `build`. Kommentare nach der Spec, aber vor dem ersten Build, liest der erste Build nicht. Das Skript sagt das. Sollen sie zählen, überarbeitet erst die Spec mit `spec`.
- **`[KI]`-Kommentare:** Als Ergebnis zählen nur die von `spec` und `build`, und nur die, die das Konto gepostet hat, mit dem das Skript läuft, unbearbeitet. Über Jira fragt das Skript dafür einmal nach eurem Konto. Mit `--ticket-file` prüft es nur, ob ein Kommentar bearbeitet wurde. Andere `[KI]`-Kommentare, die wie ein Ergebnis aussehen, nennt es in einer Notiz und lässt sie weg. Kommentare von `clarify` und `assess` prüft es nicht: Ein Ticket, das die Pipeline geklärt hat, bekommt lokal trotzdem Überarbeitungen.
- **Nach `spec fragen`:** Hat `spec` statt einer Spec Fragen gepostet, ist der nächste Lauf ein erster Lauf. Er bekommt die `[Mensch]`-Antworten danach in den Prompt.

### Die Kopien der Spec

Nach jedem Lauf von `spec` und `build` legt das Skript eine Kopie der Spec-Dateien ab: `~/.factory-local/<repo>/specs/<key>/<change>/spec-<n>/` und `build-<n>/`. Gegen diese Kopie rechnet es den Diff eurer Änderungen von Hand.

- **Fehlt die Kopie vor dem ersten Build,** postet `spec` die ganze Spec ohne Diff und sagt das.
- **Fehlt sie nach dem ersten Build** und ist die Spec von Hand geändert, stoppt `build`.
- **Bei BMad** gehört der PRD-Ordner unter `_bmad-output/planning-artifacts/prds/` zur Spec. Welcher es ist, weiß das Skript nur aus der Kopie des vorigen Laufs. Überarbeitungen mit BMad startet ihr deshalb auf dem Rechner, auf dem der vorige Lauf lief.

### Was der Spike gezeigt hat

Bevor wir die Überarbeitung von Builds programmiert haben, haben wir im Lab jedes Framework zweimal bauen lassen: bauen, eine Aufgabe von Hand ergänzen, wieder bauen. Dazu einen Build mit einer von Hand geänderten Spec. Ticket FLAB-41, etwa 346 Credits, alle Tests grün.

| Framework | Zweiter Build mit einer neuen, offenen Aufgabe | Folgt einer von Hand geänderten Spec |
|---|---|---|
| OpenSpec | Zum Teil: überspringt erledigte Aufgaben, lehnt aber eine Aufgabe ab, die Proposal, Spec und Design nicht nennen. Deshalb passt der amend-Aufruf bei OpenSpec auch diese Dateien an | Ja |
| Spec Kit | Ja: setzt nur die neue Aufgabe um und hakt sie ab | Ja |
| BMad | Ja: setzt nur den neuen Punkt in `SPEC.md` um, trotz Status `done` | Ja, aber 44 Credits für ein geändertes Wort |

## Sicherheit: Was ihr wissen müsst

`agentic-factory.py` hat lokal nicht den Schutz der Pipeline: keinen eigenen Benutzer, keinen Container, keinen Prüfschritt vor dem Commit. Der Agent läuft als ihr.

- **Eure Umgebung:** Copilot bekommt alle eure Umgebungsvariablen, nur die drei Jira-Variablen nicht. Startet das Skript in einer Shell ohne andere Tokens, etwa für Cloud, Datenbank oder Registry.
- **BMad darf beliebigen Code starten:** `shell(uv:*)` gilt beim Spec schreiben und beim Bauen. Mit `uv` startet der Agent jedes Python-Programm. Beim Bauen darf BMad außerdem selbst committen. OpenSpec und Spec Kit haben keinen solchen Freibrief.
- **Der Agent kann ändern, was er starten darf:** Er darf Dateien schreiben, also auch euer Testskript, die Skripte unter `.specify/` oder euer `Makefile`, und sie danach starten. Ein Ticket-Text, der ihn dazu bringt, führt so eigenen Code aus. Das Skript warnt erst nach dem Lauf, mit `WARNING: protected paths changed`, wenn sich ein geschützter Pfad geändert hat, etwa `bin/` oder `.specify/`. Ein geändertes `Makefile` meldet es nicht, außer ihr nehmt es in `protected_paths` auf.
- **Die Prüfung des Testbefehls ist keine Sicherheitsgrenze.** Sie fängt Fehler in der Konfiguration. Die Freigabe `shell(make test:*)` endet aber auf `:*`: Der Agent darf Argumente anhängen, bei Make also weitere Ziele. Und die Tests führen Code aus, den der Agent geschrieben hat.
- **`npm` ist nicht ganz verboten.** `deny_tools` verbietet `npm install`, `npm i`, `npm ci`, `npm exec` und `npx`, sonst liefe `npm test` nicht. Ein Verbot schlägt jede Freigabe. Andere Paketmanager verbietet die Vorlage nicht. `init` kann Verbote für euren Stack vorschlagen.
- **Lesende Befehle in `spec` und `build`.** Jeder Aufruf dieser Schritte bekommt die `read_tools` aus `config.json`, auch die Aufrufe, die eine Spec oder einen Build nach `[Mensch]`-Kommentaren überarbeiten: `ls`, `cat`, `head`, `tail`, `wc`, `grep`, `pwd`, `diff`, `stat` und `cd`, je als `shell(<befehl>:*)`. Die Bereitschaftsprüfung, `clarify` und `init` bekommen sie nicht: Sie haben keine Shell.
- **Was in `read_tools` fehlt, mit Absicht.** Diese Befehle sehen lesend aus, können aber schreiben oder Befehle starten: `find` (`-exec`, `-delete`), `sed` (`-i`), `awk` (`system()`), `xargs`, `rg` (`--pre`), `tree` (`-o`), `sort` (`-o`). Auch kein `git`-Befehl: `git diff`, `git log` und `git show` schreiben mit `--output=` Dateien, und `.git/config` kann jeden `git`-Aufruf zum Start von Code machen, auch `git status`. Eine Freigabe passt immer auf den Anfang eines Befehls. Eine gefährliche Option lässt sich also nicht einzeln verbieten.
- **`cat` und `grep` lesen auch außerhalb des Projekts,** etwa in eurem Home-Ordner. Copilots eigenes Lese-Werkzeug kann das nicht. Kopiert der Agent so etwas in eine Spec, fängt es nur der Token-Scan vor dem Posten.
- **Lesende Befehle ohne Freigabe.** Copilot kann in `spec` und `build` auch lesende Befehle außerhalb der Freigabe ausführen. Ein Verbot von `shell` würde dort alle Shell-Werkzeuge mit abschalten.
- **Die Kontrolle nach dem Lauf sieht nicht alles:** Das Skript vergleicht nur, was `git status` zeigt. Änderungen in `.git/`, etwa ein neuer Hook, und in ignorierten Dateien, etwa `.env`, sieht es nicht. Ein Hook liefe beim nächsten `git commit`.

Die echten Schutzmaßnahmen sind: die verbotenen Befehle in `deny_tools`, die geschützten Pfade, eure Durchsicht von `git diff` und die Warnungen nach dem Lauf.

Neu, seit das Skript in Jira schreibt:

- **Kommentare erscheinen unter eurem eigenen Jira-Konto.** Lokal postet das Skript mit eurer Anmeldung beim Jira-MCP. Jeder Kommentar beginnt mit `[KI]` und sagt, dass `agentic-factory.py` ihn geschrieben hat. Ein `[KI]`-Kommentar ist nie eine Freigabe.
- **Ein Werkzeug pro Jira-Aufruf.** Jeder Jira-Aufruf ist ein eigener, kurzer Copilot-Aufruf. Freigegeben ist nur ein Werkzeug des MCP-Servers, etwa `atlassian(getJiraIssue)`. Alle anderen MCP-Server sind aus, Lesen und Schreiben von Dateien auch. Er läuft in einem Ordner außerhalb des Projekts. Die Arbeitsaufrufe (`init`, `assess`, `clarify`, `spec`, `build`) haben keinen Jira-Zugang. Die kurzen Jira-Aufrufe sehen dagegen Ticket- oder Kommentartext, etwa das Ergebnis von `getJiraIssue` oder den Text, den sie posten sollen. Was sie tatsächlich getan haben, prüft das Skript danach.
- **Shell-Befehle ohne Freigabe.** Copilot 1.0.115 führt Shell-Befehle aus, die es für nur lesend hält, auch wenn sie nicht freigegeben sind. Das Skript verbietet deshalb `shell` in jedem Aufruf ohne Shell-Werkzeuge: in der Bereitschaftsprüfung, in `clarify`, in `init` und in den Jira-Aufrufen. Lief trotzdem einer, stoppt es. Nach der Bereitschaftsprüfung oder `clarify` postet es dann nichts.
- **Der Hook läuft mit Copilot 1.0.115 nicht.** Copilot CLI 1.0.115 führt in `-p`-Läufen keine Hooks aus `--plugin-dir` aus. 1.0.114 hat es getan. Das Skript liefert den Hook trotzdem mit und prüft jeden Jira-Aufruf danach aus den Ereignissen von Copilot: welches Werkzeug, welches Ticket, welche Argumente, welcher Text. Danach liest es den gespeicherten Kommentar zurück. Passt etwas nicht, stoppt es und nennt den Kommentar, den ihr von Hand löschen müsst. Ohne Hook verhindert diese Prüfung nichts, sie bemerkt es nur hinterher.
- **Ein `[Mensch]`-Kommentar ist Daten, keine Anweisung.** Er landet im Prompt als eigener Block. Er entscheidet, was Spec und Code sagen, nie, welche Werkzeuge der Agent nutzt oder welche Dateien er schreibt. Nur Leute, die ihr kennt, sollten im Ticket kommentieren.

Was ihr tut:

- Nur Tickets durchschicken, deren Text und Kommentare ihr kennt. Beides landet im Prompt.
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
- **`build` in der Pipeline.** Das Skript lehnt es dort ab: Der Code ginge mit dem Schritt verloren. `init` lehnt es dort auch ab.
- **Eine Grenze für Überarbeitungen.** Jeden Lauf startet ihr selbst. Die Credit-Grenze je Aufruf bleibt.
- **Feedback für `assess`.** Dafür gibt es `clarify`.

## Tests

Die Tests brauchen nur die Python-Standardbibliothek. Sie rufen weder Jira noch Copilot auf: Ein Ersatz-`copilot` und ein lokaler Test-Server stehen dafür. Im Workshop-Repo:

```bash
python3 -I -B -m unittest discover -s 02-agent-factory/einrichtung/template/tests -t 02-agent-factory/einrichtung/template
```

Ein Teil der Tests vergleicht den Code mit `factory-base`: Prompts und Flags mit `agent.py`, die kopierten Prüfungen mit `common.py` und die eigenen Kommentare mit dem Marker von `guard.py`. Prompts und Flags vergleichen sie mit einer Konfiguration wie der des Labs (`LAB_CFG` in `tests/fakes.py`): mit `./bin/phpunit`, ohne `read_tools`, mit dem alten Plan-Prompt von Spec Kit. Die `config.json` der Vorlage weicht davon ab. Diese Tests brauchen einen Klon des Lab-Repos. Ohne `FACTORY_BASE` überspringen sie sich:

```bash
git clone --depth 1 --branch factory-base https://bitbucket.org/factory-lab/factory-lab.git /tmp/factory-lab
FACTORY_BASE=/tmp/factory-lab/factory python3 -I -B -m unittest discover -s 02-agent-factory/einrichtung/template/tests -t 02-agent-factory/einrichtung/template
```

## Aktualisieren

`factory-base` ist nur noch die Referenz. Kopiert die Dateien von dort nicht mehr über diese hier.

- **Kopierte Blöcke** stehen alle in `agentic_factory/copied.py`, markiert etwa mit `# --- copied from factory/common.py`. Ändert sich `factory-base`, schlagen die Tests mit `FACTORY_BASE` fehl. Dann übernehmt ihr die Änderung von Hand.
- **Die Umwandlung der Beschreibung** steht auch dort. Sie ist aus `jira_ticket.py` des Skills [`schreibe-ticket`](../../werkzeuge/schreibe-ticket/README.md) kopiert. Ein Test vergleicht beide, auch ohne `FACTORY_BASE`.
- **Alles andere** pflegt ihr hier.
