# Checkliste vor dem Workshop

Workshop Agentic Engineering bei Lekkerland, 23. bis 25. November 2026, Frechen

Stand: 15. November 2026

Michael Schwarze schickt euch diese Checkliste am Montag, 16. November. Sie gilt für Führung, IT und Teilnehmende. Die Agenda steht in `lekkerland-workshop-agenda.md`, den Aufbau der Factory beschreibt `lekkerland-agent-factory-blueprint.md`.

Für die IT vorab: Die Factory soll nur Leserecht auf eure Repositories haben und nie auf `main` schreiben. Die Admin-Rechte unten gelten nur für Wegwerf-Kopien und enden mit dem Workshop.

## Auf einen Blick

| Bis wann | Was | Wer bei euch (Vorschlag) |
|---|---|---|
| Freitag, 20. November | Wie viele Personen kommen, ist jemand aus SAP dabei? | Ansprechpartner |
| Freitag, 20. November | Je Gruppe eine Repository-Kopie in Bitbucket | Bitbucket-Admin |
| Freitag, 20. November | Ein Jira-Projekt für den Pilot und ein Jira-Konto für die Factory | Jira-Admin |
| Freitag, 20. November | Je Gruppe zwei bis drei kleine, testbare Tickets | Teilnehmende |
| Freitag, 20. November | SAP: ein kleines SAP-Ticket und zwei Antworten | SAP-Teilnehmende |
| Montag, 23. November, 8:30 | Ein Copilot-Token für die Factory | eine teilnehmende Person, freiwillig |

Eure Antworten nimmt Michael Schwarze entgegen. Fehlt am Freitag etwas, sagt ihm bitte Bescheid.

## Bis Freitag, 20. November

- [ ] **Wie viele Personen kommen, und ist jemand aus SAP dabei?**
  - Warum: Danach richten wir die Gruppen ein. Wir planen mit 6 bis 12 Personen in Paaren oder Dreiergruppen.
- [ ] **Je Gruppe eine Kopie eines kleinen, testbaren Repositories in eurem Bitbucket.**
  - Ohne Secrets in Dateien, Historie und Repository-Variablen. Es baut und testet schon in Bitbucket Pipelines.
  - Das sind bis zu vier Kopien; alle dürfen vom selben Repository stammen.
  - Die Teilnehmenden sind Admins dieser Kopien und dürfen direkt auf `main` pushen. Die Person mit dem Copilot-Token ist Admin aller Kopien.
  - Warum: Am Dienstag bauen die Gruppen dort die Factory ein. Die Factory liest ihre Pipeline immer aus `main`, und wir ändern sie am Dienstag oft. Es sind Wegwerf-Kopien; euer echter Code bleibt unberührt.
- [ ] **Ein gemeinsames, team-verwaltetes Jira-Projekt (team-managed) für den Pilot.**
  - Die Teilnehmenden sind dort Projekt-Admin.
  - Dazu ein eigenes Jira-Konto für die Factory, mit API-Token. Dieses Konto hat nur die Rechte „Browse projects“, „Add comments“ und „Transition issues“, kein Admin.
  - Warum: Nur in einem team-verwalteten Projekt können Projekt-Admins den Workflow selbst ändern. Am Dienstag richten die Gruppen dort den Übergang „Spec freigegeben“ und den Status „Factory gestoppt“ ein, dazu je Gruppe eine Komponente.
- [ ] **Je Gruppe zwei bis drei kleine, testbare Jira-Tickets, möglichst präzise beschrieben.**
  - Eines davon nehmt ihr am Montag in beiden Runden, die anderen am Dienstag und Mittwoch in der Factory.
  - Siehe „Ein gutes Ticket“ unten.
- [ ] **SAP: ein kleines SAP-Ticket mitbringen und zwei Fragen beantworten.**
  - Liegt euer Code in Bitbucket?
  - Liegt ABAP in Git?

### Ein gutes Ticket

- Klein: in ein bis zwei Tagen von einer Person umsetzbar.
- Mit Akzeptanzkriterien, die ein Test prüfen kann.
- Mit Angaben zum Umfang, etwa welche Sprachen oder Länder betroffen sind. Im Vortest ergänzte das Modell neue Texte sonst meist nur auf Englisch.
- Ohne Kunden- oder personenbezogene Daten, auch nicht in Anhängen.

Beispiel: „Auf der Bestellübersicht steht neben jedem Artikel die Lieferzeit in Tagen. Fehlt sie, steht dort ‚auf Anfrage‘. Gilt für Deutsch und Englisch. Akzeptanz: Ein Test prüft beide Fälle.“

## Bis Montag, 23. November, 8:30

- [ ] **Ein Copilot-Token für die Factory.**
  - Eine teilnehmende Person legt ihn freiwillig an, auf dem GitHub-Konto, mit dem sie Copilot bei Lekkerland nutzt.
  - Fine-grained Personal Access Token, nur mit der Berechtigung „Copilot Requests“, gültig bis 4. Dezember.
  - Nur diese Person legt ihn an. Bitte nicht per E-Mail oder Chat verschicken. Am Dienstag gibt sie ihn in jeder Repository-Kopie selbst als gesicherte Deployment-Variable ein. Wer dort die Pipeline ändern darf, könnte ihn auslesen. Deshalb hat er nur „Copilot Requests“, läuft am 4. Dezember ab und lässt sich sofort widerrufen.
  - Wer Nein sagt, hat keinen Nachteil.
  - Beim Technik-Check am Montag um 8:30 testen wir ihn mit einem kurzen `copilot`-Aufruf.
  - Warum: Die Factory nutzt ihn, bis ihr einen technischen GitHub-Benutzer habt. Die Credits der Factory erscheinen in GitHub unter dieser Person. Wir werten sie nur als Kosten pro Ticket aus, nicht als Nutzung der Person.

## Unsere Annahmen

Stimmt eine davon nicht, sagt uns bitte Bescheid.

- Copilot CLI funktioniert für alle Teilnehmenden, mit aktiver Copilot-Lizenz, von den Laptops und aus der Pipeline.
- Ihr nutzt Bitbucket Cloud und Jira Cloud.
- Eure bestehende Erlaubnis, Copilot zu nutzen, deckt auch Copilot CLI und die Factory ab. Das bestätigt euer Datenschutzbeauftragter; bis dahin bleiben Tickets und Repositories mit Kunden- oder personenbezogenen Daten draußen.
- Node.js 22.12 oder neuer, uv und Git sind auf den Laptops vorhanden. Spec Kit, OpenSpec und BMad laufen am Montag bei den Teilnehmenden, lokal oder in einem Container eurer Wahl. Von uns kommt dafür nichts; beim Technik-Check prüfen wir nur, dass alles läuft.
- Die Teilnehmenden arbeiten am Montag in ihren eigenen Repositories.
- Die Teilnehmenden haben am Dienstag Zugriff auf ihre Coding Guidelines, Architekturvorgaben und die relevanten Teile des Global Book of Standards.
- Euer bisheriger Ansprechpartner ist an allen drei Tagen vor Ort.
- Der Betriebsrat weiß vom Workshop und vom Pilot. Ob er beteiligt werden muss, klärt ihr.

## Das klären wir im Workshop

- **Montag:** euer Zielbild, als Entwurf; welcher Ansatz in die Factory kommt. Bei Gleichstand entscheidet die Führung am Montag.
- **Dienstag:** die Freigabegruppe für Freigabe 1 und 2, mit Review-Kapazität; ob euer Bitbucket Workspace- oder Repository-Variablen hat.
- **Mittwoch:** Zielbild und Roadmap; technischer GitHub-Benutzer mit Budget und Abrechnung; Termin mit dem Betriebsrat. Dazu sammeln wir offene Rollen: Verantwortung für die Factory, wer die Policy bestätigt, wer bestätigt, dass die Copilot-Erlaubnis die Factory abdeckt. Wer sie übernimmt, klärt die Führung nach dem Workshop.
