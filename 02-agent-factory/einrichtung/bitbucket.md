# Bitbucket für die Factory einrichten

Diese Anleitung richtet euer Repo für die Factory ein: Branch `factory-base` mit den Custom-Pipelines `factory-spec` und `factory-build`. Läufe startet ihr per curl. Alles hier erledigt ein Admin von Lekkerland zusammen mit atra, derselbe wie in der Jira-Anleitung.

Reihenfolge: Schritte 1 bis 3 hier, dann [Jira, Teil A](jira.md#teil-a-workflow-einrichten), dann Schritte 4 bis 10, dann [Jira, Teil C](jira.md#teil-c-probelauf). Jira-Automation ([Teil B](jira.md#teil-b-flows-anlegen)) ist optional. Gesamtbild: [Überblick](../ueberblick.md).

## Vor dem Start

- [ ] Vor Schritt 4: [Jira, Teil A](jira.md#teil-a-workflow-einrichten) erledigt. Daraus brauchst du: Projektschlüssel, acht Status-IDs, fünf Übergangs-IDs, Account-IDs der Freigabe-Personen und von `factory-bot`.
- [ ] Bitbucket Cloud, Pipelines an, ein Repo für alle Gruppen. Alle Gruppen dürfen gleichzeitig starten. Die Schritte mit Secrets laufen nacheinander: Ein zweiter Lauf wartet („Queued“) und startet von selbst.
- [ ] Schritte 1 bis 10 einmal für das Repo. Ein Image, eine `config.json` mit Repo und Reviewern.
- [ ] Du hast Admin-Rechte für den Bitbucket-Workspace und das Repo. Teilnehmende bekommen kein Admin-Recht: Repository-Admins können Branch-Regeln aufheben. Prüfe, wer heute schon Admin im Repo ist.
- [ ] Konto `factory-bot`: technischer Benutzer, einer für alle Gruppen, angelegt in [Jira, Teil A, Schritt 1](jira.md#schritt-1-factory-konto-anlegen-und-berechtigen). In Jira nur die Projektrolle „Factory“, in Bitbucket „Write“ auf das Repo, keine Standardgruppe. Offen, wie es ohne Standardgruppe Zugriff bekommt: siehe [Jira, Vor dem Start](jira.md#vor-dem-start).
- [ ] GitHub-Benutzer mit Copilot-Platz und Budget. Token: Fine-grained PAT eines persönlichen Kontos, nur „Copilot Requests“, gültig bis 4. Dezember, sofort widerrufbar. Wer den Copilot-Platz hat, legt das Token an und gibt es dir über den Passwortmanager. Vor Ablauf: neues Token, neu eingeben, altes Token sofort widerrufen. Kein Classic PAT. Copilot über eine Organisation: dort die Richtlinie für Copilot CLI aktivieren.
- [ ] Docker mit buildx, auf einem Rechner mit Zugang zu `bitbucket.org`. Dazu eine Registry, aus der die Pipeline das Image zieht.
- **Offen:** Bitbucket-Plan, eigener Runner oder Cloud-Runner, und ob „Deployment permissions“ genutzt werden, mit welcher Grenze. „Deployment permissions“ und Merge-Checks nennt Atlassian für Premium. Blockiert Schritt 1, 5, 6, 8 und 9.
- **Offen:** Registry öffentlich oder privat. Ein öffentliches Image legt `factory/config.json` offen: Account-IDs, Projektschlüssel, Workspace, Reviewer-UUIDs, geschützte Pfade. Privat braucht Zugangsdaten in der Pipeline, ungetestet. Blockiert Schritt 5.
- **Offen:** Quelle der Dateien aller drei Frameworks, oder getestete Befehle, die alle drei in ein Repository installieren. Blockiert Schritt 3.
- **Offen:** Spryker-Werte (Testbefehl, Installationsbefehl, auszulassende Ordner, geschützte Pfade) und wo du die Bitbucket-Account-UUIDs der Reviewer abliest. Blockiert Schritt 4 und 5.
- **Offen:** Klickpfade für `factory-bot` mit „Write“ auf das Repo und für Repository Access Tokens. Dazu: wo du die Cloud-ID der Jira-Site abliest, und ob Leserecht in einem privaten Repo für Pull Requests und Läufe reicht. Blockiert Schritt 8. Ohne Cloud-ID schlägt jeder Lauf fehl. Ungetestet: `https://<site>.atlassian.net/_edge/tenant_info` liefert `cloudId`.
- **Offen:** Umgang mit bestehenden Workspace- oder Repository-Variablen, und Syntax, um `factory/*` in bestehenden Pipelines auszuschließen. Im echten Repo wahrscheinlich nötig. Blockiert Schritt 9.

Offene Punkte klärst du mit atra.

## Schritt 1: Start-Branch anlegen und schützen

Ziel: `factory-base`, abgezweigt vom Entwicklungs-Branch oder von `workshop-sdd-local`. Dort starten beide Pipelines, dorthin gehen die Pull Requests der Factory. Ein Start-Branch für alle Gruppen: Die Factory läuft nur auf `factory-base`, nie auf den Gruppen-Branches `workshop-<framework>-local`. Das Framework wählt das Label am Ticket.
```bash
git switch <Entwicklungs-Branch>
git pull
git switch -c factory-base
git push -u origin factory-base
```
Schütze `factory-base` sofort: Direkt pushen darf niemand. Zusammenführen nur per Pull Request, nur benannte Personen, nie `factory-bot`. Löschen und Historie umschreiben verboten. Kein Schreibrecht für Pipelines.
- Nicht `factory` nennen: Git kann ihn nicht neben `factory/<KEY>` speichern.
- Ab jetzt gehen auch deine Änderungen nur per Pull Request nach `factory-base`. Schritte 2 bis 6 auf dem Hilfs-Branch `factory-setup`.
- Ergebnisse in andere Branches übernehmen: entscheiden die Teilnehmenden, nicht Teil der Einrichtung.
- Die Factory legt im Repo Branches `factory/<KEY>` und Pull Requests an. Nach dem Workshop aufräumen: `factory/*`, offene Pull Requests, Start-Tokens.

**Prüfen:** Direkter Push auf `factory-base` scheitert, auch mit Admin-Token.

## Schritt 2: Factory-Dateien holen

Ziel: Skripte, Konfiguration, Image-Dateien und Regel-Vorlagen aus dem Beispiel `factory-lab`, fester Commit. Im Ordner deines Repos. `../factory-lab` darf noch nicht existieren.
```bash
git switch -c factory-setup factory-base
H=feb39f5ec3bedfad04c028e52a02864c5545eb69
git clone --no-checkout https://bitbucket.org/factory-lab/factory-lab.git ../factory-lab \
  && git -C ../factory-lab checkout --detach "$H" \
  && test "$(git -C ../factory-lab rev-parse HEAD)" = "$H" \
  && cp -R ../factory-lab/factory ./factory \
  && cp ../factory-lab/AGENTS.md ./AGENTS.md \
  && mkdir -p .github \
  && cp ../factory-lab/.github/copilot-instructions.md .github/ \
  && echo "OK: $H"
```
Kopiere nichts anderes, vor allem nicht die `bitbucket-pipelines.yml` des Beispiels. Gab es schon eine `AGENTS.md`, überschreibt `cp` sie. Beide Dateien von Hand zusammenführen.

**Prüfen:** Letzte Zeile zeigt `OK:` und den Hash. Sonst lief `cp` nicht.

## Schritt 3: Framework-Dateien und Regeln einfügen

Ziel: Dateien aller drei Frameworks auf `factory-base`, denn Tickets wählen das Framework per Label. Erledige das vor Schritt 4.
1. Lege die Dateien aller drei Frameworks in das Repo. OpenSpec: `.agents/skills/openspec-*`, `openspec/config.yaml`. Spec Kit: `.github/skills/speckit-*`, `.specify/`. BMad: `.agents/skills/bmad-*`, `.github/agents/`, `_bmad/`. Befehle je Framework: Leitfäden von Tag 1 zu [Spec Kit](../../01-erstworkshop/tag-1/anleitung-spec-kit.md), [OpenSpec](../../01-erstworkshop/tag-1/anleitung-openspec.md), [BMad](../../01-erstworkshop/tag-1/anleitung-bmad.md). Ungetestet: alle drei nacheinander in ein Repository.
2. Prüfe danach `AGENTS.md`. Offen, ob Spec Kit und BMad beim `init` beide hineinschreiben.
3. Passe `AGENTS.md` und `.github/copilot-instructions.md` an Lekkerland an. Die Vorlagen nennen Symfony, PHP 8.4, `./bin/phpunit` und die Ordner von `symfony/demo`.

## Schritt 4: factory/config.json anpassen

Ziel: alle Werte des Repos in `config.json`, vor Schritt 5. Das Image baut die Datei nach `/opt/factory` ein. Jede spätere Änderung: neues Image, neuer Digest.

| Schlüssel | Wert |
|---|---|
| `project_key` | Projektschlüssel |
| `jira.approver_account_ids`, `jira.factory_account_id` | Account-IDs der Freigabe-Personen (als Liste) und von `factory-bot` |
| `jira.status.*` | IDs der acht Status: `definition`, `ready`, `working`, `waiting`, `build`, `review`, `done`, `stopped` |
| `jira.transition.*` | IDs der Übergänge: `start` („Start“), `spec_done` („Spec fertig“), `back` („Zurück“), `approve` („Spec freigegeben“), `build_done` („Bau fertig“) |
| `bitbucket.workspace`, `bitbucket.repo` | Workspace und Name des Repos, aus seiner URL |
| `bitbucket.main` | `factory-base` |
| `bitbucket.reviewers` | Bitbucket-Account-UUIDs der Reviewer, in geschweiften Klammern: `["{<UUID>}"]` |
| `test_command`, `composer_install` | Test- und Installationsbefehl als Listen, im Beispiel `["./bin/phpunit"]` und `["composer", "install", "--no-interaction", "--no-progress"]` |
| `workspace_exclude` | Ordner, die der Agent-Schritt beim Patch auslässt, im Beispiel `vendor`, `var`, `node_modules`, `.phpunit.cache`, `public/bundles`, `assets/vendor` |
| `protected_paths` | reguläre Ausdrücke für Pfade, die kein Agent-Lauf ändern darf |
| `enabled_frameworks`, `label_frameworks` | `openspec`, `speckit`, `bmad` |
| `default_framework` | `null`. Jedes Ticket braucht dann ein `sdd-<name>`-Label oder `FRAMEWORK`, sonst lehnt der Guard ab. |

- **`protected_paths`:** Das Beispiel schützt die Pipeline-Datei, `factory/`, `AGENTS.md`, `.github/`, die Framework-Ordner aus Schritt 3, Dockerfiles, `composer.json`, `composer.lock`, PHPUnit-Konfiguration, `bin/`, `config/packages/`. Passe die Muster an das Spryker-Repo an.
- **Anderer Testbefehl:** Auch `./bin/phpunit` ändern: in der Bau-Regel von `factory/agent.py`, in den `build_tools` jedes Frameworks in `config.json` und im Prompt für `/speckit-plan`. Ungetestet.

**Prüfen:** Kein Wert aus dem Beispiel bleibt: kein `FLAB`, kein `factory-lab`, keine Account-IDs des Beispiels.

## Schritt 5: Image bauen

Ziel: Image mit Copilot CLI, den Frameworks und deiner `config.json`. Im Ordner deines Repos:
```bash
docker login <registry>
docker buildx create --use --name factory
docker buildx build --platform linux/arm64,linux/amd64 \
  -f factory/image/Dockerfile -t <registry>/<repo>:<tag> --push factory/
```
- Ungetestet: `docker login` und `buildx create`. Der Standard-Builder von Docker Desktop baut nicht zwei Plattformen.
- Beide Plattformen: arm64 für eigene arm64-Runner, amd64 (x86_64) für Atlassians Cloud-Runner.
- Notiere den Digest für `<registry>/<repo>@sha256:<digest>` in Schritt 6. Ungetestet: `docker buildx imagetools inspect <registry>/<repo>:<tag>` zeigt ihn.
- Keine Secrets in Build oder Image. Push-Token der Registry nur auf deinem Rechner.
- Feste Versionen im Dockerfile: Copilot CLI 1.0.112, OpenSpec 2.0.0, Spec Kit v1.4.0, BMad 6.12.4, PHP 8.4, Node.js 22 (`node:22.23.2-bookworm-slim` per Digest), Composer 2.11.2, uv 0.9.3, Python 3.12. PHP-Erweiterungen: `cli`, `xml`, `mbstring`, `intl`, `sqlite3`, `zip`, `curl`. Ungetestet, ob Spryker andere braucht.

**Prüfen:** Build ohne Fehler. Der letzte `RUN`-Befehl ruft `copilot --version` und `openspec --version` auf.

## Schritt 6: Pipeline-Datei anlegen

Ziel: Pipeline-Datei nur auf `factory-base`. Hat der Entwicklungs-Branch schon eine `bitbucket-pipelines.yml`, ersetzt `cp` sie: Schritt 9, Punkte 4 und 5, jetzt entscheiden. Erst `cp factory/pipelines.template.yml bitbucket-pipelines.yml`, dann ersetze:
- `__IMAGE__`, einmal: `<registry>/<repo>@sha256:<digest>` aus Schritt 5.
- `__RUNSON__`, in jedem Schritt: eigener Runner `runs-on: [<Labels deines Runners>]`, etwa `runs-on: [self.hosted, linux.arm64]`. Cloud-Runner: Zeile löschen. Sie verbrauchen Build-Minuten des Plans, eigene Runner nicht.
- Nie auf den Entwicklungs-Branch committen. Nie den Entwicklungs-Branch in `factory-base` zusammenführen, auch nicht per „Sync now“. Das kann die Pipeline-Datei löschen oder überschreiben; die Factory stoppt.

**Prüfen:** Datei nicht leer. Nur `factory-spec` und `factory-build`, je mit `JIRA_KEY` und `FRAMEWORK`. Keine Default- oder Branch-Pipeline. Jeder Schritt mit eigenem `auth`-Block (Leserecht) und `max-time`. Jeder Schritt mit `deployment:` hat `concurrency-group: factory`. Fester Name, keine Variablen: Bitbucket setzt sie dort nicht ein (getestet). Ohne diese Zeile hält ein zweiter Lauf dauerhaft an.

## Schritt 7: Per Pull Request nach factory-base bringen

Ziel: alles aus den Schritten 2 bis 6 auf `factory-base`.
```bash
git add factory AGENTS.md .github/copilot-instructions.md bitbucket-pipelines.yml \
  .agents/skills openspec/config.yaml .github/skills .specify .github/agents _bmad
git commit -m "Factory einrichten"
git push -u origin factory-setup
```
Pull Request von `factory-setup` nach `factory-base`. Eine benannte Person führt zusammen.

**Prüfen:** Push von `factory-setup` startet keinen Lauf. Danach liegt `bitbucket-pipelines.yml` auf `factory-base`.

## Schritt 8: Benutzer, Tokens und Umgebungen anlegen

Erledige vorher Schritt 9, Punkte 1 bis 3.

Ziel: `factory-bot` schreibt in das Repo. Jeder Schritt sieht nur die Factory-Tokens seiner Umgebung. Bitbucket gibt jedem Schritt zusätzlich eigene Tokens, begrenzt durch den `auth`-Block.

**1. `factory-bot` einladen:** „Write“ nur auf dieses Repo, keine Workspace-Gruppe. Blockiert, solange der Klickpfad offen ist (siehe „Vor dem Start“).

**Risiko, bewusst in Kauf genommen:** Wer „Write“ auf das Repo hat, kann die Tokens der Factory lesen, auch das Copilot-Token: mit eigenem Pipeline-YAML auf einem eigenen Branch. Im echten Repo sind das alle mit „Write“, nicht nur die Teilnehmenden. Mit den Tokens handelt man als `factory-bot` in Jira und im Repo und verbraucht das Copilot-Budget. Begrenzt durch: kurze Laufzeiten, Widerruf nach dem Workshop, „Deployment permissions“ auf `factory-base` (Punkt 3, falls der Plan sie hat).

**2. Tokens anlegen:**

| Token | Gehört | Art und Rechte | Umgebung |
|---|---|---|---|
| `COPILOT_GITHUB_TOKEN` | GitHub-Benutzer mit Copilot-Platz | Fine-grained PAT, nur „Copilot Requests“, bis 4. Dezember | `factory-agent` |
| `JIRA_API_TOKEN` | `factory-bot` | Atlassian-API-Token, Scopes `read:jira-work`, `write:jira-work` | `factory-jira`, `factory-publish` |
| `BB_TOKEN` | `factory-bot` | Atlassian-API-Token, Scopes `read:repository:bitbucket`, `write:repository:bitbucket`, `read:pullrequest:bitbucket`, `write:pullrequest:bitbucket` | `factory-publish` |
| Start-Token, eines pro startende Person | das Repo | Repository Access Token, nur „Pipelines: Write“ | keine: Passwortmanager der Person |
| Auslöser-Token, eines pro Flow, nur mit Jira-Automation | das Repo | Repository Access Token, nur „Pipelines: Write“ | keine: verborgener Header der Jira-Flows ([Teil B](jira.md#teil-b-flows-anlegen)) |

`JIRA_API_TOKEN`, `BB_TOKEN`, Auslöser-Tokens: kurze Laufzeit, etwa zwei Wochen. Namen etwa `factory-start-gruppe-1`, `factory-trigger`. Ablage im Passwortmanager, auch das Copilot-Token. Start-Tokens: Laufzeit höchstens bis Workshop-Ende, du widerrufst sie. Für Schritt 10 eines für dich, gleiche Laufzeit.

Bei jeder Erneuerung: altes Token sofort widerrufen.

**3. Drei Umgebungen anlegen:** `factory-jira`, `factory-agent`, `factory-publish`, jede vom Typ Production, unter „Repository Settings“ → „Pipelines“ → „Deployments“.
- Tokens als gesicherte Variablen, verteilt wie in der Tabelle. Keine Repository- oder Workspace-Variablen.
- Dazu ungesichert in `factory-jira` und `factory-publish`: `JIRA_BASE_URL` = `https://api.atlassian.com/ex/jira/<CLOUD-ID>` und `JIRA_EMAIL` = E-Mail von `factory-bot`. Gateway-URL, nicht die URL der Jira-Site: Tokens mit Scopes scheitern an der Site-URL.
- Mit „Deployment permissions“: Beschränke alle drei Umgebungen zuerst auf Branch `factory-base`. Ungetestet: ob die Grenzen wirken oder ob „nur Admins“ Läufe per Token blockiert.
- Lege die Aufbewahrung der Artefakte fest. **Offen:** Klickpfad. Leser des Repos können `out/agent.patch` herunterladen, auch abgelehnte Patches.

## Schritt 9: Andere Pipelines prüfen

Ziel: Factory-Tokens erreichen keine fremden Secrets, `factory-bot` keine anderen Branches, der Agent keine Secrets im Code.
1. **Andere Branches, Pflicht:** `factory-bot` hat „Write“ auf das ganze Repo. Beschränke die Rechte auf Entwicklungs-Branch, `main`, `release/*`, `workshop-*` und alle weiteren geschützten Branches. `factory-bot` darf dort weder pushen noch zusammenführen.
2. **Bestehende Variablen:** Prüfe „Workspace Settings“ → „Pipelines“ → „Workspace variables“ und „Repository Settings“ → „Pipelines“ → „Repository variables“. Sie gelten für alle Builds, auch den Agent-Schritt. Factory-Schritte brechen bei unbekannten Variablennamen ab. Verschiebe, was der bestehende Build braucht, in eine Umgebung, die der Agent-Schritt nicht nutzt.
3. **Custom-Pipelines auf allen Branches:** Ein Token mit „Pipelines: Write“ startet jede davon, auch Deploy-Pipelines mit ihren Secrets. Liste sie mit dem zweiten Befehl unten auf, für Branches und Tags (ungetestet). Deploy-Pipelines mit Secrets: Beschränke ihre Umgebungen per „Deployment permissions“ auf ihre Branches. Sonst gib nur wenige Start-Tokens aus und notiere ihre Besitzer.
4. **Branches `factory/<KEY>`:** Ersetzt die Factory-Datei die bisherige, startet dort kein Push einen Lauf. Kommen bestehende Pipelines in die Factory-Datei, schließe `factory/*` dort aus.
5. **`auth`-Block in jedem Schritt:** auch in bestehenden Build- und Testschritten (dort ungetestet). Ohne ihn: Schreibrechte für Repository und Pipelines bis 30. April 2027 (von Atlassian nicht bestätigt).
6. **Secrets im Code:** Der Agent liest den ganzen Stand von `factory-base` und schickt Code an Copilot, bei offenem Netz. Suche vor dem ersten Lauf nach eingecheckten Secrets und entferne sie aus `factory-base`, etwa mit dem ersten Befehl unten, auf `factory-base`. Risiko bleibt: Der Code des Repos geht an Copilot.

```bash
git ls-files | grep -iE '(^|/)\.env|\.pem$|\.key$|\.p12$|id_rsa|credentials|secret'
```

```bash
git fetch origin --tags
for b in $(git for-each-ref --format='%(refname:short)' refs/remotes/origin refs/tags); do
  echo "== $b"
  git show "$b:bitbucket-pipelines.yml" 2>/dev/null | grep -nE 'custom:|deployment:'
done
```
```yaml
auth:
  system:
    scopes: [read:git:bitbucket]
```

## Schritt 10: Ersten Lauf starten

Ziel: Pipeline, Tokens und Jira-Werte passen zusammen. Lege ein Ticket in „Definition“ an. Starte dann `factory-spec` mit diesem `JIRA_KEY` ([Läufe starten](#läufe-starten)). Der Guard stoppt vor dem Agenten, ohne AI-Credits zu verbrauchen. Protokoll: `https://bitbucket.org/<workspace>/<repo>/pipelines/results/<nr>`.

**Prüfen:** Kopfzeile zeigt `Pipeline variables: JIRA_KEY: <KEY>`, gesicherte Werte nur als Namen unter „Deployment variables“. Guard stoppt mit `spec runs start only from status Bereit`. Im Ticket ein Kommentar von `factory-bot`, Anfang `FACTORY-STOP v1`. Ganzes Ticket: [Jira, Teil C](jira.md#teil-c-probelauf).

## Läufe starten

Standardweg: per curl. Mit Jira-Automation ([Teil B](jira.md#teil-b-flows-anlegen)) starten die Läufe von selbst. Jede startende Person bekommt vom Admin ein eigenes Start-Token (Schritt 8). Status und Freigabe liest der Guard aus Jira:

1. Ticket auf „Bereit“, dann `factory-spec` starten.
2. Spec im Kommentar von `factory-bot` lesen. Ticket steht in „Wartet“.
3. Freigabe-Person setzt „Spec freigegeben“, dann `factory-build` starten.
4. Pull Request prüfen und zusammenführen, dann „Erledigt“ setzen.

Token abfragen (Eingabe unsichtbar), dann Lauf starten. Terminal mit bash oder zsh, unter Windows Git Bash:
```bash
printf 'Token: '; read -rs TOKEN; echo

printf 'header = "Authorization: Bearer %s"\n' "$TOKEN" | curl -sS -w '\nHTTP %{http_code}\n' -K - -X POST \
  -H "Content-Type: application/json" \
  "https://api.bitbucket.org/2.0/repositories/<workspace>/<repo>/pipelines" \
  -d '{"target":{"type":"pipeline_ref_target","ref_type":"branch","ref_name":"factory-base","selector":{"type":"custom","pattern":"factory-spec"}},"variables":[{"key":"JIRA_KEY","value":"<KEY>"},{"key":"FRAMEWORK","value":"<framework>"}]}'
unset TOKEN
```
- Bau: `"pattern":"factory-build"`. Ohne `FRAMEWORK`: zweites Objekt in `variables` weglassen. Ungetestet in genau dieser Form.
- Nie ein persönliches oder Admin-Token. Mit Schreibrecht startet es beliebiges YAML mit den Secrets der Factory.
- **`FRAMEWORK`** (`openspec`, `speckit`, `bmad`): Im Spec-Lauf hat es Vorrang vor dem Label. Ein unbekannter Wert bricht ab. Ohne Variable und Label stoppt der Lauf. Im Bau-Lauf muss es zum Framework der freigegebenen Spec passen, sonst Abbruch.
- **Achtung:** Das Token startet jede Custom-Pipeline des Repos, auf jedem Branch.

## Wenn die Einrichtung nicht klappt

Sind Blockaden aus „Vor dem Start“ noch offen: Teilnehmende nutzen das Lab von atra. Repository `factory-lab/factory-lab`, Jira-Projekt `FLAB`, App `symfony/demo`. Kein Code von Lekkerland im Lab. Läufe warten aufeinander wie oben.
- **Nur Leserecht, nie „Write“.** „Write“ legt die Tokens der Factory offen. Repository und `FLAB` öffentlich lesbar, das Board nicht.
- **Alles im Lab ist öffentlich:** keine internen Anforderungen, Namen oder Daten in Tickets.
- **Cloud-Runner von Atlassian.** Ein Lauf braucht dort etwa 2 Build-Minuten. Die 50 Build-Minuten des Free-Plans im Monat reichen für etwa 10 Tickets mit Spec und Bau.
- **Nur die Freigabe-Person von atra gibt frei.** In `FLAB` hat nur atra Schreibrechte: Tickets bewegen, freigeben, starten macht atra. Soll eine Freigabe-Person von Lekkerland freigeben, braucht es eine neue `config.json`, ein neues Image, einen neuen Digest (Schritte 4 bis 7) und die Regel in Jira.
