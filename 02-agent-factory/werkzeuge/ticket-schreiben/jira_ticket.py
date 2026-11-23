#!/usr/bin/env python3
"""Legt ein Jira-Ticket aus einem Entwurf an. Teil des Skills ticket-schreiben.

Nur Python-Standardbibliothek. Aufruf immer mit `python3 -I` (Windows: `py -3 -I`).

    python3 -I jira_ticket.py pruefen --config .github/ticket-schreiben.json
    python3 -I jira_ticket.py anlegen --config .github/ticket-schreiben.json --entwurf ticket-entwurf.md [--dry-run]

Zugangsdaten kommen nur aus Umgebungsvariablen:

    JIRA_BASE_URL   https://<site>.atlassian.net (Cloud) oder die Server-URL (Data Center)
    JIRA_EMAIL      nur Cloud: die E-Mail-Adresse des Kontos
    JIRA_API_TOKEN  Cloud: API-Token. Data Center: Personal Access Token.

Ist JIRA_EMAIL gesetzt, gilt Jira Cloud: Basic-Auth, REST API 3, Beschreibung als ADF.
Sonst gilt Data Center: Bearer-Token, REST API 2, Beschreibung als Wiki-Markup.

Das Skript gibt das Token nie aus. Fehlertexte von Jira werden vor der Ausgabe bereinigt.
"""

import argparse
import base64
import json
import os
import re
import sys
import urllib.error
import urllib.request

FRAMEWORKS = ("speckit", "openspec", "bmad")
KEY_RE = re.compile(r"[A-Z][A-Z0-9]+")
ISSUE_KEY_RE = re.compile(r"[A-Z][A-Z0-9]+-[0-9]+")
LABEL_RE = re.compile(r"[^\s]{1,255}")
SUMMARY_MAX = 255


class Fehler(Exception):
    """Fehler mit Exit-Code. 1: Jira oder Netz. 2: Aufruf, Konfiguration oder Entwurf."""

    def __init__(self, text, code=2):
        super().__init__(text)
        self.code = code


# --- Konfiguration und Umgebung ------------------------------------------------

def lade_config(pfad):
    try:
        with open(pfad, encoding="utf-8") as f:
            cfg = json.load(f)
    except FileNotFoundError:
        raise Fehler(f"Konfiguration fehlt: {pfad}")
    except json.JSONDecodeError as e:
        raise Fehler(f"Konfiguration ist kein gültiges JSON: {pfad} ({e})")
    if not isinstance(cfg, dict):
        raise Fehler(f"Konfiguration muss ein JSON-Objekt sein: {pfad}")
    fw = cfg.get("framework")
    if fw not in FRAMEWORKS:
        raise Fehler(f"'framework' muss einer von {', '.join(FRAMEWORKS)} sein, nicht {fw!r}")
    projekt = cfg.get("jira_project")
    if not isinstance(projekt, str) or not KEY_RE.fullmatch(projekt):
        raise Fehler(f"'jira_project' muss ein Projektschlüssel wie FLAB sein, nicht {projekt!r}")
    typ = cfg.get("issue_type", "Task")
    if not isinstance(typ, str) or not typ.strip():
        raise Fehler("'issue_type' muss ein nicht leerer Text sein")
    labels = cfg.get("labels", [])
    if not isinstance(labels, list) or not all(isinstance(x, str) and LABEL_RE.fullmatch(x) for x in labels):
        raise Fehler("'labels' muss eine Liste von Labels ohne Leerzeichen sein")
    return {"framework": fw, "jira_project": projekt, "issue_type": typ.strip(), "labels": labels}


class Zugang:
    """Liest die Jira-Variablen. Das Token bleibt in diesem Objekt und wird nie ausgegeben."""

    def __init__(self, env=None):
        env = os.environ if env is None else env
        fehlend = [n for n in ("JIRA_BASE_URL", "JIRA_API_TOKEN") if not env.get(n, "").strip()]
        if fehlend:
            raise Fehler("Umgebungsvariable fehlt: " + ", ".join(fehlend)
                         + ". Setze sie in deiner Shell, nicht im Chat (siehe ticket-skill.md).")
        self.base = env["JIRA_BASE_URL"].strip().rstrip("/")
        # Das Token geht nur verschlüsselt raus. http:// nur für einen lokalen Testserver.
        if not (self.base.lower().startswith("https://")
                or re.match(r"http://(127\.0\.0\.1|localhost)(:[0-9]+)?(/|$)", self.base.lower())):
            raise Fehler("JIRA_BASE_URL muss mit https:// beginnen")
        self.email = env.get("JIRA_EMAIL", "").strip()
        self._token = env["JIRA_API_TOKEN"].strip()
        self.cloud = bool(self.email)
        self.api = "3" if self.cloud else "2"

    @property
    def art(self):
        return "Jira Cloud (Basic-Auth, API 3)" if self.cloud else "Jira Data Center (Bearer-Token, API 2)"

    def auth_header(self):
        if self.cloud:
            return "Basic " + base64.b64encode(f"{self.email}:{self._token}".encode()).decode()
        return "Bearer " + self._token

    def bereinigen(self, text):
        """Entfernt das Token und seine Basic-Auth-Form aus einem Text."""
        for geheim in {self._token, self.auth_header().split(" ", 1)[1]}:
            if geheim:
                text = text.replace(geheim, "***")
        return text

    def aufruf(self, methode, pfad, body=None, ok=(200, 201)):
        url = f"{self.base}/rest/api/{self.api}{pfad}"
        daten = None if body is None else json.dumps(body).encode("utf-8")
        req = urllib.request.Request(url, data=daten, method=methode)
        req.add_header("Authorization", self.auth_header())
        req.add_header("Accept", "application/json")
        if daten is not None:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                roh, status = r.read(), r.status
        except urllib.error.HTTPError as e:
            roh, status = e.read(), e.code
        except (urllib.error.URLError, OSError) as e:
            raise Fehler(f"Jira nicht erreichbar ({self.base}): {self.bereinigen(str(e))}", code=1)
        if status not in ok:
            raise Fehler(f"{methode} /rest/api/{self.api}{pfad.split('?')[0]} -> HTTP {status}: "
                         + jira_fehlertext(self.bereinigen(roh.decode("utf-8", errors="replace"))), code=1)
        try:
            return json.loads(roh) if roh.strip() else {}
        except json.JSONDecodeError:
            raise Fehler(f"Jira hat kein JSON geliefert (HTTP {status}). Stimmt JIRA_BASE_URL?", code=1)


def jira_fehlertext(roh):
    """Macht aus Jiras Fehler-JSON eine Zeile. Fällt auf den gekürzten Rohtext zurück."""
    try:
        d = json.loads(roh)
    except json.JSONDecodeError:
        return roh.strip()[:300] or "(leere Antwort)"
    teile = list(d.get("errorMessages") or [])
    for feld, text in (d.get("errors") or {}).items():
        teile.append(f"{feld}: {text}")
    return "; ".join(str(t) for t in teile)[:600] or roh.strip()[:300]


# --- Entwurf ------------------------------------------------------------------

def lese_entwurf(pfad):
    """Liest den Entwurf. Die erste Zeile '# ...' ist die Zusammenfassung, der Rest die Beschreibung."""
    try:
        with open(pfad, encoding="utf-8") as f:
            zeilen = f.read().replace("\r\n", "\n").split("\n")
    except FileNotFoundError:
        raise Fehler(f"Entwurf fehlt: {pfad}")
    while zeilen and not zeilen[0].strip():
        zeilen.pop(0)
    if not zeilen or not zeilen[0].startswith("# "):
        raise Fehler("Die erste Zeile des Entwurfs muss '# <Zusammenfassung>' sein")
    summary = zeilen[0][2:].strip()
    if not summary:
        raise Fehler("Die Zusammenfassung ist leer")
    if len(summary) > SUMMARY_MAX:
        raise Fehler(f"Die Zusammenfassung ist länger als {SUMMARY_MAX} Zeichen")
    beschreibung = "\n".join(zeilen[1:]).strip("\n")
    if not beschreibung.strip():
        raise Fehler("Die Beschreibung ist leer")
    return summary, beschreibung


def bloecke(text):
    """Zerlegt die Beschreibung in Blöcke: ('h', text), ('p', text), ('ul', [items])."""
    out = []
    absatz = []

    def absatz_ende():
        if absatz:
            out.append(("p", " ".join(absatz)))
            absatz.clear()

    for zeile in text.split("\n"):
        s = zeile.strip()
        if not s:
            absatz_ende()
            continue
        m = re.match(r"#{2,6}\s+(.*)", s)
        if m:
            absatz_ende()
            out.append(("h", m.group(1).strip()))
            continue
        m = re.match(r"[-*]\s+(.*)", s)
        if m:
            absatz_ende()
            if out and out[-1][0] == "ul":
                out[-1][1].append(m.group(1).strip())
            else:
                out.append(("ul", [m.group(1).strip()]))
            continue
        if out and out[-1][0] == "ul" and zeile.startswith((" ", "\t")) and not absatz:
            # Fortsetzungszeile eines Listenpunkts
            out[-1][1][-1] += " " + s
            continue
        absatz.append(s)
    absatz_ende()
    return out


def _inline_adf(text):
    """Text mit `Code` in ADF-Textknoten. Code bekommt die Markierung 'code'."""
    knoten = []
    for i, teil in enumerate(re.split(r"`([^`]+)`", text)):
        if not teil:
            continue
        k = {"type": "text", "text": teil}
        if i % 2 == 1:
            k["marks"] = [{"type": "code"}]
        knoten.append(k)
    return knoten or [{"type": "text", "text": " "}]


def als_adf(text):
    inhalt = []
    for art, wert in bloecke(text):
        if art == "h":
            inhalt.append({"type": "heading", "attrs": {"level": 3}, "content": _inline_adf(wert)})
        elif art == "p":
            inhalt.append({"type": "paragraph", "content": _inline_adf(wert)})
        else:
            inhalt.append({"type": "bulletList", "content": [
                {"type": "listItem", "content": [{"type": "paragraph", "content": _inline_adf(x)}]} for x in wert]})
    return {"type": "doc", "version": 1, "content": inhalt}


def als_wiki(text):
    def inline(s):
        return re.sub(r"`([^`]+)`", r"{{\1}}", s)

    teile = []
    for art, wert in bloecke(text):
        if art == "h":
            teile.append(f"h3. {inline(wert)}")
        elif art == "p":
            teile.append(inline(wert))
        else:
            teile.append("\n".join(f"* {inline(x)}" for x in wert))
    return "\n\n".join(teile)


def labels_fuer(cfg, extra):
    labels = [f"sdd-{cfg['framework']}"] + list(cfg["labels"]) + list(extra or [])
    for x in labels:
        if not LABEL_RE.fullmatch(x):
            raise Fehler(f"Ungültiges Label: {x!r} (keine Leerzeichen)")
    andere_sdd = [x for x in labels if x.startswith("sdd-") and x != f"sdd-{cfg['framework']}"]
    if andere_sdd:
        raise Fehler(f"Genau ein sdd-Label ist erlaubt. Zusätzlich gefunden: {', '.join(andere_sdd)}")
    return list(dict.fromkeys(labels))


def payload(cfg, summary, beschreibung, cloud, extra_labels=None, typ=None, parent=None):
    felder = {
        "project": {"key": cfg["jira_project"]},
        "issuetype": {"name": typ or cfg["issue_type"]},
        "summary": summary,
        "labels": labels_fuer(cfg, extra_labels),
        "description": als_adf(beschreibung) if cloud else als_wiki(beschreibung),
    }
    if parent:
        if not ISSUE_KEY_RE.fullmatch(parent):
            raise Fehler(f"--parent muss ein Ticket-Schlüssel wie FLAB-12 sein, nicht {parent!r}")
        felder["parent"] = {"key": parent}
    return {"fields": felder}


# --- Befehle ------------------------------------------------------------------

def cmd_pruefen(args, env=None):
    cfg = lade_config(args.config)
    z = Zugang(env)
    print(f"Jira: {z.base} ({z.art})")
    ich = z.aufruf("GET", "/myself")
    print(f"Angemeldet als: {ich.get('displayName') or ich.get('name') or '(ohne Namen)'}")
    projekt = z.aufruf("GET", f"/project/{cfg['jira_project']}")
    print(f"Projekt: {projekt.get('key')} ({projekt.get('name')})")
    typen = [t.get("name") for t in projekt.get("issueTypes", []) if not t.get("subtask")]
    if typen and cfg["issue_type"] not in typen:
        raise Fehler(f"Vorgangstyp {cfg['issue_type']!r} fehlt im Projekt. Vorhanden: {', '.join(typen)}")
    print(f"Vorgangstyp: {cfg['issue_type']}")
    print(f"Labels beim Anlegen: {', '.join(labels_fuer(cfg, []))}")
    print("OK")
    return 0


def cmd_anlegen(args, env=None):
    cfg = lade_config(args.config)
    summary, beschreibung = lese_entwurf(args.entwurf)
    if args.dry_run:
        cloud = bool((os.environ if env is None else env).get("JIRA_EMAIL", "").strip())
        daten = payload(cfg, summary, beschreibung, cloud, args.label, args.typ, args.parent)
        print(json.dumps(daten, ensure_ascii=False, indent=2))
        print("Probelauf: nichts angelegt.", file=sys.stderr)
        return 0
    z = Zugang(env)
    daten = payload(cfg, summary, beschreibung, z.cloud, args.label, args.typ, args.parent)
    antwort = z.aufruf("POST", "/issue", daten, ok=(200, 201))
    key = antwort.get("key")
    if not key:
        raise Fehler("Jira hat keinen Ticket-Schlüssel zurückgegeben", code=1)
    print(f"Angelegt: {key}")
    print(f"URL: {z.base}/browse/{key}")
    try:
        status = z.aufruf("GET", f"/issue/{key}?fields=status,labels")["fields"]
        print(f"Status: {status['status']['name']}")
        print(f"Labels: {', '.join(status.get('labels', []))}")
    except (Fehler, KeyError, TypeError):
        print("Status: konnte nicht gelesen werden (das Ticket existiert trotzdem)")
    return 0


def parser():
    p = argparse.ArgumentParser(prog="jira_ticket.py", description="Legt ein Ticket für die Agent Factory in Jira an.")
    sub = p.add_subparsers(dest="befehl", required=True)
    pr = sub.add_parser("pruefen", help="Zugang, Projekt und Vorgangstyp prüfen")
    pr.add_argument("--config", default=".github/ticket-schreiben.json")
    an = sub.add_parser("anlegen", help="Ticket aus dem Entwurf anlegen")
    an.add_argument("--config", default=".github/ticket-schreiben.json")
    an.add_argument("--entwurf", default="ticket-entwurf.md")
    an.add_argument("--label", action="append", default=[], help="weiteres Label, mehrfach möglich")
    an.add_argument("--typ", help="Vorgangstyp statt dem aus der Konfiguration, z. B. Epic")
    an.add_argument("--parent", help="übergeordnetes Ticket, z. B. das Epic")
    an.add_argument("--dry-run", action="store_true", help="nur die Anfrage zeigen, nichts anlegen")
    return p


def main(argv=None, env=None):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    args = parser().parse_args(argv)
    try:
        return (cmd_pruefen if args.befehl == "pruefen" else cmd_anlegen)(args, env)
    except Fehler as e:
        print(f"Fehler: {e}", file=sys.stderr)
        return e.code


if __name__ == "__main__":
    sys.exit(main())
