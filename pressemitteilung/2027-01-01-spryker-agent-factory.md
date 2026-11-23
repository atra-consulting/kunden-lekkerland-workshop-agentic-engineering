# Agent Factory: Das Spryker-Team macht den Anfang

**Frechen, 1. Januar 2027**

![img.png](img.png)

Seit heute arbeitet unser Spryker-Team mit der **Agent Factory**. Tickets aus Jira gehen an KI-Agenten, die daraus eine Spezifikation und Code machen. Menschen geben die Spezifikation frei und prüfen den Pull Request. Das Spryker-Team ist unser Pilot. In der zweiten Phase folgen Frontend, Microservices, Plattform sowie SAP und Java.

## Wo wir herkommen

KI-Assistenten nutzen viele von uns schon länger. GitHub Copilot ist im Einsatz, die Lizenzen kommen über die REWE Group. Bisher hat aber jedes Team, oft jede Person, auf eigene Art damit gearbeitet. Es gab viele Experimente, aber keine gemeinsamen Regeln für Agenten.

Im September 2026 hat sich das Spryker-Team selbst eingeschätzt: Wie weit helfen Agenten in den zehn Schritten von der Anforderung bis zur Auslieferung? Das Ergebnis war ehrlich. Beim Bauen ließ das Team die KI schon ganze Aufgaben erledigen. In den meisten anderen Schritten kam KI noch nicht vor, etwa bei Kritik, Freigabe, Laufzeitprüfung und Auslieferung.

Im November folgten zwei Schulungen mit atra: „Einstieg in Agentic Engineering“ und „Agent Factory bauen & betreiben“. Vom 23. bis 25. November haben wir dann drei Tage lang in Frechen gemeinsam mit atra einen Workshop gemacht. Drei Gruppen haben die Frameworks Spec Kit, OpenSpec und BMad Method an echten Tickets in Kopien unserer Repositories ausprobiert und jeweils an eine erste Factory angeschlossen.

## So arbeitet die Factory

1. **Anforderung:** Ein Jira-Ticket mit Akzeptanzkriterien geht an die Factory.
2. **Lauf 1:** Ein Agent liest Ticket und Code und schreibt eine Spezifikation. Dafür nutzen wir [Framework – die Entscheidung fällt nach dem Workshop].
3. **Freigabe 1:** Ein Mensch aus der Freigabegruppe prüft die Spezifikation und gibt sie in Jira frei. Ändert sich danach Ticket oder Spezifikation, gilt die Freigabe nicht mehr.
4. **Lauf 2:** Der Agent setzt die freigegebene Spezifikation um. Build, Tests und Schutzprüfungen laufen in Bitbucket Pipelines. Danach öffnet die Pipeline einen Pull Request.
5. **Freigabe 2:** Wir reviewen den Pull Request wie gewohnt nach dem Vier- oder Sechs-Augen-Prinzip.
6. **Auslieferung:** Merge und Auslieferung laufen über unseren bestehenden Weg. Die Factory liefert nichts selbst aus.

Die Agenten arbeiten mit Copilot CLI und freigegebenen Modellen wie Claude Sonnet. Damit übernimmt die Factory sechs der zehn Schritte. Die beiden Freigaben bleiben Pflicht, und sie bleiben bei uns. Es gilt ein einfaches Prinzip: KI unterstützt, Menschen entscheiden.

## Sicherheit: Die Factory darf wenig

Wir gehen davon aus, dass in einem Ticket-Text auch einmal eine versteckte Anweisung an den Agenten stecken kann, eine sogenannte Prompt Injection. Deshalb haben wir die Factory so gebaut, dass ein Agent möglichst wenig Schaden anrichten kann:

- Der Agent hat keinen Zugang zu Jira und darf das Repository in Bitbucket nur lesen.
- Er sieht keine Secrets außer seinem eigenen, kurz gültigen Copilot-Token.
- Code, den der Agent schreibt, läuft nur in Schritten ohne Secrets.
- `main` ist geschützt. Nur benannte Menschen dürfen dorthin pushen.
- Jede Person im Pilot kann ein Ticket auf „Factory gestoppt“ setzen. Aufheben können den Stopp nur Menschen.
- Im Zweifel stoppt die Factory, statt zu pushen oder zu kommentieren.

## Was wir im Vortest gelernt haben

Vor dem Workshop lief die Factory an einer kleinen PHP-Beispielanwendung. Drei Erkenntnisse haben das Design geprägt:

- **Freigabe 1 ist nötig.** Zwei Läufe zum selben Ticket trafen unterschiedliche fachliche Annahmen. Ohne einen Menschen, der die Spezifikation prüft, hätten wir zwei verschiedene Lösungen bekommen.
- **Die Factory muss selbst nachprüfen.** Copilot CLI meldete auch dann Erfolg, wenn ein Schritt abgelehnt wurde oder pausierte.
- **Klare Vorgaben helfen.** Ohne genannten Testbefehl wählte das Modell immer wieder einen, der nicht erlaubt war.

Die größte Herausforderung ist also nicht die KI selbst, sondern ihre verlässliche und nachvollziehbare Nutzung. Deshalb setzen wir auf klare Leitplanken, gemeinsame Regeln und konsequente Prüfungen.

## Was es kostet

Im Vortest kostete ein kleines Feature je nach Framework 30 bis 120 AI Credits, also 0,30 bis 1,20 US-Dollar. Das waren Einzelwerte an Beispielcode, kein Erwartungswert. Für echte Tickets im Spryker-Code messen wir die Kosten jetzt laufend. Die Factory läuft über einen technischen Benutzer mit eigenem Budget. Ist das Budget aufgebraucht, stoppt sie.

## Stimmen aus dem Team

> „[Zitat aus dem Spryker-Team]“

## Wie es weitergeht

In Phase 2 binden wir Frontend, Microservices, Plattform sowie SAP und Java an. Ein zentrales Agent-Factory-Team entwickelt die Plattform weiter: Regeln, Skills und Prüfungen. AI Champions in den einzelnen Teams sammeln Erfahrungen und geben sie weiter. So profitieren alle Teams von gemeinsamen Standards und einem wachsenden Wissensnetzwerk.

Ihr wollt sehen, wie die Factory im Alltag aussieht? Sprecht das Spryker-Team an. [Kontakt oder Termin für eine Demo]
