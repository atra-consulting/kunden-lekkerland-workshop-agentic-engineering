# Live-Demo 2: Zu vage, dann konkret

Tag 2, 09:15. Karsten setzt ein vages Ticket auf „Bereit“. Die Bereitschaftsprüfung lehnt es ab. Dann macht er es konkret, und es kommt durch.

- Ticket: [FLAB-40 „Suche verbessern“](https://betterprojectsfaster.atlassian.net/browse/FLAB-40), Label `sdd-openspec`
- Läufe: [Pipelines](https://bitbucket.org/factory-lab/factory-lab/pipelines)
- Die Kriterien: [`factory/readiness.md`](https://bitbucket.org/factory-lab/factory-lab/src/factory-base/factory/readiness.md), erklärt in [Ticket-Bereitschaft](../../02-agent-factory/bedienung/ticket-bereitschaft.md)

Den Status ändert ihr im Ticket über den Statusknopf neben dem Titel. Direkte Links auf einen Übergang gibt es in Jira Cloud nicht.

## Teil 1: Abgelehnt

| Schritt | Status danach | Wer | Was passiert | Wo ihr es seht |
|---|---|---|---|---|
| 1 | Definition | Mensch | Das Ticket: „Die Suche im Blog soll besser werden. Leser finden oft nicht, was sie suchen.“ | [FLAB-40](https://betterprojectsfaster.atlassian.net/browse/FLAB-40) |
| 2 | Bereit | Mensch | Übergang **„Bereit“**. Flow 1 startet `factory-spec` | [Pipelines](https://bitbucket.org/factory-lab/factory-lab/pipelines) |
| 3 | Bereit | Factory | Lauf 1: Copilot prüft Ticket und Code. Urteil: nicht bereit. OpenSpec läuft gar nicht erst | das Protokoll des Laufs |
| 4 | In Arbeit, dann Klärung nötig | `factory-bot` | Kommentar `FACTORY-NOT-READY v1`, erwartet: `missing_detail` und `untestable`, dazu Fragen. Keine Spec, kein Code, kein Branch | Kommentar in [FLAB-40](https://betterprojectsfaster.atlassian.net/browse/FLAB-40) |

Das dauert etwa eine bis zwei Minuten und kostet etwa 10 Credits.

## Teil 2: Konkret

| Schritt | Status danach | Wer | Was passiert |
|---|---|---|---|
| 5 | Klärung nötig | Mensch | Titel und Beschreibung ersetzen, Text unten. Die Fragen beantwortet ihr in der Beschreibung, nicht im Kommentar |
| 6 | Bereit | Mensch | Übergang **„Bereit“**. Neuer Lauf, neue Prüfung |
| 7 | Wartet | `factory-bot` | Kommentar `FACTORY-SPEC v1` mit „Readiness check: passed“. Weiter wie in [Live-Demo 1](demo-durchlauf.md) ab Schritt 5 |

Titel: `Suche findet Beiträge auch über den Autornamen`

Beschreibung:

```text
Die Blog-Suche (Suchfeld im Header und Live-Suche, beide über PostRepository::findBySearchQuery) findet Beiträge heute nur über den Titel. Sie soll Beiträge auch über den vollständigen Namen des Autors finden (User::fullName, etwa Jane Doe).

Akzeptanzkriterien:
1. Eine Suche nach "Jane" liefert mindestens einen Beitrag, und jeder Treffer hat Jane Doe als Autor. Die Fixtures legen den ersten Beitrag immer mit Jane Doe als Autorin an.
2. Suchen nach Wörtern im Titel liefern dieselben Treffer wie bisher. Der bestehende Test testAjaxSearch bleibt unverändert grün.
3. Ein neuer PHPUnit-Test in tests/Controller/BlogControllerTest.php prüft Kriterium 1 über /en/blog/search.

Keine Änderung an Fixtures, Konfiguration oder Paketen.
```

## Was ihr daran seht

- **Die Prüfung liest den Code.** Im Lab nannte die Ablehnung die drei Stellen, an denen gesucht wird.
- **Konkret heißt: Seite, Ergebnis, Test.** Die zweite Fassung nennt die Methode, das erwartete Ergebnis, einen Test und was unverändert bleibt.
- **Es kann mehr als eine Runde brauchen.** Im Lab ([FLAB-31](https://betterprojectsfaster.atlassian.net/browse/FLAB-31)) lehnte die Prüfung eine Zwischenfassung noch einmal ab: Sie hätte einen bestehenden Test gebrochen (`contradicts_code`). Die Prüfung ist ein Modellaufruf, keine feste Regel.
