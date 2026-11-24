# Übung 3: Tickets mit dem Skill schreiben

Der Copilot-Skill `ticket-schreiben` macht aus einer Absicht ein oder mehrere Jira-Tickets, die die Bereitschaftsprüfung der Factory bestehen. Ihr gebt eine echte Absicht aus eurem Backlog ein und seht zu: Code-Erkundung, Fragen des Frameworks, Prüfung jedes Entwurfs, euer Ja, das Ticket in Jira. Die Referenz: [Tickets mit dem Skill schreiben](../../02-agent-factory/bedienung/ticket-skill.md).

- **Ihr braucht** den Framework-Branch mit `factory/` aus [Übung 1](uebung-factory-lokal.md) und eurem Kriterium aus [Übung 2](uebung-bereitschaft.md), dazu den Jira-MCP-Server `atlassian` aus Übung 1.
- **Nur Absichten, die ihr an Copilot schicken dürft.** Keine Personendaten, keine vertraulichen Kundendaten.
- **Ein Rechner je Gruppe, wenn möglich ein Mac.** Windows ist nicht getestet.
- **Kosten:** Im Lab kostete ein Ticket 29 bis 43 Credits, dazu 6 bis 13 Credits je Prüfung durch die Factory. Ein Lauf mit einem Ticket dauerte samt Lesen und Antworten etwa 5 bis 10 Minuten.
- **Freiwillig:** Der Skill ist kein Teil der Factory. Die Factory startet erst, wenn ein Ticket auf „Bereit“ steht.

## 1. Skill ins Projekt kopieren

`<workshop-repo>` ist der Ordner, in dem euer Klon dieses Workshop-Repos liegt.

```bash
git switch <framework-branch>
mkdir -p .github/skills
cp -R <workshop-repo>/02-agent-factory/werkzeuge/ticket-schreiben .github/skills/
rm -rf .github/skills/ticket-schreiben/tests
```

**Das seht ihr:** `.github/skills/ticket-schreiben/` mit `SKILL.md`, `jira_ticket.py`, `arbeitsstand.py` und `ticket-schreiben.example.json`.

## 2. Konfiguration schreiben

Legt `.github/ticket-schreiben.json` an:

```json
{
  "framework": "openspec",
  "jira_project": "<PROJEKT>",
  "issue_type": "Task",
  "labels": [],
  "test_command": "make test",
  "module_docs": "<ordner-der-modul-doku>"
}
```

- `framework`: `openspec` oder `speckit`, passend zu eurem Branch. Der Skill fragt mit diesem Framework nach und setzt das Label `sdd-<framework>`.
- `jira_project`: der Projektschlüssel in Jira. Den Vorgangstyp `issue_type` muss es in diesem Projekt geben.
- `module_docs`: der Ordner mit der Modul-Doku, die ihr in Übung 1 zusammengeführt habt. Ohne Modul-Doku lasst ihr `module_docs` weg.
- `confluence_space` lasst ihr weg. Die Suche nach der Domäne in Confluence und in `module_docs` ist nicht getestet: Das Lab hat keinen Confluence-Bereich mit Domänen.

**Das seht ihr:** Die Datei liegt neben `.github/skills/`.

## 3. Committen und prüfen

```bash
git add .github/skills/ticket-schreiben .github/ticket-schreiben.json
git commit -m "Skill ticket-schreiben"
copilot skill list
git status --short
```

**Das seht ihr:** `copilot skill list` zeigt `ticket-schreiben`. `git status --short` zeigt nichts. Das braucht der Skill: Er merkt sich den Stand und stellt ihn am Ende wieder her.

## 4. Skill starten

Wählt eine echte, kleine Absicht aus eurem Backlog. Schreibt sie direkt hinter den Befehl:

```bash
copilot
```

```text
/ticket-schreiben <eure Absicht in einem Satz>
```

Im Lab lautete eine Absicht: „Leser sollen sehen, wie lange sie für einen Artikel brauchen.“

Copilot fragt vor jedem Befehl. Lest die Befehle, dann `1. Yes`. Der Skill ändert keinen Produktcode und committet nichts. Will Copilot in Produktcode oder Tests schreiben, lehnt ab.

**Das seht ihr:** Der Skill liest die Konfiguration, merkt sich den Stand des Repos (`arbeitsstand.py merken`) und sucht `factory/local.py`.

## 5. Zusehen: Code, Fragen, Prüfung

| Schritt | Das seht ihr |
|---|---|
| Code-Erkundung | Der Skill liest Code, Tests und eure Modul-Doku. Gibt es die Funktion schon oder widerspricht sie dem Code, sagt er es sofort, mit Datei und Zeile. Im Lab fand er den RSS-Feed, bevor das Framework die erste Frage stellte ([FLAB-29](https://betterprojectsfaster.atlassian.net/browse/FLAB-29)). |
| Fragen des Frameworks | Spec Kit: `speckit-specify`, dann `speckit-clarify` mit wenigen Fragen und einem Antwortvorschlag. OpenSpec: `openspec-explore` stellt Optionen zur Wahl. Danach nennt der Skill die Annahmen des Frameworks. Ihr bestätigt oder korrigiert sie. |
| Reife-Check des Skills | Eine Tabelle mit allen Kriterien, je „erfüllt“ oder „offen“. Der Skill liest `factory/readiness.md`, also auch euer `missing_domain`. Ist die Absicht `too_big`, schlägt er ein Epic mit mehreren Tickets vor. |
| Prüfung der Factory | Für jeden Entwurf `jira_ticket.py pruefdatei`, dann `python3 -I factory/local.py assess --ticket-file ticket-entwurf-1.json`. Exit-Code 0 heißt „ready“, 4 heißt „not_ready“ mit Gründen und Fragen. |

## 6. Bestätigen

Der Skill zeigt euch alles zusammen: Reife-Tabelle, Urteil der Factory und den ganzen Text jedes Tickets. Darunter fragt er einmal: „Soll ich diese Tickets so in <PROJEKT> anlegen?“ Lest alles, dann sagt Ja oder ändert die Entwürfe.

Ein Ticket mit „not_ready“ legt der Skill nur an, wenn ihr ausdrücklich „trotzdem anlegen“ sagt. Dann bekommt es den Abschnitt „Offene Punkte“.

**Das seht ihr:** Ziel, Akzeptanzkriterien, Nicht Teil des Tickets und Hinweise, je Ticket.

## 7. Das Ticket in Jira

Der Skill legt das Ticket über den Jira-MCP an. Copilot fragt vor dem Aufruf von `createJiraIssue`. Danach räumt der Skill auf (`arbeitsstand.py aufraeumen --ja`).

**Das seht ihr:** die URL des neuen Tickets. In Jira steht es im ersten Status eures Projekts, bei der Factory „Definition“, mit dem Label `sdd-<framework>`. Ein Lauf startet dadurch nicht. Am Ende sieht `git status --short` aus wie vorher.

Über den Jira-MCP ist nur das Anlegen eines einzelnen Tickets getestet ([FLAB-36](https://betterprojectsfaster.atlassian.net/browse/FLAB-36)), nicht ein ganzer Lauf und kein Epic mit Tickets darunter.

**Dürft ihr in Jira nicht anlegen,** lehnt bei der Rückfrage zu `createJiraIssue` ab. Kopiert vorher den Text aus Schritt 6. Bittet Copilot, mit `python3 -I .github/skills/ticket-schreiben/jira_ticket.py anlegen --entwurf ticket-entwurf-1.md --dry-run` die Anfrage an Jira zu zeigen. Bei einem einzelnen Ticket heißt der Entwurf `ticket-entwurf.md`. Der Probelauf legt nichts an. Niemand hat diesen Weg im Skill getestet. Die Referenz beschreibt den zweiten Zugang mit API-Token unter [Weg B](../../02-agent-factory/bedienung/ticket-skill.md#weg-b-api-token-und-jira_ticketpy).

## Wenn es hakt

- **`MCP server 'atlassian' requires authentication` oder `OAuth callback timeout`:** `/mcp`, `atlassian`, noch einmal „Authenticate“. Im Lab reichte der zweite Versuch. Lehnt Atlassian die Anmeldung ab, fragt euren Atlassian-Admin.
- **Der Skill zeigt Annahmen oder einen Entwurf, ohne dass `openspec-explore` oder `speckit-specify` lief:** Sagt „Frag bitte erst mit dem Framework nach.“ Im Lab hat der Skill diesen Schritt einmal übersprungen.
- **`arbeitsstand.py merken` endet mit Exit-Code 3:** Es gab schon Änderungen. Beendet den Skill, committet oder sichert mit `git stash`, startet neu.
- **Tabelle und Ticket-Text fehlen vor der Frage „Soll ich … anlegen?“:** Bittet Copilot, sie ins Frageformular zu schreiben. Im Lab standen sie dann vollständig dort.
- **Der Skill meldet, dass `factory/local.py` fehlt oder `local.py` mit einem Fehler endet:** Dann gilt nur sein eigener Reife-Check. Prüft, ob `factory/local.py` auf eurem Branch liegt.

## Ergebnis

Eure Gruppe hat:

- ein echtes Ticket in eurem Jira, mit Akzeptanzkriterien und dem Label `sdd-<framework>`, geprüft mit euren Kriterien,
- den Skill und seine Konfiguration auf dem Framework-Branch,
- ein sauberes Repo: `git status --short` zeigt nichts.
