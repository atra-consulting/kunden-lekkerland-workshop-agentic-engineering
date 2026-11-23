# Merkblatt: Mit der Factory arbeiten

Die Factory schreibt zu eurem Jira-Ticket eine Spec und baut sie nach der Freigabe. Eingerichtet hat sie der Admin. Ihr schreibt Tickets, startet Läufe, gebt frei und prüft.

## Vom Admin bekommt ihr

- Workspace und Name eures Repos.
- Ein Start-Token, nur für euch, gültig bis Workshop-Ende. Nie weitergeben, nie in Tickets, Chats oder Dateien.
- Die Namen der Freigabe-Personen.

## Ablauf

1. Ticket in Jira anlegen, Status „Definition“. Beschreibung mit Akzeptanzkriterien.
2. Genau ein Framework-Label: `sdd-openspec`, `sdd-speckit` oder `sdd-bmad`.
3. Ticket auf „Bereit“ setzen. Ohne Automation: `factory-spec` starten (unten).
4. Warten, bis das Ticket in „Wartet“ steht. Spec im Kommentar von `factory-bot` lesen. Ticket in „Klärung nötig“: Gründe und Fragen im Kommentar lesen, Beschreibung ergänzen, wieder auf „Bereit“, siehe [Ticket-Bereitschaft](ticket-bereitschaft.md).
5. Spec passt: Eine Freigabe-Person setzt „Spec freigegeben“. Spec passt nicht: „Zurück“, Ticket überarbeiten, weiter bei 3.
6. Ohne Automation: `factory-build` starten.
7. `factory-bot` öffnet einen Pull Request und setzt „Review“. Prüfen, eine benannte Person führt zusammen. Dann „Erledigt“.

## Lauf starten

Terminal mit bash oder zsh, unter Windows Git Bash. Platzhalter in spitzen Klammern ersetzen. Das Token tippt ihr unsichtbar ein.

```bash
printf 'Token: '; read -rs TOKEN; echo

printf 'header = "Authorization: Bearer %s"\n' "$TOKEN" | curl -sS -w '\nHTTP %{http_code}\n' -K - -X POST \
  -H "Content-Type: application/json" \
  "https://api.bitbucket.org/2.0/repositories/<workspace>/<repo>/pipelines" \
  -d '{"target":{"type":"pipeline_ref_target","ref_type":"branch","ref_name":"factory-base","selector":{"type":"custom","pattern":"factory-spec"}},"variables":[{"key":"JIRA_KEY","value":"<KEY>"}]}'
unset TOKEN
```

- Bau: `factory-build` statt `factory-spec`.
- Erwartet: `HTTP 201`. Den Lauf seht ihr in Bitbucket unter „Pipelines“ eures Repos.
- `HTTP 404`: Token, Workspace oder Repository falsch.

## Regeln

- Genau ein `sdd-`-Label. Kein, zwei oder ein unbekanntes Label: Der Lauf stoppt.
- Alle Gruppen dürfen gleichzeitig starten. Die Läufe warten aufeinander: „Queued“ in Bitbucket heißt warten, nicht neu starten. Im Lab war ein Lauf nach 1,5 bis 2 Minuten fertig; im Lekkerland-Repo und mit Wartezeit dauert es länger.
- Die Factory läuft nur auf `factory-base`, nicht auf euren Branches `workshop-<framework>-local`. Das Label wählt das Framework.
- Nach der Freigabe Beschreibung und Labels nicht ändern, Kommentare nicht bearbeiten. Sonst bricht der Bau ab.
- „In Arbeit“, „Wartet“, „Klärung nötig“ und „Review“ setzt nur `factory-bot`.
- Notaus: „Factory stoppen“. Laufende Läufe brechen ab. Weiter geht es nur mit „Fortsetzen“ durch eine Freigabe-Person.
- BMad darf im Lauf beliebiges Python ausführen. Nur Tickets aus vertrauenswürdiger Quelle.

## Wenn ein Lauf stoppt

- Kommentar `FACTORY-STOP v1` am Ticket: Der Grund steht darin, auf Englisch. Häufig: falscher Status (`spec runs start only from status Bereit`) oder fehlendes Label (`no framework chosen`).
- Kein Kommentar: Protokoll in Bitbucket unter „Pipelines“ lesen, dann den Admin fragen.

## Ergebnisse

Was ihr von `factory-base` in andere Branches übernehmt, entscheidet ihr.

## Lab von atra

Nur wenn die Einrichtung bei Lekkerland nicht klappt. Alles im Lab ist öffentlich: keine internen Anforderungen, Namen oder Daten in Tickets. Starten und freigeben macht dort atra.
