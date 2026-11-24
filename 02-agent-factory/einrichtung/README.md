# Einrichtung

Anleitungen für Admins, die die Factory einmalig einrichten. Gesamtbild: [Überblick](../ueberblick.md).

## Anleitungen

- [Voraussetzungen](voraussetzungen.md): Lizenzen, Konten, Tokens und Freigaben.
- [Bitbucket](bitbucket.md): Branch `factory-base` und die Custom-Pipelines.
- [Jira](jira.md): Konto `factory-bot`, Status, Freigabe und optionale Automation-Flows.
- [GitHub Copilot](copilot.md): technischer Nutzer, Token und Budget.
- [Abnahme](pruefung.md): Checkliste und erstes Testticket.

Bitbucket und Jira greifen ineinander. Die Reihenfolge steht am Anfang der [Bitbucket-Anleitung](bitbucket.md).

## Factory-Schritte lokal: die Vorlage

Der Ordner [`template/`](template/README.md) enthält die vier Dateien, mit denen Entwickler die Copilot-Aufrufe der Factory im eigenen Projekt starten, ohne Pipeline:

- `local.py`, das Programm,
- `config.json` mit Prompts, Werkzeug-Freigaben und Modell, dieselbe Datei wie in der Pipeline,
- `readiness.md` mit den Kriterien der Bereitschaftsprüfung,
- `local.example.json`, die Vorlage für eigene Anpassungen wie den Testbefehl.

Sie sind eine unveränderte Kopie aus dem Lab-Repo, Branch `factory-base`. Die [README der Vorlage](template/README.md) erklärt das Kopieren, die Sicherheitsrisiken und das Aktualisieren. Die Anleitung: [Factory-Schritte lokal ausführen](../bedienung/lokal-ausfuehren.md), im Workshop [Übung 1](../../01-erstworkshop/tag-2/uebung-factory-lokal.md).

## Zum Nachlesen

- [Prompt-Beispiele](prompt-beispiele/README.md): jeder Copilot-Aufruf der Factory für das Ticket FLAB-41, mit Prompt, erlaubten Werkzeugen und Flags, für Bereitschaft, Spec und Bauen mit allen drei Frameworks.
- [Spec Kit, OpenSpec und BMAD im Vergleich](sdd-frameworks/vergleich.md): was die drei SDD-Frameworks laut eigener Dokumentation können, dazu unsere Beobachtungen im Demo-Repo und Stimmen aus unabhängigen Reviews. Ohne Empfehlung.
