# Jira für die Factory einrichten

Diese Anleitung richtet das Jira-Projekt für die Factory ein: Konto `factory-bot`, neun Status, Übergänge mit Freigabe (Gate 1) und Prüfung der Ticket-Bereitschaft. Optional: zwei Automation-Flows, die die Bitbucket-Pipelines starten. Ohne Flows startet ihr die Läufe per curl. Teil A braucht die Factory immer: Der Guard liest Status und Freigabe aus Jira. Alles hier erledigt ein Admin von Lekkerland zusammen mit atra, auch das Anlegen von `factory-bot`.

Pipeline: [Bitbucket-Anleitung](bitbucket.md). Gesamtbild: [Überblick](../ueberblick.md).

## Vor dem Start

- Reihenfolge: Bitbucket, Schritte 1 bis 3, dann Teil A, dann Bitbucket, Schritte 4 bis 10, dann Teil C. Teil B nur, wenn Läufe von selbst starten sollen.
- [ ] Ein team-managed Projekt in Jira Cloud für den Pilot. Nur dort ändern Projekt-Admins den Workflow selbst.
- [ ] Du hast Admin-Rechte für die Jira-Site und das Projekt.
- [ ] Eine E-Mail-Adresse für `factory-bot`, ein Konto für alle Gruppen.
- [ ] Ein Passwortmanager für die Tokens.
- **Offen:** Wie `factory-bot` ohne die Standardgruppe Zugriff auf Jira bekommt; braucht es dafür einen Jira-Platz? Blockiert Schritt 1.
- **Offen:** Klickpfad für ein Atlassian-API-Token mit Scopes. Blockiert Schritt 1 und `JIRA_API_TOKEN` in der Bitbucket-Anleitung.
- **Offen:** Wo Lekkerland die Cloud-ID abliest. Blockiert Schritt 1 (Prüfen), Schritt 6 und Teil C, Probe 3. Ungetestet: `https://<site>.atlassian.net/_edge/tenant_info` liefert `cloudId`.
- **Offen:** Bietet der Jira-Plan die zwei Regeln aus Schritt 4? Blockiert Schritt 4. Ohne sie gibt es keinen getesteten Weg.
- **Offen:** Monatliches Automation-Limit des Jira-Plans. Betrifft Teil B.
- **Offen:** Namen der Freigabe-Personen. Blockiert Schritt 4 und 6.

Offene Punkte klärst du mit atra.

## Teil A: Workflow einrichten

### Schritt 1: Factory-Konto anlegen und berechtigen

Ziel: `factory-bot` sieht, kommentiert und verschiebt nur Tickets dieses Projekts. Wer sein Token hat, handelt als `factory-bot`. Nur du legst seine Tokens an und verwahrst sie.

1. Lege den Benutzer `factory-bot` mit seiner E-Mail-Adresse an. Passwort und zweiten Faktor von `factory-bot` im Passwortmanager. Sein Postfach erreichst nur du.
2. Stelle den Projektzugriff auf „Private“.
3. Nimm `factory-bot` aus der Standardgruppe der Site. Zugriff nur: in Jira die Projektrolle „Factory“ für dieses Projekt, in Bitbucket „Write“ nur auf das Repo, keine Workspace-Gruppe.
4. Lege eine eigene Rolle an, etwa „Factory“, als Kopie von „Viewer“.
5. Gib der Rolle nur „Transition any issue“ und „Add comments“, dazu die Ansicht aus „Viewer“. Kein Bearbeiten, Anlegen oder Löschen, auch keine Anhänge. Kein Bearbeiten oder Löschen eigener Kommentare: So ändert `factory-bot` die Spec nach der Freigabe nicht.
6. Gib `factory-bot` diese Rolle im Projekt.
7. Lege für `factory-bot` ein API-Token an: Scopes `read:jira-work` und `write:jira-work`, kurze Laufzeit (etwa zwei Wochen), im Passwortmanager. Vor Ablauf: neues Token anlegen, in Bitbucket neu eingeben. Altes Token sofort widerrufen.

Tokens mit Scopes gehen nicht über `https://<site>.atlassian.net`. Für alle Aufrufe hier gilt darum `JIRA=https://api.atlassian.com/ex/jira/<CLOUD-ID>`. curl fragt jeweils nach dem Token.

**Prüfen (ungetestet):** `curl -s -u "<FACTORY-BOT-E-MAIL>" "$JIRA/rest/api/3/project/search"` mit dem Token von `factory-bot`. Erwartet: nur das Pilot-Projekt.

### Schritt 2: Status anlegen

Ziel: ein Workflow für alle Ticket-Typen (Epic, Subtask, Task, Story) mit diesen neun Status. Der Guard prüft IDs, nicht Namen. Englische Namen: ungetestet.

| Status | Kategorie | Bedeutung |
|---|---|---|
| Definition | „To Do“ | Eine Person schreibt das Ticket. |
| Bereit | „To Do“ | Startet den Spec-Lauf. |
| Klärung nötig | „To Do“ | Ticket ist nicht bereit für eine Spec. Eine Person ergänzt es. Siehe [Ticket-Bereitschaft](../bedienung/ticket-bereitschaft.md). |
| In Arbeit | „In Progress“ | Nur kurz, im Spec-Lauf. |
| Wartet | „In Progress“ | Spec wartet auf Freigabe. |
| Bau | „In Progress“ | Freigegeben. Startet den Bau-Lauf. |
| Review | „In Progress“ | Pull Request offen. |
| Erledigt | „Done“ | Fertig. |
| Factory gestoppt | „In Progress“ | Notaus. Laufende Pipelines brechen ab. |

### Schritt 3: Übergänge anlegen

Ziel: diese zehn Übergänge. Nur „Factory stoppen“ ist global. Neue Tickets starten in „Definition“.

| Übergang | Von | Nach | Wer |
|---|---|---|---|
| Bereit | Definition oder Klärung nötig | Bereit | eine Person |
| Start | Bereit | In Arbeit | `factory-bot` |
| Spec fertig | In Arbeit | Wartet | `factory-bot` |
| Klärung nötig | In Arbeit | Klärung nötig | `factory-bot`: Ticket nicht bereit oder Rückfragen des Frameworks |
| Spec freigegeben | Wartet | Bau | nur Freigabe-Personen (Schritt 4) |
| Zurück | Wartet | Definition | eine Person, wenn die Spec nicht passt |
| Bau fertig | Bau | Review | `factory-bot` |
| Erledigt | Review | Erledigt | eine Person, nach dem Zusammenführen |
| Factory stoppen | jeder Status | Factory gestoppt | jede Person, auch `factory-bot` |
| Fortsetzen | Factory gestoppt | Definition | nur Freigabe-Personen (Schritt 4) |

Schritt 4 erzwingt die Spalte „Wer“ für die Freigabe und für die vier Übergänge von `factory-bot`. Den Rest regelt die Absprache.

### Schritt 4: Freigabe absichern

Ziel: Nur Freigabe-Personen geben frei, nie `factory-bot`. Setze beide Regeln auf den Übergang „Spec freigegeben“:

| Regel | Einstellung | Wirkung |
|---|---|---|
| „Restrict who can move a work item“ | die Freigabe-Personen als einzelne Benutzer (Gruppe: ungetestet) | Nur sie geben frei. |
| „Restrict users who have previously updated a work item's status“ | Übergang In Arbeit → Wartet | Wer „Spec fertig“ gesetzt hat (`factory-bot`), gibt nicht frei. |

- „Fortsetzen“: erste Regel ebenso, mit den Freigabe-Personen.
- „Start“, „Spec fertig“, „Klärung nötig“ und „Bau fertig“: erste Regel mit der Projektrolle „Factory“ aus Schritt 1. So setzt nur `factory-bot` diese Status. Im Lab getestet in einem company-managed Projekt (Bedingung „User Is In Project Role“); in einem team-managed Projekt ungetestet. Setze diese Regel erst nach Schritt 6: Sonst kann der Admin die vier Übergänge am Testticket weder setzen noch ihre IDs ablesen.
- Freigabe-Personen setzen nie „Spec fertig“. Sonst können sie dieses Ticket nicht freigeben.
- Mache nur benannte Personen zu Projekt-Admins. Jeder Projekt-Admin kann diese Regeln ändern.

**Prüfen:** Teil C, Probe 3.

### Schritt 5: Framework-Labels festlegen

Ziel: Das Label am Ticket wählt das SDD-Framework. In Jira nichts vorab anlegen; Teilnehmende setzen das Label am Ticket. Labels: `sdd-openspec` (OpenSpec), `sdd-speckit` (Spec Kit), `sdd-bmad` (BMad). Gib den Teilnehmenden diese Regeln mit:

- Genau ein Label am Ticket, oder `FRAMEWORK` beim Start per curl. Kein Label, zwei Labels oder ein unbekanntes `sdd-`-Label: Spec-Lauf stoppt.
- Mehrere Tickets dürfen gleichzeitig starten. Die Läufe warten aufeinander („Queued“) und starten von selbst.
- Nach der Freigabe nichts an Beschreibung oder Labels ändern. Sonst bricht der Bau ab.
- Beim Start per curl hat die Pipeline-Variable `FRAMEWORK` Vorrang vor dem Label.
- Risiko: Wer Tickets bearbeiten darf, wählt das Framework. BMad erlaubt beliebiges Python (`shell(uv:*)`).

### Schritt 6: IDs sammeln

Ziel: die Werte für `factory/config.json`, siehe Bitbucket-Anleitung, [Schritt 4](bitbucket.md#schritt-4-factoryconfigjson-anpassen). Übernimm keine IDs aus anderen Projekten.

| Config-Schlüssel | Wert | Quelle |
|---|---|---|
| `project_key` | Projektschlüssel | vorne im Ticket-Schlüssel |
| `jira.status.definition`, `ready`, `working`, `waiting`, `build`, `review`, `done`, `stopped`, `clarify` | IDs der neun Status; `clarify` ist „Klärung nötig“ | Aufruf 1 |
| `jira.transition.start`, `spec_done`, `clarify`, `approve`, `build_done` | IDs von Start, Spec fertig, Klärung nötig, Spec freigegeben, Bau fertig. Nur diese fünf braucht die Config. | Aufruf 2, Testticket |
| `jira.approver_account_ids` | Account-IDs der Freigabe-Personen, als Liste | Aufruf 3 |
| `jira.factory_account_id` | Account-ID von `factory-bot` | Aufruf 3 |

Nimm deine eigene E-Mail-Adresse und ein eigenes API-Token: nur `read:jira-work`, wenige Tage, danach widerrufen.

```bash
JIRA=https://api.atlassian.com/ex/jira/<CLOUD-ID>
curl -s -u "<E-MAIL>" "$JIRA/rest/api/3/project/<PROJEKTSCHLÜSSEL>/statuses"  # Aufruf 1: je Status das Feld id
curl -s -u "<E-MAIL>" "$JIRA/rest/api/3/issue/<KEY>/transitions"              # Aufruf 2: Übergänge
curl -s -u "<E-MAIL>" "$JIRA/rest/api/3/issue/<KEY>/comment"                  # Aufruf 3: author.accountId
```

Für Aufruf 3: Jede Freigabe-Person kommentiert das Testticket, du kommentierst mit dem Konto von `factory-bot`. Dann liest du alle `author.accountId` ab. Ungetestet als Alternative: `curl -s -u "<E-MAIL>" "$JIRA/rest/api/3/user/search?query=<E-MAIL-DER-PERSON>"` liefert `accountId`; braucht zusätzlich den Scope `read:jira-user`.

Aufruf 2 zeigt nur Übergänge, die die aufrufende Person machen darf. Lies die Übergangs-IDs darum an einem Testticket ab, in dieser Reihenfolge. Lege das Testticket an, bevor es Flows gibt; sonst startet „Bereit“ einen Spec-Lauf. Ungetestet: dieser Weg.

| # | Wer | Was, in dieser Reihenfolge | Ticket steht in | Abgelesene ID |
|---|---|---|---|---|
| 1 | Admin | erst Ticket anlegen und „Bereit“ setzen, dann Aufruf 2 | Bereit | Start |
| 2 | Admin | erst „Start“ setzen, dann Aufruf 2 | In Arbeit | Spec fertig, Klärung nötig |
| 3 | Admin | erst „Spec fertig“ setzen, dann Aufruf 2 | Wartet | (nichts, weiter zu Zeile 4) |
| 4 | Freigabe-Person | erst Aufruf 2, dann „Spec freigegeben“ setzen | Wartet | Spec freigegeben |
| 5 | Admin | erst Aufruf 2 (Bau fertig ablesen), dann zum Aufräumen „Factory stoppen“ setzen | Bau | Bau fertig |

Bist du selbst Freigabe-Person, macht eine andere Freigabe-Person Zeile 4. Wer „Spec fertig“ gesetzt hat, darf dieses Ticket nicht freigeben.

## Teil B: Flows anlegen

Optional. Ohne Flows startet ihr die Läufe per curl: Bitbucket-Anleitung, [Läufe starten](bitbucket.md#läufe-starten).

Ziel: zwei Flows für das Projekt, die die Pipelines im Repo starten. Alle Gruppen teilen sie; Komponenten braucht es nicht. Vorher nötig: die Pipeline-Datei auf `factory-base` (sonst scheitern beide Flows) und zwei Auslöser-Tokens, eins pro Flow, aus der Bitbucket-Anleitung, [Schritt 8](bitbucket.md#schritt-8-benutzer-tokens-und-umgebungen-anlegen). Jedes: Repository Access Token nur mit „Pipelines: Write“, kurze Laufzeit, im Passwortmanager. Vor Ablauf: neues anlegen und im Flow neu eingeben. Altes Token sofort widerrufen.

| Einstellung | Flow 1 | Flow 2 |
|---|---|---|
| Name | „Factory: Spec starten“ | „Factory: Bau starten“ |
| Auslöser | „Work item transitioned“, Von: Definition und Klärung nötig, Nach: Bereit | „Work item transitioned“, Wartet → Bau |
| Aktion | „Send web request“ | „Send web request“ |
| `pattern` im Body | `factory-spec` | `factory-build` |
| Token | Auslöser-Token 1 | Auslöser-Token 2 |
| Geltungsbereich, Akteur | nur dieses Projekt, „Automation for Jira“ | gleich |
| Auslösen, Bearbeiten | „Only user actions can trigger this flow“, „Private“ | gleich |
| Web Request | auf Antwort warten, bei Fehlerantwort stoppen | gleich |
| Bei Fehlern | E-Mail an die verantwortliche Person | gleich |

Request und Body für Flow 1 (Flow 2: `"pattern": "factory-build"`). Wähle in der Aktion einen eigenen Body und füge den JSON-Text ein. Lege `Authorization` als verborgenen Header an, `Content-Type` als normalen. Jira ersetzt `{{issue.key}}` durch den Ticket-Schlüssel.

```text
POST https://api.bitbucket.org/2.0/repositories/<workspace>/<repo>/pipelines
Authorization: Bearer <Auslöser-Token>
Content-Type: application/json

{"target": {"type": "pipeline_ref_target", "ref_type": "branch", "ref_name": "factory-base",
            "selector": {"type": "custom", "pattern": "factory-spec"}},
 "variables": [{"key": "JIRA_KEY", "value": "{{issue.key}}"}]}
```

1. Lege Flow 1 an. Nur du gibst den Header-Wert ein.
2. Prüfe ihn mit „Validate your web request configuration“ und einem Ticket in „Definition“. Achtung: Das startet einen echten Lauf. Der Guard stoppt ihn sofort und kommentiert `FACTORY-STOP` im Ticket.
3. Lege Flow 2 neu an. Flow 1 nicht kopieren (eine Kopie scheiterte). Token-Wert neu eingeben.
4. Prüfe Flow 2 genauso.
5. Schalte beide Flows an. Lies das Audit-Log beider Flows, auch nach jeder späteren Änderung: Flows scheitern still.
6. Nach jeder Änderung am Flow, etwa an Body oder Geltungsbereich, kann der verborgene Header fehlen. Dann: Header-Zeile löschen, neu eingeben und mit „Validate“ prüfen.

**Prüfen:** „Validate“ meldet HTTP 201 Created, in Bitbucket erscheint ein Lauf. Bei HTTP 404 zuerst Token im Header prüfen, dann URL, Workspace und Repository. Bitbucket meldet ein ungültiges Token bei privaten Repositorys mit 404, nicht 401.

## Teil C: Probelauf

Ohne Flows: nach „Bereit“ `factory-spec` starten, nach „Spec freigegeben“ `factory-build`, jeweils per curl ([Läufe starten](bitbucket.md#läufe-starten)). Mit Flows starten die Läufe von selbst. Probe 3 und 4 nutzen das Ticket aus Probe 2.

1. **Ticket ohne `sdd-`-Label auf „Bereit“.** Erwartet: Guard stoppt den Lauf, Kommentar `FACTORY-STOP v1 …` mit „no framework chosen“.
2. **Ticket mit genau einem `sdd-`-Label auf „Bereit“.** Erwartet: Spec-Kommentar von `factory-bot` mit „Readiness check: passed“, Status „Wartet“.
   - **Vages Ticket mit Label, nur ein Titel wie „Suche verbessern“, auf „Bereit“.** Erwartet: Kommentar `FACTORY-NOT-READY v1 …` mit Gründen und Fragen, Status „Klärung nötig“, kein Branch. Beschreibung ergänzen, zurück auf „Bereit“: ein neuer Spec-Lauf startet. Siehe [Ticket-Bereitschaft](../bedienung/ticket-bereitschaft.md).
3. **`factory-bot` versucht „Spec freigegeben“.** Mit Flows: Schalte vor der Probe Flow 2 aus. Dann mit dem Token von `factory-bot` (`$JIRA` wie in Schritt 1):

   ```bash
   curl -s -w '\nHTTP %{http_code}\n' -u "<FACTORY-BOT-E-MAIL>" -X POST -H "Content-Type: application/json" \
     -d '{"transition":{"id":"<ID von Spec freigegeben>"}}' "$JIRA/rest/api/3/issue/<KEY>/transitions"
   ```

   Erwartet: HTTP 400 „Can't move“. Erst dann Flow 2 wieder an. Klappt der Aufruf: kein Bau-Lauf, Flow 2 bleibt aus. Ticket auf „Factory stoppen“ setzen, zurück zu Schritt 4.
4. **Bau ohne Freigabe.** Ticket in „Wartet“, `factory-build` per curl starten. Erwartet: Guard stoppt mit `build runs start only from status Bau`. Mit Flows zusätzlich: Kommentar „Freigegeben“ ohne Übergang startet nichts.
5. **Freigabe-Person setzt „Spec freigegeben“, Bau startet.** Erwartet: `factory-bot` öffnet einen Pull Request, kommentiert den Link, setzt „Review“. Freigabe-Person prüft und führt zusammen (Gate 2). Dann setzt eine Person „Erledigt“.
6. **„Factory stoppen“ während eines Laufs.** Erwartet: Der Lauf bricht vor jedem Schreiben ab. Er legt keinen Kommentar und keinen Branch an. „Fortsetzen“ (nur Freigabe-Personen) führt zurück nach „Definition“.

## Wenn etwas nicht klappt

- **Flows scheitern:** Läufe per curl starten, siehe Bitbucket-Anleitung, [Läufe starten](bitbucket.md#läufe-starten). Jede startende Person braucht ein Start-Token von dir.
- **Ohne Teil A läuft nichts,** auch nicht per curl: Der Guard liest Status und Freigabe aus Jira.
- **Wenn nichts klappt:** Lab von atra, Jira-Projekt `FLAB` und Repository `factory-lab/factory-lab`. Siehe Bitbucket-Anleitung, [„Wenn die Einrichtung nicht klappt“](bitbucket.md#wenn-die-einrichtung-nicht-klappt). Alles im Lab ist öffentlich: keine internen Anforderungen, Namen oder Daten in Tickets.
