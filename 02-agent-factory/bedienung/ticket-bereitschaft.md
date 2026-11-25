# Ticket-Bereitschaft: Die Prüfung vor dem Spec-Lauf

Bevor die Factory eine Spec schreibt, prüft sie das Ticket. Ein eigener Copilot-Aufruf liest das Ticket, liest den Code und urteilt: bereit oder nicht bereit. Ein Ticket, das nicht bereit ist, landet in „Klärung nötig“, mit Gründen und Fragen im Kommentar. Die Factory schreibt dann keine Spec, keinen Code und keinen Branch.

Was „nicht bereit“ heißt, legt ihr selbst fest: [So passt ihr die Kriterien an](#so-passt-ihr-die-kriterien-an).

## Ablauf

1. Du setzt das Ticket auf „Bereit“. Flow 1 startet den Spec-Lauf.
2. Schritt 2 der Pipeline (Agent) ruft Copilot zuerst nur zur Prüfung auf. Copilot darf dabei Dateien lesen und genau eine Datei schreiben: `FACTORY-ASSESSMENT.json`.
3. **Bereit:** Der Spec-Lauf geht weiter wie bisher. Der Spec-Kommentar nennt die bestandene Prüfung.
4. **Nicht bereit:** Die Factory überspringt das SDD-Framework. Der Check-Schritt lässt nur die Datei `FACTORY-ASSESSMENT.json` durch und prüft ihr Format. `factory-bot` kommentiert Gründe und Fragen und setzt das Ticket auf „Klärung nötig“.

Die Prüfung kostet im Lab etwa 6 bis 14 Credits und 10 bis 25 Sekunden. Ein ganzer Spec-Lauf, der mit „Klärung nötig“ endet, dauert etwa 50 Sekunden. Die Obergrenze pro Prüfung steht in `factory/config.json` unter `assess.max_ai_credits` (40).

## Die sechs Kriterien

Ein Ticket ist nicht bereit, wenn mindestens ein Kriterium zutrifft. Die IDs stehen so im Kommentar.

| ID | Nicht bereit, wenn … | Beispiel |
|---|---|---|
| `missing_detail` | Ziel, betroffene Seite oder erwartetes Ergebnis unklar sind. Der Agent müsste raten. | „Suche verbessern“: Welche Suche, und was soll besser werden? |
| `untestable` | Ein Akzeptanzkriterium in keinem automatischen Test scheitern kann. | „Die Tag-Liste soll moderner aussehen.“ |
| `already_exists` | Der Code schon tut, was das Ticket verlangt. | „Anzahl der Beiträge in der Überschrift der Blog-Übersicht“, wenn das Template sie schon zeigt. |
| `contradicts_code` | Das Ticket bestehendem Code oder bestehenden Tests widerspricht und nicht sagt, dass diese Änderung gewollt ist. | „Der Befehl `app:add-user` nimmt den Namen ‚JaneDoe‘ an“, wenn Validator und Test nur Kleinbuchstaben erlauben. |
| `protected_paths` | Das Ticket Änderungen braucht, die die Factory ablehnt: neue Pakete, Konfiguration, CI und die anderen geschützten Pfade aus `factory/config.json`. | „Relative Datumsangaben mit der Bibliothek Carbon“: braucht ein neues Composer-Paket. |
| `too_big` | Das Ticket nicht in einen Pull Request passt, also mehr als etwa eine Stunde Arbeit für einen Menschen ist. | „Benutzerprofile mit Avatar, Follower-Funktion und E-Mail-Benachrichtigungen.“ |

Kleine Lücken, die eine Entwicklerin auf die naheliegende Art füllt, sind kein Grund. Stil, Tippfehler oder ein fehlendes User-Story-Format auch nicht.

Ein Ticket, das schon fertig ist, schreibst du am besten gar nicht erst. Der Copilot-Skill aus [Tickets mit dem Skill schreiben](ticket-skill.md) prüft dieselben sechs Kriterien, bevor er ein Ticket anlegt.

## So sieht der Kommentar aus

Echter Kommentar aus dem Lab, Ticket „Suche verbessern“ ohne weitere Beschreibung. Der feste Text ist Englisch, wie bei allen Factory-Kommentaren. Gründe und Fragen stehen in der Sprache des Tickets.

```text
FACTORY-NOT-READY v1 key=FLAB-31 run=87 reasons=missing_detail,untestable
The readiness check found that this ticket is not ready for a spec. The factory wrote no spec, no code, and no branch.
Reasons:
• missing_detail: Das Ticket sagt nicht, was an der Suche besser werden soll. Es gibt mehrere Stellen: die Suche in src/Repository/PostRepository.php, src/Controller/BlogController.php und die Live-Komponente src/Twig/Components/BlogSearch.php. Ein Entwickler müsste Ziel und erwartetes Ergebnis raten.
• untestable: "Besser" ist kein Kriterium, das in einem automatisierten Test fehlschlagen kann. Es gibt keine überprüfbare Abnahmebedingung.
Questions:
• Welche Suche ist gemeint (Blog-Suche im Header, Suchseite, Live-Suche) und was funktioniert dort heute nicht wie gewünscht?
• Was soll konkret besser werden, zum Beispiel in Titel, Inhalt, Autor oder Tags suchen, Sortierung der Treffer, Teilwort-Treffer oder Anzahl der Ergebnisse?
• Welches Ergebnis soll bei einer konkreten Beispielsuche erscheinen, damit man es testen kann?
Improve the ticket description, then move the ticket from 'Klärung nötig' to 'Bereit'. That starts a new spec run with a new readiness check.
Criteria: factory/readiness.md
Pipeline: run 87
```

## Ein Ticket in „Klärung nötig“

1. Lies Gründe und Fragen im Kommentar von `factory-bot`.
2. Beantworte die Fragen in der **Beschreibung** des Tickets, nicht in einem Kommentar. Die Factory liest nur Titel und Beschreibung.
3. Passt das Ticket so nicht, teile es auf oder schließe es. Bei `already_exists` ist meist nichts mehr zu tun.
4. Setze das Ticket auf „Bereit“. Flow 1 startet einen neuen Spec-Lauf mit einer neuen Prüfung.

Fragt ein SDD-Framework im Spec-Lauf nach (`FACTORY-QUESTIONS v1`), landet das Ticket ebenfalls in „Klärung nötig“. Der Weg zurück ist derselbe.

## So passt ihr die Kriterien an

Die Kriterien stehen in einer Datei: `factory/readiness.md` auf `factory-base`. Das Modell liest sie bei jeder Prüfung. Agents können sie nicht ändern, denn `factory/` ist ein geschützter Pfad.

### Die Datei

- Jedes Kriterium ist eine Überschrift der dritten Ebene mit der ID in Backticks, darunter Text und Beispiel:

  ```markdown
  ### `missing_detail`

  The goal, the affected page or behavior, or the expected result is unclear. The agent would have to guess.

  Example: "Improve the search." Which search, and what should be better?
  ```

- Die Factory liest die IDs aus diesen Überschriften. Nur diese IDs darf das Urteil nennen.
- **Kriterium ändern:** Text oder Beispiel anpassen. Konkrete Beispiele aus eurem Code wirken am stärksten.
- **Kriterium hinzufügen:** neuen Abschnitt mit neuer ID anlegen. ID: Kleinbuchstaben, Ziffern und Unterstrich, etwa `missing_jira_link`.
- **Kriterium streichen:** den ganzen Abschnitt löschen.
- **Strenger oder lockerer urteilen:** den Abschnitt „How to Judge“ ändern. Dort steht zum Beispiel, dass kleine Lücken kein Grund sind.
- Die Datei ist Englisch, weil das Modell sie liest. Deutsch geht auch, ist aber ungetestet.

### Optional: `factory/config.json`, Block `assess`

| Schlüssel | Bedeutung |
|---|---|
| `enabled` | `false` schaltet die Prüfung ab. Der Spec-Lauf startet dann direkt mit dem Framework. |
| `max_ai_credits` | Obergrenze pro Prüfung. Im Lab: 40. |
| `prompt` | Der Prompt um Ticket und Kriterien herum. Nur ändern, wenn die Kriterien nicht reichen. |
| `tools` | Zusätzliche Werkzeuge für die Prüfung. Leer heißt: nur lesen, plus die eine Datei schreiben. |
| `criteria_file` | Name der Kriterien-Datei, Standard `readiness.md`. |

### Die Änderung ausrollen

1. Lege einen Branch von `factory-base` an. Ändere `factory/readiness.md` und, falls nötig, `factory/config.json`.
2. Prüfe lokal: `python3 -I -B -m unittest discover -s factory/tests`. Der Test erwartet die sechs IDs aus dem Lab. Passe die Liste in `test_six_ids_from_readiness_md` an deine IDs an.
3. Probiere die Kriterien an echten Tickets aus, ohne Pipeline. Das geht in einem Projekt, in dem die [Vorlage](../einrichtung/template/README.md) aus diesem Repo in `factory/` liegt (auf dem Branch von `factory-base` heißt das Skript `local.py`). Kopiere die geänderte `readiness.md` neben `agentic-factory.py` und starte `python3 -I factory/agentic-factory.py assess --key <KEY>`, siehe [Lokal ausführen](lokal-ausfuehren.md).
4. Baue das Factory-Image neu und schiebe es in eure Registry. Die Kriterien stecken im Image, nicht im Arbeitsverzeichnis des Laufs.
5. Ersetze den Digest in `bitbucket-pipelines.yml` (Vorlage: `factory/pipelines.template.yml`) durch den neuen.
6. Pull Request auf `factory-base`, Review durch eine zweite Person, zusammenführen.
7. Probelauf: ein absichtlich vages Ticket auf „Bereit“. Erwartet: `FACTORY-NOT-READY v1` und „Klärung nötig“.

Nur Schritt 4 und 5 bringen die Änderung in die Pipeline. Eine geänderte `readiness.md` ohne neues Image wirkt nicht.

### Die Prüfung abschalten

Setze in `factory/config.json` `"enabled": false` im Block `assess`, dann weiter mit Schritt 4 bis 6 oben. Der Spec-Kommentar sagt dann „Readiness check: off“. Status „Klärung nötig“ und Flow 1 könnt ihr lassen: Fragen der SDD-Frameworks landen weiter dort.

## Wenn etwas nicht klappt

- **Kein Kommentar, Lauf rot in Schritt 2:** Copilot hat kein gültiges Urteil geschrieben oder weitere Dateien geändert. Das Ticket bleibt in „Bereit“. Protokoll in Bitbucket lesen. Neu starten: `factory-spec` per curl, siehe [Merkblatt](merkblatt.md#lauf-starten), oder den Admin fragen.
- **Urteil falsch:** Kommentar und Ticket an atra oder den Admin. Wiederholt sich der Fehler, schärft ein Beispiel in `readiness.md` das Urteil.
- **Ticket bleibt in „Klärung nötig“ und nichts startet:** Flow 1 muss auch auf „Klärung nötig“ → „Bereit“ reagieren, siehe [Jira einrichten](../einrichtung/jira.md), Teil B.
