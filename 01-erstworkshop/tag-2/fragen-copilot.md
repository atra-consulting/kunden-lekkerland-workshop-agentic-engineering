# Fragen zum Copilot

## Copilot

1. Welche IDEs nutzt ihr: VS Code, PhpStorm, andere?

   - IntelliJ
   - Terminal
   - OpenCode
   - GitHub Copilot App
   - T3 Code

2. Wem gehören die Copilot-Lizenzen und Richtlinien: Lekkerland oder REWE? Wer genehmigt Änderungen?

   - REWE

3. Business oder Enterprise?

   In der Plan-Übersicht von GitHub haben beide dieselben Funktionen, auch Copilot CLI, MCP und Content Exclusion. Sie unterscheiden sich im Preis und in den AI Credits. Business kostet 19 USD pro Lizenz und Monat und bringt 1.900 Credits pro Nutzer, gepoolt über die Organisation. Enterprise kostet 39 USD und bringt 3.900 Credits, gepoolt über das Enterprise. Was über den Pool hinausgeht, kostet 0,01 USD pro Credit. Davon hängt ab, wie viele Läufe der Factory euer Budget trägt.

   - Business

4. Ist Copilot CLI freigeschaltet? Ist die Richtlinie "MCP servers in Copilot" an?

   - Mittlerweile ja

5. Gibt es zentrale Einstellungen? Über welchen Weg: vom Server, per MDM oder als Datei?

   Mit den Enterprise Managed Settings legen Admins Einstellungen in einer Datei `managed-settings.json` fest, die für alle Copilot-Clients gelten: Copilot CLI, VS Code, die Copilot-App, Copilot in the Cloud und JetBrains-IDEs wie PhpStorm. Welche Einstellung welcher Client beachtet, steht in der Referenz von GitHub.

   Es gibt drei Wege. Vom Server liegt die Datei im Repo `.github-private` eurer Organisation. Per MDM kommt sie über die Registry unter Windows oder ein Profil unter macOS. Als Datei liegt sie in einem festen Ordner, unter Windows in `%ProgramFiles%\GitHubCopilot\`. Gibt es mehrere, gewinnt MDM vor Server vor Datei. Die Einstellungen der Nutzer kommen zuletzt.

   - ja

6. Welche `permissions`-Einstellungen sind gesetzt? Ist der Bypass-Modus aus?

   Im Block `permissions` der Managed Settings stehen Regeln, was Copilot ohne Nachfrage darf (`allow`), nur nach Nachfrage (`ask`) und gar nicht (`deny`). Bei Konflikten gewinnt `deny` vor `ask` vor `allow`.

   Im Bypass-Modus fragt Copilot gar nicht mehr nach, in Copilot CLI zum Beispiel mit `--yolo` oder `--allow-all`. Dann darf Copilot alles, was ihr dürft. Mit `permissions.disableBypassPermissionsMode` auf `"disable"` schalten Admins ihn ab. Dann wirken `--yolo` und `--allow-all` nicht mehr, und in VS Code lässt sich die automatische Freigabe aller Tools nicht mehr einschalten. `permissions.defaultMode` setzt dagegen nur einen Standard, den Nutzer ändern können.

   - vermutlich

7. Gibt es eine MCP-Allowlist?

   Eine Allowlist legt fest, welche MCP-Server Copilot starten darf, zum Beispiel nur den Atlassian-MCP-Server. Der sichere Weg sind die Schlüssel `allowedMcpServers` und `deniedMcpServers` in den Managed Settings. Sie erkennen Server an Name, URL oder Startbefehl und gelten in der Copilot-App, in Copilot CLI und in VS Code. Der zweite Weg ist eine eigene MCP-Registry. Laut GitHub ist sie schwächer: Nutzer können die Sperre umgehen, indem sie ihre Konfigurationsdateien ändern.

   - ja

8. Welche VS-Code-Richtlinien sind verteilt?

   VS Code liest eigene Richtlinien, unabhängig von GitHub: unter Windows per Group Policy mit ADMX-Vorlagen, unter macOS per Profil über MDM, unter Linux aus `/etc/vscode/policy.json`. Für Copilot zählen vor allem diese:

   - `ChatAgentMode`: ob der Agent-Modus mit Tools läuft, die etwas verändern
   - `ChatMCP`: ob installierte MCP-Server laufen dürfen
   - `ChatToolsAutoApprove`: ob alle Tools ohne Nachfrage laufen; Microsoft rät davon ab
   - `ChatToolsTerminalEnableAutoApprove`: ob Terminal-Befehle ohne Nachfrage laufen
     - Vermutlich nicht

9. Ist die Sandbox Pflicht? Läuft sie auf euren Windows-Laptops?

   Die lokale Sandbox isoliert, was Copilot CLI und die Copilot-App auf eurem Rechner ausführen: welche Pfade Befehle lesen und schreiben dürfen und ob sie ins Netz kommen. Ohne Sandbox laufen diese Befehle mit euren vollen Rechten. Laut GitHub ist sie standardmäßig aus. Unternehmen können sie vorschreiben und ihre Einstellungen zentral durchsetzen, vom Server, per MDM oder als Datei.

   Auf Windows braucht die Sandbox ein aktuelles Windows-11-Update. Ob gesperrte Pfade, localhost-Verbindungen und Proxy funktionieren, hängt von der Windows-Version ab. Außerdem verlässt sie sich auf Windows darauf, dass Programme die Proxy-Einstellungen beachten. Gegen direkte Netzverbindungen schützt sie dort also weniger als auf macOS und Linux.

   - vermutlich aus

10. Ist Content Exclusion eingerichtet?

    Mit Content Exclusion legen Admins Dateien und Pfade fest, die Copilot nicht als Kontext nutzt, zum Beispiel Konfiguration mit Zugangsdaten. Das geht auf Ebene von Enterprise, Organisation und Repository und nur in Copilot Business und Enterprise. Copilot CLI beachtet diese Regeln. Wie weit sie in den einzelnen IDEs greifen, zeigt die Übersicht „Availability of content exclusion“ in der Doku von GitHub. Prüft dort, was für eure IDEs gilt.

    - Unklar/nein

11. Zeichnet die Telemetrie Inhalte auf? Wohin geht sie?

    Copilot CLI, die Copilot-App und VS Code können Traces und Metriken per OpenTelemetry senden. Laut GitHub enthalten sie standardmäßig keine Prompts, Antworten oder Tool-Argumente. Das muss jemand ausdrücklich einschalten. Die Daten gehen an einen Endpunkt, den ihr selbst festlegt, oder in eine lokale Datei. Admins können das über den Block `telemetry` in den Managed Settings vorgeben. Mit `lockCaptureContent` verhindern sie, dass jemand lokal das Aufzeichnen von Inhalten einschaltet.

    - Unklar

12. Dürfen Entwickler und die Factory persönliche Fine-grained Tokens nutzen?

    Ohne Browser-Login, etwa in einer Pipeline, meldet sich Copilot CLI mit einem Token aus einer Umgebungsvariable an: `COPILOT_GITHUB_TOKEN`, `GH_TOKEN` oder `GITHUB_TOKEN`. Laut GitHub geht das mit einem Fine-grained Personal Access Token mit der Berechtigung „Copilot Requests“. Diese Berechtigung gibt es nur bei Tokens, die einer Person gehören, nicht einer Organisation. Klassische Tokens unterstützt Copilot CLI nicht.

    Die Factory läuft also mit dem Token und der Lizenz einer Person. Ihre Credits zählen auf diese Lizenz, sie arbeitet mit deren Rechten, und sie hört auf zu laufen, wenn die Person geht oder das Token abläuft. Darum die Frage, ob das erlaubt ist, und Frage 13 nach einem eigenen Konto.

    - Unklar

13. Kann die Factory ein eigenes Konto mit Lizenz bekommen?

    - Hängt vom DevOps ab
    - Es gibt schon einen DevOps-Bot als eigenen Nutzer

## Atlassian und Bitbucket

14. Wer verwaltet den Atlassian-MCP-Server? Sind API-Tokens erlaubt? Sind Schreibrechte für Jira und Bitbucket an?
    - Ja, Authentifizierung über Browser-Login

15. Welcher Bitbucket-Plan? Merge Checks und Deployment-Rechte brauchen Premium.
    - Merge Checks sind erlaubt

16. Wer darf auf geschützten Branches freigeben und mergen? Wer darf Jira-Automation-Flows ändern?
    - Spryker: Nicht direkt auf master pushen, mergen nach develop für viele erlaubt, Merge nach master nur von release
    - Front End: Manche dürfen auf develop force-pushen, master geschützt
    - Java/GCP: main ist geschützt, nur technischer Nutzer darf darauf pushen (weil noch Release Version hochzählen)

