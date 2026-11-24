# Copilot absichern

Kurzfassung für Mittwoch, 25. November 2026. Stand: 24. November 2026, Entwurf.

Grundlage: die Dokumentation von GitHub, Microsoft und Atlassian vom November 2026 und unsere Tests im Factory-Lab vom 17. bis 19. November. Die meisten Angaben sind Herstellerangaben. Niemand hat sie für euch getestet.

## Die Frage

Kann ein Prompt, ein Skill oder ein Ticket-Text Copilot dazu bringen, Schaden anzurichten? Zum Beispiel einen Pull Request mergen, ein Ticket freigeben oder Secrets lesen. Und was hilft dagegen?

## Kurzfassung

- **Anweisungen kommen von überall.** Copilot liest Anweisungsdateien wie `AGENTS.md`, `.github/copilot-instructions.md` und `CLAUDE.md`. Dazu kommen Skills aus `.github/skills` und `.agents/skills`, eigene Agenten aus `.github/agents/` und Plugins aus den Repo-Einstellungen. Auch Dateien, Webseiten, Ticket-Texte und Tool-Ergebnisse können Anweisungen einschleusen.
- **Beim Review gilt der Branch des Pull Requests.** Copilot liest Anweisungen und Skills aus dem Branch, der gemergt werden soll, nicht aus dem Ziel-Branch. Ein Pull Request kann also ändern, was sein Reviewer gesagt bekommt.
- **Copilot kann blockieren, aber nur als Filter auf den Befehlstext.** Deny-Regeln, `--deny-tool` und Hooks prüfen, wie ein Befehl aussieht. Ein Befehl, der anders aussieht, kommt durch. Läuft ein Hook in einen Timeout, lässt Copilot den Befehl zu.
- **Die Hersteller nennen mehrere ihrer Schutzmechanismen selbst "best effort".** Das gilt für vertrauenswürdige Ordner, Content Exclusion, die Sandbox für die eingebauten Datei-Tools, den Lockdown des GitHub-MCP-Servers und das Befehls-Matching in VS Code.
- **Zentrale Richtlinien können ausfallen.** Kann die CLI die Richtlinie nicht laden und hat sie keinen Cache, startet sie seit Version 1.0.78 ohne die zentrale Einschränkung. Die Einstellung `forceRemoteSettingsRefresh` verhindert das.
- **Copilot handelt als ihr.** Auf eurem Laptop nutzt Copilot euren Atlassian-Login, eure Git-Zugangsdaten und euren SSH-Agent. Jira und Bitbucket sehen euch, nicht "einen Agenten".
- **Deshalb gehören die wichtigen Sperren außerhalb von Copilot.** Das sind Bitbucket-Branch-Regeln, Einschränkungen für Jira-Übergänge, die Rechte im Atlassian-MCP-Server und Tokens mit wenig Rechten. Copilot-Einstellungen sind die zweite Linie.

## Beispiel: Ein Skill will einen Pull Request mergen

| Weg | Was ihn stoppt |
|---|---|
| Ein Bitbucket-Token liegt in eurer Shell. Copilot mergt als ihr. | Nur eine Bitbucket-Branch-Regel: Mergen nur per Pull Request und nur für eine kleine Gruppe. Merge Checks mit Freigaben und Builds brauchen Bitbucket Premium. |
| Der Atlassian-MCP-Server hat Schreibrechte für Bitbucket. Copilot ruft `mergeBitbucketRepoPullRequest` auf. | Schreibrechte für Bitbucket im Atlassian-Admin abschalten. `--deny-tool` wirkt nur je Sitzung und ist ein Filter. |
| Browser Use steuert euren Browser, in dem ihr bei Bitbucket eingeloggt seid. | `features.browserUse: false` zentral setzen. |

Wer Specs freigeben und Pull Requests mergen darf und Copilot mit Schreibrechten verbindet, legt Freigabe 1 und Freigabe 2 in eine einzige Sitzung. Eine eingeschleuste Anweisung überwindet dann beide.

## Sechs Punkte für euch, ohne Admin-Rechte

1. Startet Copilot im Projektordner, nie im Home-Ordner.
2. Öffnet fremde Repos in VS Code im Restricted Mode. In der CLI lest ihr vorher `.github/hooks/`, `.github/agents/`, `.claude/agents/`, `.mcp.json`, `.github/mcp.json`, `.claude/settings.json` und `.github/copilot/settings.json`. Achtet dort auf `enabledPlugins` und `extraKnownMarketplaces`.
3. Startet Copilot aus einer Shell ohne `GH_TOKEN`, `GITHUB_TOKEN`, Bitbucket- oder Atlassian-Tokens. Ein Token in der Umgebung ersetzt still euren gespeicherten Login.
4. Prüft, was Spec Kit, OpenSpec oder BMad in `.github/skills` oder `.agents/skills` installieren, bevor ihr es committet.
5. Braucht die CLI ein Token, nehmt ein Fine-grained Token mit nur der Berechtigung "Copilot Requests". Fragt vorher eure Admins.
6. Kein `--yolo`, kein `--allow-all` und in VS Code kein `chat.tools.global.autoApprove`. `/reset-allowed-tools` löscht gespeicherte Freigaben für den aktuellen Ordner.

**Wer Specs freigibt oder Pull Requests mergt:** Lasst keine Atlassian-Zugangsdaten in Reichweite von Copilot. Also kein Rovo-MCP mit Schreibrechten, kein Jira-Token in Konfigurationsdateien, Skripten oder `~/.netrc` und kein Browser Use mit eurem Atlassian-Login.

## Was eure Admins tun können

**Phase 0, Bestand aufnehmen:** Wer verwaltet Copilot, Atlassian und Bitbucket? Welcher Plan? Welche IDEs? Welche Richtlinien gelten heute?

**Phase 1, Sperren außerhalb von Copilot:**

- **Bitbucket:** Auf `main`, `develop` und Release-Branches keine direkten Pushes. Mergen nur per Pull Request, nur für eine kleine Gruppe. Kein Löschen, kein Umschreiben der History.
- **Bitbucket-Secrets:** Secured Variables kann jeder lesen, der Schreibrechte am Repo hat. Ein neuer Branch mit eigener Pipeline-Datei kommt also an die Secrets.
- **Atlassian-MCP:** `delete_jira` und `manage_jira` bleiben aus. Schreibrechte für Jira und Bitbucket abschalten, wenn kein Team sie braucht. Nur OAuth, keine API-Tokens.
- **Jira:** Die Freigabe-Übergänge nur für benannte Personen erlauben.

**Phase 2, Copilot-Einstellungen, erst in einer Pilotgruppe:**

- `forceRemoteSettingsRefresh: true`, verteilt per MDM.
- Bypass-Modus und Assisted-Modus abschalten, Standardmodus `manual`.
- Computer Use und Browser Use abschalten.
- Nur zentral verwaltete Hooks und MCP-Server erlauben. Die MCP-Allowlist nach URL oder Befehl, nicht nach Namen.
- `strictKnownMarketplaces: []`, damit Repos keine Plugins installieren.
- In VS Code Auto-Approve per Richtlinie abschalten.

So sieht der Kern der zentralen Einstellungen aus:

```json
{
  "forceRemoteSettingsRefresh": true,
  "features": { "computerUse": false, "browserUse": false },
  "permissions": {
    "disableBypassPermissionsMode": "disable",
    "disableAssistedPermissionsMode": true,
    "defaultMode": "manual",
    "ask": ["Shell(git push *)"],
    "deny": ["Read(~/.ssh/**)"]
  }
}
```

**Später:** die Sandbox der CLI, getestet auf euren Windows-Laptops, und Content Exclusion als zusätzliche Schicht.

## Was die Factory schon macht

- Copilot läuft als eigener Nutzer `agent`, nur mit dem Copilot-Token. Er hat keinen Zugang zu Jira oder Bitbucket.
- Der Agent liefert nur einen Patch. Die Prüfungen laufen außerhalb des Agenten, die Skripte kommen aus dem Image.
- Auf `factory-base` gibt es keine direkten Pushes. Gemergt wird nur per Pull Request.
- Nur die freigebende Person kann eine Spec freigeben.

**Noch offen:**

- Das Netzwerk des Agenten ist offen. Das hat die höchste Priorität.
- Eine zentrale Einstellungsdatei im Image, die `agent` nicht ändern kann.
- Mehr geschützte Dateien: `AGENTS.md`, `CLAUDE.md`, `.github/`, `.claude/`, `.agents/`, `.vscode/` und `.mcp.json`.
- Das Copilot-Token gehört heute zu einem persönlichen Konto. Besser ist ein eigenes Konto für die Factory.

## Fragen an eure Admins

**Copilot:**

1. Welche IDEs nutzt ihr: VS Code, PhpStorm, andere?
2. Wem gehören die Copilot-Lizenzen und Richtlinien: Lekkerland oder REWE? Wer genehmigt Änderungen?
3. Business oder Enterprise?
4. Ist Copilot CLI freigeschaltet? Ist die Richtlinie "MCP servers in Copilot" an?
5. Gibt es zentrale Einstellungen? Über welchen Weg: vom Server, per MDM oder als Datei?
6. Welche `permissions`-Einstellungen sind gesetzt? Ist der Bypass-Modus aus?
7. Gibt es eine MCP-Allowlist?
8. Welche VS-Code-Richtlinien sind verteilt?
9. Ist die Sandbox Pflicht? Läuft sie auf euren Windows-Laptops?
10. Ist Content Exclusion eingerichtet?
11. Zeichnet die Telemetrie Inhalte auf? Wohin geht sie?
12. Dürfen Entwickler und die Factory persönliche Fine-grained Tokens nutzen? Kann die Factory ein eigenes Konto mit Lizenz bekommen?

**Atlassian und Bitbucket:**

13. Wer verwaltet den Atlassian-MCP-Server? Sind API-Tokens erlaubt? Sind Schreibrechte für Jira und Bitbucket an?
14. Welcher Bitbucket-Plan? Merge Checks und Deployment-Rechte brauchen Premium.
15. Wer darf auf geschützten Branches freigeben und mergen? Wer darf Jira-Automation-Flows ändern?

## Was wir nicht wissen

- Ob Bitbucket-Branch-Regeln auch einen Merge über den Atlassian-MCP-Server stoppen. Wahrscheinlich ja, weil der Server mit euren Rechten arbeitet.
- Ob zentrale Deny-Regeln MCP-Tools benennen können. Die Doku nennt nur Shell-Befehle, Dateien und Domains.
- Ob GitHubs MCP-Richtlinien in der CLI greifen. Die Doku widerspricht sich.
- Ob die Sandbox mit `copilot -p` läuft, und welche Hosts Copilot braucht.

**Das veraltet schnell.** Copilot CLI hatte im November 2026 mehrere Releases pro Woche. Prüft die Angaben vor jeder Änderung neu.
