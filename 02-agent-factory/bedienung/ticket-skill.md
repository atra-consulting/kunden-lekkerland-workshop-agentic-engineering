# Tickets mit dem Skill schreiben

Der Copilot-Skill `ticket-schreiben` macht aus einer Absicht ein Jira-Ticket, das die Factory ohne Rückfrage umsetzen kann. Du startest ihn lokal in Copilot CLI, in deinem Projekt.

- Er liest zuerst selbst den Code: Gibt es das schon? Widerspricht es dem heutigen Verhalten? Was würde es berühren?
- Dann fragt er mit dem SDD-Framework deines Projekts nach: Spec Kit, OpenSpec oder BMad.
- Er prüft das Ergebnis gegen dieselben Kriterien wie die Factory vor dem Spec-Lauf.
- Er zeigt dir den Ticket-Text, legt das Ticket nach deinem Ja in Jira an und räumt danach auf. Dein Repository ist danach wie vorher.

Der Skill ist **optional** und kein Teil der Factory. Er läuft auf deinem Rechner, mit deiner Copilot-Lizenz. Die Factory startet erst, wenn du das Ticket in Jira nach „Bereit“ schiebst.

## Was du brauchst

- Copilot CLI 1.0.112 oder neuer, mit Claude Sonnet 5.5.
- Python 3, nur die Standardbibliothek. macOS: `python3`. Windows: `py -3`.
- Git und ein Projekt, in dem schon ein SDD-Framework installiert ist, wie am ersten Tag.
- Einen Jira-Zugang, der im Projekt Tickets anlegen darf.

## Einrichten

### 1. Skill ins Projekt kopieren

Kopiere den Ordner `02-agent-factory/werkzeuge/ticket-schreiben/` nach `.github/skills/ticket-schreiben/` in deinem Projekt. Den Unterordner `tests/` brauchst du dort nicht.

macOS und Linux:

```sh
mkdir -p .github/skills
cp -R <workshop-repo>/02-agent-factory/werkzeuge/ticket-schreiben .github/skills/
rm -rf .github/skills/ticket-schreiben/tests
```

Windows (PowerShell, nicht getestet):

```powershell
New-Item -ItemType Directory -Force .github\skills | Out-Null
Copy-Item -Recurse <workshop-repo>\02-agent-factory\werkzeuge\ticket-schreiben .github\skills\
Remove-Item -Recurse .github\skills\ticket-schreiben\tests
```

### 2. Konfiguration schreiben

Leg `.github/ticket-schreiben.json` an. Vorlage: `ticket-schreiben.example.json` im Skill-Ordner.

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

Fehlt die Datei, fragt der Skill einmal nach den Werten und bietet an, sie zu schreiben.

### 3. Committen und prüfen

Committe Skill und Konfiguration. Dann startet jeder Lauf mit einem sauberen `git status`, und das Aufräumen ist eindeutig.

```sh
git add .github/skills/ticket-schreiben .github/ticket-schreiben.json
git commit -m "Skill ticket-schreiben"
copilot skill list        # zeigt ticket-schreiben
```

### 4. Jira-Zugang setzen

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
python3 -I .github/skills/ticket-schreiben/jira_ticket.py pruefen
```

Die Ausgabe nennt Jira-Adresse, deinen Namen, Projekt, Vorgangstyp und Labels, nie das Token. Am Ende steht `OK`.

## So läuft es

Starte `copilot` im Projekt und gib die Absicht direkt hinter dem Befehl ein:

```text
/ticket-schreiben Leser sollen sehen, wie lange sie für einen Artikel brauchen.
```

| Schritt | Was passiert |
|---|---|
| 1. Konfiguration und Arbeitsstand | Der Skill liest die Konfiguration, merkt sich den Stand des Repositorys (`arbeitsstand.py merken`) und prüft Jira. |
| 2. Absicht | Er nimmt deine Worte auf, noch ohne sie zu verbessern. |
| 3. Code-Erkundung | Er liest Routen, Controller, Templates, Entities und Tests. Gibt es das schon oder widerspricht es dem Code, sagt er es sofort, mit Datei und Zeile. |
| 4. Nachfragen mit dem Framework | Das Framework stellt die Fragen. Danach nennt der Skill die Annahmen, die das Framework ohne Frage getroffen hat, und lässt sie dich bestätigen. |
| 5. Reife-Check | Eine Tabelle mit allen Kriterien, je „erfüllt“ oder „offen“. |
| 6. Ticket-Text | Ziel, Akzeptanzkriterien, Nicht Teil des Tickets, Hinweise. Du siehst den ganzen Text und sagst Ja oder änderst ihn. |
| 7. In Jira anlegen | `jira_ticket.py anlegen`. Das Ticket startet in „Definition“. Das startet noch keinen Lauf. |
| 8. Aufräumen | `arbeitsstand.py aufraeumen --ja` entfernt die Dateien des Frameworks und den Entwurf. `git status` ist wie vorher. |

Brichst du ab, springt der Skill direkt zu Schritt 8.

Copilot fragt vor jedem Befehl. Lies die Befehle. Der Skill selbst ändert keinen Produktcode und committet nichts. Schreibt Copilot in `src/`, `templates/` oder `tests/`, lehn ab.

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

Spec Kit fragte nur dieses eine Mal. Die Übersetzung in „die Sprache des Besuchers“ hatte es selbst angenommen. Erst auf Nachfrage wurde daraus „nur Deutsch und Englisch“. Seitdem zeigt der Skill solche Annahmen ausdrücklich. Ticket: FLAB-28.

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

Dazu kommt die Zeit, in der du liest und antwortest. Im Lab dauerte ein Lauf insgesamt etwa 5 bis 10 Minuten.

## Die Kriterien ändern

Der Skill prüft dieselben Kriterien wie die Factory vor dem Spec-Lauf. Liegt `factory/readiness.md` im Projekt, liest der Skill diese Datei. Ändert ihr die Kriterien dort, gilt die Änderung für beide. Wie das geht, steht in [Ticket-Bereitschaft](ticket-bereitschaft.md), Abschnitt „So passt ihr die Kriterien an“.

Ohne `factory/readiness.md` nutzt der Skill die sechs Kriterien aus seiner `SKILL.md`: `missing_detail`, `untestable`, `already_exists`, `contradicts_code`, `protected_paths`, `too_big`.

Besteht jemand auf einem Ticket mit offenen Punkten, schreibt der Skill den Abschnitt „Offene Punkte“ dazu. Die Factory schickt so ein Ticket sehr wahrscheinlich nach „Klärung nötig“.

## Zu groß: mehrere Tickets und ein Epic

Ist ein Ticket `too_big`, schlägt der Skill eine Aufteilung vor. Willst du das, legt er zuerst ein Epic an und dann jedes Ticket darunter:

```sh
python3 -I .github/skills/ticket-schreiben/jira_ticket.py anlegen --entwurf ticket-entwurf.md --typ Epic
python3 -I .github/skills/ticket-schreiben/jira_ticket.py anlegen --entwurf ticket-entwurf.md --parent FLAB-40
```

Dieser Weg ist nur mit Unit-Tests geprüft, nicht im Lab gegen Jira.

## Wenn etwas schiefgeht

| Meldung | Bedeutung und Abhilfe |
|---|---|
| `Umgebungsvariable fehlt: JIRA_API_TOKEN` | Die Variable fehlt in der Shell, in der Copilot läuft. Beende Copilot, setz die Variable, starte neu. |
| `HTTP 401` bei `/myself` | Token oder E-Mail falsch, oder ein Scoped Token mit der Site-URL. Nimm die URL `https://api.atlassian.com/ex/jira/<cloud-id>`. |
| `Vorgangstyp 'Story' fehlt im Projekt` | `issue_type` in der Konfiguration anpassen. Die Meldung nennt die vorhandenen Typen. |
| `HTTP 400` beim Anlegen | Jira lehnt ein Feld ab, die Meldung nennt es. Oft ein Pflichtfeld im Projekt, das der Skill nicht setzt. |
| `arbeitsstand.py` endet mit Exit-Code 1 | Es gibt neue Commits, oder eine Datei ließ sich nicht zurücksetzen. Das Skript fasst Commits nie an. Prüf mit `git log` und `git status` selbst. |
| `arbeitsstand.py merken` endet mit Exit-Code 3 | Es gab schon Änderungen. Sie bleiben unberührt. Besser: vorher committen oder stashen. |

## Was nicht getestet ist

- Windows. Die Befehle für PowerShell sind nicht gelaufen.
- Jira Data Center. Nur mit Unit-Tests gegen einen Fake-Server geprüft.
- Epic und `--parent` gegen echtes Jira.
- Ob die Prüfung der Factory die Tickets aus dem Skill als bereit durchlässt.
