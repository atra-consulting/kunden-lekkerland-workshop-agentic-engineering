# Die Agentic Factory in einer Bitbucket-Pipeline laufen lassen, gestartet von Jira Automation

**Ein Weg von mehreren.** Diese Anleitung zeigt einen Weg, die Factory in Bitbucket zu betreiben. Es ist nicht der einzige. Ihr könnt sie auch anders aufsetzen, etwa mit einem anderen CI-System, einem anderen Auslöser oder einer anderen Aufteilung der Secrets. Passt die Schritte an euer Projekt an.

**Stand.** Die `agentic-*`-Pipelines liefen bisher nie in Bitbucket. Die Vorlage ist [`factory-base` aus dem Lab in `factory-lab/factory-lab`](https://bitbucket.org/factory-lab/factory-lab/src/factory-base/factory/), mit dem [Jira-Space `FLAB`](https://betterprojectsfaster.atlassian.net/jira/software/c/projects/FLAB/boards/3).

Kennzeichen: (S-nnnn) ist ein Beleg des Herstellers. (intern) ist der Code der Factory oder die Workshop-Doku. (Lab) ist, was das Lab getan oder gesehen hat. (ungetestet) ist eine Wahl, die niemand ausprobiert hat. Zitate aus den Belegen bleiben englisch.

## Voraussetzungen

1. **Ein Bitbucket-Cloud-Repository mit eingeschalteten Pipelines.** Vom Repository-Admin. Kein dokumentierter Weg.
2. **Ein Runner.** Die Runner von Atlassian, oder ein selbst gehosteter Runner mit seinen Labels, vom Repository-Admin.
3. **Ein Image und das Dockerfile, das ihr dafür schreibt.** Es braucht `python3` ab 3.9, `git` und Copilot CLI, getestet mit 1.0.115 (intern).
4. **Eine Registry,** aus der der Runner ohne Zugangsdaten zieht, oder mit Zugangsdaten nur zum Lesen (ungetestet).
5. **Ein technischer Jira-User,** `<bot-email>`, vom Jira-Admin. Rolle: lesen und „Add comments“, nicht bearbeiten (Lab). Einen Kommentar anzulegen braucht „Browse projects and Add comments project permission“ (S-7123).
6. **Ein Jira-API-Token** für diesen User, mit den Scopes `read:jira-work` und `write:jira-work` (Lab). „Once you create an API token, you can't modify its scopes.“ (S-7534, Tokens für Service-Accounts). Kein dokumentierter Weg für das Token eines normalen Users.
7. **Die Cloud-ID** eurer Jira-Site.
8. **Ein feingranulares Copilot-PAT** vom Copilot-Nutzer. 
9. **Bitbucket-Repository-Access-Tokens** nur mit „Pipelines: Write“. Ihr braucht ein Auslöse-Token für die Regel und ein Start-Token pro Starter.
10. **Drei Deployment-Umgebungen,** `agentic-jira`, `agentic-agent` und `agentic-post`, mit ihren Deployment-Rechten.
11. **Ein Opt-in-Label,** `<opt-in-label>`, etwa `agentic`. Der Jira-Admin wählt es.

## Einrichtung

`assess` prüft, ob ein Ticket reif für eine Spec ist. Es kommentiert nur, wenn das Ticket nicht reif ist. `clarify` postet pro Lauf eine Runde mit Fragen und Annahmen. Menschen antworten mit einem Kommentar, der mit `[Mensch]` beginnt. Die Kommentare der Factory beginnen mit `[KI]`. Die Texte sind deutsch (intern).

### 1. Das Repository prüfen

- Gibt es schon `bitbucket-pipelines.yml`, führt ihr die Datei in Schritt 7 zusammen.
- Schaut unter „Workspace Settings → Pipelines → Workspace variables“ und „Repository Settings → Pipelines → Repository variables“ nach. Diese Variablen erreichen jeden Step, auch den Agenten (intern). Verschiebt, was ein bestehender Build braucht, in ein Deployment, das der Agent nicht nutzt.
- Listet die Custom-Pipelines auf allen Branches und Tags auf. Das Auslöse-Token kann jede davon starten (Lab). Schützt die, die Deployment-Secrets nutzen, mit Deployment-Rechten, oder verschiebt sie (ungetestet).

```bash
git fetch origin --tags
for b in $(git for-each-ref --format='%(refname:short)' refs/remotes/origin refs/tags); do
  echo "== $b"; git show "$b:bitbucket-pipelines.yml" 2>/dev/null | grep -nE 'custom:|deployment:'
done
```

### 2. Den Start-Branch schützen

Wählt `<start-branch>`. Erlaubt keinen direkten Push und Merges nur per Pull Request durch benannte Personen. Verbietet Löschen und das Umschreiben der Historie (Lab). Prüft, dass ein direkter Push scheitert. Tut das, bevor ihr ein Secret speichert.

Der Branch-Schutz schützt die Secrets nicht. Jeder mit Schreibrechten kann die Deployments von einem anderen Branch aus nutzen (ungetestet). Beschränkt alle drei Deployments mit Deployment-Rechten auf `<start-branch>` (ungetestet). Die Belege bestätigen nicht, dass das wirkt.

### 3. `factory/` kopieren

Das Skript läuft nur als [`factory/agentic-factory.py`](https://github.com/atra-consulting/kunden-lekkerland-workshop-agentic-engineering/blob/main/02-agent-factory/einrichtung/factory/agentic-factory.py) im obersten Ordner des Git-Klons. In einer Pipeline verweigert es `build` und `init`. Öffnet jetzt einen Pull Request und merged ihn in Schritt 7. Aus dem obersten Ordner eures Repositorys:

```bash
F=<workshop>/02-agent-factory/einrichtung/factory
mkdir -p factory
cp -R "$F/agentic_factory" factory/
cp "$F"/{agentic-factory.py,config.json,readiness.md,.gitignore} factory/
if [ -e bitbucket-pipelines.yml ]; then
  cp "$F/pipelines.example.yml" pipelines.agentic.yml   # in Schritt 7 von Hand zusammenführen, dann löschen
else
  cp "$F/pipelines.example.yml" bitbucket-pipelines.yml
fi
```

Passt `config.json` und `readiness.md` an euer Projekt an. Dazu führt ihr `init` lokal aus (intern).

### 4. Den Runner festlegen und das Image bauen

- **Runner von Atlassian:** Löscht in Schritt 7 jede Zeile `runs-on:` und baut für amd64 (Lab).
- **Ein selbst gehosteter Runner:** Nehmt seine Labels. „A runs-on parameter must contain a self.hosted label.“ (S-7520). Die Belege bestätigen `linux.arm64` als Label nicht.
- Baut das Image, pusht es nach `<registry>` und pinnt es als `<registry>/<image>@sha256:<digest>` (Lab).
- Prüft, dass `copilot --version` im Image läuft.

### 5. Die Tokens anlegen

- Legt das Jira-Token und das Copilot-Token an. Speichert sie nur in Deployments (Schritt 6).
- Legt das Auslöse-Token an. Speichert es nur als verborgenen Header der Regel (Schritt 9).
- Gebt Start-Tokens nur Startern, die schon Schreibrechte haben (ungetestet). Ein Start-Request kann Deployment-Variablen überschreiben: „Pipeline > Deployment > Repository > Workspace“. Die Belege sagen nicht, ob das auch für nicht deklarierte Namen wie `JIRA_BASE_URL` gilt.
- Startet Läufe nie mit einem persönlichen Token oder einem Admin-Token (Lab).
- Übergebt Tokens über einen Passwort-Manager, nie über ein Ticket oder einen Chat.

### 6. Die Deployments und ihre Variablen anlegen

Legt die Umgebungen unter „Repository Settings → Pipelines → Deployments“ an. Nehmt dafür nie Repository- oder Workspace-Variablen (intern).

| Umgebung | Secured | Nicht secured |
|---|---|---|
| `agentic-jira` | `JIRA_API_TOKEN` | `JIRA_BASE_URL`, `JIRA_EMAIL` |
| `agentic-agent` | `COPILOT_GITHUB_TOKEN` | – |
| `agentic-post` | `JIRA_API_TOKEN` | `JIRA_BASE_URL`, `JIRA_EMAIL` |

`JIRA_BASE_URL` ist `https://api.atlassian.com/ex/jira/<cloud-id>` (Lab). `JIRA_EMAIL` ist `<bot-email>`. Das Skript stoppt, wenn `fetch` oder `post` das Copilot-Token sieht oder `agent` das Jira-Token (intern).

### 7. `bitbucket-pipelines.yml` fertigstellen und mergen

Ergänzt `agentic-assess-dryrun` in der Datei (ungetestet). Das ist `agentic-assess` mit `--no-post` bei fetch und post. `agentic-assess` aus dem Beispiel bleibt, wie es ist, bis auf die Änderungen an Image und `runs-on`. Sein Agent-Step behält `max-time: 25`, weil assess nur einen Aufruf macht (intern).

```yaml
image:
  name: <registry>/<image>@sha256:<digest>
options:
  max-time: 45                                # Beispiel: 30 (ungetestet)
pipelines:
  custom:
    agentic-clarify:
      - variables:
          - name: JIRA_KEY
          - name: APPLY                       # nur von Hand setzen, nie in der Regel
      - step:
          name: fetch (Jira token only)
          runs-on: [self.hosted, linux.arm64] # eure Labels, oder löschen für Runner von Atlassian
          deployment: agentic-jira
          concurrency-group: agentic
          max-time: 5
          auth: { system: { scopes: [read:git:bitbucket] } }
          script:
            - python3 -I factory/agentic-factory.py clarify --key "$JIRA_KEY" --step fetch
          artifacts: [agentic-io/in/**]
      - step:
          name: agent (Copilot token only)
          runs-on: [self.hosted, linux.arm64]
          deployment: agentic-agent
          concurrency-group: agentic
          max-time: 45                        # Beispiel: 25 (ungetestet)
          auth: { system: { scopes: [read:git:bitbucket] } }
          script:
            - python3 -I factory/agentic-factory.py clarify --key "$JIRA_KEY" --step agent
          artifacts: [agentic-io/out/**]
      - step:
          name: post (Jira token only)
          runs-on: [self.hosted, linux.arm64]
          deployment: agentic-post
          concurrency-group: agentic
          max-time: 5
          auth: { system: { scopes: [read:git:bitbucket] } }
          script:
            - python3 -I factory/agentic-factory.py clarify --key "$JIRA_KEY" --step post
    agentic-assess-dryrun:                    # ungetestet; löschen, wenn Lauf 1 klappt
      - variables:
          - name: JIRA_KEY
      - step:
          name: fetch (Jira token only)
          runs-on: [self.hosted, linux.arm64]
          deployment: agentic-jira
          concurrency-group: agentic
          max-time: 5
          auth: { system: { scopes: [read:git:bitbucket] } }
          script:
            - python3 -I factory/agentic-factory.py assess --key "$JIRA_KEY" --step fetch --no-post
          artifacts: [agentic-io/in/**]
      - step:
          name: agent (Copilot token only)
          runs-on: [self.hosted, linux.arm64]
          deployment: agentic-agent
          concurrency-group: agentic
          max-time: 25
          auth: { system: { scopes: [read:git:bitbucket] } }
          script:
            - python3 -I factory/agentic-factory.py assess --key "$JIRA_KEY" --step agent
          artifacts: [agentic-io/out/**]
      - step:
          name: post (Jira token only)
          runs-on: [self.hosted, linux.arm64]
          deployment: agentic-post
          concurrency-group: agentic
          max-time: 5
          auth: { system: { scopes: [read:git:bitbucket] } }
          script:
            - python3 -I factory/agentic-factory.py assess --key "$JIRA_KEY" --step post --no-post
          artifacts: [agentic-io/out/**]      # behält comment-1.txt
```

**`max-time`.** Jeder Copilot-Aufruf darf 20 Minuten laufen (`agent_timeout_s` 1200, intern). Ein `clarify`-Lauf kann zwei Aufrufe machen. Deshalb bekommt der Agent-Step 45: zwei Aufrufe plus 5 Minuten Puffer (ungetestet). Erlaubte Werte: „A positive integer between 1 and 720“ (S-7117).

**Zusammenführen.** Gab es die Datei schon, folgt dieser Checkliste (ungetestet):

- Kopiert `image` und `options` nicht.
- Prüft, dass ein bestehendes globales `max-time` mindestens 45 ist.
- Ergänzt in jedem Agentic-Step `image: name: <registry>/<image>@sha256:<digest>`. Die Belege bestätigen ein `image` auf Step-Ebene nicht.
- Behaltet das eigene `max-time` jedes Steps.

Merged erst, wenn Schritt 6 fertig ist, und prüft gegen andere Änderungen an der Datei.

### 8. Von Hand testen

Nehmt ein Testticket `PROJ-123`, das nicht reif ist und keine personenbezogenen Daten oder Kundendaten enthält. Es braucht kein Opt-in-Label. Startet Läufe mit „Run pipeline“ in Bitbucket (intern) oder mit einem Start-Token über die API (Lab):

```bash
printf 'Token: '; read -rs TOKEN; echo
printf 'header = "Authorization: Bearer %s"\n' "$TOKEN" | curl -sS -w '\nHTTP %{http_code}\n' -K - -X POST \
  -H "Content-Type: application/json" \
  "https://api.bitbucket.org/2.0/repositories/<workspace>/<repo>/pipelines" \
  -d '{"target":{"type":"pipeline_ref_target","ref_type":"branch","ref_name":"<start-branch>","selector":{"type":"custom","pattern":"agentic-assess-dryrun"}},"variables":[{"key":"JIRA_KEY","value":"PROJ-123"}]}'
unset TOKEN
```

Erwartet `HTTP 201`. S-7529 nennt 201, 400 und 404 für diesen Aufruf. Lauft in dieser Reihenfolge (ungetestet):

| # | Pipeline | Erwartete Zeile oder Ergebnis (intern) |
|---|---|---|
| 1 | `agentic-assess-dryrun` | post: `comment not posted (--no-post)`. Der Text liegt in den Artefakten des Laufs |
| 2 | `agentic-assess` | Ein Kommentar `[KI] agentic-factory assess` im Ticket |
| 3 | `agentic-clarify` | `[KI] agentic-factory klärung runde=1 key=PROJ-123` |
| 4 | Optional: `agentic-clarify` mit `{"key":"APPLY","value":"1"}`, nach einem Vorschlag | `PROJ-123: description set`. Wahrscheinlich stoppt es, weil die Lab-Rolle nicht bearbeiten darf (ungetestet) |

Eine grüne Pipeline heißt nicht „reif“. Die Steps enden mit 0, außer bei einem Fehler. Lest die Agent-Zeile: `exit code 0` heißt reif, 4 nicht reif, 5 Fragen oder warten auf Antworten (intern).

### 9. Die Automation-Regel anlegen

Die Regel startet die nächste `clarify`-Runde, wenn jemand mit `[Mensch]` antwortet. Runde 1 startet ihr von Hand (Schritt 8). Der Starter setzt vorher `<opt-in-label>`.

| Einstellung | Wert |
|---|---|
| Trigger | Comment added. „Editing a comment will not trigger this flow.“ (S-7533) |
| Aktion | „Send web request“, `POST https://api.bitbucket.org/2.0/repositories/<workspace>/<repo>/pipelines` (Lab) |
| Header | Verborgen `Authorization: Bearer <trigger-token>`, normal `Content-Type: application/json` (Lab) |
| Body | `{"target": {"type": "pipeline_ref_target", "ref_type": "branch", "ref_name": "<start-branch>", "selector": {"type": "custom", "pattern": "agentic-clarify"}}, "variables": [{"key": "JIRA_KEY", "value": "{{issue.key}}"}]}`. Nie `APPLY` |
| Geltungsbereich und Akteur | Nur dieses Projekt, „Automation for Jira“ (Lab) |
| Auslösen und Bearbeiten | „Only user actions can trigger this flow“, „Private“ (Lab) |
| Antwort | Auf die Antwort warten, bei einer Fehlerantwort stoppen. Bei Fehlern den Ersthelfer per E-Mail benachrichtigen (Lab) |

Bedingungen (ungetestet; kein Beleg nennt die Syntax):

1. Der Kommentar beginnt mit `[Mensch]`. Die Skizze: `{{comment.body.trim().startsWith("[Mensch]")}}` ist gleich `true` (intern).
2. Das Ticket hat `<opt-in-label>`.
3. Der Autor des Kommentars ist in einer benannten Gruppe oder Projektrolle.
4. Der Autor des Kommentars ist nicht `<bot-email>`.

Behandelt jeden, der die Regel bearbeiten darf, so, als hätte er das Auslöse-Token (ungetestet).

Prüft mit „Validate your web request configuration“ an einem Ticket, das eine `[KI]`-Runde und keine neuere `[Mensch]`-Antwort hat. Das startet einen echten Lauf (Lab). Er endet mit `waiting for answers` und ohne Copilot-Aufruf (intern). Legt jede Regel neu an, ohne zu kopieren. Gebt nach jeder Änderung den verborgenen Header neu ein (Lab).

**Schleifentest.** Beantwortet die Runde einmal mit `[Mensch] …`. Prüft, dass genau ein Lauf startet. Starten mehr, alarmiert der Ersthelfer den Jira-Admin, und der schaltet die Regel ab. Eine Schleife, wiederholte `[Mensch]`-Kommentare oder ungewollte Runden starten ungewollte Läufe, posten ungewollte Kommentare und schicken Tickettext an Copilot. Die Bedingungen 2 und 3 begrenzen, wer sie starten kann.

### 10. Mit einem Pilotticket live gehen

1. Schaltet die Regel für ein Pilotticket mit `<opt-in-label>` ein.
2. Prüft, dass die Läufe 1 bis 3 und der Schleifentest geklappt haben.
3. Lest nach jeder Änderung das Audit-Log der Regel. Regeln scheitern still (Lab).
4. Löscht `agentic-assess-dryrun` per Pull Request.

**Tokens tauschen und zurückrollen** (ungetestet):

- **Tauscht** das Jira-, Copilot- und Auslöse-Token:
  1. Pausiert die Regel und wartet, bis kein Lauf mehr läuft oder in der Warteschlange steht.
  2. Tragt das neue Token ein und macht Lauf 2 aus Schritt 8 als Smoke-Test.
  3. Widerruft das alte Token. Dann setzt die Regel fort.
- **Rollt zurück:**
  1. Der Jira-Admin schaltet die Regel ab.
  2. Der Repository-Admin widerruft das Auslöse-Token und die Start-Tokens und löscht die Deployment-Variablen.
  3. Der Token-Koordinator lässt das Jira- und das Copilot-Token widerrufen.

## Wenn etwas scheitert

| Meldung oder Symptom | Lösung |
|---|---|
| `… not in a folder named factory/` oder `… is not the top folder of a git repository` | Legt `factory/` in den obersten Ordner des Klons (Schritt 3, intern) |
| `--step agent must not see JIRA_API_TOKEN` oder `--step fetch must not see COPILOT_GITHUB_TOKEN` | Haltet jedes Token nur in seinem eigenen Deployment (Schritt 6, intern) |
| `the api route needs JIRA_BASE_URL and JIRA_API_TOKEN` | Ergänzt die Variablen in `agentic-jira` und `agentic-post` (intern) |
| `Jira … HTTP 401` | Prüft `JIRA_EMAIL` und `JIRA_API_TOKEN` (intern) |
| `Jira … HTTP 404` | Prüft `JIRA_BASE_URL`: Nehmt die Cloud-ID, nicht die Organization ID (S-7534) |
| `copilot exited with timeout`, oder der Agent-Step hat `max-time` erreicht | Erhöht `agent_timeout_s` in `config.json` und `max-time` gleich mit (intern) |
| Step scheitert beim Start: kein Runner | Korrigiert `runs-on`. „If you don't have any online runners in your repository that match all your labels, the step will fail.“ (S-7520) |
| „The system scopes provided contains unsupported scopes.“ (S-7521) | Prüft die Schreibweise der Scopes. Nur für einen ersten Test: Löscht den Block `auth`. Bis 30.04.2027 bekommt der Step dann weitere Scopes (S-7118) |
| Copilot startet nicht | Nehmt ein feingranulares PAT, kein klassisches `ghp_`-Token (S-7539, S-7540) |
| Der Start-Request liefert 404, oder die Regel lief, aber keine Pipeline startete | Prüft das Token, dann die URL. Gebt den verborgenen Header neu ein (Lab) |

## Offene Lücken

- Ob die Secrets pro Deployment getrennt bleiben, ist nicht geprüft (Schritt 6).
- Ein Forenbeitrag sagt, Starts mit eigenen Variablen lieferten HTTP 400. Euer erster Start über die API zeigt es.
- Die Belege sagen nicht, ob ein Start-Request Deployment-Variablen überschreiben kann (Schritt 5).
- Es gibt kein Dockerfile. Die Belege decken weder die Installation von Copilot CLI noch den Zugang zu einer privaten Registry ab.
- Das Beispiel führt das Skript aus dem Arbeitsverzeichnis aus. Liegt es im Image, scheitert die Prüfung des Ablageorts (intern).
- Die Belege nennen nicht den Scope, den `GET /myself` braucht. `APPLY=1` nutzt ihn und braucht außerdem Bearbeitungsrechte.
- Kein Cloud-Beleg zeigt POST, einen eigenen Body, verborgene Header oder die Syntax der Bedingungen für „Send web request“.
- Die Belege sagen nicht, ob die eigenen Kommentare der Factory den Trigger auslösen.
- Die Belege bestätigen weder `read:git:bitbucket` noch die Verschachtelung von `auth` im YAML noch das Label `linux.arm64`.
