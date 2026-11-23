# Spec Kit, OpenSpec und BMAD im Vergleich

Diese Datei vergleicht drei Frameworks für Spec-Driven Development: Spec Kit, OpenSpec und BMAD (in den eigenen Quellen „BMad Method“). Ihr findet hier, was die Projekte in ihrer eigenen Dokumentation sagen. Jede Aussage beruht auf einer geprüften Quelle im Almanach von atra. Zwei Ausnahmen: Was mit **Lab** markiert ist, haben wir selbst im Demo-Repo beobachtet. Zahlen mit **API-Stand** sind gespeichert, aber noch nicht als Fakt geprüft. Die Datei gibt keine Empfehlung.

Quellenstand: 8. November 2026. Die meisten Quellen haben wir am 23. November 2026 erneut abgerufen; sie waren unverändert.

## Legende

- **eingebaut:** Die Dokumentation nennt dafür einen eigenen Befehl, Skill oder Schritt.
- **erwähnt:** Die Dokumentation spricht es an, ohne eigenen Schritt.
- **optional:** Erweiterung, die ihr selbst einschaltet, oder optionaler Teil.
- **Beispiel:** Beispieltext, z. B. aus einer Team-Anpassung, kein Standardverhalten.
- **Lab:** Beobachtung von atra im Demo-Repo (Symfony-App, Modell `claude-sonnet-5.5`, Copilot CLI 1.0.112 und 1.0.114, November 2026). Kein Fakt aus den Projektquellen.
- **API-Stand:** Zahlen aus der GitHub-API, abgerufen am 23. November 2026, Daten in UTC. Gespeichert, aber noch nicht als Fakt geprüft. Sterne und Forks zeigen Aufmerksamkeit, nicht Nutzung oder Qualität.
- **nicht belegt:** kein geprüfter Fakt. Das kann heißen: Die Quellen sagen nichts. Oder ein Fakt ist strittig oder zur Nachprüfung fällig. Es heißt nicht „gibt es nicht“.

## Überblick

| | Spec Kit | OpenSpec | BMAD |
|---|---|---|---|
| **Wer steht dahinter** | Repo-Eigentümer `github`; laut SUPPORT.md gepflegt von GitHub-Mitarbeitenden und der Community | Repo-Eigentümer `Fission-AI`; ein Lead Maintainer laut MAINTAINERS.md | Repo-Eigentümer `bmad-code-org`; Marken von BMad Code, LLC; laut SECURITY.md gepflegt von einem kleinen Team |
| **Aufmerksamkeit auf GitHub** | 151.098 GitHub-Sterne, 13.571 Forks, letzter Push 22. November 2026 (API-Stand); Repo seit 21. August 2025, UTC | 75.531 GitHub-Sterne, 5.163 Forks, letzter Push 23. November 2026 (API-Stand); Repo seit 5. August 2025 | 55.651 GitHub-Sterne, 6.203 Forks, letzter Push 23. November 2026, Repo seit 13. April 2025 (API-Stand); Release v6.12.4 vom 14. Oktober 2026 |
| **Stärken (Lab)** | Jede Phase lief ohne Rückfrage durch; ein neuer Prozess fand Spec und Plan im Repo. Kurzer Weg über die offizielle Bug-Extension. Artefakte: Spec, Checkliste, Plan, Recherche, Datenmodell, Aufgaben | Geringster Einrichtungsaufwand: ein Installationsbefehl, eine Rechte-Regel (`shell(openspec:*)`). Zustand nur in committeten Dateien. Bis zu vier kurze Dateien je Änderung | `bmad-build-auto` setzte ohne Gespräch um, prüfte mit vier Prüf-Subagenten und committete, mit einer Zusatzanweisung zum vollen Ablauf. `bmad-prd` meldet seinen Status als JSON (`complete`, `partial`, `blocked`). Installiert 29 Skills und 5 Agenten (Analyst, Architekt, Dev, PM, UX) |
| **Schwächen (Lab)** | Der Zeiger auf das aktuelle Feature (`.specify/feature.json`) ist git-ignoriert. Im Test fand Copilot den Ordner selbst; sicherer ist die Variable `SPECIFY_FEATURE_DIRECTORY`. Der Plan nannte einen Branch, den es nicht gab | Kurzer Weg schwach: `design.md` ist optional, das Modell entscheidet; beim Bug schrieb es sie trotzdem. Die Skills heißen `/openspec-propose` usw., nicht `/opsx:propose` | Braucht für den vollen Ablauf das Recht `shell(uv:*)` und darf damit beliebiges Python ausführen (Copilot CLI 1.0.112). Im ersten Versuch übersprang `bmad-build-auto` die Prüf-Subagenten |
| **Agenten** | Doku nennt u. a. Copilot, Claude, Codex, Gemini; Copilot CLI: nicht belegt | Tool-IDs u. a. `claude`, `codex`, `cursor`, `gemini`, `github-copilot`; Copilot CLI: nicht belegt | Installer-Einträge u. a. `claude-code`, `codex`, `cursor`, `github-copilot` bei v6.12.4; Copilot CLI: nicht belegt |
| **Zweck** | Laut Repository-Beschreibung ein Toolkit für den Einstieg in SDD oder einen anderen Prozess; Absicht und Belege vor die Implementierung stellen | Mensch und KI stimmen sich über die Specs ab, bevor Code entsteht | „BMad keeps you in control“; Agenten und Workflows machen wichtige Entscheidungen explizit, als Kontext für spätere Arbeit |
| **Ablauf und Artefakte** | Specify → Plan → Tasks → Implement → Converge; je Phase ein Markdown-Artefakt | Laut FAQ der einfachste Ablauf („simplest possible flow“): `/opsx:explore` (optional) → `/opsx:propose` → `/opsx:apply` → `/opsx:archive`. Explore erkundet die Codebasis; das Archiv bewahrt den Kontext jeder Änderung. Artefakte: Specs (Was), Design (Wie, nur bei Bedarf), Tasks. **Lab:** In Copilot CLI heißen die Befehle `/openspec-propose`, `/openspec-apply-change` usw. Propose legt `proposal.md`, `design.md`, `tasks.md` und `specs/` in `openspec/changes/<name>/` an. Apply schreibt Code und Tests und hakt die Aufgaben ab. Archive verschiebt die Änderung nach `changes/archive/` und übernimmt nach „Sync now“ die Specs nach `openspec/specs/`. | Laut Doku-Seite zur Planung in einer Organisation: Planen mit `bmad-prd` (PRD), dann `bmad-spec` (eine Spec je Epic); weitere Skills für Architektur (`bmad-architecture`) und UX (`bmad-ux`). Umsetzen: `bmad-build` mit der gewünschten Änderung aufrufen; nach dieser Entscheidung setzt der Skill um und prüft die eigene Arbeit. Ihr könnt die Artefakte auch einzeln im eigenen Lieferprozess nutzen. **Lab:** `bmad-prd` schreibt `prd.md`, `bmad-spec` schreibt `SPEC.md`, beide in `_bmad-output/`. Ohne Epics: `bmad-spec` schrieb eine `SPEC.md` je Ticket. `bmad-build-auto` lieferte Code, Tests, Prüfbefunde und einen Commit; dabei starteten mehrere Prüf-Subagenten. |
| **Freigaben** | `/speckit.checklist` als optionales Quality Gate; `/speckit.implement` fragt bei offenen Checklistenpunkten nach; Freigabe durch eine Person: nicht belegt | Team-Ablauf insgesamt als Konvention, nicht erzwungen; darin: Teammitglied prüft und mergt | Drei Gates: CHECKPOINT 1, die Freigabe der Spec vor der Umsetzung in `bmad-build`; Epic-Liste; Sprint Change Proposal. Diese drei Gates sind Anweisungen an den Agenten in den Skill-Dateien. Offen: ob CHECKPOINT 1 auf dem leichten Weg gilt |
| **Installation** | Python 3.11+; `uv tool install specify-cli`; offline und hinter Firewalls nutzbar; Windows, macOS, Linux | Installationsweg: nicht belegt; Node-Version: nicht belegt | Node.js 20.12+, Python 3.10+, uv; `npx bmad-method install` |
| **Bestehender Code (Brownfield)** | Leitfaden „Adopt Spec Kit safely in an established codebase“; vorher committen oder stashen, Branch anlegen | README nennt als Philosophie „built for brownfield not just greenfield“ | erst `bmad-project-context` erwägen, dann wie gewohnt bauen; der Skill schreibt einen kleinen, verifizierten Block mit Anweisungen für Agenten |
| **Team** | Presets für organisatorische oder regulatorische Standards; Rollen und Rechte: nicht belegt | Doku rät: Delta-Spec (die Änderungen an den Specs) oben in die PR-Beschreibung oder Reviewer auf den Change-Ordner verweisen; Rollen und Rechte: nicht belegt | Team-Konfiguration in Git, persönliche `.user.toml` in der `.gitignore`; Rollen und Rechte: nicht belegt |
| **Sicherheit und Telemetrie** | E-Mail an opensource-security[@]github.com, aus GitHubs allgemeinem Sicherheitstext, der Spec Kit nicht nennt; Telemetrie: nicht belegt | Meldung über GitHub Security Advisories; anonyme Telemetrie, abschaltbar mit `OPENSPEC_TELEMETRY=0` | Private Vulnerability Reporting oder security@bmadcode.com. Das Ausführen von Anweisungen aus Markdown-Dateien ist laut SECURITY.md beabsichtigtes Design, keine Schwachstelle. Sicherheitsgrenze: Inhalte, die ein Nutzer weder selbst verfasst noch wissentlich installiert hat, sollen das Verhalten der Agenten nicht unbeabsichtigt ändern können. Telemetrie: nicht belegt |
| **Lizenz** | MIT; Preis: nicht belegt | MIT; Preis: nicht belegt | LICENSE-Titel „MIT License“ bei v6.12.4, GitHub-API: „Other“; kostenlos, keine Workflows hinter einer Paywall |
| **Ausstieg** | „No lock-in“ beim Agentenwechsel, Aussage des Projekts; Deinstallation der CLI: nicht belegt | `npm uninstall -g @fission-ai/openspec` entfernt das globale Paket; optional `openspec/` und Tool-Dateien löschen | Installer löscht alte Skill-Verzeichnisse entfernter Module nicht; vollständige Deinstallation: nicht belegt |

## Eure Spryker-Schritte

Die zehn Schritte stammen aus der Selbsteinschätzung eures Spryker-Teams im September 2026. Die Zuordnung der Framework-Angaben zu euren Schritten ist unsere eigene; die Angaben selbst stammen aus dem allgemeinen Lebenszyklus unten.

| Euer Schritt | Spec Kit | OpenSpec | BMAD |
|---|---|---|---|
| **1. Anforderung** | Anforderungen und User Stories eingebaut; GitHub Issues optional; Jira erwähnt, Beispiel | Specs (Was) eingebaut; Tickets nicht belegt | PRD eingebaut; Jira erwähnt, Beispiel |
| **2. Verstehen** | Recherche optional | Codebasis erkunden eingebaut | Absicht eingebaut; Recherche eingebaut |
| **3. Spezifikation** | Specify → Plan → Tasks eingebaut; Architektur eingebaut | Specs, Design (nur bei Bedarf), Tasks eingebaut | Spec je Epic eingebaut; Architektur und UX eingebaut; Akzeptanzkriterien eingebaut |
| **4. Kritik** | Rückfragen eingebaut; Annahmen erwähnt; Prüfung der Akzeptanzkriterien erwähnt; optionales Quality Gate | Risiken erwähnt; Plan lesen (Mensch) | Annahmen eingebaut; offene Fragen beantwortet ihr vor der Freigabe |
| **5. Freigabe der Spec** | Nachfrage bei offenen Checklistenpunkten; Freigabe durch eine Person nicht belegt | Team-Ablauf als Konvention, nicht erzwungen | CHECKPOINT 1 eingebaut, als Anweisung an den Agenten; offen, ob er auf dem leichten Weg gilt |
| **6. Bauen** | Code eingebaut | `/opsx:apply` als Schritt genannt; was er tut: nicht belegt | Code eingebaut |
| **7. Laufzeitprüfung** | Unit-Tests erwähnt, Beispiel; E2E erwähnt, Beispiel; CI nicht belegt | Tests und CI nicht belegt | Tests (test-first) erwähnt; E2E eingebaut; CI nicht belegt |
| **8. Prüfachsen** | Code gegen Spec eingebaut; Code- und Security-Review per Extension oder Preset möglich; Regeln eingebaut | `/opsx:verify` prüft Code gegen Plan, blockiert das Archivieren nicht, nicht in `core`; Security nicht belegt | Code-Review eingebaut; Security erwähnt, Beispiel; Code gegen Spec nicht belegt |
| **9. Freigabe des Pull Requests** | Auto-Commit optional; PR nicht belegt | Ihr committet selbst; Commit, PR und Review durch ein Teammitglied als Konvention | Agent öffnet den PR auf eure Bitte; Review-Skill nimmt PR-Verweise an |
| **10. Auslieferung** | Deployment erwähnt, Beispiel | Deployment erwähnt | Deployment erwähnt |

## Allgemeiner Lebenszyklus

| Tätigkeit | Spec Kit | OpenSpec | BMAD |
|---|---|---|---|
| **Absicht klären** | Rückfragen eingebaut; Annahmen erwähnt; Recherche optional | Codebasis erkunden eingebaut; Risiken erwähnt | Absicht eingebaut; Annahmen eingebaut; Recherche eingebaut |
| **Anforderungen und Akzeptanz** | eingebaut; Akzeptanz erwähnt | eingebaut; Akzeptanz erwähnt | eingebaut; Akzeptanz eingebaut |
| **Entwurf** | Architektur eingebaut; UX nicht belegt | Design eingebaut, nur bei Bedarf; UX nicht belegt | Architektur eingebaut; UX eingebaut |
| **Aufgaben, Tickets, Schätzung** | Tasks eingebaut; GitHub Issues optional; Jira erwähnt, Beispiel; Schätzung nicht belegt | Tasks eingebaut; Tickets, Schätzung nicht belegt | Epics: `bmad-create-epics-and-stories` mit Freigabe der Epic-Liste; Jira erwähnt, Beispiel; Schätzung erwähnt |
| **Code und Tests** | Code eingebaut; Unit-Tests erwähnt, Beispiel; E2E erwähnt, Beispiel | `/opsx:apply` als Schritt genannt; was der Befehl tut und Tests: nicht belegt | Code eingebaut; Tests (test-first) erwähnt; E2E eingebaut |
| **Code gegen Spec prüfen** | eingebaut | `/opsx:verify` prüft Code gegen Plan, blockiert das Archivieren nicht; nicht in den Standard-Workflows von `core` | nicht belegt |
| **Review und Sicherheit** | Code-Review per Extension möglich; Security-Review per Preset möglich | Plan lesen (Mensch), vor `/opsx:apply`; Code: `/opsx:verify`, siehe Zeile „Code gegen Spec prüfen“; Security nicht belegt | Code-Review eingebaut; Security erwähnt, Beispiel |
| **Commit und Pull Request** | Auto-Commit optional; PR nicht belegt | OpenSpec committet nie, ihr committet selbst; Commit und PR als Konvention | PR erwähnt: Agent pusht und öffnet den PR auf eure Bitte; Review-Skill löst PR-Verweise per `gh pr view` zu Branch oder Commit auf |
| **CI, Auslieferung, Betrieb** | Deployment erwähnt, Beispiel; Betrieb erwähnt; CI nicht belegt | Deployment erwähnt; CI, Betrieb nicht belegt | Deployment erwähnt; Betrieb erwähnt, optional; CI nicht belegt |
| **Freigaben, Audit, Regeln** | Freigabe: optionales Quality Gate, Nachfrage bei offenen Checklistenpunkten, Freigabe durch eine Person nicht belegt; Audit erwähnt; Regeln eingebaut | Team-Ablauf als Konvention, nicht erzwungen; die CLI `openspec archive` bricht ohne interaktive Eingabe und ohne `--yes` ab, etwa bei einem KI-Agenten; Archiv als Audit-Spur; Regeln nicht belegt | Freigabe eingebaut, als Anweisungen an den Agenten; offen, ob CHECKPOINT 1 auf dem leichten Weg gilt; Audit für einen `bmad-prd`-Lauf; Regeln nicht belegt |

## Leichter Weg

- **BMAD:** Ein Entwurf ohne Befund bei drei Punkten nimmt den leichten Weg: Lücken in der Absicht, irreversible Aktionen, Umfang. Dann entstehen eine minimale Spec und die Umsetzung in derselben Sitzung; das Review folgt danach. Markierte Punkte bekommen zuerst einen vollständigen schriftlichen Plan; offene Fragen beantwortet ihr vor der Freigabe. Offen: ob CHECKPOINT 1 auf dem leichten Weg gilt.
- **OpenSpec:** Es gibt eine Lite spec und den Quick-Feature-Workflow. Die Dokumentation nennt den Quick-Feature-Workflow für kleine bis mittlere Features, Bugfixes und einfache Änderungen. Sie führt den Quick-Feature-Workflow unter dem erweiterten Modus, nicht unter `core`. Kein Fakt nennt eines davon einen leichten Weg.
- **Spec Kit:** nicht belegt.

## Was nicht geprüft wurde

- Die Datei nutzt keine strittigen, offenen oder zur Nachprüfung fälligen Fakten.
- **Copilot CLI:** Kein geprüfter Fakt nennt sie für eines der drei Frameworks. Die Fakten nennen nur „Copilot“ oder `github-copilot`.
- **Jira und Bitbucket:** Spec Kit nennt „Jira integration“ als Beispiel dafür, was Extensions bereitstellen können. BMAD zeigt Jira im Anpassungsbeispiel eines Teams. Bitbucket: kein geprüfter Fakt. Die Fakten zum Git-Hosting beziehen sich auf GitHub.
- **Python:** Spec Kit und BMAD nennen verschiedene Mindestversionen. Welche Version eure Laptops haben, prüft diese Datei nicht.
- **Wer freigegeben hat:** kein geprüfter Fakt.
