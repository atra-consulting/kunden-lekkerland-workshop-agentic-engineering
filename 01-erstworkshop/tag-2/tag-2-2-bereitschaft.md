# Übung 2: Ein Ticket ablehnen lassen und die Kriterien anpassen

Tag 2, 13:00 bis 14:00. Zuerst lasst ihr die Bereitschaftsprüfung ein absichtlich dünnes Ticket ablehnen. Ihr bessert es nach, bis sie „ready“ sagt. Dann ergänzt ihr ein eigenes Kriterium für Lekkerland. Die Referenz: [Ticket-Bereitschaft](../../02-agent-factory/bedienung/ticket-bereitschaft.md).

- **Ihr braucht** den Ordner `factory/` aus [Übung 1](tag-2-1-lokal.md). Jira braucht ihr nicht: Das Ticket ist eine Datei.
- **Ein Rechner je Gruppe, wenn möglich ein Mac.** Windows ist nicht getestet.
- **Kosten:** Eine Prüfung kostete im Lab etwa 6 bis 14 Credits und 10 bis 25 Sekunden. Plant vier bis sechs Prüfungen ein.

## 1. Ein dünnes Ticket schreiben

```bash
git switch <framework-branch>
git status --short
```

Legt mit dem Editor die Datei `~/factory-tickets/LL-0.json` an. Wählt eine Funktion aus eurem Code und beschreibt sie absichtlich vage, in einem Satz:

```json
{"key": "LL-0", "summary": "Suche verbessern", "description": "Die Suche soll besser werden.", "labels": []}
```

- `LL-0` ist ein erfundener Schlüssel. Er muss nur wie ein Jira-Schlüssel aussehen.
- `assess` braucht kein Framework-Label.

**Das seht ihr:** `git status --short` zeigt nichts. Die Datei liegt außerhalb eures Repos.

## 2. Prüfen lassen

```bash
python3 factory/local.py assess --ticket-file ~/factory-tickets/LL-0.json
```

**Das seht ihr:**

```text
[local] LL-0: readiness check, project …
[local] copilot readiness check: tools ['read', 'write']
…
  verdict: not_ready
  - missing_detail: …
  ? …
[local] not ready: no spec calls. Credits …. The verdict is in FACTORY-ASSESSMENT.json; don't commit it
```

Exit-Code 4. Im Lab lehnte die Prüfung „Suche verbessern“ mit `missing_detail` und `untestable` ab und nannte die drei Stellen im Code, an denen gesucht wird: [FLAB-31](https://betterprojectsfaster.atlassian.net/browse/FLAB-31).

## 3. Gründe und Fragen lesen

Jeder Grund beginnt mit der ID eines Kriteriums. Die sechs IDs erklärt die Tabelle [Die sechs Kriterien](../../02-agent-factory/bedienung/ticket-bereitschaft.md#die-sechs-kriterien).

- Nennt die Prüfung echte Dateien aus eurem Code?
- Würde eine Entwicklerin aus eurem Team dieselben Fragen stellen?

**Das seht ihr:** Gründe mit `-`, Fragen mit `?`, in der Sprache des Tickets.

## 4. Ticket verbessern und neu prüfen

Beantwortet die Fragen in `description`. Die Gliederung aus dem [Walkthrough](walkthrough-agent-factory.md#mit-konto) hilft: Ziel, Akzeptanzkriterien, Nicht Teil des Tickets, Hinweise. Zeilenumbrüche schreibt ihr in JSON als `\n`. Dann startet ihr denselben Befehl wie in Schritt 2 noch einmal, bis die Prüfung zustimmt.

**Das seht ihr:**

```text
  verdict: ready
[local] ready. Credits …, … s, logs in …
```

Exit-Code 0. Nach „ready“ löscht `local.py` die Datei `FACTORY-ASSESSMENT.json` selbst. Im Lab brauchte FLAB-31 drei Fassungen: Die zweite widersprach einem bestehenden Test (`contradicts_code`).

## 5. Ein eigenes Kriterium ergänzen

Öffnet `factory/readiness.md`. Hängt am Ende des Abschnitts `## Criteria` einen neuen Abschnitt an:

```markdown
### `missing_domain`

The ticket doesn't name its business domain and its module cluster. The agent can't tell which module docs apply.

Example: "Add a filter to the list." Which domain, and which module cluster?
```

- Jedes Kriterium ist eine Überschrift der dritten Ebene mit der ID in Backticks. Nur diese IDs darf das Urteil nennen.
- ID: Kleinbuchstaben, Ziffern und Unterstrich.
- Die Datei ist Englisch, weil das Modell sie liest. Deutsch geht auch, ist aber ungetestet.
- Konkrete Beispiele aus eurem Code wirken am stärksten.

**Das seht ihr:** `git diff factory/readiness.md` zeigt nur den neuen Abschnitt.

## 6. Das neue Kriterium testen

Prüft das Ticket aus Schritt 4 noch einmal, mit demselben Befehl. Nennt es Domäne und Modul-Cluster noch nicht, erwartet ihr eine Ablehnung:

```text
  verdict: not_ready
  - missing_domain: …
```

Ergänzt Domäne und Modul-Cluster in `description` und prüft erneut, bis `verdict: ready` kommt. Ein eigenes Kriterium hat im Lab niemand ausprobiert. Ihr seid die Ersten.

Dann committet ihr die Kriterien auf dem Framework-Branch. So gilt euer Kriterium auch für den Skill in Übung 3:

```bash
rm -f FACTORY-ASSESSMENT.json
git add factory/readiness.md
git commit -m "Kriterium missing_domain"
```

**Das seht ihr:** `git status --short` zeigt danach nichts.

## 7. Was für die Pipeline gilt

Eure Änderung wirkt nur lokal. In der Pipeline stecken die Kriterien im Factory-Image, nicht im Arbeitsverzeichnis. Eine geänderte `readiness.md` wirkt dort erst nach einem neuen Image und einem neuen Digest in `bitbucket-pipelines.yml`. Das macht DevOps. Die Schritte: [Die Änderung ausrollen](../../02-agent-factory/bedienung/ticket-bereitschaft.md#die-änderung-ausrollen).

**Das seht ihr:** nichts im Terminal. Notiert euer Kriterium für das Gespräch mit DevOps.

## Wenn es hakt

- **`readiness.md not found`:** `readiness.md` gehört neben `local.py`, also nach `factory/`.
- **`ticket key … does not match …`:** Der Schlüssel in der Datei sieht nicht wie ein Jira-Schlüssel aus. Nehmt `LL-0`.
- **`local.py` kann die Datei nicht lesen:** Meist ist das JSON kaputt, etwa durch einen echten Zeilenumbruch in `description`. Schreibt `\n`.
- **Das Urteil wirkt falsch:** Der Lab-Test lief je Fall nur zweimal. Ein konkretes Beispiel in `readiness.md` schärft das Urteil.

## Ergebnis

Eure Gruppe hat:

- ein Ticket, das die Prüfung erst ablehnt und nach euren Antworten durchlässt,
- ein Gefühl dafür, welche Fragen die Prüfung zu eurem Code stellt,
- ein eigenes Kriterium in `factory/readiness.md`, getestet und auf dem Framework-Branch committet,
- eine Notiz für DevOps: Neue Kriterien brauchen ein neues Image.
