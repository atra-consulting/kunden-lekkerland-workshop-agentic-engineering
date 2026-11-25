# Tag 2, 24. November 2026

Folien, Übungen und Ergebnisse von Tag 2.

## Folien

[Workshop Agentic Engineering – Tag 2](Workshop%20Agentic%20Engineering%20%E2%80%93%20Tag%202.pdf) (PDF, 39 Seiten)

## Ablauf

Dieser Ablauf ersetzt den Dienstag aus der [Kurzfassung der Agenda](../vorbereitung/agenda-kurz.md). Statt einer Pipeline in jeder Repository-Kopie führt ihr die Schritte der Factory lokal aus, in eurem eigenen Repo.

| Zeit | Block | Ergebnis |
|---|---|---|
| 09:00 | Rückblick und Fragen | Plan für den Tag |
| 09:15 | Demo: die Factory im Lab, die Bereitschaftsprüfung, lokal ausführen | Ihr habt gesehen, wie aus einem Ticket Spec und Pull Request werden |
| 10:00 | Pause | |
| 10:15 | [Übung 1, Teil 1](uebung-factory-lokal.md): einrichten, die erste Spec mit eurem Framework | `agentic-factory.py` läuft, eine Spec |
| 11:00 | Pause | |
| 11:15 | [Übung 1, Teil 2](uebung-factory-lokal.md#teil-2-bauen-und-ein-zweites-framework): bauen, dann dasselbe Ticket mit dem anderen Framework | Ein Ticket mit Spec und Code, ein Vergleich von Spec Kit und OpenSpec |
| 12:00 | Mittag | |
| 13:00 | [Übung 2: Ein Ticket ablehnen lassen, Kriterien anpassen](uebung-bereitschaft.md) | Ein abgelehntes Ticket, eure eigenen Kriterien |
| 14:00 | Pause | |
| 14:15 | [Übung 3: Tickets mit dem Skill schreiben](uebung-ticket-schreiben.md) | Je Gruppe ein Ticket vom Skill |
| 15:00 | Pause | |
| 15:15 | Freie Arbeit in den Gruppen: weitere Tickets, offene Punkte | Was ihr euch vornehmt |
| 16:30 | Rückblick, Plan für Mittwoch | |

**Ergebnis je Gruppe:** ein Ticket mit Spec und Code, ein abgelehntes Ticket und eure Kriterien in `factory/readiness.md`. Als Branch und Pull Request in eurem Repo, in eurem Review.

**Nach dem Workshop, für euer DevOps-Team:** die Schritte in Bitbucket Pipelines übernehmen. Die Vorlage ist die Ausgabe von `agentic-factory.py --print-only`. Was dazugehört, steht im [Walkthrough unter „Für eure eigene Factory“](walkthrough-agent-factory.md#für-eure-eigene-factory).

## Walkthrough

[Die Agent Factory im Lab](walkthrough-agent-factory.md): ein echtes Ticket von Jira bis zum Pull Request, die Prüfpunkte und was ihr ohne Konto ansehen könnt.

Die zwei Live-Demos um 09:15, Schritt für Schritt:

- [Live-Demo 1: Ein Ticket läuft durch](demo-durchlauf.md), mit [FLAB-41](https://betterprojectsfaster.atlassian.net/browse/FLAB-41)
- [Live-Demo 2: Zu vage, dann konkret](demo-abgelehnt.md), mit [FLAB-42](https://betterprojectsfaster.atlassian.net/browse/FLAB-42)

Die Blog-App des Labs startet ihr auf eurem Rechner mit fünf Befehlen: [Die Blog-App lokal starten](walkthrough-agent-factory.md#die-blog-app-lokal-starten).

## Kosten

[Credits messen und sparen](credits-messen-und-sparen.md): die Kurzfassung für Mittwoch, die Fragen dafür heute und die Fragen an Führung und Copilot-Admin am Mittwoch.

## Sicherheit

[Copilot absichern](fragen-copilot.md): die Fragen an eure Copilot-, Atlassian- und Bitbucket-Admins.

## Prozess

[Euer Entwicklungsprozess](fragen-entwicklung.md): neun Fragen, wie eine Anforderung bei euch in Produktion kommt.

## Übungen

Jede Gruppe arbeitet in ihrem eigenen Repo, auf ihrem Framework-Branch von Tag 1:

- [Übung 1: Ein Ticket lokal durch die Factory-Schritte](uebung-factory-lokal.md), 10:15 bis 12:00, in zwei Teilen mit Pause von 11:00 bis 11:15
- [Übung 2: Ein Ticket ablehnen lassen und die Kriterien anpassen](uebung-bereitschaft.md), 13:00 bis 14:00
- [Übung 3: Tickets mit dem Skill schreiben](uebung-ticket-schreiben.md), 14:15 bis 15:00

Folien und Ergebnisse folgen.
