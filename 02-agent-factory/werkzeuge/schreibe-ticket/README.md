# Skill `schreibe-ticket`

Der Copilot-Skill macht aus einer Absicht ein oder mehrere Jira-Tickets, die die Bereitschaftsprüfung der Factory bestehen. Du startest ihn in Copilot CLI mit `/schreibe-ticket <Absicht>`.

- Einrichten und Bedienung: [Tickets mit dem Skill schreiben](../../bedienung/ticket-skill.md)
- Übung im Workshop: [Übung 3](../../../01-erstworkshop/tag-2/uebung-ticket-schreiben.md)
- Anweisungen an Copilot: [`SKILL.md`](SKILL.md)

Diese Seite erklärt drei Fragen: Woher kennt der Skill das Framework? Wie arbeitet er damit? Und wie passt sein Ergebnis zu dem, was `agentic-factory.py assess` durchlässt?

## Die Dateien

| Datei | Zweck |
|---|---|
| `SKILL.md` | Die neun Schritte, die Copilot befolgt |
| `jira_ticket.py` | Prüft den Jira-Zugang (`pruefen`), schreibt die Prüfdatei (`pruefdatei`) und legt Tickets per API-Token an (`anlegen`) |
| `arbeitsstand.py` | Merkt sich den Stand des Repos (`merken`) und räumt am Ende auf (`zeigen`, `aufraeumen --ja`) |
| `schreibe-ticket.example.json` | Vorlage für `.github/schreibe-ticket.json` |
| `tests/` | Unit-Tests: `python3 -I -m unittest discover -s tests`. Im Projekt löschst du den Ordner. |

## 1. Woher der Skill das Framework kennt

Aus der Konfiguration `.github/schreibe-ticket.json`, Feld `"framework"`: `openspec`, `speckit` oder `bmad`. Der Skill erkennt das Framework nicht selbst im Repo.

- `jira_ticket.py` lässt nur diese drei Werte zu (`FRAMEWORKS`).
- Jedes Ticket bekommt das Label `sdd-<framework>`. Daran wählt die Factory später dasselbe Framework.
- `labels_fuer` setzt das Label und lehnt ein zweites `sdd-`-Label ab. Das ist dieselbe Regel wie in `agentic-factory.py`: genau ein `sdd-`-Label.

## 2. Wie er mit dem Framework arbeitet

In Schritt 4 von `SKILL.md` stellt das Framework die Fragen, nicht der Skill. Er hört vor Plan und Tasks auf:

| `framework` | Framework-Skills | Ergebnis, in Schritt 9 wieder gelöscht |
|---|---|---|
| `speckit` | `speckit-specify`, dann `speckit-clarify` | `specs/<NNN>-<name>/spec.md` |
| `openspec` | `openspec-explore`, dann `openspec-propose`, nur Proposal und Spec-Deltas | `openspec/changes/<name>/` |
| `bmad` | `bmad-forge-idea`, dann `bmad-spec` (Express) | `_bmad-output/.../SPEC.md` |

Entscheidungen und Akzeptanzkriterien aus dem Ergebnis übernimmt der Skill in den Ticket-Text. Design, Tasks und Code schreibt später die Factory.

Im Test am 24. November hat der Skill diesen Schritt mit OpenSpec übersprungen, in einem Lauf mit `copilot -p`. Er rief `openspec-explore` nicht auf und legte den Change-Ordner von Hand an. Seitdem verlangt `SKILL.md`: Schritt 5 beginnt erst, wenn ein Framework-Skill gelaufen ist, und OpenSpec-Changes entstehen mit `openspec new change`. Diese Fassung ist noch nicht in einem echten Lauf getestet.

## 3. Wie das Ergebnis zu `agentic-factory.py assess` passt

Es gibt zwei Ebenen. Die zweite ist die eigentliche Prüfung der Factory.

**Der eigene Reife-Check (Schritt 5).** Gibt es `factory/readiness.md`, liest der Skill dessen Kriterien und den Abschnitt „How to Judge“. Sonst nimmt er seine sechs Kriterien aus `SKILL.md`. Ergänzt ein Team ein Kriterium wie `missing_domain`, sieht der Skill es auch.

**Die echte Prüfung der Factory (Schritt 7).** Für jeden Entwurf:

```bash
python3 -I .github/skills/schreibe-ticket/jira_ticket.py pruefdatei --entwurf ticket-entwurf-1.md
python3 -I factory/agentic-factory.py assess --ticket-file ticket-entwurf-1.json
```

- `pruefdatei` schreibt den Entwurf als JSON, so wie die Factory ihn aus Jira liest. Den Text wandelt es ins Dokumentformat von Jira und zurück (`adf_text(als_adf(…))`). Das ist dieselbe Umwandlung, die die Factory beim Lesen nutzt. Dazu kommen der Platzhalter-Schlüssel `<PROJEKT>-0` und das Label `sdd-<framework>`.
- `agentic-factory.py assess` (früher `local.py`) ist die Prüfung der Factory selbst: derselbe Prompt und dieselben Werkzeuge aus `config.json`, dieselbe `readiness.md`, dasselbe Modell und dieselbe Credit-Grenze wie der Assess-Schritt der Pipeline. Mit `--ticket-file` fragt es Jira nicht und postet keinen Kommentar.
- Exit-Code 0 heißt „ready“, 4 heißt „not_ready“ mit Gründen und Fragen. Jeder andere Exit-Code ist ein Fehler, kein Urteil. Dann gilt der eigene Check des Skills.
- Ein Ticket mit „not_ready“ legt der Skill nur an, wenn du ausdrücklich „trotzdem anlegen“ sagst. Dann bekommt es den Abschnitt „Offene Punkte“.

**Die Regeln des Teams (Schritt 6).** Hat `factory/config.json` einen Block `rules`, liest der Skill die Dateien unter `rules.calls.clarify`, etwa `factory/regeln/stil.md` und `factory/regeln/ticket.md`. Er befolgt sie beim Schreiben der Tickets. Fehlt eine Datei, überspringt er sie. `agentic-factory.py` hängt dieselben Dateien an den Prompt von `clarify`. Die Bereitschaftsprüfung (`assess`) bekommt die Dateien unter `rules.calls.assess`, in der Vorlage nur `regeln/ticket.md`.

Im Test am 24. November lief diese Kette wie beschrieben: `pruefdatei`, dann `assess`, Urteil „ready“ für 7 Credits. Vor der Frage „Soll ich … anlegen?“ stand der ganze Ticket-Text.

## Wo es von der Pipeline abweichen kann

- **Das Urteil ist nicht garantiert.** Die Prüfung ist ein Aufruf eines Sprachmodells. Prüft die Pipeline das Ticket auf „Bereit“ noch einmal, kann sie bei demselben Text anders urteilen.
- **Dieselben Dateien.** `agentic-factory.py` nimmt `config.json`, `readiness.md` und `regeln/` aus deinem Ordner `factory/`. Gleich wie in der Pipeline sind sie nur, wenn du die Fassungen der Pipeline kopiert hast.
- **Jira-MCP.** Legt der Skill das Ticket über `createJiraIssue` an, schickt er Markdown, und Jira wandelt es selbst um. `pruefdatei` bildet die Umwandlung von `jira_ticket.py` nach. Ob der Text, den die Factory danach aus Jira liest, Wort für Wort gleich ist, ist über den MCP-Weg nicht getestet.
