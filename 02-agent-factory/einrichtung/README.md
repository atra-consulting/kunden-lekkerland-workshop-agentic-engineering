# Einrichtung

Anleitungen für Admins, die die Factory einmalig einrichten. Gesamtbild: [Überblick](../ueberblick.md).

## Anleitungen

Es gibt zwei Wege, die Factory in Bitbucket zu betreiben:

- **[Pipeline für `assess` und `clarify`](factory/factory-bitbucket-pipeline-guide.md):** Die Vorlage `agentic-factory.py` prüft Tickets und klärt sie in Runden von Kommentaren. Jira Automation startet die nächste Runde. Die Anleitung nennt alle Voraussetzungen: Konten, Tokens, Copilot-PAT, Runner, Image und Deployments. Die Abnahme steht in Schritt 8 (von Hand testen) und Schritt 10 (Pilotticket). Spec und Bauen laufen auf diesem Weg lokal.
- **Pipeline der Lab-Factory mit Spec und Bauen:** zwei Läufe, `factory-spec` und `factory-build`, mit zwei Freigaben in Jira.
  - [Bitbucket](bitbucket.md): Branch `factory-base` und die Custom-Pipelines.
  - [Jira](jira.md): Konto `factory-bot`, Status, Freigabe und optionale Automation-Flows.

  Bitbucket und Jira greifen ineinander. Die Reihenfolge steht am Anfang der [Bitbucket-Anleitung](bitbucket.md).

Beide Wege sind Vorschläge. Passt sie an euer Projekt an.

## Factory-Schritte lokal: die Vorlage

Der Ordner [`factory/`](factory/README.md) enthält die Dateien, mit denen Entwickler die Copilot-Aufrufe der Factory im eigenen Projekt starten, ohne Pipeline:

- `agentic-factory.py`, das Programm (früher `local.py`). Es kennt fünf Modi: `init`, `assess`, `clarify`, `spec` und `build`. Es liest Kommentare im Ticket und schreibt `[KI]`-Kommentare. Ein zweiter Lauf von `spec` oder `build` überarbeitet Spec oder Code nach `[Mensch]`-Kommentaren.
- `agentic_factory/`, der Code, den das Programm lädt,
- `agentic-factory-plugin/`, der Hook für die Jira-Aufrufe über MCP,
- `config.json` mit Prompts, Werkzeug-Freigaben, Modell und Testbefehl, ohne Annahmen über euren Stack,
- `readiness.md` mit den Kriterien der Bereitschaftsprüfung,
- `local.example.json`, die Vorlage für die Einstellungen eures Rechners, etwa Modell und Copilot-Befehl,
- `pipelines.example.yml`, ein Beispiel für Bitbucket Pipelines, eingerichtet nach der [Pipeline-Anleitung](factory/factory-bitbucket-pipeline-guide.md),
- `tests/`, die Tests der Vorlage.

Sie sind aus dem Lab-Repo, Branch `factory-base`, entstanden und keine unveränderte Kopie mehr. Die [README der Vorlage](factory/README.md) erklärt das Kopieren, die Einrichtung mit `init`, das Überarbeiten von Spec und Build, die Sicherheitsrisiken und das Aktualisieren. Die Regeln eures Teams gehören in `AGENTS.md` eures Projekts. Die Anleitung: [Factory-Schritte lokal ausführen](../bedienung/lokal-ausfuehren.md), im Workshop [Übung 1](../../01-erstworkshop/tag-2/uebung-factory-lokal.md).

## Zum Nachlesen

- [Prompt-Beispiele](prompt-beispiele/README.md): jeder Copilot-Aufruf der Factory für das Ticket FLAB-41, mit Prompt, erlaubten Werkzeugen und Flags, für Bereitschaft, Spec und Bauen mit allen drei Frameworks.
- [Spec Kit, OpenSpec und BMAD im Vergleich](sdd-frameworks/vergleich.md): was die drei SDD-Frameworks laut eigener Dokumentation können, dazu unsere Beobachtungen im Demo-Repo und Stimmen aus unabhängigen Reviews. Ohne Empfehlung.
