# Live-Demo 1: Ein Ticket läuft durch

Tag 2, 09:15. Karsten schickt ein Ticket durch die Factory im Lab, von „Definition“ bis zum Pull Request. Ihr seht zu und öffnet die Links mit.

- Ticket: [FLAB-41 „Lesezeit auf der Artikelseite“](https://betterprojectsfaster.atlassian.net/browse/FLAB-41), Label `sdd-openspec`
- Läufe: [Pipelines](https://bitbucket.org/factory-lab/factory-lab/pipelines)
- Ergebnis: [Pull Requests](https://bitbucket.org/factory-lab/factory-lab/pull-requests/)
- Wie ein Lauf aufgebaut ist: [Walkthrough, „Was in einem Lauf passiert“](walkthrough-agent-factory.md#was-in-einem-lauf-passiert)

## Das Label wählt das Framework

Welches SDD-Framework die Factory nutzt, bestimmt ein Label am Ticket. Ihr setzt es im Ticket rechts unter „Details“ → „Labels“, bevor das Ticket auf „Bereit“ geht.

| Label | Framework | Im Lab je Ticket |
|---|---|---|
| `sdd-openspec` | OpenSpec | etwa 25 bis 50 Credits |
| `sdd-speckit` | Spec Kit | etwa 76 Credits |
| `sdd-bmad` | BMad Method | etwa 89 Credits |

- **Genau ein Label.** Kein Label, zwei Labels oder ein unbekanntes: Der Lauf stoppt mit dem Kommentar `FACTORY-STOP v1`, etwa „no framework chosen“. Ein Beispiel ist [FLAB-21](https://betterprojectsfaster.atlassian.net/browse/FLAB-21).
- **Andere Labels stören nicht.** Nur Labels mit `sdd-` am Anfang zählen.
- **Nach der Freigabe nichts mehr ändern.** Ein geändertes Label nach „Spec freigegeben“ bricht den Bau ab, wie jede Änderung am Ticket.
- Die Demo nutzt OpenSpec, weil es im Lab am schnellsten war.

## Die Schritte

Den Status ändert ihr im Ticket über den Statusknopf neben dem Titel. Direkte Links auf einen Übergang gibt es in Jira Cloud nicht: Jira verlangt dafür einen Klick im Ticket.

| Schritt | Status danach | Wer | Was passiert | Wo ihr es seht |
|---|---|---|---|---|
| 1 | Definition | Mensch | Das Ticket steht bereit: Ziel, drei prüfbare Kriterien, ein Framework-Label | [FLAB-41](https://betterprojectsfaster.atlassian.net/browse/FLAB-41) |
| 2 | Bereit | Mensch | Übergang **„Bereit“**. Flow 1 startet die Pipeline `factory-spec` | [Pipelines](https://bitbucket.org/factory-lab/factory-lab/pipelines) |
| 3 | Bereit | Factory | Lauf 1: Guard, dann Copilot. Zuerst die Bereitschaftsprüfung, dann schreibt OpenSpec die Spec. Danach Prüfung und Veröffentlichen | das Protokoll des Laufs |
| 4 | In Arbeit, dann Wartet | `factory-bot` | Kommentar `FACTORY-SPEC v1` mit der Spec und „Readiness check: passed“. Branch `factory/FLAB-41` | Kommentar in [FLAB-41](https://betterprojectsfaster.atlassian.net/browse/FLAB-41) |
| 5 | Bau | Mensch | **Freigabe 1:** Spec lesen, dann Übergang **„Spec freigegeben“**. Flow 2 startet `factory-build` | [Pipelines](https://bitbucket.org/factory-lab/factory-lab/pipelines) |
| 6 | Bau | Factory | Lauf 2: Guard prüft die Freigabe, Copilot setzt die Spec um, Prüfung, Tests in einem frischen Checkout, Veröffentlichen | das Protokoll des Laufs |
| 7 | Review | `factory-bot` | Pull Request auf `factory-base`, verlinkt im Ticket | [Pull Requests](https://bitbucket.org/factory-lab/factory-lab/pull-requests/) |
| 8 | Review | Mensch | **Freigabe 2:** Diff und Tests lesen. In der Demo führt niemand zusammen | der Pull Request |

Passt die Spec in Schritt 5 nicht, geht das Ticket mit **„Zurück“** nach „Definition“.

## Dauer und Kosten

Im Lab dauerte Lauf 1 mit OpenSpec etwa 1 bis 2,5 Minuten und Lauf 2 etwa 2 bis 3,5 Minuten, dazu die Wartezeit im Runner. Zusammen etwa 45 Credits. Läufe warten aufeinander: „Queued“ heißt warten, nicht neu starten.

## Die Übergänge im Lab

| Übergang | Von | Nach | Wer |
|---|---|---|---|
| Bereit | Definition, Klärung nötig | Bereit | Mensch |
| Start | Bereit | In Arbeit | nur `factory-bot` |
| Spec fertig | In Arbeit | Wartet | nur `factory-bot` |
| Klärung nötig | In Arbeit | Klärung nötig | nur `factory-bot` |
| Spec freigegeben | Wartet | Bau | nur Freigabe-Personen |
| Zurück | Wartet | Definition | Mensch |
| Bau fertig | Bau | Review | nur `factory-bot` |
| Erledigt | Review | Erledigt | Mensch |
| Factory stoppen | jeder Status | Factory gestoppt | jeder |
| Fortsetzen | Factory gestoppt | Definition | nur Freigabe-Personen |

Ein Bild des Workflows steht im [Walkthrough](walkthrough-agent-factory.md#so-sieht-es-in-jira-aus).
