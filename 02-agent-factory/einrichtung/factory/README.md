# Vorlage: die Factory-Schritte lokal mit `agentic-factory.py`

`agentic-factory.py` bringt ein Jira-Ticket mit GitHub Copilot CLI zu einer Spec und zu Code, in eurem eigenen Projekt, mit jedem Stack. Jedes Ergebnis landet als Kommentar im Ticket. Mit euren Antworten im Ticket steuert ihr die nächste Runde. Das Skript kennt fünf Modi:

| Modus | Was er tut |
|---|---|
| `init` | Die Doku des Projekts lesen und Änderungen an `config.json` und `readiness.md` vorschlagen |
| `assess` | Bereitschaft prüfen |
| `clarify` | Ein Ticket in Runden von Kommentaren klären, bis es bereit ist |
| `spec` | Bereitschaft prüfen, dann die Spec schreiben. Noch einmal gestartet: die Spec nach Kommentaren und Änderungen von Hand überarbeiten |
| `build` | Die Spec umsetzen. Noch einmal gestartet: den Code nach Kommentaren und Änderungen an der Spec nachbessern |

Jeder Kommentar des Skripts beginnt mit `[KI]`. Eure Antworten beginnen mit `[Mensch]`.

- **Anleitung:** [Factory-Schritte lokal ausführen](../../bedienung/lokal-ausfuehren.md) und [Übung 1](../../../01-erstworkshop/tag-2/uebung-factory-lokal.md).
- **Aufbau:** Wie das Skript gebaut ist, welche Leitplanken es hat und welche Datei was tut, steht in [`aufbau.md`](aufbau.md).
- **Änderungen:** Was sich gegenüber `local.py` und der früheren Vorlage geändert hat und wie ihr umsteigt, steht in [`aenderungen.md`](aenderungen.md).

## Begriffe

- **Bereitschaftsprüfung:** Ein Copilot-Aufruf prüft, ob ein Ticket genau genug für eine Spec ist. Die Kriterien stehen in `readiness.md`.
- **Spec:** Die Beschreibung dessen, was gebaut wird, als Dateien im Projekt. Ein SDD-Framework schreibt sie.
- **OpenSpec, Spec Kit, BMad:** Die drei Frameworks für Spec-Driven Development (SDD), die das Skript kennt. Das Label `sdd-<framework>` am Ticket oder `--framework` wählt eines. Einen Vergleich findet ihr unter [SDD-Frameworks](../sdd-frameworks/vergleich.md).
- **Change:** Der Ordner einer Spec, etwa `openspec/changes/<name>/` oder `specs/<nnn-name>/`.
- **amend:** Der Aufruf, der nach dem ersten Build eure `[Mensch]`-Kommentare als neue Aufgaben in die Spec schreibt.
- **Credits:** Die Einheit, in der GitHub Copilot abrechnet. 1 AI Credit kostet 0,01 US-Dollar ([Überblick](../../ueberblick.md), Quelle 1). Jeder Aufruf hat eine Obergrenze: 40 Credits für Bereitschaftsprüfung, `clarify` und `init`, 150 für die Aufrufe der Frameworks.

## Voraussetzungen

- **GitHub Copilot CLI** 1.0.115, installiert und einmal interaktiv mit `copilot` angemeldet. Eure Lizenz muss das Modell aus `config.json` erlauben, `claude-sonnet-5.5`.
- **Python** 3.9 oder neuer. Das Skript braucht nur die Standardbibliothek.
- **Git:** Euer Projekt ist ein Git-Repository, mit mindestens einem installierten Framework (`openspec/`, `.specify/` oder `_bmad/`).
- **Jira:** Jira Cloud über euren Jira-MCP-Server oder per API-Token. Jira Data Center nur per API-Token (`--jira api`). Ohne Jira geht es mit einer Ticket-Datei (`--ticket-file`).
- **Datenschutz:** Euer Datenschutzbeauftragter hat bestätigt, dass eure Erlaubnis für Copilot auch Copilot CLI und die Factory abdeckt (siehe [Checkliste](../../../01-erstworkshop/vorbereitung/checkliste.md)). Bis dahin schickt ihr keine Tickets mit Personen- oder Kundendaten durch. Mehr unter [Datenschutz](#datenschutz).

## Schnellstart

Im Wurzelordner eures Repos:

```bash
mkdir -p factory
cp -R <dieser Ordner>/{agentic_factory,agentic-factory-plugin} factory/
cp <dieser Ordner>/{agentic-factory.py,config.json,readiness.md,local.example.json} factory/
cp -R <dieser Ordner>/tests factory/     # optional
cp factory/local.example.json factory/local.json
python3 -I factory/agentic-factory.py init --print-only   # nur den Copilot-Befehl zeigen, kostet nichts
python3 -I factory/agentic-factory.py init                # Vorschläge prüfen lassen, bis zu 40 Credits
python3 -I factory/agentic-factory.py init --apply        # die geprüften Vorschläge schreiben, kostet nichts
python3 -I factory/agentic-factory.py spec --ticket-file ~/factory-tickets/LL-123.json --print-only
```

- `<dieser Ordner>` ist dieser Ordner im Workshop-Repo: `02-agent-factory/einrichtung/factory/`.
- Eine Ticket-Datei ist JSON mit `key`, `summary`, `description` und `labels`. Ein Muster: [`ticket-FLAB-41.json`](../prompt-beispiele/ticket-FLAB-41.json).
- Nur Läufe mit `--print-only` starten keinen Copilot-Aufruf und kosten nichts. `init` ohne `--print-only` kostet bis zu 40 Credits.
- Das Ticket nennt ihr direkt nach dem Modus, als Schlüssel oder als URL aus dem Browser: `spec LL-123` oder `spec https://example.atlassian.net/browse/LL-123`. Der Host der URL muss zu eurer Jira-Seite passen (`jira_site` in `local.json` oder `JIRA_BASE_URL`), sonst stoppt das Skript. `--key LL-123` ist die lange Form und geht weiter.
- `--ticket-file` bedeutet offline: Das Skript fragt Jira nie und postet nichts. Den Kommentar schreibt es in eine Datei, die letzte Zeile nennt sie. Ohne das Label `sdd-<framework>` in der Datei wählt ihr das Framework mit `--framework`.
- Feedback probiert ihr auch offline aus: `--comments-file c.json` gibt dem Lauf Kommentare aus einer Datei, als JSON-Liste mit `body` und optional `created`, `id`, `author` und `updated`. Legt dort den `[KI]`-Kommentar des vorigen Laufs und einen `[Mensch]`-Kommentar ab und startet `spec` noch einmal.
- `agentic-factory.py` liest `config.json`, `readiness.md` und `local.json` **neben sich**, nicht im aktuellen Ordner. Die Ordner `agentic_factory/` und `agentic-factory-plugin/` auch. Fehlt `agentic_factory/`, stoppt das Skript mit Exit-Code 2.
- Der Ordner heißt `factory/`, denn dort sucht der Skill [`schreibe-ticket`](../../werkzeuge/schreibe-ticket/README.md) `agentic-factory.py` und `readiness.md`.
- Euren Testbefehl tragt ihr in `config.json` ein, als `test_command`, etwa `"make test"`. `init` schlägt ihn vor. Ohne ihn stoppt `build` mit `set test_command in config.json (or run init)`. `assess`, `clarify` und `spec` brauchen ihn nicht. Was das Skript am Testbefehl prüft, steht unter [Der Testbefehl](#der-testbefehl).
- `local.json` hat nur die Einstellungen eures Rechners. Steht dort ein älterer Schlüssel, stoppt das Skript und sagt, wohin der Wert gehört, etwa `test_command moved to config.json (key test_command); remove it from local.json`.
- Jira-Zugangsdaten gehören nie in `local.json`, nur in die Umgebung: `JIRA_BASE_URL`, `JIRA_API_TOKEN` und für Jira Cloud `JIRA_EMAIL`. Die braucht nur `--jira api`.
- Die Tests in `tests/` prüfen die Dateien der Vorlage. Ändert ihr `config.json`, schlagen einige fehl. Kopiert sie nur, wenn ihr den Code selbst ändern wollt.

Für den Weg über den Jira-MCP, einmal pro Rechner:

```bash
copilot mcp add --transport http atlassian https://mcp.atlassian.com/v1/mcp
copilot          # dann /mcp, atlassian, „Authenticate“, im Browser anmelden, /exit
```

Dann in `factory/local.json` eure Jira-Cloud-Adresse eintragen, etwa `"jira_site": "https://example.atlassian.net"`. Fehlt `jira_site`, nimmt das Skript `JIRA_BASE_URL`. Jira Data Center hat keinen MCP-Weg: Nehmt dort `--jira api`.

Habt ihr den Server schon mit einer Werkzeug-Liste angelegt (`"tools": [...]` in `~/.copilot/mcp-config.json`, etwa in Übung 1), muss sie diese Werkzeuge enthalten: `getJiraIssue` (lesen), `addCommentToJiraIssue` (posten), `editJiraIssue` (`clarify --apply`) und `atlassianUserInfo` (euer Konto, bei `clarify --apply` und bei jedem weiteren Lauf von `spec` und `build`). Ergänzt die Liste, oder legt den Server mit `copilot mcp remove atlassian` und dem Befehl oben neu an. Alles Weitere steht in [Factory-Schritte lokal ausführen](../../bedienung/lokal-ausfuehren.md#jira-über-den-mcp-server).

Was `agentic-factory.py` mit diesen Dateien an Copilot schickt, zeigen die [Prompt-Beispiele](../prompt-beispiele/README.md).

## Die Dateien

| Datei | Wozu | Nötig? |
|---|---|---|
| [`agentic-factory.py`](agentic-factory.py) | Das Programm, nur ein Starter: Es lädt den Code aus `agentic_factory/` neben sich. Nur Python-Standardbibliothek | Ja |
| [`agentic_factory/`](agentic_factory/) | Der Code, ein Modul pro Teil. Was welches Modul tut, steht in [`aufbau.md`](aufbau.md). Der Ordner muss **neben dem Skript** liegen | Ja |
| [`config.json`](config.json) | Prompts, Werkzeug-Freigaben, verbotene Befehle, Modell und Credit-Grenzen, für OpenSpec, Spec Kit und BMad. Ohne Annahmen über euren Stack. Darin auch `test_command`, zum Start leer, und `read_tools`, die lesenden Befehle für `spec` und `build` | Ja |
| [`readiness.md`](readiness.md) | Die Kriterien der Bereitschaftsprüfung. `clarify` nutzt sie auch. `init` kann Änderungen vorschlagen | Für `assess`, `clarify` und `spec` mit Bereitschaftsprüfung |
| [`local.example.json`](local.example.json) | Vorlage für `local.json`: nur die Einstellungen eures Rechners, also `model`, `copilot` (der Befehl, der Copilot startet), `jira_mcp_server` und `jira_site` | Nein. Ohne `local.json` gelten die Werte aus `config.json`. Für `--jira mcp` braucht ihr `jira_site` oder `JIRA_BASE_URL` |
| [`agentic-factory-plugin/`](agentic-factory-plugin/) | Der Hook für die Jira-Aufrufe über MCP: Er lässt nur den einen erwarteten Aufruf durch. Der Ordner muss **neben dem Skript** liegen. Das Skript lädt ihn von dort, nie aus `.github/` | Für `--jira mcp`. Copilot 1.0.115 führt ihn nicht aus, siehe [Sicherheit](#sicherheit-was-ihr-wissen-müsst) |
| [`pipelines.example.yml`](pipelines.example.yml) | Beispiel für Bitbucket Pipelines: `agentic-clarify` und `agentic-assess`, je mit den Schritten `fetch`, `agent` und `post` | Nein. Nur für die Pipeline |
| [`tests/`](tests/) | Die Tests, meist eine Datei pro Modul, siehe [Tests](#tests) | Nein |
| [`aenderungen.md`](aenderungen.md) | Was sich gegenüber `local.py` und der früheren Vorlage geändert hat, und wie ihr umsteigt | Nein |
| [`aufbau.md`](aufbau.md) | Ziel, Design, Leitplanken und Hooks der Vorlage, und welche Datei was tut | Nein |

Außerhalb des Projekts legt das Skript an, in `~/.factory-local/<repo>/`:

| Pfad | Was drin steht |
|---|---|
| `<zeit>-<modus>-<key>/` | Die Protokolle eines Laufs: Ereignisse und Verbrauch jedes Copilot-Aufrufs, also Befehle und Antworten des Modells, dazu `io/` mit Ticket, Kommentaren samt Konto-IDs und Ergebnissen. Bei `init` heißt der Ordner `<zeit>-init-INIT/`, mit `init-result.json` |
| `blocked.jsonl` | Was Copilot in allen Läufen abgelehnt hat, siehe [Blockierte Aufrufe](#blockierte-aufrufe-blockedjsonl) |
| `specs/<key>/<change>/<modus>-<n>/` | Eine Kopie der Spec-Dateien nach jedem Lauf von `spec` und `build`, siehe [Die Kopien der Spec](#die-kopien-der-spec) |

Dazu kommt `~/.factory-local/no-hooks/`, ein leerer Ordner: Jeder `git`-Befehl des Skripts sucht seine Hooks dort.

Die Ordner bleiben, bis ihr sie löscht. Ist ein Ticket fertig, löscht ihr seine Läufe und Kopien:

```bash
rm -rf ~/.factory-local/<repo>/*-<KEY>/ ~/.factory-local/<repo>/specs/<KEY>/
```

Alles eines Projekts auf einmal: `rm -rf ~/.factory-local/<repo>/`. Danach braucht ein weiterer Lauf von `spec` oder `build` für dieses Ticket `--fresh`.

## Der Testbefehl

`build` braucht `test_command` in `config.json`. Das Skript macht daraus zwei Dinge:

- **Die Regel im Prompt:** `Run the tests with exactly: make test.`
- **Eine Freigabe:** der ganze Befehl als Anfang, nicht nur das erste Wort. Aus `make test` wird `shell(make test:*)`, aus `npm test` wird `shell(npm test:*)`, aus `uv run pytest` wird `shell(uv run pytest:*)`. Das ist enger als `shell(make:*)` oder `shell(uv:*)`. Weil die Freigabe auf `:*` endet, darf der Agent aber Argumente anhängen, bei Make also auch weitere Ziele, etwa `make test deploy`.

Vor jedem Build-Aufruf prüft das Skript den Befehl. Es stoppt bei:

- Code direkt im Befehl, etwa `bash -c`, `sh -c`, `python3 -c` oder `node -e`,
- Zeichen der Shell, etwa `;`, `&&`, `|`, `$(`, `>`, und Anführungszeichen,
- einer Variablen davor, etwa `CI=1 make test`,
- einem Befehl ohne festes Ziel, etwa `python3` allein,
- Optionen eines Wrappers wie `timeout` oder `uv run`, die nicht die Form `--opt=value` haben,
- einem Befehl, den ein Eintrag in `deny_tools` trifft. Ein Verbot schlägt jede Freigabe,
- einer Liste statt eines Textes, wie in alten Konfigurationen: `test_command must be a string such as "make test"`.

Braucht euer Test mehr, schreibt ein Skript oder ein Make-Ziel und tragt das ein. Diese Prüfung fängt Fehler in der Konfiguration. Eine Sicherheitsgrenze ist sie nicht, siehe [Sicherheit](#sicherheit-was-ihr-wissen-müsst).

**Zeit.** Jeder Copilot-Aufruf darf höchstens `agent_timeout_s` Sekunden laufen, in der Vorlage 1200, also 20 Minuten. Der Build-Aufruf startet die Tests oft mehrmals. Dauern eure Tests lange, erhöht den Wert in `config.json`.

## Hinweise des Teams gehören in `AGENTS.md`

Regeln eures Teams, etwa „minimale Änderungen, kein Refactoring nebenbei“, schreibt ihr in `AGENTS.md` im Wurzelordner eures Repos. Copilot lädt die Datei in jedem Arbeitsaufruf selbst. Die Regeln jedes Arbeitsaufrufs in `config.json` sagen dem Agenten, dass er sie und die Dateien, auf die sie verlinkt, befolgen soll, und dass bei einem Widerspruch die Regeln der Factory gewinnen. Verlinkte Dateien lädt Copilot nicht selbst: Der Agent liest sie, weil der Prompt es sagt. Dort beschreibt ihr auch euren Stack: Der Plan-Prompt von Spec Kit sagt nur „Use the existing stack and test setup; no new dependencies.“

- Hat eure `config.json` noch einen Block `rules`, stoppt das Skript: `config.json has a rules block: team rules were removed; move them to AGENTS.md`.
- `AGENTS.md` ist ein geschützter Pfad, auch in Unterordnern und in jeder Schreibweise. Ändert ein Aufruf sie, einen anderen geschützten Pfad oder eine Datei, auf die `AGENTS.md` verlinkt, und folgt noch ein Aufruf, stoppt das Skript vor diesem: Er würde die geänderte Datei befolgen. Es stoppt auch, wenn Copilot danach andere Anweisungs-Dateien lädt als vorher. Nach dem letzten Aufruf warnt es.
- Copilot lädt außer `AGENTS.md` auch `CLAUDE.md`, `GEMINI.md`, `.github/copilot-instructions.md` und `.github/instructions/*.instructions.md`, auch kleingeschrieben wie `agents.md`. Haltet sie gleich oder löscht, was veraltet ist. Vor jedem Lauf nennt das Skript die Dateien, die Copilot lädt (`copilot instruction list --json`). Lädt Copilot auch Dateien von außerhalb des Projekts, etwa eure persönlichen in `~/.copilot/`, warnt es: Der Container der Factory hat sie nicht.
- `AGENTS.md` in Unterordnern lädt Copilot nicht. Schreibt alles in die Datei im Wurzelordner oder verlinkt von dort.
- `--no-custom-instructions` schaltet `AGENTS.md` ab. Das Skript stoppt, wenn das Flag im Befehl steht, auch mit einer alten `config.json`.
- `init` liest `AGENTS.md` und die Dateien, auf die sie verlinkt.

## Erste Einrichtung mit `init`

`init` liest die Doku eures Projekts und schlägt Änderungen an `config.json` und `readiness.md` vor. Es braucht kein Ticket und kein Jira. Es läuft nur lokal: In einer Pipeline lehnt das Skript es ab.

```bash
python3 -I factory/agentic-factory.py init               # Bericht und Diff zeigen, nichts ändern
python3 -I factory/agentic-factory.py init --apply       # das geprüfte Ergebnis des letzten Laufs schreiben, kein Aufruf
python3 -I factory/agentic-factory.py init --print-only  # nur den Copilot-Befehl zeigen, kein Aufruf
```

**Was der Aufruf liest.** Ein Copilot-Aufruf liest `AGENTS.md` und die Dateien, auf die sie verlinkt, `README*`, `CONTRIBUTING*`, `.github/copilot-instructions.md` und die Build-Dateien, etwa `Makefile`, `package.json`, `pom.xml`, `build.gradle*`, `pyproject.toml`, `go.mod` und `Cargo.toml`. Das Skript gibt ihm dazu mit:

- den Teil von `config.json`, den `init` ändern darf: Testbefehl, Frameworks, geschützte Pfade, verbotene Befehle und die Werkzeuge je Framework,
- `readiness.md`,
- die installierten Frameworks, also die Ordner `openspec/`, `.specify/` und `_bmad/`,
- eine Zusammenfassung von `blocked.jsonl`: wie oft Copilot welchen Befehl in welchem Modus abgelehnt hat. Die Datei liegt außerhalb des Projekts. Der `init`-Aufruf hat keine Shell und kann sie nicht selbst lesen.

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
- Diese Werkzeuge lehnt es ab:
  - `shell` ohne Klammer und alles, was `deny_tools` verbietet,
  - Shells und Interpreter, etwa `bash`, `sh`, `python` und `node`,
  - Wrapper wie `env`, `timeout` oder `xargs`,
  - Paket-Starter, etwa `npx`, `uvx` und `npm exec`,
  - Netzwerk-Befehle, etwa `curl`, `wget`, `ssh`, `scp` und `nc`,
  - jeden `git`-Befehl,
  - Befehle, die Dateien schreiben oder Befehle starten können: `find`, `sed`, `awk`, `rg`, `tree`, `sort`, `tar`, `docker`, `podman`.
- Paketmanager nimmt es nur mit Test- und Run-Befehlen an: `npm`, `pnpm`, `yarn`, `bun` mit `test`, `t`, `tst` oder `run`; `uv`, `poetry`, `pipenv`, `pdm`, `hatch`, `rye` mit `run`; `cargo` mit `test`, `build`, `check`, `clippy` oder `fmt`; `go` mit `test`, `build` oder `vet`; `composer` mit `test` oder `run-script`. Für `bundle`, `gem` und `pip` nichts. Davor stehen nur Optionen der Form `--opt=value`.
- Ein vorgeschlagener Testbefehl durchläuft dieselben Prüfungen wie einer von Hand, siehe [Der Testbefehl](#der-testbefehl). `uv run pytest` geht also, obwohl `shell(uv:*)` abgelehnt wäre. Dazu prüft `init` ihn gegen die Liste oben, nur ohne die Regel für Interpreter. Einen Testbefehl wie `docker compose run --rm test` lehnt `init` deshalb ab. Den tragt ihr von Hand ein.
- Geschützte Pfade: höchstens 200 Zeichen, ohne Leer- und Steuerzeichen, höchstens 20 neue pro Lauf.
- Ein neues Verbot darf keinen der `read_tools` und nicht den Testbefehl treffen.
- `readiness_md` muss jede bisherige Kriterium-ID behalten. Steuerzeichen und Zeichen für die Schreibrichtung lehnt das Skript ab.
- `enabled_frameworks` muss `default_framework` enthalten, wenn es gesetzt ist.

Abgelehnte Vorschläge zeigt der Bericht mit Grund. Er lässt sie nicht still weg. Breite Werkzeuge markiert er, etwa `shell(make:*)` mit „allows every Make target“.

**Was ihr seht.** Ohne `--apply`: den Bericht, dann einen Diff von `config.json` und `readiness.md`. Nichts ändert sich, Exit-Code 0. Das Skript speichert das geprüfte Ergebnis im Log-Ordner des Laufs, als `init-result.json`, und nennt den Pfad. Dazu kommen Prüfsummen von `config.json` und `readiness.md`.

**Was `--apply` tut.** `init --apply` startet keinen Copilot-Aufruf und kostet keine Credits. Es nimmt das gespeicherte Ergebnis des letzten `init`-Laufs, prüft es noch einmal und schreibt genau den Diff, den ihr gelesen habt, in `config.json` und `readiness.md`, sonst nichts. Hat sich eine der beiden Dateien seitdem geändert, stoppt es: Startet dann `init` noch einmal. Hatte der letzte Lauf nichts zu schreiben, stoppt es auch. Danach lest ihr `git diff` und gebt die Änderung in den Review, siehe [Wer `config.json` pflegt](#wer-configjson-und-readinessmd-pflegt).

`init` läuft jederzeit wieder, etwa nachdem sich `blocked.jsonl` gefüllt hat. Es vergleicht immer mit den aktuellen Dateien.

## Blockierte Aufrufe: `blocked.jsonl`

Copilot läuft unbeaufsichtigt (`--no-ask-user`). Alles ohne Freigabe lehnt er ab. Der Agent sucht dann einen anderen Weg oder gibt auf. Das Skript sammelt diese Ablehnungen pro Projekt in einer Datei: `~/.factory-local/<repo>/blocked.jsonl`. Daraus passt ihr `config.json` an.

- **Was hineinkommt:** eine JSON-Zeile pro abgelehntem Werkzeug-Aufruf, aus jedem Arbeitsaufruf von `init`, `assess`, `clarify`, `spec` und `build`. `kind` ist `denied` (das Werkzeug steht nicht auf der Freigabe) oder `blocked` (Copilots eigener Schutz, die Meldung beginnt mit „Command blocked“). Normale Fehler, etwa „Parent directory does not exist“, kommen nicht hinein.
- **Was nicht hineinkommt:** die kurzen Jira-Aufrufe. Eine Ablehnung dort ist ein Sicherheitssignal, keine Lücke in der Konfiguration. Das Skript prüft diese Aufrufe selbst.
- **Die Felder:** `at`, `run` (der Protokoll-Ordner), `mode`, `framework`, `key`, `call` (der Aufruf), `tool`, `command` (der ganze Befehl), `kind`, `message` und `allowed` (die Freigabe des Aufrufs).
- **Die letzte Antwort:** Hatte ein Aufruf mindestens eine Ablehnung, folgt eine Zeile `{"kind": "final", "call": …, "text": …}` mit seiner letzten Antwort. Dort sagt der Agent meist, was er nicht tun konnte. Fragen, die er nicht stellen durfte, stehen nur dort oder in `FACTORY-QUESTIONS.md`.
- **Geschwärzt:** Bekannte Token-Formate und die Werte der Secrets des Laufs ersetzt das Skript in `command`, `message` und `text` durch `[REDACTED]`. Andere Daten nicht.
- **Die Zeile am Ende jedes Laufs mit Copilot-Aufrufen:** etwa `[agentic-factory] 2 blocked call(s), see ~/.factory-local/<repo>/blocked.jsonl`, sonst `[agentic-factory] no blocked calls`. Erkennt das Skript die Ereignisse von Copilot nicht, steht dort stattdessen eine `WARNING`, siehe [Sicherheit](#sicherheit-was-ihr-wissen-müsst).

Ein ausgedachtes Beispiel, gekürzt:

```json
{"at": "2026-11-25T10:00:00+0100", "run": "20261125-095800-build-LL-123", "mode": "build", "framework": "openspec", "key": "LL-123", "call": "1", "tool": "bash", "command": "cd src && make lint", "kind": "denied", "message": "Permission denied because no interactive user response was available. …", "allowed": ["read", "write", "shell(openspec:*)", "…", "shell(make test:*)"]}
```

So gebt ihr die Datei weiter:

1. Lest sie durch. Sie enthält ganze Befehle, also Pfade und manchmal Text aus dem Ticket. Löscht Namen, Kundendaten und Secrets, die das Skript nicht geschwärzt hat.
2. Startet `init`. Es bekommt eine Zusammenfassung der Datei und schlägt passende Werkzeuge vor.
3. Oder gebt die Datei der Person, die `config.json` pflegt. Sie entscheidet, welche Freigabe fehlt. Viele Ablehnungen sind gewollt. Im Lab waren es: `rm` eigener Hilfsdateien, `git diff` mit Umleitung, Ketten mit `cd … &&` und Bearbeiten per Shell (`sed -i`, Python). In diesen Läufen fanden die Agenten jedes Mal einen anderen Weg.
4. Danach dürft ihr die Datei löschen. Der nächste Lauf legt sie neu an.

## Feedback zu Spec und Build

Ihr steuert eine Spec und einen Build vom Ticket aus. Es gibt zwei Wege:

- **Ein `[Mensch]`-Kommentar im Ticket.** Für alle, die Zugang zum Ticket haben, und wenn der Agent schreiben soll.
- **Eine Änderung der Spec-Dateien von Hand,** im Projekt auf eurem Rechner.

Beide Wege sind für die Zeit vor dem Pull Request. Was danach kommt, steht unter [Nach dem Build](#nach-dem-build-branch-pull-request-review).

Was ein neuer Lauf damit macht, hängt davon ab, ob es schon einen Build gibt. „Nach dem ersten Build“ heißt: Im Ticket steht ein vertrauenswürdiger `[KI]`-Kommentar von `build`.

| | Vor dem ersten Build | Nach dem ersten Build |
|---|---|---|
| `[Mensch]`-Kommentar, dann neu starten | `spec` überarbeitet die Spec | `build` macht aus den Kommentaren neue Aufgaben und baut sie |
| Spec-Dateien von Hand geändert, dann neu starten | `spec` postet die Spec, wie sie jetzt ist, mit Diff. Kein Copilot-Aufruf | `build` passt den Code an die geänderte Spec an |
| Beides | `spec` überarbeitet, ausgehend von euren geänderten Dateien | `build` macht beides |
| `spec` neu starten | wie oben | lehnt ab, siehe unten |

Vor jedem Lauf nennt das Skript Nummer und Konto jedes `[Mensch]`-Kommentars, den es bearbeitet, etwa `handles comments 10234 (by 557058:…)`.

### Schritt für Schritt: vor dem ersten Build

1. `spec` schreibt die Spec und postet `[KI] agentic-factory spec key=LL-123`.
2. Lest die Spec. Schreibt euer Feedback als Kommentar ins Ticket, der mit `[Mensch]` beginnt. Oder ändert die Spec-Dateien selbst. Oder beides.
3. Prüft, was der nächste Lauf tun würde: `python3 -I factory/agentic-factory.py spec LL-123 --print-only`. Die Ausgabe nennt die Kommentare, die er bearbeitet, und ob die Spec von Hand geändert ist.
4. Startet `spec` noch einmal, mit denselben Optionen wie beim ersten Mal, etwa `--framework`: `python3 -I factory/agentic-factory.py spec LL-123`.
5. Das Skript postet `[KI] agentic-factory spec überarbeitung=2 key=LL-123`: welche Kommentare bearbeitet sind, den Diff zur vorigen Fassung und die ganze Spec. Lest ihn.
6. Wiederholt das, bis die Spec passt. Dann startet ihr `build`.

`[Mensch]` ist für Änderungen, nicht für eine Freigabe: Ein „[Mensch] passt so“ startet einen weiteren Aufruf. Nimmt bei euch der Product Owner die Spec ab, macht er das wie gewohnt, etwa per Status oder mit einem Kommentar ohne `[Mensch]`.

Eine Überarbeitung hat keine Bereitschaftsprüfung: Das Ticket hat sie beim ersten Mal bestanden. Bei neuen Kommentaren startet ein Aufruf mit dem `revise_prompt` des Frameworks. Schreibt er außerhalb des Spec-Bereichs, warnt das Skript. Legt er einen zweiten Change an, stoppt es.

### Schritt für Schritt: nach dem ersten Build

1. `build` setzt die Spec um und postet `[KI] agentic-factory build key=LL-123`, mit den geänderten Dateien, der Testzeile, `Start-Commit` und `Spec-Prüfsumme`.
2. Lest `git diff` und startet die Tests. Schreibt euer Feedback als `[Mensch]`-Kommentar ins Ticket. Oder ändert die Spec-Dateien. Oder beides. Committen dürft ihr zwischendurch: Das Skript vergleicht mit dem `Start-Commit`, committete und uncommittete Änderungen zählen gleich.
3. Startet `build` noch einmal: `python3 -I factory/agentic-factory.py build LL-123`. Das passiert:
   - **Mit neuen Kommentaren** startet zuerst ein Aufruf „amend“. Er schreibt die Kommentare als neue, offene Aufgaben in die Spec, unter der Überschrift `## Änderungen nach Review (Überarbeitung <n>)`. Danach prüft das Skript, dass er nur die erlaubten Dateien geändert und nichts committet hat.
   - **Dann der Build-Aufruf** des Frameworks, mit dem normalen Prompt. Er setzt die offenen Aufgaben um. Habt ihr die Spec von Hand geändert, bekommt der Prompt dazu den Diff seit dem letzten Build, als Block `<<<SPEC CHANGES … SPEC CHANGES>>>`, mit dem Auftrag, den Code daran anzupassen. Die Tests laufen wieder.
   - Die Änderungen liegen danach uncommittet auf dem vorigen Build.
4. Das Skript postet `[KI] agentic-factory build überarbeitung=2 key=LL-123`. Lest ihn und `git diff`.

Wohin der amend-Aufruf schreibt:

| Framework | Was er ändern darf | Was danach in der Spec steht |
|---|---|---|
| OpenSpec | Den ganzen Change-Ordner: neue Aufgaben in `tasks.md`, dazu passt er `proposal.md`, die Specs unter `specs/` und `design.md` an | Die Spec beschreibt die Änderung mit |
| Spec Kit | Nur `tasks.md` | Die Änderung steht nur in den Aufgaben. `spec.md` und `plan.md` bleiben, wie sie waren |
| BMad | Nur die gebaute `SPEC.md` | Die Änderung steht nur im Abschnitt mit den neuen Aufgaben |

Bei OpenSpec darf der amend-Aufruf mehr, zur Vorsicht: `/openspec-apply-change` lehnte im Spike eine Aufgabe ab, die Proposal, Spec und Design nicht abdeckten (siehe [Was der Spike gezeigt hat](#was-der-spike-gezeigt-hat)).

**Keine neue Aufgabe.** Macht der amend-Aufruf aus den Kommentaren keine Aufgabe, etwa weil sie nichts zu bauen verlangen, und habt ihr die Spec nicht von Hand geändert, startet kein Build-Aufruf. Der Kommentar sagt dann: „Der Agent hat aus den Kommentaren keine neue Aufgabe abgeleitet. Darum hat agentic-factory.py nichts gebaut.“ Die Kommentare gelten trotzdem als bearbeitet.

**Nichts Neues.** Keine neuen `[Mensch]`-Kommentare und keine Änderung von Hand seit dem letzten `[KI]`-Kommentar: Der Lauf endet vor jedem Aufruf mit `nothing new since comment …`. Er postet nichts, kostet nichts und endet mit Exit-Code 0.

### Wann `spec` ablehnt

Nach dem ersten Build stoppt `spec` mit `a build exists for LL-123 (comment …); give feedback through build, or run spec --fresh`. Feedback nach dem Build läuft über `build`: Bei OpenSpec ändert es erst die Spec, dann den Code. Bei Spec Kit und BMad landet das Feedback nur in den Aufgaben, Spec und Plan bleiben dort hinter dem Code zurück.

### Neu anfangen mit `--fresh`

`spec --fresh` und `build --fresh` übergehen alle früheren `[KI]`-Kommentare des Modus und laufen wie beim ersten Mal. `spec --fresh` hat also wieder eine Bereitschaftsprüfung. Der neue Kommentar zählt wieder als Überarbeitung 1. `[Mensch]`-Kommentare davor gelten als bearbeitet. `spec --fresh` nach einem Build beendet die Build-Phase: Der nächste `build` ist wieder ein erster Build.

Nehmt `--fresh` nach einem verworfenen Build, einem gelöschten Spec-Ordner, einem Kommentar, dem das Skript nicht traut, und für eine Spec, die die Pipeline oder das Konto eines Kollegen gepostet hat.

### Wann das Skript stoppt

Jeder Stopp endet mit Exit-Code 2 und postet nichts.

| Meldung | Was passiert ist | Was ihr tut |
|---|---|---|
| `a build exists for … ; give feedback through build, or run spec --fresh` | `spec` nach dem ersten Build | Feedback über `build`. Oder `spec --fresh` |
| `the spec folder <name> is missing; restore it, or run spec --fresh` (bei `build`: `run build --fresh`) | Der Spec-Ordner aus dem vorigen Kommentar fehlt im Projekt | Den Ordner zurückholen, etwa per `git stash pop` oder Branch-Wechsel. Oder `--fresh` |
| `the change <name> has no spec files left; nothing is posted` | Im Spec-Ordner liegt keine Spec-Datei mehr | Die Dateien zurückholen. Oder `--fresh` |
| `the first build is gone: … ; run build --fresh` | Die Dateien des vorigen Builds unterscheiden sich nicht mehr vom `Start-Commit`, oder das Repo kennt den `Start-Commit` nicht | Den Build zurückholen. Oder `build --fresh` |
| `the spec changed since the last build, but the copy of the built spec is missing; run build --fresh` | Die Spec ist von Hand geändert, aber die Kopie unter `~/.factory-local/` fehlt, etwa auf einem anderen Rechner | Auf dem Rechner des vorigen Laufs weitermachen. Oder `build --fresh` |
| `the spec changed since the last build, but the copy of the built spec (…) doesn't match comment …; run build --fresh` | Die Kopie auf diesem Rechner gehört zu einem anderen Stand als der letzte Kommentar | `build --fresh` |
| `the comment … can't be trusted: it wasn't posted by the account running this script` oder `it was edited after it was posted` | Den letzten Ergebnis-Kommentar hat ein anderes Konto gepostet, oder jemand hat ihn bearbeitet | Mit dem Konto starten, das ihn gepostet hat. Oder `--fresh` |
| `the spec comment for … is longer than … characters even without the full spec text` | Schon der Diff ist zu lang für einen Jira-Kommentar (`jira.max_comment_chars`, 30.000 Zeichen) | In kleineren Schritten überarbeiten. Oder `spec --fresh` |
| `the build comment for … is longer than … characters even without the spec diff` | Schon die Liste der geänderten Dateien ist zu lang | In kleineren Schritten arbeiten |
| `the build comment … names no Start-Commit` oder `the … comment … names no valid change` | Der vorige Kommentar hat die Zeile `Start-Commit` oder `Change` nicht, etwa weil er älter ist | `--fresh` |
| `the latest result comment … is a spec posted after the build …; run build --fresh` | Nach dem letzten Build steht noch ein Spec-Ergebnis im Ticket | `build --fresh` |
| `--change … differs from the change … that comment … built; run build --fresh to build another change` | `--change` nennt einen anderen Change als der vorige Build | `--change` weglassen. Oder `build --fresh` |
| `the revision wrote another change besides …`, `the revision removed the spec folder …` oder `the amend call changed more than …` | Der Agent hat außerhalb seines Bereichs geschrieben oder den Spec-Ordner gelöscht | `git diff` lesen, die fremden Änderungen verwerfen, neu starten |
| `…/in/request.json: me names another account than the one this post step …` | In der Pipeline: Der `post`-Schritt läuft unter einem anderen Konto als der `fetch`-Schritt | Beide Schritte mit demselben Konto starten |

Hat der vorige Kommentar keine Zeile `Spec-Prüfsumme`, stoppt das Skript nicht. Es meldet `note: comment … has no Spec-Prüfsumme, so hand edits since then can't be told` und sieht keine Änderung von Hand.

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

Wollt ihr etwas ändern, antwortet mit einem Kommentar, der mit [Mensch] beginnt. Der nächste Lauf von build arbeitet ihn ein.

Start-Commit: 3f93817…

Spec-Prüfsumme: 9c1e…
~~~

| Zeile | Was sie sagt |
|---|---|
| Erste Zeile | Der Marker: `spec`, `spec überarbeitung=<n>`, `build` oder `build überarbeitung=<n>`. Der erste Kommentar ohne Nummer zählt als Überarbeitung 1 |
| `Change: <name>.` | Der Spec-Ordner. Spätere Läufe nehmen ihn von hier, nicht aus den geänderten Dateien |
| `Bearbeitet: Kommentar 10234, 10240.` | Die `[Mensch]`-Kommentare, die dieser Lauf bearbeitet hat. Sie zählen danach nicht mehr als neu |
| `Wollt ihr etwas ändern, …` | Wie ihr antwortet. Jeder Kommentar von `spec` und `build` hat diese Zeile |
| `Start-Commit: <sha>` | Nur bei `build`: der Commit, auf dem der erste Build startete. Überarbeitungen behalten ihn |
| `Spec-Prüfsumme: <sha256>` | Eine Prüfsumme über die Spec-Dateien des Change nach dem letzten Aufruf. Bei `build` nach dem Abhaken der Aufgaben, abgehakte Kästchen zählen also nicht als Änderung von Hand. Weicht die Spec später davon ab, hat sie jemand von Hand geändert |

Eine Spec-Überarbeitung sagt außerdem, ob die Spec von Hand geändert war, zeigt den Diff zur vorigen Fassung und die ganze Spec. Eine Build-Überarbeitung zeigt die Änderungen von Hand an der Spec, die geänderten Dateien und die Testzeile. Ändert diese Kommentare nicht: Einem geänderten Kommentar traut das Skript nicht mehr.

### Welche Kommentare zählen

- **`[Mensch]`-Kommentare:** die nach dem letzten `[KI]`-Kommentar von `spec` oder `build`, die keine `Bearbeitet`-Zeile nennt. Vor dem ersten Build bearbeitet sie `spec`, danach `build`. Kommentare nach der Spec, aber vor dem ersten Build, liest der erste Build nicht. Das Skript sagt das. Sollen sie zählen, überarbeitet erst die Spec mit `spec`.
- **`[KI]`-Kommentare:** Als Ergebnis zählen nur die von `spec` und `build`, und nur die, die das Konto gepostet hat, mit dem das Skript läuft, unbearbeitet. Über Jira fragt das Skript dafür einmal nach eurem Konto. Mit `--ticket-file` prüft es nur, ob ein Kommentar schon bearbeitet ist. Andere `[KI]`-Kommentare, die wie ein Ergebnis aussehen, nennt es in einer Notiz und lässt sie weg. Kommentare von `clarify` und `assess` prüft es nicht: Ein Ticket, das die Pipeline geklärt hat, bekommt lokal trotzdem Überarbeitungen.
- **Nach Fragen von `spec`:** Hat `spec` statt einer Spec Fragen gepostet, ist der nächste Lauf ein erster Lauf. Er bekommt die `[Mensch]`-Antworten danach in den Prompt.

### Die Kopien der Spec

Nach jedem Lauf von `spec` und `build` legt das Skript eine Kopie der Spec-Dateien ab: `~/.factory-local/<repo>/specs/<key>/<change>/spec-<n>/` und `build-<n>/`. Gegen diese Kopie rechnet es den Diff eurer Änderungen von Hand.

- **Fehlt die Kopie vor dem ersten Build,** postet `spec` die ganze Spec ohne Diff und sagt das.
- **Fehlt sie nach dem ersten Build** und ist die Spec von Hand geändert, stoppt `build`.
- **Bei BMad** gehört der PRD-Ordner unter `_bmad-output/planning-artifacts/prds/` zur Spec. Welcher es ist, weiß das Skript nur aus der Kopie des vorigen Laufs. Überarbeitungen mit BMad startet ihr deshalb auf dem Rechner, auf dem der vorige Lauf lief.

### Was der Spike gezeigt hat

Bevor wir die Überarbeitung von Builds programmiert haben, haben wir im Lab jedes Framework zweimal bauen lassen: bauen, eine Aufgabe von Hand ergänzen, wieder bauen. Dazu einen Build mit einer von Hand geänderten Spec. Ticket FLAB-41 im PHP-Projekt des Labs, alle Tests grün.

Das sind Beobachtungen aus je einem Lauf, keine Regeln: Jedes Framework lief einmal, mit einem Ticket. Die Änderung von Hand war ein umbenanntes Wort. Den Diff der Spec haben wir von Hand in den Prompt gelegt, bevor das Skript ihn baute. Die neue Aufgabe für OpenSpec lag absichtlich außerhalb der Spec.

| Framework | Zweiter Build mit einer neuen, offenen Aufgabe | Folgte einer von Hand geänderten Spec |
|---|---|---|
| OpenSpec | Zum Teil: übersprang erledigte Aufgaben, lehnte aber die Aufgabe ab, die Proposal, Spec und Design nicht nennen. Eine Aufgabe innerhalb der Spec setzte es um | Ja, einmal geprüft (ein umbenanntes Wort) |
| Spec Kit | Ja: setzte nur die neue Aufgabe um und hakte sie ab | Ja, einmal geprüft (ein umbenanntes Wort) |
| BMad | Ja: setzte nur den neuen Punkt in `SPEC.md` um, obwohl der Status schon `done` war | Ja, einmal geprüft (ein umbenanntes Wort) |

Credits je Schritt in diesem Lauf, gerundet:

| Framework | Spec | Build 1 | Build 2 | Build nach Änderung der Spec | Summe |
|---|---|---|---|---|---|
| OpenSpec | 20,5 | 17,7 | 7,9 | 5,8 | 64,6 (mit einem weiteren Build von 12,7) |
| Spec Kit | 47,2 | 19,8 | 12,1 | 5,3 | 84,4 |
| BMad | 30,9 | 73,9 | 47,5 | 44,3 | 196,6 |

Kein Aufruf erreichte die Grenze von 150 Credits. Der teuerste war der erste Build von BMad mit 73,9.

## Nach dem Build: Branch, Pull Request, Review

Das Skript endet bei uncommitteten Änderungen. Danach geht es weiter wie bei Code von Hand:

1. Startet den ersten Lauf auf einem eigenen Branch mit dem Schlüssel des Tickets im Namen, etwa `feature/LL-123-tags`. Nicht auf `main` oder einem geteilten Branch.
2. Lest `git diff`, startet die Tests, committet, pusht und öffnet einen Pull Request.
3. Der Review im Pull Request bleibt eure Freigabe. Die CI-Pipeline ist die Prüfung, die lokal fehlt. Ein `[KI]`-Kommentar ersetzt keines von beiden. Schreibt in den Pull Request, dass ein Agent den Code geschrieben hat.
4. Die `[Mensch]`-Runden sind für die Zeit vor dem Pull Request. Ist er offen, gehört der Review dorthin. Kommentare aus dem Review setzt ihr von Hand um. Oder ihr fasst sie in einem `[Mensch]`-Kommentar im Ticket zusammen und startet `build` noch einmal, im selben Klon und auf demselben Branch. Maßgeblich ist danach die Spec im Pull Request, nicht der Kommentar im Ticket.

**Übergabe an eine Kollegin.** Das Skript traut nur `[KI]`-Kommentaren des Kontos, das es gerade startet, und die Kopien der Spec liegen auf einem Rechner. Übernimmt jemand das Ticket, pusht ihr den Branch mit der Spec. Die neue Person startet auf diesem Branch mit `--fresh`. Dabei gehen die Zählung der Überarbeitungen und der Diff zur vorigen Fassung verloren. `spec --fresh` prüft die Bereitschaft noch einmal.

### Wer `config.json` und `readiness.md` pflegt

Die beiden Dateien legen fest, was der Agent darf und wann ein Ticket bereit ist. Ändert sie nur über einen Pull Request mit Review, wie Code. Das gilt auch nach `init --apply` und nach einer Auswertung von `blocked.jsonl`. Benennt eine Person, die die Dateien pflegt und über neue Freigaben entscheidet, etwa per `CODEOWNERS` für `factory/`.

## Sicherheit: Was ihr wissen müsst

**Kurz:** `agentic-factory.py` hat lokal nicht den Schutz der Pipeline: keinen eigenen Benutzer, keinen Container, keinen Prüfschritt vor dem Commit. Der Agent läuft als ihr. Startet das Skript deshalb so:

1. In einem eigenen Klon, auf einem eigenen Branch, mit allem committet.
2. In einer Shell ohne andere Tokens: keine Zugangsdaten für Cloud, Datenbank oder Registry, kein SSH-Agent mit Schlüsseln für Server. Copilot und jeder Befehl, den der Agent startet, sehen eure ganze Umgebung.
3. Nur mit Tickets, deren Text und Kommentare ihr kennt, ohne Personen- oder Kundendaten.
4. Nach jedem Lauf: erst die [Prüfung unten](#was-ihr-tut), dann `git diff`.

### Datenschutz

- **Was an GitHub Copilot geht:** Titel und Beschreibung des Tickets, die `[KI]`- und `[Mensch]`-Kommentare ohne Autor, und der Code, den der Agent im Projekt liest. GitHub gibt das an den Anbieter des Modells aus `config.json` weiter. Über den Jira-MCP sieht dazu jeder Lese-Aufruf das ganze Ticket, mit allen Kommentaren und ihren Autoren.
- **Keine Personen- oder Kundendaten, keine Zugangsdaten** in Tickets, die ihr durchschickt. Voraussetzung ist die Bestätigung eures Datenschutzbeauftragten, dass eure Erlaubnis für Copilot auch Copilot CLI und die Factory abdeckt (siehe [Checkliste](../../../01-erstworkshop/vorbereitung/checkliste.md)).
- **Was auf eurem Rechner bleibt:** Unter `~/.factory-local/<repo>/` liegen Ticket-Text, Kommentare mit Konto-IDs, die Ereignisse jedes Aufrufs mit Befehlen und Antworten des Modells, Kopien der Spec und `blocked.jsonl`. Das Skript löscht nichts davon. Wie ihr es löscht, steht unter [Die Dateien](#die-dateien).
- **Bevor ihr `blocked.jsonl` weitergebt,** löscht ihr Namen, Kundendaten und Secrets daraus, siehe [Blockierte Aufrufe](#blockierte-aufrufe-blockedjsonl).

### Was das Skript nicht verhindert

- **Eure Umgebung:** Copilot bekommt alle eure Umgebungsvariablen, nur die drei Jira-Variablen nicht. Code, den der Agent startet, etwa Tests oder Skripte von BMad und Spec Kit, läuft mit derselben Umgebung und eurer Anmeldung, auch bei git. Darum die Shell ohne andere Tokens.
- **BMad darf beliebigen Code starten:** `shell(uv:*)` gilt beim Spec schreiben und beim Bauen. Mit `uv` startet der Agent jedes Python-Programm. Beim Bauen darf BMad außerdem selbst committen. OpenSpec und Spec Kit haben keinen solchen Freibrief.
- **Der Agent kann ändern, was er starten darf:** Er darf Dateien schreiben, also auch euer Testskript, die Skripte unter `.specify/` oder euer `Makefile`, und sie danach starten. Ein Ticket-Text, der ihn dazu bringt, führt so eigenen Code aus. Das Skript warnt erst nach dem Lauf, mit `WARNING: protected paths changed`, wenn sich ein geschützter Pfad geändert hat, etwa `.specify/` oder `.github/`. Ein geändertes `Makefile` meldet es nicht, außer ihr nehmt es in `protected_paths` auf.
- **Die Prüfung des Testbefehls ist keine Sicherheitsgrenze.** Sie fängt Fehler in der Konfiguration. Die Freigabe `shell(make test:*)` endet aber auf `:*`: Der Agent darf Argumente anhängen, bei Make also weitere Ziele. Und die Tests führen Code aus, den der Agent geschrieben hat.
- **`npm` ist nicht ganz verboten.** `deny_tools` verbietet `npm install`, `npm i`, `npm ci`, `npm exec` und `npx`, sonst liefe `npm test` nicht. Ein Verbot schlägt jede Freigabe. Andere Paketmanager verbietet die Vorlage nicht. `init` kann Verbote für euren Stack vorschlagen.
- **Lesende Befehle in `spec` und `build`.** Jeder Aufruf dieser Schritte bekommt die `read_tools` aus `config.json`, auch die Aufrufe, die eine Spec oder einen Build nach `[Mensch]`-Kommentaren überarbeiten: `ls`, `cat`, `head`, `tail`, `wc`, `grep`, `pwd`, `diff`, `stat` und `cd`, je als `shell(<befehl>:*)`. Die Bereitschaftsprüfung, `clarify` und `init` bekommen sie nicht: Sie haben keine Shell.
- **Was in `read_tools` fehlt, mit Absicht.** Diese Befehle sehen lesend aus, können aber schreiben oder Befehle starten: `find` (`-exec`, `-delete`), `sed` (`-i`), `awk` (`system()`), `xargs`, `rg` (`--pre`), `tree` (`-o`), `sort` (`-o`). Auch kein `git`-Befehl: `git diff`, `git log` und `git show` schreiben mit `--output=` Dateien, und `.git/config` kann jeden `git`-Aufruf zum Start von Code machen, auch `git status`. Eine Freigabe passt immer auf den Anfang eines Befehls. Eine gefährliche Option lässt sich also nicht einzeln verbieten. Braucht euer Agent `find`, tragt ihr `shell(find:*)` von Hand in `read_tools` ein. Dann kann er über `find` auch Dateien löschen (`-delete`) und Befehle starten (`-exec`).
- **`cat` und `grep` lesen auch außerhalb des Projekts,** etwa in eurem Home-Ordner. Copilots eigenes Lese-Werkzeug kann das nicht. Kopiert der Agent so etwas in eine Spec, fängt es nur der Token-Scan vor dem Posten.
- **Lesende Befehle ohne Freigabe.** Copilot kann in `spec` und `build` auch lesende Befehle außerhalb der Freigabe ausführen. Ein Verbot von `shell` würde dort alle Shell-Werkzeuge mit abschalten.
- **`.git/`:** Eine geänderte `.git/config` oder ein neuer Hook kann jeden `git`-Befehl zum Start von Code machen. Das Skript startet git deshalb ohne fsmonitor, Hooks, externen Diff und Pager. Es vergleicht `.git/config`, `config.worktree`, die Hooks und eingebundene Konfigurationsdateien vor jedem `git`-Befehl und nach jedem Copilot-Aufruf mit dem Stand beim Start. Ändert sich etwas, stoppt es vor dem nächsten `git`-Befehl: `the work call changed .git/config; nothing is posted. … inspect these files with cat and ls before you run any git command`. Bindet `.git/config` eine Datei im Projekt ein (`include.path`), stoppt es vor dem ersten Aufruf. Das ist zusätzlicher Schutz, keine Grenze.
- **Ignorierte Dateien:** Das Skript vergleicht nur, was `git status` zeigt. Änderungen in ignorierten Dateien, etwa `.env`, sieht es nicht.
- **Die Ereignisse von Copilot:** `blocked.jsonl`, die Shell-Prüfung und die Testzeile lesen die JSON-Ereignisse von Copilot CLI 1.0.115. Sehen sie anders aus oder meldet Copilot eine andere Version, schreibt das Skript `WARNING: Copilot … events not recognized` oder `WARNING: Copilot … is not the tested 1.0.115`. Dann kann es dort etwas übersehen.

Verhindern kann nur Copilots Freigabeliste, mit den Verboten in `deny_tools`. Alles andere bemerkt erst danach: die geschützten Pfade, die Warnungen nach dem Lauf und eure Durchsicht von `git diff`. `spec`, `build` und `clarify` posten ihr Ergebnis aber sofort. Lest ihr `git diff`, steht der Kommentar schon im Ticket. Wollt ihr erst lesen, startet mit `--no-post`.

Neu, seit das Skript in Jira schreibt:

- **Kommentare erscheinen unter eurem eigenen Jira-Konto.** Lokal postet das Skript mit eurer Anmeldung beim Jira-MCP. Jeder Kommentar beginnt mit `[KI]` und sagt, dass `agentic-factory.py` ihn geschrieben hat. Ein `[KI]`-Kommentar ist nie eine Freigabe.
- **Ein Werkzeug pro Jira-Aufruf.** Jeder Jira-Aufruf ist ein eigener, kurzer Copilot-Aufruf. Die Freigabe gilt nur für ein Werkzeug des MCP-Servers, etwa `atlassian(getJiraIssue)`. Alle anderen MCP-Server sind aus, Lesen und Schreiben von Dateien auch. Er läuft in einem Ordner außerhalb des Projekts. Die Arbeitsaufrufe (`init`, `assess`, `clarify`, `spec`, `build`) haben keine Jira-Werkzeuge. Die kurzen Jira-Aufrufe sehen dagegen Ticket- oder Kommentartext, etwa das Ergebnis von `getJiraIssue` oder den Text, den sie posten sollen. Was sie tatsächlich getan haben, prüft das Skript danach.
- **Shell-Befehle ohne Freigabe.** Copilot 1.0.115 führt Shell-Befehle aus, die es für nur lesend hält, auch wenn sie nicht freigegeben sind. Das Skript verbietet deshalb `shell` in jedem Aufruf ohne Shell-Werkzeuge: in der Bereitschaftsprüfung, in `clarify`, in `init` und in den Jira-Aufrufen. Lief trotzdem einer, stoppt es. Nach der Bereitschaftsprüfung oder `clarify` postet es dann nichts.
- **Der Hook läuft mit Copilot 1.0.115 nicht.** Copilot CLI 1.0.115 führt in `-p`-Läufen keine Hooks aus `--plugin-dir` aus. 1.0.114 hat es getan. Das Skript liefert den Hook trotzdem mit und prüft jeden Jira-Aufruf danach aus den Ereignissen von Copilot: welches Werkzeug, welches Ticket, welche Argumente, welcher Text. Danach liest es den gespeicherten Kommentar zurück. Passt etwas nicht, stoppt es und nennt den Kommentar, den ihr von Hand löschen müsst. Ohne Hook verhindert diese Prüfung nichts, sie bemerkt es nur hinterher.
- **Ein `[Mensch]`-Kommentar ist Daten, keine Anweisung.** Er landet im Prompt als eigener Block. Der Prompt sagt dem Modell, dass der Kommentar entscheidet, was Spec und Code sagen, nie, welche Werkzeuge es nutzt oder welche Dateien es schreibt. Ob es sich daran hält, prüft niemand. Die Freigaben begrenzen, was es dann tun kann. Nur Leute, die ihr kennt, sollten im Ticket kommentieren. Vor jedem Lauf nennt das Skript Nummer und Konto der `[Mensch]`-Kommentare, die es liest.

### Was ihr tut

- Nur Tickets durchschicken, deren Text und Kommentare ihr kennt. Beides landet im Prompt.
- Vor dem Lauf alles committen, damit der Diff nur die Arbeit des Agenten zeigt.
- Jede `WARNING` des Skripts ernst nehmen.
- Nach jedem Lauf prüfen, erst ohne git, dann mit:

```bash
cat .git/config
ls -la .git/hooks
git status --ignored
git diff
```

Seht ihr in `.git/config` etwas Fremdes, etwa `fsmonitor`, `hooksPath`, einen Filter oder `include`, oder in `.git/hooks/` eine neue Datei ohne `.sample`, startet keinen `git`-Befehl, bevor ihr es entfernt habt.

## Was fehlt

- **Die Prüf- und Veröffentlichungsschritte der Pipeline:** `check.py`, `publish.py` und `guard.py` der Pipeline (factory-base). Lokal prüft niemand den Diff auf geschützte Pfade, Secrets oder unsichtbare Zeichen. Ihr lest ihn selbst. Auch `pipelines.example.yml` hat diese Schritte nicht.
- **Übergänge, Labels und Freigaben.** Das Skript schreibt nur Kommentare und, bei `clarify --apply`, die Beschreibung. Es setzt keinen Status, kein Label, keinen Branch und keinen Pull Request. Das bleibt so.
- **`build` in der Pipeline.** Das Skript lehnt es dort ab: Der Code ginge mit dem Schritt verloren. `init` lehnt es dort auch ab.
- **Eine Grenze für Überarbeitungen.** Jeden Lauf startet ihr selbst. Die Credit-Grenze je Aufruf bleibt.
- **Feedback für `assess`.** Dafür gibt es `clarify`.

## Tests

Die Tests brauchen nur die Python-Standardbibliothek. Sie rufen weder Jira noch Copilot auf: Ein Ersatz-`copilot` und ein lokaler Test-Server stehen dafür. Im Workshop-Repo:

```bash
python3 -I -B -m unittest discover -s 02-agent-factory/einrichtung/factory/tests -t 02-agent-factory/einrichtung/factory
```

Ein Teil der Tests vergleicht den Code mit `factory-base`: Prompts und Flags mit `agent.py`, die kopierten Prüfungen mit `common.py` und die eigenen Kommentare mit dem Marker von `guard.py`. Prompts und Flags vergleichen sie mit einer Konfiguration wie der des Labs (`LAB_CFG` in `tests/fakes.py`): mit `./bin/phpunit`, ohne `read_tools`, mit dem alten Plan-Prompt von Spec Kit und den alten Texten der Bereitschaftsprüfung und der Regeln. Die `config.json` der Vorlage weicht davon ab. Diese Tests brauchen einen Klon des Lab-Repos. Ohne `FACTORY_BASE` überspringen sie sich:

```bash
git clone --depth 1 --branch factory-base https://bitbucket.org/factory-lab/factory-lab.git /tmp/factory-lab
FACTORY_BASE=/tmp/factory-lab/factory python3 -I -B -m unittest discover -s 02-agent-factory/einrichtung/factory/tests -t 02-agent-factory/einrichtung/factory
```

## Aktualisieren

`factory-base` ist nur noch die Referenz. Kopiert die Dateien von dort nicht mehr über diese hier.

- **Kopierte Blöcke** stehen alle in `agentic_factory/copied.py`, markiert etwa mit `# --- copied from factory/common.py`. Ändert sich `factory-base`, schlagen die Tests mit `FACTORY_BASE` fehl. Dann übernehmt ihr die Änderung von Hand.
- **Die Umwandlung der Beschreibung** steht auch dort. Sie ist aus `jira_ticket.py` des Skills [`schreibe-ticket`](../../werkzeuge/schreibe-ticket/README.md) kopiert. Ein Test vergleicht beide, auch ohne `FACTORY_BASE`.
- **Alles andere** pflegt ihr hier.

## Herkunft und Stand

- **Quelle:** `agentic-factory.py` hieß früher `local.py`. Es ist angepasst aus `local.py` im Lab-Repo [factory-lab](https://bitbucket.org/factory-lab/factory-lab/src/factory-base/factory/), Branch `factory-base`, Commit `a414237`, Ordner `factory/`. Es ist keine unveränderte Kopie mehr.
- **Stand:** 25. November 2026, Copilot CLI 1.0.115, Modell `claude-sonnet-5.5`.
