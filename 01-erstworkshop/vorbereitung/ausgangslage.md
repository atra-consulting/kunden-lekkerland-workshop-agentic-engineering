# Ausgangslage, wie wir sie verstehen

Workshop Agentic Engineering, 23. bis 25. November 2026, Frechen – bitte korrigiert uns

Stand: 15. November 2026

Vor dem Workshop wollen wir eure Lage richtig verstehen. Hier steht, was wir aus euren Antworten und aus öffentlichen Quellen mitgenommen haben. Wo wir falsch liegen oder etwas fehlt, korrigiert uns bitte.

Öffentliche Quellen haben eine Nummer in eckigen Klammern, etwa [1]. Alles ohne Nummer stammt aus euren eigenen Angaben: Angaben von Lekkerland (Fragebogen, Herbst 2026), Ankündigung an die Frontrunner, Organisationsübersicht und Selbsteinschätzung (September 2026). Diese Angaben haben wir nicht gegengeprüft. Die Schulungen am 4. und 5. November hat atra durchgeführt; ihre Titel stammen aus unseren Unterlagen.

Korrekturen und Ergänzungen nehmen wir im Workshop auf.

## Umfeld

Lekkerland gehört seit 2020 zur REWE Group [1]. Für 2025 nennt Lekkerland rund 15,3 Mrd. € Umsatz, davon rund 10,3 Mrd. € in Deutschland [1]. Im Finanzbericht der REWE-ZENTRALFINANZ eG erscheint das Geschäft als Segment Convenience: in Deutschland und den Niederlanden als Lekkerland, in Belgien und Spanien als Conway [2]. Der Segmentumsatz lag 2025 bei 15.254,0 Mio. €, praktisch auf Vorjahresniveau [2]. Für 2026 erwartet das Segment einen leicht höheren Umsatz [2].

In den Niederlanden gilt seit 1. Juli 2024 ein Verkaufsverbot für Tabakprodukte in Supermärkten [3], in Belgien seit 1. April 2025 [2]. Wegen strengerer Tabakgesetze in den Niederlanden und Belgien erwartet das Segment für 2026 einen Rückgang der Tabakumsätze gegenüber 2025 [2]. Laut Annahme im Bericht soll die Umsatzentwicklung in Deutschland den Rückgang mehr als ausgleichen [2]. Im November 2025 kündigte Lekkerland an, die Smart Box, eines von vier Smart-Store-Formaten, ab Anfang 2026 einzuführen [4]. Für die Logistikzentren sieht Lekkerland bis 2030 eine neue Struktur vor; Stand Januar 2023 war sie in Norddeutschland bereits umgesetzt, der Rest geplant [5].

## Wie ihr heute Software baut

Ulf Adebahr ist CIO von Lekkerland [1].

| Thema | Was wir verstanden haben |
|---|---|
| Organisation (September 2026) | Unter dem CIO rund 200 Mitarbeitende. Darunter Engineering mit Stefan Nogly, rund 45. Web mit Mike Franke, rund 25: Spryker, Frontend, Microservices. SAP mit Chris Blum, rund 20: SAP und Java. Dazu Microsoft (CRM) und ein übergreifendes Plattform-Team. Stimmen die Teamgrößen? Für Microsoft und Plattform fehlen uns Zahlen. |
| Pilot | Phase 1: Spryker. Phase 2: Frontend, Microservices, Plattform, SAP und Java. |
| Web | Spryker mit PHP/Symfony, Angular-Monorepo, Ibexa für Inhalte, Node.js. |
| SAP | SAP Business Technology Platform (BTP) mit Node.js, ABAP. Dazu ein Java-Team. |
| Werkzeuge | Repositories in Bitbucket. Continuous Integration (CI) in Bitbucket Pipelines. Tickets in Jira. Lokale Entwicklung auf Macs mit Docker – laut Fragebogen allgemein, für SAP/ABAP offen. |
| Review | Pflicht-Review per Pull Request nach dem Vier-Augen-Prinzip, teils nach dem Sechs-Augen-Prinzip. |
| Tests und Builds | Testansatz und Abdeckung je Team unterschiedlich. Automatisierte Tests laufen in der CI, wo es sie gibt. Build und Tests dauern einige Minuten bis knapp eine halbe Stunde, im SAP-Umfeld auch länger. |
| Vorgaben | Etablierte Programmierrichtlinien und Architekturvorgaben. Dazu das konzernweite Global Book of Standards, an dem ihr euch orientieren müsst. Besonderer Schutz für Bereiche wie Authentifizierung und personenbezogene Daten. |

## KI heute

- **Werkzeuge:** GitHub Copilot ist im Einsatz. Claude Code und Cursor prüft ihr.
- **Lizenzen:** ein Enterprise-Modell mit zentraler Verwaltung und Abrechnung. Die Lizenzen kommen von REWE.
- **Modelle:** nur ausgewählte, freigegebene Modelle, aus Datenschutzgründen, darunter Sonnet.
- **Budget:** rund 300 € pro Entwickler und Monat, vom Head-of überwacht.
- **Regeln:** keine festen Konfigurationsvorgaben, noch keine feste Policy für Agenten. Agenten dürfen Repositories und Konfigurationen sehen, aber keine Kundendaten und keine Secrets.
- **Erfahrung:** Die Teilnehmenden des Workshops arbeiten intensiv und täglich mit KI-Assistenten. Ein Team im Microsoft-Umfeld experimentiert, noch ohne abgestimmten gemeinsamen Ansatz.
- **Schulungen:** am 4. November „Basic: Einstieg in Agentic Engineering“, am 5. November „Advanced: Agent Factory bauen & betreiben“.
- **Ziele:** nach dem Workshop ein gemeinsames Zielbild und eine Roadmap. Nach drei Monaten sind KI-Assistenten fester Teil des Entwickleralltags und sparen messbar Zeit.

### Selbsteinschätzung des Spryker-Teams

Die Skala stammt aus unserem gemeinsamen Termin im September 2026: 0 Tippen (Vorschlag beim Tippen), 1 Dialog (jeder Schritt bestätigt), 2 Auftrag (Aufgabe rein, Ergebnis prüfen), 3 Kette (Kette von Spezialisten mit zwei Pflichtfreigaben), 4 Durchlauf (einmal starten, Ergebnis beurteilen), 5 Portfolio (mehrere Durchläufe, über Budget gesteuert). „fehlt“ verstehen wir als „nicht bewertet oder noch nicht vorhanden“ – bitte bestätigen.

| Nr. | Schritt | Heute |
|---|---|---|
| 1 | Anforderung | teilweise 1 |
| 2 | Verstehen | fehlt |
| 3 | Spezifikation | teilweise 1 |
| 4 | Kritik | fehlt |
| 5 | Freigabe | fehlt |
| 6 | Bauen | 2 |
| 7 | Laufzeitprüfung | fehlt |
| 8 | Prüfachsen (Prüfungen aus mehreren Blickwinkeln; so verstehen wir es – bitte bestätigen) | fehlt |
| 9 | Freigabe | fehlt |
| 10 | Auslieferung | fehlt |

Weitere Prüfschritte neben dem Pflicht-Review per Pull Request und den CI-Tests kennen wir bisher nicht – bitte ergänzt.

## Themen für den Workshop

1. **Vom Assistenten zur Kette:** Welche Schritte übernehmen Agenten im Spryker-Pilot zuerst, und wo sitzen die zwei Freigaben?
2. **Prüfungen:** Welche Prüfungen laufen im Spryker-Team schon automatisch, und welche fehlen euch?
3. **Regeln für Agenten:** Wie soll eine Policy für Agenten aussehen, und wer entscheidet darüber?
4. **Plattform:** Die CI läuft in Bitbucket Pipelines, eine Jira-Anbindung ist gewünscht; Copilot-Lizenzen kommen über REWE, Verwaltung und Abrechnung laufen zentral.
5. **Web und SAP:** Wie weit kommt ihr jeweils mit Git, Containern und Pull Requests, und was braucht SAP zuerst?
6. **Messen:** Woran macht ihr „messbar Zeit sparen“ fest, und welche Werte gibt es dafür schon?
7. **REWE Group:** Welche Vorgaben und Initiativen der REWE Group sollten wir berücksichtigen?

## Offene Fragen

Diese Fragen klären wir im Workshop:

1. Bedeutet „fehlt“ in der Selbsteinschätzung „nicht bewertet“ oder „noch nicht vorhanden“?
2. Welche Teile des Global Book of Standards betreffen Entwicklung und KI-Werkzeuge?
3. Was heißt das Ziel „Stufe 3 in allen Schritten bis Ende 2026“ für euch konkret?
4. Welcher SAP-Code liegt in Git, etwa über abapGit oder gCTS? Welche Teile bauen und testen in einem Container?
5. Was messt ihr heute schon, etwa Durchlaufzeit, Review-Dauer oder Fehlerquote? Woran wollt ihr „messbar Zeit sparen“ festmachen?
6. Welche Initiativen der REWE Group betreffen euch? Etwa das Pilotprojekt von REWE Digital mit „AI Ambassador Programm“ und „AI Hub“ [6], oder der Plan, alle SAP-Systeme von REWE in die Google Cloud zu bringen und über mehrere Jahre auf S/4HANA zu migrieren [7].

## Quellen

1. Lekkerland: „Über uns“, abgerufen am 15.11.2026. https://www.lekkerland.de/ueber-uns/
2. REWE-ZENTRALFINANZ eG: Financial Report 2025 (englische Fassung), 2026. https://www.rewe-group.com/content/uploads/2026/05/RZF-Finanzbericht-31.12.2025-final_EN.pdf
3. REWE-ZENTRALFINANZ eG: Finanzbericht 2024, 2025. https://www.rewe-group.com/content/uploads/2025/05/RZF-Finanzbericht-31.12.2024.pdf
4. The Retail Optimiser (Fourspot e.K.): „Lekkerland considers smart store concept with AiFi ready for rollout“, 26.11.2025. https://retail-optimiser.de/en/lekkerland-considers-smart-store-concept-with-aifi-ready-for-rollout/
5. Lekkerland Magazin: „Lekkerland macht seine Logistik fit für die Zukunft“, 24.01.2023. https://www.lekkerland.de/magazin/logistik/lekkerland-macht-logistik-fit-fuer-zukunft/
6. Lebensmittel Zeitung: „Rewe setzt auf KI-Botschafter“ (Rubrik: Transformation), 13.02.2026. https://www.lebensmittelzeitung.net/handel/karriere/transformation-rewe-setzt-auf-ki-botschafter-189343
7. Computerwoche: „Rewe packt seine SAP-Systeme in die Google-Cloud“, Mai 2025. https://www.computerwoche.de/article/3977214/rewe-packt-seine-sap-systeme-in-die-google-cloud.html
