# Workshop Agentic Engineering bei Lekkerland: Kurzfassung

23. bis 25. November 2026, Frechen

Stand: 15. November 2026

Die Kurzfassung der Agenda: der Überblick und jeder Tag Stunde für Stunde. Was in den einzelnen Blöcken passiert, steht in der ausführlichen Fassung (`lekkerland-workshop-agenda.md`). Dazu gehören drei Dokumente:

- **Checkliste vor dem Workshop** (`lekkerland-checkliste.md`): was wir bis 20. November von euch brauchen, und unsere Annahmen.
- **Blueprint der Agent Factory** (`lekkerland-agent-factory-blueprint.md`): wie die Factory eure zehn Schritte abdeckt, und ihre Sicherheit.
- **Ausgangslage, wie wir sie verstehen** (`lekkerland-analyse.md`).

Das ist unser Vorschlag. Die Entscheidungen trefft ihr.

## Überblick

| | Montag, 23. November | Dienstag, 24. November | Mittwoch, 25. November |
|---|---|---|---|
| **Thema** | Zielbild und Ausprobieren | Factory anpassen | Betreiben und Roadmap |
| **Was passiert** | Euer Zielbild schärfen; zwei Frameworks an eurem eigenen Ticket ausprobieren und vergleichen | Die Factory in euren Repository-Kopien einrichten; ein echtes Ticket läuft durch | Puffer für den Dienstag; die Factory selbst bedienen; Zielbild und Roadmap mit der Führung |
| **Pflicht-Ergebnis** | Gewählter Ansatz für die Factory | Je Gruppe ein Pull Request mit der angepassten Vorlage | Zielbild und Roadmap |
| **Führung dabei** | 9:00 bis 11:00 und ab 15:45 | optional 30 Minuten ab 13:30 | ab 13:30 |

- **Wann:** jeweils 9:00 bis 17:00. Am Montag ab 8:30 Technik-Check.
- **Wo:** bei Lekkerland in Frechen.
- **Mitbringen:** Laptop mit funktionierendem Copilot-Zugang, Node.js, uv und Git; je Gruppe zwei bis drei kleine, testbare Jira-Tickets.
- **Danach:** zwei Folgetage vor dem 18. Dezember.

## Rahmen

- **Plattform:** Repositories in Bitbucket, CI in Bitbucket Pipelines, Tickets in Jira, GitHub Copilot. Im Workshop nutzen wir Copilot in VS Code und als Copilot CLI. Wir gehen davon aus, dass beides bei euch erlaubt ist (siehe Checkliste, „Unsere Annahmen“).
- **Teilnehmende:** Planungsannahme 6 bis 12 Personen, in Paaren oder Dreiergruppen. Bitte sagt uns bis Freitag, 20. November, wie viele Personen kommen und ob jemand aus SAP dabei ist.
- **atra:** Karsten Silz moderiert alle drei Tage. Michael Schwarze und Daniel Wochnik eröffnen am Montag. Höchstens vier Gruppen, bei 12 Personen also Dreiergruppen.
- **Lekkerland:** Euer bisheriger Ansprechpartner ist an allen drei Tagen vor Ort (siehe Checkliste, „Unsere Annahmen“). Die Führung (Stefan Nogly, Mike Franke, Chris Blum, nach Möglichkeit Ulf Adebahr) ist zu festen Zeiten dabei. Die Termine stimmt Michael Schwarze im Vorgespräch ab.
- **Zeit danach:** Vom 26. November bis 18. Dezember bleiben 17 Arbeitstage. Danach beginnt für viele der Weihnachtsurlaub. Das ist unsere Planungsannahme.

## Kurz erklärt

- **Factory:** eine Pipeline, in der Agenten Tickets bearbeiten und an festen Stellen Menschen fragen. In unserer Schulung am 5. November habt ihr eine Factory lokal gebaut.
- **Freigabe 1:** Ein Mensch gibt die Spezifikation in Jira frei. **Freigabe 2:** Ein Mensch gibt den Pull Request frei – euer bestehendes Review.
- **Freigabegruppe:** die Personen, die Freigabe 1 oder 2 erteilen dürfen. Die Factory gehört nie dazu.
- **Stufe, Kette:** die Skala aus eurer Selbsteinschätzung im Workshop vom September: 0 Tippen, 1 Dialog, 2 Auftrag, 3 Kette (zwei erzwungene Freigaben), 4 Durchlauf, 5 Portfolio.
- **Folgetag:** einer der zwei Tage Unterstützung nach dem Workshop, vor dem 18. Dezember.
- **AI Credits:** GitHubs Abrechnungseinheit für Copilot.

## Montag, 23. November: Zielbild und Ausprobieren

| Zeit | Block | Ergebnis | Wer |
|---|---|---|---|
| 08:30 | Technik-Check | Jede Gruppe arbeitsfähig | mindestens eine Person je Gruppe; Karsten Silz |
| 09:00 | Eröffnung, mit Kontextrunde (30 Minuten) | Gemeinsames Bild der drei Tage | Michael Schwarze, Daniel Wochnik, Führung, alle |
| 09:30 | Vortrag: Coding mit KI, Spec-Driven Development, Agent Factory (30 Minuten) | Gemeinsame Begriffe | Karsten Silz |
| 10:00 | Zielbild schärfen | Entwurf Zielbild, eine Seite | Führung, alle |
| 11:00 | Pause | | |
| 11:10 | Ergebnisse unseres Vortests; Tickets und Gruppen | Jede Gruppe hat ihr Ticket | alle |
| 11:30 | Runde 1: GitHub Spec Kit | Mindestens eine Spec für das Ticket | Gruppen |
| 13:00 | Mittag | | |
| 14:00 | Runde 2: BMad Method oder OpenSpec, jede Gruppe wählt | Mindestens eine Spec; Kriterienblatt | Gruppen |
| 15:35 | Pause | | |
| 15:45 | Vergleich anhand der Kriterienblätter | Bewertung der Ansätze | alle, Führung |
| 16:15 | Abstimmung der Teilnehmenden, dann Ja oder Nein der Führung | **Pflicht: gewählter Ansatz für die Factory** | Teilnehmende, Führung |

**Kriterienblatt (eine Seite):** Bewertet wird der Ansatz, nicht die Gruppe. Es ist ein erster Eindruck nach einem Versuch, kein Messergebnis. Versteht ein Reviewer die Spec schnell? Passt der Aufwand zur Ticketgröße? Kommt der Ansatz mit eurem Code zurecht? Läuft er unbeaufsichtigt in der Pipeline? Ist er besser als reines Copilot, gemessen an eurer Erfahrung vom 5. November?

**Entwurf:** die Kriterienblätter.

**Was ihr mitnehmt:** Ihr habt zwei Frameworks an eurem eigenen Ticket ausprobiert und wisst, welches ihr nehmt – und warum.

## Dienstag, 24. November: Factory anpassen

**In welchem Repository?** Jede Gruppe in ihrer eigenen Kopie aus der Checkliste: ein kleines, testbares Repository in eurem Bitbucket, ohne Secrets. So kommen sich die Gruppen nicht in die Quere. Die Teilnehmenden dürfen dort direkt auf `main` pushen, denn die Factory liest ihre Pipeline und Skripte immer aus `main`. Wir ändern sie am Dienstag oft. Deshalb sichert ihr `main` um 10:30 als Erstes ab: Nur ihr dürft dorthin pushen, die Factory nie. Nach dem Workshop nimmt `main` Änderungen nur noch über Pull Requests an.


| Zeit | Block | Ergebnis | Wer |
|---|---|---|---|
| 09:00 | Rückblick; Weg für heute | Plan für den Tag | alle |
| 09:15 | Vorlage im Überblick, inklusive Sicherheit | Alle kennen Aufbau und Grenzen | Karsten Silz |
| 10:15 | Pause | | |
| 10:30 | Anpassen I: `main` absichern, Pipeline und Zugänge | Pipeline läuft | Gruppen, Karsten Silz |
| 12:30 | Mittag. Läuft die Pipeline einer Gruppe nicht, schließt sie sich einer anderen Gruppe an | Weg für den Nachmittag | alle |
| 13:30 | Anpassen II: Framework, Regeln, Jira und Freigaben; Policy-Entwurf | Freigaben eingerichtet, Freigabegruppe benannt | Gruppen, Karsten Silz; optional 30 Minuten Führung |
| 15:00 | Pause | | |
| 15:15 | Erstes echtes Jira-Ticket von Anfang bis Ende | Ticket durchgelaufen oder Hindernisse notiert | alle |
| 16:30 | Retrospektive; Pull Request | **Pflicht: je Gruppe ein Pull Request mit der angepassten Vorlage, in eurem Review** | alle; Review: Lekkerland |

- **Aufzeichnung:** Nur wenn alle Sichtbaren zustimmen, zeichnen wir den Bildschirm mit dem Factory-Lauf auf. Wer Nein sagt, hat keinen Nachteil. Die Aufzeichnung zeigt nur Terminal und Pipeline-Protokoll, keine Token und keine Personen. Sie liegt auf einem Rechner von atra, dient nur der Vorführung am Mittwoch, und wir löschen sie spätestens am 26. November.
- **Build:** Die Factory nutzt das Build-Image, mit dem eure Repository-Kopien schon in Bitbucket Pipelines bauen und testen.
- **Copilot-Token:** Bis ihr einen technischen GitHub-Benutzer habt, nutzt die Factory den Token einer teilnehmenden Person: nur „Copilot Requests“, gültig bis 4. Dezember. Die Person macht das freiwillig. Die Credits der Factory erscheinen in GitHub unter dieser Person; wir werten sie nur als Kosten pro Ticket aus, nicht als Nutzung der Person.
- **Entwurf:** Policy für Agenten auf Basis unseres Entwurfs. Bestätigen müssen sie eure Compliance, euer Datenschutzbeauftragter und eure IT-Sicherheit.

**Was ihr mitnehmt:** Ihr habt gesehen, wie aus einem Jira-Ticket eine Spec und ein Pull Request werden – und wo ihr eingreift.

## Mittwoch, 25. November: Betreiben und Roadmap

| Zeit | Block | Ergebnis | Wer |
|---|---|---|---|
| 09:00 | Puffer: fertig machen, was am Dienstag offen blieb | Factory läuft in jeder Gruppe, oder die Hindernisse sind notiert | Gruppen, Karsten Silz |
| 10:30 | Pause | | |
| 10:45 | Weitere Tickets, ohne Moderator an der Tastatur | Entwurf Handbuch „Factory betreiben und reparieren“ | Gruppen; Karsten Silz berät |
| 12:00 | Messen: Grundsätze und Betriebsrat (30 Minuten) | Grundsätze; Termin mit dem Betriebsrat vereinbart, möglichst bis 1. Dezember | alle |
| 12:30 | Mittag | | |
| 13:30 | Zielbild bestätigen, dann Roadmap | Zielbild; Roadmap mit nächsten Schritten | Führung, alle |
| 15:15 | Pause | | |
| 15:30 | Ergebnisse für die Führung: Live-Durchlauf, Zielbild, Roadmap | Gemeinsamer Stand | Gruppen stellen vor |
| 16:30 | Abschluss; Folgetage bestätigen | Termine der Folgetage | alle |

| Ergebnis | Stand am Mittwoch | Wer macht fertig | Bis wann |
|---|---|---|---|
| Zielbild | **Pflicht, fertig** | Führung | 25. November |
| Roadmap | **Pflicht, fertig:** Ziel bis 18. Dezember und nächste Schritte | Führung | 25. November |
| Offene Rollen | gesammelt | Führung | nach dem Workshop |
| Handbuch | Entwurf | Frontrunner mit Karsten Silz | Folgetag 1 |
| Messplan | Grundsätze | Lekkerland mit Karsten Silz | Entwurf bis Folgetag 1 |

**Was ihr mitnehmt:** Ihr wisst, wie ihr die Factory startet und stoppt; das Handbuch dazu entsteht als Entwurf.

## Wenn die Zeit knapp wird

Wir kürzen in dieser Reihenfolge:

1. die Tiefe der zweiten Runde am Montag;
2. die Übernahme eurer Regeln am Dienstag – dann holen wir sie am Folgetag 1 nach;
3. die Arbeit an der Policy am Dienstag – dann bleibt es bei unserem Entwurf und der Anbindung der Freigaben;
4. den Live-Durchlauf am Mittwoch – dann zeigen wir die Aufzeichnung oder das Pipeline-Protokoll;
5. die Tiefe des SAP-Strangs.

Die Pflicht-Ergebnisse kürzen wir nicht: die Wahl am Montag, die Pull Requests am Dienstag, Zielbild und Roadmap am Mittwoch. Verzug vom Dienstag fängt der Puffer am Mittwochmorgen auf.

## Für SAP-Teilnehmende

Wenn ihr nur mit ABAP arbeitet, bekommt ihr trotzdem drei Tage echte Arbeit.

- **Montag:** An einem echten SAP-Ticket bearbeitet ihr die vordere Hälfte: Anforderung, Verstehen, Spezifikation, Kritik, Freigabe. Diese Schritte hängen nach unserer Annahme nicht von der Technik ab. Den Code könnt ihr weiter in den ABAP Development Tools schreiben.
- **Dienstag:** Ihr füllt eine einseitige Vorlage mit 3 bis 5 Fragen: Wie dürfen Agenten auf SAP-Entwicklungssysteme zugreifen? Git für ABAP – abapGit oder gCTS? Verantwortlich: Chris Blum oder eine Vertretung.
- **Mittwoch:** SAP bekommt einen eigenen Strang in Zielbild und Roadmap.

Bauen, Prüfen und Transport bleiben bei euch. Liegt ein BTP/Node- oder Java-Repository in Bitbucket, arbeitet ihr damit wie die Web-Gruppen. Kommt niemand aus SAP, verteilen wir die Zeit auf die anderen Gruppen.

## Vor dem Workshop

Was wir bis Freitag, 20. November, von euch brauchen, steht in der Checkliste (`lekkerland-checkliste.md`): Teilnehmerzahl, Repository-Kopien, Jira-Projekt, Tickets und bis Montag, 8:30, ein Copilot-Token. Dort stehen auch unsere Annahmen.

## Nach dem Workshop

**Lieferung.** Am Dienstag öffnet jede Gruppe ihren Pull Request mit der angepassten Vorlage selbst; er durchläuft euer eigenes Review. Verbesserungen aus den Folgetagen schicken wir als ZIP-Datei. Jemand von Lekkerland öffnet daraus einen Pull Request.

**Zwei Folgetage**, remote oder vor Ort. Wir reservieren sie vorläufig und sagen sie ab, wenn ihr sie nicht braucht:

- **Folgetag 1, 1. oder 2. Dezember:** weitere Tickets begleiten, Factory nachschärfen, eure Regeln ergänzen, falls am Dienstag gekürzt, prüfen, dass `main` nur Pull Requests annimmt, Token der teilnehmenden Person durch den des technischen GitHub-Benutzers ersetzen, Handbuch fertig, Messplan als Entwurf.
- **Folgetag 2, 15. oder 16. Dezember:** erste Messrunde, ohne Namen und mit Ausgangswerten nur nach Zustimmung des Betriebsrats, Review des Pilot-Umfangs, Pilot-Richtlinie für das Framework prüfen, Roadmap für Januar anpassen.
