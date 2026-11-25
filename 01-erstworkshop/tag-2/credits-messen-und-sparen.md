# Credits messen und sparen

Kurzfassung für Mittwoch, 25. November 2026, und die Fragen, die wir dafür heute, am Dienstag, klären. Stand: 24. November 2026, Entwurf.

## Fragen für heute, Dienstag

Die Antworten brauchen wir am Mittwoch. Die meisten kennt ihr aus eurem Alltag.

**Copilot im Alltag:**

1. Womit arbeitet ihr mit Copilot: Copilot CLI, VS Code, eine andere IDE? Wer nutzt was?
2. Welches Modell nutzt ihr im Alltag? Ist Claude Sonnet 5.5 euer Hauptmodell, oder nur das Modell im Workshop?
3. Seht ihr in Copilot CLI mit `/usage`, was eine Sitzung kostet? Habt ihr schon einmal darauf geschaut?
4. Wie viele Tickets bearbeitet eine Person im Monat ungefähr? Wir brauchen nur eine grobe Zahl je Team.
5. Haben eure Business-Analysten eine Copilot-Lizenz? Wenn ja: Womit arbeiten sie?

**Für Mittwoch vorbereiten:**

6. Wer verwaltet Copilot bei euch: REWE oder Lekkerland? Wer davon kann am Mittwoch dabei sein oder vorher antworten?
7. Wer kennt euer Copilot-Budget: die rund 300 Euro je Person und Monat? Was gehört dazu: nur Copilot, oder auch andere Werkzeuge?
8. Wer ist bei euch für Betriebsrat und Datenschutz die Ansprechperson, wenn wir Verbrauch je Person messen wollen?
9. Läuft Copilot bei euch über einen Proxy?

## Kurzfassung

**Ob das Budget reicht, wissen wir noch nicht.** Dafür fehlen eure echten Verbrauchszahlen. Was wir wissen:

- **Abrechnung:** Copilot rechnet seit 1. Juni 2026 in AI Credits ab. 1 Credit kostet 0,01 US-Dollar. Code-Vervollständigung im Editor verbraucht keine Credits.
- **Der Pool:** Jede Lizenz bringt Credits in einen gemeinsamen Pool, 1.900 bei Business und 3.900 bei Enterprise. Erst danach wird es teurer: weiter mit 0,01 US-Dollar je Credit, wenn Mehrverbrauch erlaubt ist. Sonst ist bis zum nächsten Abrechnungszeitraum Schluss. Nicht genutzte Credits verfallen.
- **Euer Budget:** rund 300 Euro je Person und Monat, also etwa 30.000 bis 34.500 Credits, je nach Wechselkurs.
- **Im Lab:** etwa 30 bis 120 Credits je kleinem Ticket, je nach Framework und Ablauf. Das sind Einzelwerte mit einer Beispiel-App, nicht euer Code.

**Rechenbeispiel, mit den Werten aus dem Lab:**

| Tickets je Person und Monat | Credits | Anteil am Business-Pool (1.900) | Anteil am Enterprise-Pool (3.900) | Anteil an 300 Euro |
|---|---|---|---|---|
| 20 | 600 bis 2.380 | 32 bis 125 % | 15 bis 61 % | 2 bis 8 % |
| 40 | 1.200 bis 4.760 | 63 bis 251 % | 31 bis 122 % | 3,5 bis 16 % |

Gerechnet mit 30 bis 119 Credits je Ticket. Der Pool ist gemeinsam, die Anteile gelten für eine durchschnittliche Person.

Gegen 300 Euro bleibt viel Luft. Gegen den Anteil am Pool nicht. Welche Grenze bei euch zuerst greift, klären wir am Mittwoch.

**Wichtig:** Solange ihr im Pool bleibt, spart ihr mit weniger Credits kein Geld. Sparen lohnt sich erst über dem Pool. Agenten-Ketten mit Review-Agenten kosten deutlich mehr als einfache Läufe: Im Lab kostete ein Bau-Schritt mit Review-Agenten 88 Credits, ohne sie 23.

## So messt ihr

| Was | Wer | Zeigt |
|---|---|---|
| Rechnung und Budgets in GitHub | Copilot-Admin | Die einzige echte Summe. Budgets je Person oder je Kostenstelle |
| Metriken-Schnittstelle von GitHub | Copilot-Admin | Credits je Person und Tag. Keine Aufteilung nach Modell oder Werkzeug, und keine Rechnung |
| `/usage` in Copilot CLI | jede Person | Token je Modell und Credits der Sitzung |
| `/context` und `/mcp` in Copilot CLI | jede Person | Wie viel Platz Werkzeuge und Verlauf belegen |
| `--usage-output-file` | Factory, `agentic-factory.py` | Credits je Lauf. So messen wir im Lab |

Verbrauch je Person misst Menschen. Ob dafür Betriebsrat und Datenschutz zustimmen müssen, entscheidet ihr. Bis dahin messen wir je Team und je Ticket.

## Was sofort hilft, ohne Werkzeug

| Gewohnheit | Wirkung |
|---|---|
| Den Testbefehl im Prompt nennen, und genau ihn erlauben | Im Lab 25 bis 38 % weniger je Bau-Lauf. Einzelne Läufe |
| Vorlagen-Fehler beheben, an denen Factory-Läufe scheitern | Im Lab 11,5 % einer Testreihe |
| Eine Sitzung je Ticket, mit `/clear` dazwischen | Sauberer Kontext. Ersparnis nicht gemessen |
| Modell und Aufwand zu Beginn festlegen, nicht mitten in der Sitzung wechseln | Ein Wechsel kann den Cache verlieren. Ersparnis nicht gemessen |
| `--disable-builtin-mcps` in Bitbucket-Repos | Der eingebaute GitHub-Server findet dort ohnehin nichts |
| Eine kurze Anweisungsdatei je Repo | Copilot liest alle Anweisungsdateien in jeder Sitzung |

Deutsch statt Englisch kostet vermutlich etwas mehr Token. Wie viel, hat niemand gemessen. Bleibt bei Deutsch, wo es der Verständlichkeit dient.

## Der Plan

| Wann | Was | Wer |
|---|---|---|
| Mittwoch, 25. November | Zugang klären: Copilot-Admin, Budgets, Abrechnung | Führung |
| bis 18. Dezember | **Grundlage messen:** Rechnung und Metriken, 5 bis 10 Referenz-Tickets je Team mit `/usage`, Hochrechnung für Agenten-Ketten | Copilot-Admin, Team-Leads, Plattform-Team |
| ab 4. Januar 2027 | **Gewohnheiten** aus der Tabelle oben | Team-Leads, Plattform-Team |
| Januar 2027 | **Entscheidung:** Reicht das, oder braucht ihr mehr, etwa Telemetrie oder ein Gateway? | Führung |

Gibt es bis 4. Dezember keinen Zugang zu Rechnung und Metriken, messen die Teams die Referenz-Tickets selbst mit `/usage`. Zahlen aus dem Dezember sind wegen der Feiertage niedrig. Die Entscheidung im Januar stützt sich deshalb auf November und Januar.

## Fragen für Mittwoch, an Führung und Copilot-Admin

1. **Wer verwaltet Copilot,** REWE oder Lekkerland? Bekommen wir Lesezugriff auf Rechnung und Metriken?
2. **Welcher Plan:** Business oder Enterprise? Wie viele Lizenzen?
3. **Welche Grenze stoppt eine Person:** ein Budget je Person, ein Budget je Kostenstelle, oder der leere Pool ohne Mehrverbrauch?
4. **Ist Mehrverbrauch erlaubt,** und wer zahlt ihn?
5. **Was umfassen die 300 Euro** je Person und Monat?
6. **Verbrauch je Person messen:** Müssen Betriebsrat und Datenschutz zustimmen? Bis wann?
7. **Wer übernimmt** die Messung bis 18. Dezember: Copilot-Admin, Team-Leads, Plattform-Team?
