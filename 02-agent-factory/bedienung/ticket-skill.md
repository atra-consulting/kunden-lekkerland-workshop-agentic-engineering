# Tickets mit dem Skill schreiben

Der Copilot-Skill `schreibe-ticket` macht aus einer Absicht ein oder mehrere Jira-Tickets, die die Factory ohne Rückfrage umsetzen kann. Du startest ihn lokal in Copilot CLI, in deinem Projekt.

- Er liest zuerst selbst den Code: Gibt es das schon? Widerspricht es dem heutigen Verhalten? Was würde es berühren? Gibt es Doku zur fachlichen Domäne, liest er sie mit.
- Dann fragt er mit dem SDD-Framework deines Projekts nach: Spec Kit, OpenSpec oder BMad.
- Ist es zu groß für einen Pull Request, schlägt er ein Epic mit mehreren Tickets vor.
- Er prüft jeden Entwurf mit der Prüfung der Factory selbst (`factory/agentic-factory.py assess`), so wie später der Spec-Lauf.
- Er zeigt dir alle Texte, legt die Tickets nach deinem einen Ja in Jira an und räumt danach auf. Dein Repository ist danach wie vorher.
- Nach Jira kommt er über den Jira-MCP-Server mit Anmeldung im Browser, ohne Token. Wer ein API-Token hat, kann stattdessen das Skript `jira_ticket.py` nehmen.

Der Skill ist **optional** und kein Teil der Factory. Er läuft auf deinem Rechner, mit deiner Copilot-Lizenz. Die Factory startet erst, wenn du das Ticket in Jira nach „Bereit“ schiebst.

## Was du brauchst

- Copilot CLI 1.0.114 oder neuer, mit Claude Sonnet 5.5.
- Python 3, nur die Standardbibliothek. macOS: `python3`. Windows: `py -3`.
- Git und ein Projekt, in dem schon ein SDD-Framework installiert ist, wie am ersten Tag.
- Einen Jira-Zugang, der im Projekt Tickets anlegen darf: über den Atlassian-MCP-Server (Anmeldung im Browser) oder mit einem API-Token.
- Für die Prüfung der Factory: den Ordner `factory/` im Projekt, mit `agentic-factory.py`. Ohne ihn prüft der Skill nur selbst.

## Einrichten

### 1. Skill ins Projekt kopieren

Kopiere den Ordner `02-agent-factory/werkzeuge/schreibe-ticket/` nach `.github/skills/schreibe-ticket/` in deinem Projekt. Den Unterordner `tests/` brauchst du dort nicht.

macOS und Linux:

```sh
mkdir -p .github/skills
cp -R <workshop-repo>/02-agent-factory/werkzeuge/schreibe-ticket .github/skills/
rm -rf .github/skills/schreibe-ticket/tests
```

Windows (PowerShell, nicht getestet):

```powershell
New-Item -ItemType Directory -Force .github\skills | Out-Null
Copy-Item -Recurse <workshop-repo>\02-agent-factory\werkzeuge\schreibe-ticket .github\skills\
Remove-Item -Recurse .github\skills\schreibe-ticket\tests
```

### 2. Konfiguration schreiben

Leg `.github/schreibe-ticket.json` an. Vorlage: `schreibe-ticket.example.json` im Skill-Ordner. Eine ältere Datei `.github/ticket-schreiben.json` liest das Skript weiter und weist mit einem Hinweis auf den neuen Namen hin.

```json
{
  "framework": "speckit",
  "jira_project": "FLAB",
  "issue_type": "Task",
  "labels": [],
  "test_command": "./bin/phpunit"
}
```

| Feld | Bedeutung |
|---|---|
| `framework` | `speckit`, `openspec` oder `bmad`. Der Skill fragt mit diesem Framework nach und setzt das Label `sdd-<framework>`. Damit nimmt die Factory später dasselbe Framework. |
| `jira_project` | Der Projektschlüssel in Jira. |
| `issue_type` | Der Vorgangstyp, meist `Task`. |
| `labels` | Optional: weitere Labels für jedes Ticket. |
| `test_command` | Optional: der Testbefehl deines Projekts, zum Beispiel `make test`. Er steht dann im Ticket. |
| `confluence_space` | Optional: der Schlüssel des Confluence-Bereichs mit euren fachlichen Domänen. Mit einem Confluence-MCP-Werkzeug sucht der Skill dort die Domäne der Absicht. |
| `module_docs` | Optional: der Ordner im Repo mit der Doku der Module, zum Beispiel `docs/module/`. |

Fehlt die Datei, fragt der Skill einmal nach den Werten und bietet an, sie zu schreiben.

### 3. Committen und prüfen

Committe Skill und Konfiguration. Dann startet jeder Lauf mit einem sauberen `git status`, und das Aufräumen ist eindeutig.

```sh
git add .github/skills/schreibe-ticket .github/schreibe-ticket.json
git commit -m "Skill schreibe-ticket"
copilot skill list        # zeigt schreibe-ticket
```

### 4. Jira-Zugang

Der Skill kennt zwei Wege. Hat Copilot ein Jira-Werkzeug eines MCP-Servers, nimmt er das. Sonst nimmt er `jira_ticket.py` mit einem API-Token.

#### Weg A: Atlassian-MCP-Server, Anmeldung im Browser

Du brauchst kein Token. Füg den Server in deine Copilot-Konfiguration `~/.copilot/mcp-config.json` ein (Windows: `%USERPROFILE%\.copilot\mcp-config.json`):

```json
{
  "mcpServers": {
    "atlassian": {
      "type": "http",
      "url": "https://mcp.atlassian.com/v1/mcp",
      "tools": ["*"]
    }
  }
}
```

Oder in Copilot: `/mcp`, dann „Add MCP server…“, mit derselben URL.

Beim ersten Start öffnet Copilot die Anmeldung von Atlassian im Browser. Melde dich an und erlaube den Zugriff auf eure Site. Der Browser zeigt dann „Authorization Successful“. Prüf in Copilot mit `/mcp`, dass `atlassian` verbunden ist. Zeigt Copilot „requires authentication“, wähl in `/mcp` bei `atlassian` den Punkt „Authenticate“.

Im Lab lief die Anmeldung beim ersten Versuch in eine Zeitüberschreitung („OAuth callback timeout“). „Authenticate“ ein zweites Mal reichte dann. Lehnt Atlassian die Anmeldung ab, frag euren Atlassian-Admin, ob der MCP-Server für eure Site erlaubt ist.

Der Skill nutzt dann die Werkzeuge `getAccessibleAtlassianResources`, `createJiraIssue` und `getJiraIssue`. Copilot fragt vor jedem Aufruf.

#### Weg B: API-Token und `jira_ticket.py`

Der Skill liest drei Umgebungsvariablen. Setz sie in der Shell, in der du `copilot` startest. **Schreib das Token nie in den Chat und nie in eine Datei im Repository.**

| Variable | Jira Cloud | Jira Data Center |
|---|---|---|
| `JIRA_BASE_URL` | `https://<site>.atlassian.net`. Mit einem Scoped Token: `https://api.atlassian.com/ex/jira/<cloud-id>` | Die Server-URL |
| `JIRA_EMAIL` | Die E-Mail-Adresse deines Kontos | Nicht setzen |
| `JIRA_API_TOKEN` | API-Token, von https://id.atlassian.com/manage-profile/security/api-tokens | Personal Access Token |

Ist `JIRA_EMAIL` gesetzt, nimmt der Skill Jira Cloud an: Basic-Auth, REST API 3. Sonst Data Center: Bearer-Token, REST API 2. Nur `https://` ist erlaubt.

Die `<cloud-id>` für Scoped Tokens zeigt `https://<site>.atlassian.net/_edge/tenant_info`. Die Ticket-Links baut der Skill trotzdem mit der normalen Site-Adresse.

macOS und Linux (zsh oder bash):

```sh
export JIRA_BASE_URL='https://<site>.atlassian.net' JIRA_EMAIL='<deine E-Mail>'
read -s JIRA_API_TOKEN && export JIRA_API_TOKEN     # Token einfügen, Enter
```

Windows (PowerShell 7, nicht getestet):

```powershell
$env:JIRA_BASE_URL = 'https://<site>.atlassian.net'
$env:JIRA_EMAIL = '<deine E-Mail>'
$env:JIRA_API_TOKEN = Read-Host -MaskInput 'Token'
```

Prüf den Zugang:

```sh
python3 -I .github/skills/schreibe-ticket/jira_ticket.py pruefen
```

Die Ausgabe nennt Jira-Adresse, deinen Namen, Projekt, Vorgangstyp und Labels, nie das Token. Am Ende steht `OK`.

## So läuft es

Starte `copilot` im Projekt und gib die Absicht direkt hinter dem Befehl ein:

```text
/schreibe-ticket Leser sollen sehen, wie lange sie für einen Artikel brauchen.
```

| Schritt | Was passiert |
|---|---|
| 1. Konfiguration und Arbeitsstand | Der Skill liest die Konfiguration, merkt sich den Stand des Repositorys (`arbeitsstand.py merken`), wählt den Weg nach Jira und schaut, ob es `factory/agentic-factory.py` gibt. |
| 2. Absicht | Er nimmt deine Worte auf, noch ohne sie zu verbessern. |
| 3. Code-Erkundung | Er liest Routen, Controller, Templates, Entities und Tests, dazu Modul-Doku und Confluence, falls eingerichtet. Gibt es das schon oder widerspricht es dem Code, sagt er es sofort, mit Datei und Zeile. |
| 4. Nachfragen mit dem Framework | Das Framework stellt die Fragen. Danach nennt der Skill die Annahmen, die das Framework ohne Frage getroffen hat, und lässt sie dich bestätigen. |
| 5. Reife-Check | Eine Tabelle mit allen Kriterien, je „erfüllt“ oder „offen“. Bei `too_big` schlägt er ein Epic mit mehreren Tickets vor. |
| 6. Ticket-Texte | Je Ticket: Ziel, Akzeptanzkriterien, Nicht Teil des Tickets, Hinweise. Bei einer Aufteilung dazu ein kurzes Epic. |
| 7. Prüfung durch die Factory | `factory/agentic-factory.py assess` bewertet jeden Entwurf. Du siehst alle Texte und Urteile und sagst einmal Ja oder änderst sie. |
| 8. In Jira anlegen | Über Jira-MCP oder `jira_ticket.py`. Erst das Epic, dann die Tickets darunter. Alles startet in „Definition“. Das startet noch keinen Lauf. |
| 9. Aufräumen | `arbeitsstand.py aufraeumen --ja` entfernt die Dateien des Frameworks, die Entwürfe und die Prüfdateien. `git status` ist wie vorher. |

Brichst du ab, springt der Skill direkt zu Schritt 9.

Copilot fragt vor jedem Befehl. Lies die Befehle. Der Skill selbst ändert keinen Produktcode und committet nichts. Schreibt Copilot in `src/`, `templates/` oder `tests/`, lehne ab.

## Was jedes Framework liefert

Die Code-Erkundung in Schritt 3 gehört dem Skill, nicht dem Framework. Spec Kits Specify-Schritt beschreibt zum Beispiel absichtlich nur das Was und Warum, nicht das Wie. Die Fragen in Schritt 4 kommen vom Framework:

| Framework | Skills | Art der Fragen | Ergebnis, das der Skill danach löscht |
|---|---|---|---|
| Spec Kit | `speckit-specify`, dann `speckit-clarify` | Wenige gezielte Fragen mit Antwortvorschlag. Specify trifft viele Annahmen selbst. | `specs/<NNN>-<name>/` |
| OpenSpec | `openspec-explore`, dann `openspec-propose` nur bis Proposal und Spec-Delta | Gesprächspartner, der den Code liest und Optionen zur Wahl stellt. | `openspec/changes/<name>/` |
| BMad | `bmad-forge-idea`, dann `bmad-spec` (Express) | Personas greifen die Idee an, bis sie „Hardened“ ist. | `_bmad-output/forge/…`, `_bmad-output/specs/…` |

`design.md`, `tasks.md` und den Plan schreibt später die Factory. Der Skill hört vorher auf.

### Auszüge aus den Lab-Tests

Alle Tests liefen am 23.11.2026 im Lab, in Kopien von `sdd-demo-speckit`, `sdd-demo-openspec` und `sdd-demo-bmad`, mit Copilot CLI 1.0.114 und Claude Sonnet 5.5.

**Spec Kit**, Absicht „Leser sollen sehen, wie lange sie für einen Artikel brauchen.“ Die Code-Erkundung fand: „Lesezeit fehlt bisher: Artikel und Listenkarte zeigen nur Datum und Autor.“ Dann `speckit-clarify`:

```text
Frage 1 von Speckit-Clarify: Mit welcher Lesegeschwindigkeit und welchem Text soll die Lesezeit
angezeigt werden? (Wichtig, damit die Tests einen festen Wert prüfen können.) Mein Vorschlag:
200 Wörter pro Minute, aufgerundet, mindestens 1, Text „5 Min. Lesezeit“.
```

Spec Kit fragte nur dieses eine Mal. Die Übersetzung in „die Sprache des Besuchers“ hatte es selbst angenommen. Erst die Antwort des Product Owners machte daraus „nur Deutsch und Englisch“. Seitdem zeigt der Skill solche Annahmen ausdrücklich. Ticket: FLAB-28.

**OpenSpec**, Absicht „Wir brauchen einen RSS-Feed, damit Leser neue Artikel abonnieren können.“ Die Code-Erkundung schlug vor jeder Framework-Frage an:

```text
Den RSS-Feed gibt es bereits (Route `blog_rss` im BlogController, Template, Auto-Discovery-Link
und Test), das Kriterium `already_exists` ist also erfüllt.
Der Feed existiert schon, ganz (siehe oben). Wie weiter?
```

Die neue Absicht „nur Artikel zu einem Tag abonnieren“ gab es auch schon (`/blog/rss.xml?tag=…`). `openspec-explore` fand die echten Lücken und ließ wählen:

```text
Der Tag-Feed funktioniert technisch schon. Was soll das Ticket konkret ändern?
  ✓ Unbekannter Tag liefert 404 statt Feed mit allen Artikeln
  ✓ Feed-Titel enthält den Tag-Namen (z. B. 'Blog - symfony')
  • Auto-Discovery-Link im head zeigt auf den Tag-Feed, wenn ?tag= aktiv ist
```

Das Ticket nennt das alte Verhalten, das sich bewusst ändert, mit Datei und Zeile. So erfüllt es `contradicts_code`. Ticket: FLAB-29.

**BMad**, Absicht „Tags sollen nicht doppelt entstehen, nur weil jemand sie unterschiedlich schreibt.“ Die Code-Erkundung fand den Grund: Der Vergleich in `TagArrayToStringTransformer` beachtet Groß- und Kleinschreibung. `bmad-forge-idea` fragte zuerst, was als gleich gilt. Dann brachten zwei Personas Einwände:

```text
Winston und Dr. Brandt haben zwei Fragen aufgeworfen: welche Schreibweise bei Tags gelten soll
(ich schlage vor, ein bestehendes `Hello` gewinnt gegen `hello`), und ob Altdaten und den exakten
`?tag=`-Filter in `BlogController.php:57` im Ticket anfassen. Ich lasse beides außerhalb des
Tickets, weil das eine Migration wäre, und frage dich, ob das für dich passt.
```

Das Ticket hat Testfälle wie „`world, HELLO, Foo` ergibt `World`, `Hello` und neu `Foo`“. Migration und Index sind ausdrücklich nicht Teil. Ticket: FLAB-30.

## Beobachtet im Lab

Ein Test pro Framework, mit einem Menschen, der wie ein Product Owner antwortet. Die Zahlen sind Beobachtungen aus je einem Lauf, keine Zusagen.

| Framework | Ticket | AI Credits | API-Zeit | Dialoge mit der Person |
|---|---|---|---|---|
| Spec Kit | FLAB-28 | 29,42 | 4 min 34 s | 3: eine Frage von Clarify, eine Änderung am Entwurf, die Freigabe |
| OpenSpec | FLAB-29 | 28,87 | 4 min 10 s | 4: „Wie weiter?“ nach dem `already_exists`-Fund, Umfang, zwei Annahmen, die Freigabe |
| BMad | FLAB-30 | 42,80 | 5 min 16 s | 4: zwei Fragen der Forge, die Annahmen, die Freigabe |

Ein erster Spec-Kit-Lauf mit einer älteren Fassung des Skills übersprang das Framework und kostete bis zum Abbruch 25,99 Credits. Seitdem ist Schritt 4 Pflicht.

Spätere Läufe mit der aktuellen Fassung, im Lab-Repo mit `factory/local.py` (heute `agentic-factory.py`):

| Lauf | Tickets | AI Credits | Ergebnis |
|---|---|---|---|
| Spec Kit, Absicht mit drei Funktionen | Epic FLAB-32, Tickets FLAB-33 bis FLAB-35 | 60,72 für den Skill, dazu 28,03 für drei Prüfungen (13,19, 6,28 und 8,56) | Aufteilung vorgeschlagen, alle drei Tickets „ready“, `parent` und Labels in Jira geprüft. |
| Nur Schritt 8 über Jira-MCP, ohne Token | FLAB-36 | 14,03 | Ticket in „Definition“ mit `sdd-openspec` und `test-nacht`. |
| Nur die Prüfung, `local.py assess --key` | FLAB-30 | 11,08 | „ready“ in 11 Sekunden. |
| Spec Kit, ganzer Lauf, Absicht „Kommentaranzahl in der Artikelliste“ | FLAB-38 | 37,33 | Annahmen, Reife-Tabelle und Ticket-Text standen im Frageformular. Eigener Check, weil `factory/local.py` im Demo-Repo fehlt. |

Dazu kommt die Zeit, in der du liest und antwortest. Im Lab dauerte ein Lauf mit einem Ticket insgesamt etwa 5 bis 10 Minuten, der Lauf mit Epic und drei Tickets etwa 20 Minuten.

## Die Kriterien ändern

Der Skill prüft dieselben Kriterien wie die Factory vor dem Spec-Lauf. Liegt `factory/readiness.md` im Projekt, liest der Skill diese Datei. Änderst du die Kriterien dort, gilt die Änderung für beide. Wie das geht, steht in [Ticket-Bereitschaft](ticket-bereitschaft.md), Abschnitt „So passt ihr die Kriterien an“.

Ohne `factory/readiness.md` nutzt der Skill die sechs Kriterien aus seiner `SKILL.md`: `missing_detail`, `untestable`, `already_exists`, `contradicts_code`, `protected_paths`, `too_big`.

Willst du ein Ticket trotz offener Punkte anlegen, schreibt der Skill den Abschnitt „Offene Punkte“ dazu. Die Factory schickt so ein Ticket sehr wahrscheinlich nach „Klärung nötig“.

## Zu groß: ein Epic und mehrere Tickets

Ist eine Absicht `too_big`, ist das kein Fehler. Der Skill schlägt eine Aufteilung vor: ein Epic für das Ganze und darunter Tickets, jedes ein Pull Request groß. Er schreibt alle Entwürfe, lässt jedes Ticket von der Factory prüfen und zeigt dir alles zusammen. Nach einem Ja legt er erst das Epic an, dann die Tickets darunter.

- Das Epic hat Ziel, Umfang und „Nicht Teil“, aber keine Akzeptanzkriterien. Es bekommt kein `sdd-`-Label, denn die Factory baut keine Epics.
- Jedes Ticket sagt unter „Nicht Teil des Tickets“, welche Teile die anderen Tickets abdecken.
- Du schiebst jedes Ticket einzeln nach „Bereit“.

Mit `jira_ticket.py` sehen die Befehle so aus:

```sh
python3 -I .github/skills/schreibe-ticket/jira_ticket.py anlegen --entwurf ticket-entwurf-epic.md --typ Epic --ohne-sdd-label
python3 -I .github/skills/schreibe-ticket/jira_ticket.py anlegen --entwurf ticket-entwurf-1.md --parent FLAB-32
```

Im Lab, mit der Absicht „Die Artikelseite soll Lesern mehr bieten: Lesezeit anzeigen, Links zum vorherigen und nächsten Artikel, und eine Liste ähnlicher Artikel mit gleichen Tags.“ fragte `speckit-clarify` nach Sortierung und Obergrenze der ähnlichen Artikel. Dann schlug der Skill vor:

```text
Aufteilen wie vorgeschlagen (Epic + 3 Tickets)? Und stimmen die 6 Annahmen?
```

Ergebnis: Epic FLAB-32 mit FLAB-33 (Lesezeit), FLAB-34 (vorheriger und nächster Artikel) und FLAB-35 (ähnliche Artikel).

## Die Prüfung der Factory vor dem Anlegen

Gibt es `factory/agentic-factory.py` im Projekt, lässt der Skill jeden Ticket-Entwurf von der Prüfung der Factory bewerten, bevor er etwas anlegt. Es ist derselbe Copilot-Aufruf mit demselben Prompt und denselben Kriterien wie im Spec-Lauf. Mehr zu `agentic-factory.py` steht in [Lokal ausführen](lokal-ausfuehren.md).

```sh
python3 -I .github/skills/schreibe-ticket/jira_ticket.py pruefdatei --entwurf ticket-entwurf-1.md
python3 -I factory/agentic-factory.py assess --ticket-file ticket-entwurf-1.json
```

- `pruefdatei` schreibt den Entwurf so als JSON, wie die Factory ihn später aus Jira liest. Der Schlüssel ist ein Platzhalter, etwa `FLAB-0`.
- Exit-Code 0 heißt „ready“, Exit-Code 4 heißt „not_ready“ mit Gründen und Fragen.
- Ein Ticket mit „not_ready“ legt der Skill nur an, wenn du ausdrücklich „trotzdem anlegen“ sagst. Dann schreibt er die Gründe unter „Offene Punkte“.
- Ohne `factory/agentic-factory.py` gilt der eigene Reife-Check des Skills.

Im Lab kostete eine Prüfung 6 bis 13 Credits und 8 bis 13 Sekunden API-Zeit.

## Wenn etwas schiefgeht

| Meldung | Bedeutung und Abhilfe |
|---|---|
| `Umgebungsvariable fehlt: JIRA_API_TOKEN` | Die Variable fehlt in der Shell, in der Copilot läuft. Beende Copilot, setz die Variable, starte neu. |
| `HTTP 401` bei `/myself` | Token oder E-Mail falsch, oder ein Scoped Token mit der Site-URL. Nimm die URL `https://api.atlassian.com/ex/jira/<cloud-id>`. |
| `Vorgangstyp 'Story' fehlt im Projekt` | `issue_type` in der Konfiguration anpassen. Die Meldung nennt die vorhandenen Typen. |
| `HTTP 400` beim Anlegen | Jira lehnt ein Feld ab, die Meldung nennt es. Oft ein Pflichtfeld im Projekt, das der Skill nicht setzt. |
| `arbeitsstand.py` endet mit Exit-Code 1 | Es gibt neue Commits, oder eine Datei ließ sich nicht zurücksetzen. Das Skript fasst Commits nie an. Prüf mit `git log` und `git status` selbst. |
| `arbeitsstand.py merken` endet mit Exit-Code 3 | Es gab schon Änderungen. Sie bleiben unberührt. Besser: vorher committen oder mit `git stash` sichern. |
| `OAuth callback timeout` bei `atlassian` | Die Anmeldung im Browser kam zu spät an. In `/mcp` bei `atlassian` noch einmal „Authenticate“ wählen. |
| `MCP server 'atlassian' requires authentication` | Copilot ist noch nicht angemeldet. `/mcp`, dann `atlassian`, dann „Authenticate“. |
| `agentic-factory.py` endet mit einem Exit-Code außer 0 und 4 | Ein Fehler, kein Urteil. Der Skill sagt das und nutzt seinen eigenen Reife-Check. |

## Was nicht getestet ist

- Windows. Die Befehle für PowerShell sind nicht gelaufen.
- Jira Data Center. Nur mit Unit-Tests gegen einen Fake-Server geprüft.
- Über Jira-MCP: Epic und `parent`. Getestet ist nur ein einzelnes Ticket mit Labels (FLAB-36), und nur Schritt 8, nicht ein ganzer Lauf.
- Die Suche nach der Domäne in Confluence und in `module_docs`. Das Lab hat keinen Confluence-Bereich mit Domänen.
- Die Konfiguration über `~/.copilot/mcp-config.json` und über „Add MCP server…“. Im Lab lief derselbe Inhalt über `copilot --additional-mcp-config @datei`.
- Die Prüfung der Factory in der Pipeline. Lokal lief sie auf FLAB-30 und auf den Entwürfen von FLAB-33 bis FLAB-35, jedes Mal „ready“.
