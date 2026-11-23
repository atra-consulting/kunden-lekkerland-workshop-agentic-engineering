# Walkthrough: Die Agent Factory im Lab

Tag 2, 24. November 2026. Dieses Dokument führt euch durch die Agent Factory im Lab von atra. Ihr braucht dafür kein Konto: Fast alles ist öffentlich lesbar. Wo ein Login nötig ist, zeigt ein Bild, wie es aussieht.

Das Lab arbeitet mit [`symfony/demo`](https://github.com/symfony/demo), einem kleinen PHP-Blog, nicht mit eurem Code. Eure eigene Factory richtet ihr später in eurem Bitbucket ein: [Einrichtung](../../02-agent-factory/einrichtung/README.md).

Stand: 23. November 2026, Entwurf. Abschnitte mit „Folgt.“ ergänzen wir bis zum Workshop.

## Die Bausteine auf einen Blick

| Baustein | Wo | Ohne Login sichtbar |
|---|---|---|
| Jira-Space „Factory Lab Public“ (FLAB) | Ticket-Seiten, z. B. [FLAB-22](https://betterprojectsfaster.atlassian.net/browse/FLAB-22) | Ja |
| Kanban-Board | [FLAB board](https://betterprojectsfaster.atlassian.net/jira/software/c/projects/FLAB/boards/3) | Nein. Bild folgt |
| Jira-Workflow und zwei Automation-Regeln | Space-Einstellungen | Nein. Bild folgt |
| Bitbucket-Repository `factory-lab/factory-lab`, Start-Branch `factory-base` | [Quellcode](https://bitbucket.org/factory-lab/factory-lab/src/factory-base/) | Ja |
| Pipeline-Definition | [`bitbucket-pipelines.yml`](https://bitbucket.org/factory-lab/factory-lab/src/factory-base/bitbucket-pipelines.yml) | Ja |
| Die Skripte der Factory | [`factory/`](https://bitbucket.org/factory-lab/factory-lab/src/factory-base/factory/), mit [README](https://bitbucket.org/factory-lab/factory-lab/src/factory-base/factory/README.md) | Ja |
| Die Läufe | [Pipelines](https://bitbucket.org/factory-lab/factory-lab/pipelines) | Ja |
| Die Ergebnisse | [Pull Requests](https://bitbucket.org/factory-lab/factory-lab/pull-requests/) | Ja |
| Das Image mit Copilot CLI und den drei Frameworks | [Docker Hub, `joedata/factory-lab`](https://hub.docker.com/r/joedata/factory-lab) | Ja |
| Deployment-Variablen mit den Tokens | Repository-Einstellungen | Nein, und das ist Absicht |

Die Factory nutzt Copilot CLI mit dem Modell Claude Sonnet 5.5. Spec Kit, OpenSpec und BMad liegen fertig im Image. Welches Framework ein Lauf nutzt, bestimmt das Label am Ticket.

## Der Ablauf an einem echten Ticket: FLAB-22

FLAB-22 „Current year in the page footer“ lief am 23. November mit OpenSpec durch die Factory. Öffnet die Links nebeneinander und folgt dem Ticket.

| Schritt | Status in Jira | Wer | Was passiert | Wo ihr es seht |
|---|---|---|---|---|
| 1 | Definition | Mensch | Ticket mit Akzeptanzkriterien und genau einem Label, hier `sdd-openspec` | [FLAB-22](https://betterprojectsfaster.atlassian.net/browse/FLAB-22) |
| 2 | Bereit | Mensch | Das Ticket auf „Bereit“ setzen. Eine Jira-Automation startet die Pipeline `factory-spec` | Bild folgt |
| 3 | Bereit | Factory | Lauf 1: Copilot schreibt die Spec mit OpenSpec. Die Factory prüft sie | [Pipelines](https://bitbucket.org/factory-lab/factory-lab/pipelines) |
| 4 | In Arbeit, dann Wartet | `factory-bot` | Die Spec steht als Kommentar `FACTORY-SPEC v1` am Ticket und auf dem Branch `factory/FLAB-22` | Kommentar in [FLAB-22](https://betterprojectsfaster.atlassian.net/browse/FLAB-22) |
| 5 | Bau | Mensch | **Freigabe 1:** Ein Mensch aus der Freigabegruppe setzt „Spec freigegeben“. Die zweite Automation startet `factory-build`. Lauf 2: Copilot setzt die Spec um, die Tests laufen | [Lauf #85](https://bitbucket.org/factory-lab/factory-lab/pipelines/results/85). Im Lab gibt nur Karsten frei |
| 6 | Review | `factory-bot` | Die Factory öffnet einen Pull Request und verlinkt ihn am Ticket | [Pull Request #19](https://bitbucket.org/factory-lab/factory-lab/pull-requests/19) |
| 7 | Erledigt | Mensch | **Freigabe 2:** Ein Mensch prüft den Pull Request und führt ihn zusammen. Die Factory führt nie selbst zusammen | Pull Request #19 |

Dieselbe Strecke mit den anderen Frameworks:

- Spec Kit: [FLAB-18](https://betterprojectsfaster.atlassian.net/browse/FLAB-18), [Pull Request #13](https://bitbucket.org/factory-lab/factory-lab/pull-requests/13). Das Ticket hat zwei Spec-Kommentare, weil es zweimal lief.
- BMad: [FLAB-19](https://betterprojectsfaster.atlassian.net/browse/FLAB-19), [Pull Request #15](https://bitbucket.org/factory-lab/factory-lab/pull-requests/15). Das Ticket hat zwei Framework-Labels, weil es vor der Regel „genau ein Label“ lief. Heute stoppt so ein Ticket.

## Was in einem Lauf passiert

Jeder Lauf besteht aus mehreren Schritten. Jeder Schritt sieht nur die Secrets, die er braucht.

**`factory-spec`, Lauf 1:**

1. **Guard und Vorbereitung:** Stimmen Ticket-Schlüssel, Status und Label? Ist die Factory gestoppt? Dann holt die Factory das Ticket aus Jira.
2. **Agent:** Copilot CLI schreibt die Spec mit dem gewählten Framework. Dieser Schritt sieht nur den Copilot-Token. Copilot läuft als eigener Benutzer ohne Rechte, und nur ein Patch verlässt den Schritt.
3. **Prüfung, ohne Secrets:** Hat der Agent nur Spec-Dateien geändert? Stecken Token-Muster oder unsichtbare Zeichen im Patch?
4. **Veröffentlichen:** Die Factory prüft alles noch einmal, pusht den Branch, kommentiert die Spec und setzt den Status.

**`factory-build`, Lauf 2:**

1. **Guard:** Die Factory prüft Freigabe 1. Hat eine Freigabe-Person freigegeben, und zwar nach dem Spec-Kommentar? Hat sich danach etwas geändert? Ist der Branch noch genau auf dem freigegebenen Stand?
2. **Agent:** Copilot setzt die Spec um und führt die Tests aus.
3. **Prüfung:** Hat der Agent geschützte Dateien geändert?
4. **Build und Tests, ohne Secrets:** frischer Checkout, `composer install`, Testbefehl.
5. **Veröffentlichen:** Branch pushen, Build-Status setzen, Pull Request öffnen.

Geschützt sind unter anderem die Pipeline-Definition, `factory/`, `AGENTS.md`, `.github/`, die Ordner der Frameworks, `composer.json` und `composer.lock`, `bin/`, die PHPUnit- und PHPStan-Konfiguration und `.env*`. Neue Pakete kann der Agent also nicht einbauen. Die vollständige Liste steht unter `protected_paths` in [`factory/config.json`](https://bitbucket.org/factory-lab/factory-lab/src/factory-base/factory/config.json).

## Die Prüfpunkte

### Neu: Ist das Ticket bereit?

Folgt.

### Freigabe 1: Die Spec

Nur benannte Personen können „Spec freigegeben“ setzen. Im Lab ist das Karsten. Die Freigabe gilt nur für genau die Spec im Kommentar. Ändert jemand danach Beschreibung, Labels oder Kommentare, bricht der Bau ab.

Passt die Spec nicht, geht das Ticket mit „Zurück“ nach „Definition“. Ihr überarbeitet es und startet neu.

### Freigabe 2: Der Pull Request

Ihr lest den Diff wie bei jedem Pull Request. Die Fragen dazu:

- Decken die Tests jedes Akzeptanzkriterium ab?
- Hat der Agent etwas geändert, das das Ticket nicht verlangt?
- Würdet ihr den Code von einem Kollegen so annehmen?

## Wenn die Factory stoppt

Die Factory stoppt lieber, als etwas Falsches zu schreiben. Ihr seht drei Arten:

| Art | Beispiel | Was ihr tut |
|---|---|---|
| Kommentar `FACTORY-STOP v1`: Der Lauf passt nicht, etwa falscher Status oder kein Label | [FLAB-21](https://betterprojectsfaster.atlassian.net/browse/FLAB-21): „no framework chosen“ | Den Grund beheben, Ticket wieder auf „Bereit“ |
| Kommentar `FACTORY-QUESTIONS v1`: Das Ticket ist zu vage für eine Spec. Das Ticket geht zurück nach „Definition“ | [FLAB-6](https://betterprojectsfaster.atlassian.net/browse/FLAB-6): „Make the blog better“ | Die Fragen in der Beschreibung beantworten, neu starten |
| Kein Kommentar | – | Das Protokoll unter [Pipelines](https://bitbucket.org/factory-lab/factory-lab/pipelines) lesen |

**Notaus:** Jede Person kann ein Ticket auf „Factory gestoppt“ setzen. Jeder Lauf zu diesem Ticket bricht dann ab, beim Start und vor jedem Schreiben. Weiter geht es nur mit „Fortsetzen“ durch eine Freigabe-Person.

## Kosten und Dauer im Lab

Gemessen im Lab mit `symfony/demo`, je Ticket. Das sind Einzelwerte aus wenigen Läufen, keine Erwartung für euren Code. 1 AI Credit kostet 0,01 US-Dollar.

| | OpenSpec | Spec Kit | BMad |
|---|---|---|---|
| Lauf 1, Spec | 12 bis 21 Credits | 42 Credits | 26 Credits |
| Lauf 2, Bau | 12 bis 27 Credits | 34 Credits | 63 Credits |
| **Je Ticket** | **etwa 30 bis 50 Credits** | **etwa 76 Credits** | **etwa 89 Credits** |

- Ein zu vages Ticket kostete 4 Credits und 42 Sekunden, bis die Fragen am Ticket standen.
- Ein Lauf 1 dauerte 75 bis 147 Sekunden, ein Lauf 2 115 bis 211 Sekunden. Dazu kommen Wartezeit und die Zeit bis zur Freigabe.
- Jeder Copilot-Aufruf stoppt bei 150 Credits.
- Läufe warten aufeinander. „Queued“ in Bitbucket heißt warten, nicht neu starten.

## Selbst ausprobieren

### Ohne Konto

Öffnet die Links oben: Ticket, Pipeline-Lauf, Pull Request. Im Protokoll eines Laufs seht ihr jeden Schritt, auch den Copilot-Aufruf mit seinen Optionen.

### Mit Konto

Der Zugang ist für eure DevOps-Ansprechperson gedacht. Damit legt ihr Tickets in FLAB an, setzt Labels und schiebt Tickets auf „Bereit“. Spec freigeben und zusammenführen kann im Lab nur Karsten.

So schreibt ihr ein Ticket:

```text
Ziel
Wer will was und warum, in einem Satz.

Akzeptanzkriterien
- Wenn …, dann … (je Kriterium ein Satz, prüfbar durch einen Test)

Nicht Teil des Tickets
- Was der Agent nicht ändern soll.

Hinweise
- Betroffene Seite oder Route, z. B. Artikelseite /blog/posts/{slug}.
```

- Genau ein Label: `sdd-openspec`, `sdd-speckit` oder `sdd-bmad`.
- Klein: ein Pull Request, etwa eine Stunde Arbeit für einen Menschen.
- Prüfbar: Jedes Kriterium kann in einem Test scheitern.
- Vollständig: Der Agent fragt nicht nach. Was nicht im Ticket steht, rät er.
- **Öffentlich:** FLAB und das Repository sind öffentlich. Keine internen Anforderungen, Namen oder Daten.

### Lokal, ohne Pipeline

Folgt.

### Ein Ticket schreiben lassen

Folgt.

## Für eure eigene Factory

- [Überblick](../../02-agent-factory/ueberblick.md): eure zehn Schritte in der Factory.
- [Einrichtung](../../02-agent-factory/einrichtung/README.md): Bitbucket, Jira und Copilot, Schritt für Schritt.
- [Merkblatt](../../02-agent-factory/bedienung/merkblatt.md): die Bedienung auf einer Seite.

Was das Lab nicht zeigt und ihr mit eurem DevOps-Team klärt:

- Euer Testbefehl läuft in Docker, etwa `make test`. In Bitbucket Pipelines braucht der Testschritt dann Docker.
- Tokens: ein technischer GitHub-Benutzer mit Copilot-Lizenz, ein Jira-Konto und ein Bitbucket-Zugang für die Factory.
- Runner: Atlassians Cloud-Runner oder eigene Runner. Das Lab nutzt einen eigenen Runner, um Build-Minuten zu sparen.
