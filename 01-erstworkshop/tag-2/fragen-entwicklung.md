# Euer Entwicklungsprozess

## Fragen an euer Team

**Vom Wunsch zum Ticket:**

1. Wer schreibt die Tickets: die Fachabteilung, ein BA im Team oder die Entwickler? Wie viele BAs und Entwickler hat ein Team?
   - P&O (Spryker + Front End): PO schreibt Tickets und dann Prozess siehe Foto, manchmal schreiben auch Entwickler Tickets, zwei POs, sechs BE-Entwickler, drei FE-Entwicklung, eine QA-Person (System-Tests, meist FE & BE zusammen)
   - Java/GCP: Ein PO, drei BE-Entwickler, zwei DevoOps (technische Plattform, FinOps, Entwickler-Unterstützung, kleinere Projekte), kleine Front Ends, PO schreibt Tickets
   - Lawa: Zwei Entwickler schreiben/refinen Tickets
   - Fachabteilungen schreiben selten Tickets
2. Wer verfeinert und prüft ein Ticket, bevor jemand es umsetzt? Wann gilt es als fertig beschrieben?
   - P&O: Team verfeinert und prüft im Refinemen t
   - Java/GCP: Refinement
   - Lawa: kein reguläres Refinement

**Planung:**

3. Arbeitet ihr in Sprints? Wie lang sind sie, und welche Termine gehören dazu: Refinement, Planning, Review, Retro?
   - P&O: Sprints, 2 Wochen, synchronisiert über viele Teams, Pre-Refinement, Refinment, Planung, Retro, Sprint Close (Team-intern, Status von Tickets klären/Review kommen erst
   - Java/GCP: Kanban, Refinment & Retro
4. Wie kommt ein Ticket zu einer Person: Jemand weist es zu, ihr verteilt es im Planning, oder jeder nimmt sich das nächste?
   - P&O: Manchmal im Refinement schon zugewiesen, meist im Sprint gezogen, leere To-Do-Spalte = Ticket in Spring ziehen
   - Java/GCP: Team weist bei Erstellung oder Planung Ticket zu

**Umsetzung, Test und Auslieferung:**

5. Wer reviewt den Code? Wie lange wartet ein Pull Request im Schnitt?
   - P&O: Zwei Approvals per PR, PR kann schon mal dauern
   - Java/GCP: Ein Approval, PR wartet nicht lange (oft nur eine halbe Stunde)
6. Wer testet wie: automatisierte Tests, manuelle Tests, eine Abnahme durch die Fachabteilung? Auf welcher Umgebung?
   - P&O: Automatisiert: Unit & Feature Tests und E2E-Tests, auch manuelles Testen
   - Java/GCP: Größtenteils automatisiert im Build, Nightly Tests, Abnahme durch manuelles Testen von Produkt-Teams
7. Wie oft liefert ihr aus, und wer gibt frei?
   - P&O: 0-n
   - Java/GCP: pro Ticket, mehrmals pro Tag

**Zahlen:**

8. Wie lange dauert es im Schnitt von „Ticket geschrieben“ bis „Ticket in Produktion“? Wo wartet ein Ticket am längsten?
   - P&O: Dringend (Produktions-Probleme): am selben Tage, Tickets, die im Backlog schmoren: dauert lange, wird , Commitment auf Features pro Quartal
   - Java/GCP: Relevante Tickets ein-drei Tage, nicht relevante Tickets: länger, auch Ziele pro Quartal
9. Wie oft bleibt ein Ticket hängen oder geht zurück, weil etwas unklar ist? Wie schnell bekommt ihr dann eine Antwort?
   - P&O: Passiert selten während Entwicklung, weil Pre-Finement & Refinement
   - Java/GCP: regelmäßig, wird im gemeinsamen Team (PO, Fachabteilung) beantwortet



## SAP

- Alt-Systeme on premise
  - Transport-Fenster am Mittwoch
  - Soll abgelöst werden
  - Einbindung in Factory? Unklar
- Neu-System in Cloud
  - Drei POCs live, die aktuell manuell aktualisiert werden
  - Läuft mit Git, aber "SAP-verkapselt"
  - Migrations-Projekt
  - In Scope für Factory? Wenn ja, nur mit Anforderungen von beschränkter Komplexität
  - Sollen Externe an die Factory angebunden?
