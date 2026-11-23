#!/usr/bin/env python3
"""Merkt sich den Arbeitsstand eines Git-Repos und stellt ihn nach dem Skill wieder her.

Teil des Skills ticket-schreiben. Nur Python-Standardbibliothek. Aufruf immer mit `python3 -I`.

    python3 -I arbeitsstand.py merken       # vor der Arbeit mit dem Framework
    python3 -I arbeitsstand.py zeigen       # was aufraeumen ändern würde
    python3 -I arbeitsstand.py aufraeumen --ja

`aufraeumen` macht nur diese Dinge rückgängig:

- neue, ungetrackte Dateien, die beim Merken noch nicht da waren, löschen;
- neue, von Git ignorierte Dateien in den Framework-Ordnern löschen (specs/, openspec/, _bmad-output/, .specify/);
- getrackte Dateien, die beim Merken unverändert waren, auf den Stand von HEAD zurücksetzen;
- zurück auf den gemerkten Branch wechseln und neue Branches ohne eigene Commits löschen.

Neue Commits auf dem gemerkten Branch fasst das Skript nicht an. Es meldet sie und endet mit Exit-Code 1.
Der gemerkte Stand liegt in `.git/ticket-schreiben-stand.json`, also außerhalb des Arbeitsbaums.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys

STAND_DATEI = "ticket-schreiben-stand.json"
FRAMEWORK_ORDNER = ("specs", "openspec", "_bmad-output", ".specify")


class Fehler(Exception):
    pass


def git(*args, cwd=None, ok=(0,)):
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True)
    if r.returncode not in ok:
        raise Fehler(f"git {' '.join(args)} ist fehlgeschlagen: {r.stderr.decode('utf-8', 'replace').strip()}")
    return r.stdout.decode("utf-8", "surrogateescape")


def wurzel():
    try:
        return git("rev-parse", "--show-toplevel").strip()
    except Fehler:
        raise Fehler("Kein Git-Repository. Starte den Skill im Projektordner.")


def stand_pfad(root):
    p = git("rev-parse", "--git-path", STAND_DATEI, cwd=root).strip()
    return p if os.path.isabs(p) else os.path.join(root, p)


def status_eintraege(root):
    """git status als {pfad: xy}. Ignorierte Dateien fehlen hier."""
    roh = git("status", "--porcelain=v1", "-z", "--untracked-files=all", cwd=root)
    teile = roh.split("\0")
    out = {}
    i = 0
    while i < len(teile):
        e = teile[i]
        i += 1
        if len(e) < 4:
            continue
        xy, pfad = e[:2], e[3:]
        out[pfad] = xy
        if xy[0] in "RC":
            i += 1  # der alte Pfad folgt als eigener Eintrag
    return out


def framework_dateien(root):
    """Alle Dateien in den Framework-Ordnern, auch ignorierte, als Pfade relativ zur Wurzel."""
    out = set()
    for ordner in FRAMEWORK_ORDNER:
        basis = os.path.join(root, ordner)
        if not os.path.isdir(basis):
            continue
        for d, _, dateien in os.walk(basis):
            for name in dateien:
                out.add(os.path.relpath(os.path.join(d, name), root).replace(os.sep, "/"))
    return out


def framework_unterordner(root):
    """Alle Ordner in den Framework-Ordnern, einschließlich der Framework-Ordner selbst."""
    out = set()
    for ordner in FRAMEWORK_ORDNER:
        basis = os.path.join(root, ordner)
        if not os.path.isdir(basis):
            continue
        for d, _, _ in os.walk(basis):
            out.add(os.path.relpath(d, root).replace(os.sep, "/"))
    return out


def neue_leere_ordner(root, alt):
    """Neue Ordner in den Framework-Ordnern, in denen keine Datei liegt. Git zeigt sie nicht an."""
    vorher = set(alt.get("framework_ordner", []))
    leer = []
    for d in sorted(framework_unterordner(root) - vorher, key=len, reverse=True):
        voll = os.path.join(root, d)
        if not any(dateien for _, _, dateien in os.walk(voll)):
            leer.append(d)
    return leer


def getrackt(root):
    return set(git("ls-files", "-z", cwd=root).split("\0")) - {""}


def branch(root):
    name = git("symbolic-ref", "--short", "-q", "HEAD", cwd=root, ok=(0, 1)).strip()
    return name or None


def branches(root):
    return {z.split(" ", 1)[0]: z.split(" ", 1)[1]
            for z in git("for-each-ref", "--format=%(refname:short) %(objectname)", "refs/heads", cwd=root).splitlines()}


def aufnehmen(root):
    return {
        "root": root,
        "branch": branch(root),
        "head": git("rev-parse", "HEAD", cwd=root).strip(),
        "branches": branches(root),
        "status": status_eintraege(root),
        "framework_dateien": sorted(framework_dateien(root)),
        "framework_ordner": sorted(framework_unterordner(root)),
    }


def merken(root):
    stand = aufnehmen(root)
    pfad = stand_pfad(root)
    with open(pfad, "w", encoding="utf-8") as f:
        json.dump(stand, f, ensure_ascii=False, indent=1)
    print(f"Gemerkt: Branch {stand['branch'] or '(losgelöst)'}, HEAD {stand['head'][:10]}.")
    if stand["status"]:
        print(f"Achtung: {len(stand['status'])} Datei(en) sind schon geändert oder neu. Sie bleiben, wie sie sind:")
        for p, xy in sorted(stand["status"].items())[:20]:
            print(f"  {xy} {p}")
        return 3
    print("Der Arbeitsbaum ist sauber.")
    return 0


def lade(root):
    pfad = stand_pfad(root)
    try:
        with open(pfad, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise Fehler("Kein gemerkter Stand. Rufe zuerst 'merken' auf.")


def plan(root, alt):
    """Was aufraeumen tun würde."""
    jetzt = aufnehmen(root)
    neu_ungetrackt = sorted(p for p, xy in jetzt["status"].items() if xy == "??" and p not in alt["status"])
    tracked = getrackt(root)
    neu_ignoriert = sorted(set(jetzt["framework_dateien"]) - set(alt["framework_dateien"])
                           - set(neu_ungetrackt) - tracked)
    zuruecksetzen = sorted(p for p, xy in jetzt["status"].items() if xy != "??" and p not in alt["status"])
    schon_geaendert = sorted(p for p in jetzt["status"] if p in alt["status"] and jetzt["status"][p] != alt["status"][p])
    neue_branches = sorted(b for b in jetzt["branches"] if b not in alt["branches"])
    return {
        "loeschen": neu_ungetrackt + neu_ignoriert,
        "zuruecksetzen": zuruecksetzen,
        "branch_wechsel": alt["branch"] if alt["branch"] and jetzt["branch"] != alt["branch"] else None,
        "neue_branches": neue_branches,
        "neue_commits": alt["branch"] is not None and jetzt["branches"].get(alt["branch"]) not in (None, alt["head"]),
        "vorher_geaendert_und_jetzt_anders": schon_geaendert,
    }


def zeigen(root, p):
    leer = True
    if p["branch_wechsel"]:
        print(f"Zurück auf Branch: {p['branch_wechsel']}")
        leer = False
    for b in p["neue_branches"]:
        print(f"Branch löschen: {b}")
        leer = False
    for x in p["loeschen"]:
        print(f"Löschen: {x}")
        leer = False
    for x in p["zuruecksetzen"]:
        print(f"Zurücksetzen: {x}")
        leer = False
    if p["neue_commits"]:
        print("Achtung: Auf dem gemerkten Branch gibt es neue Commits. Das Skript fasst sie nicht an.")
    for x in p["vorher_geaendert_und_jetzt_anders"]:
        print(f"Achtung: {x} war schon vorher geändert und ist jetzt anders. Das Skript fasst die Datei nicht an.")
    if leer:
        print("Nichts aufzuräumen.")


def leere_ordner_entfernen(root, pfad):
    d = os.path.dirname(os.path.join(root, pfad))
    while os.path.abspath(d) != os.path.abspath(root):
        try:
            os.rmdir(d)
        except OSError:
            return
        d = os.path.dirname(d)


def im_baum(root, pfad):
    voll = os.path.realpath(os.path.join(root, pfad))
    return voll.startswith(os.path.realpath(root) + os.sep)


def aufraeumen(root, alt, p):
    if p["branch_wechsel"]:
        git("switch", p["branch_wechsel"], cwd=root)
        print(f"Zurück auf Branch: {p['branch_wechsel']}")
    for x in p["zuruecksetzen"]:
        git("restore", "--source=HEAD", "--staged", "--worktree", "--", x, cwd=root, ok=(0, 1))
        if os.path.lexists(os.path.join(root, x)) and x not in getrackt(root):
            os.remove(os.path.join(root, x))  # neu hinzugefügt (git add), aber nicht in HEAD
        print(f"Zurückgesetzt: {x}")
    for x in p["loeschen"]:
        if not im_baum(root, x):
            print(f"Übersprungen (außerhalb des Repos): {x}")
            continue
        voll = os.path.join(root, x)
        if os.path.isdir(voll) and not os.path.islink(voll):
            shutil.rmtree(voll)
        elif os.path.lexists(voll):
            os.remove(voll)
        leere_ordner_entfernen(root, x)
        print(f"Gelöscht: {x}")
    for d in neue_leere_ordner(root, alt):  # tiefste zuerst
        try:
            os.rmdir(os.path.join(root, d))
            print(f"Leeren Ordner gelöscht: {d}")
        except OSError:
            pass
    for b in p["neue_branches"]:
        r = subprocess.run(["git", "branch", "-d", b], cwd=root, capture_output=True)
        print(f"Branch gelöscht: {b}" if r.returncode == 0
              else f"Branch nicht gelöscht, er hat eigene Commits: {b}")
    rest = plan(root, alt)
    probleme = rest["neue_commits"] or rest["loeschen"] or rest["zuruecksetzen"] or rest["branch_wechsel"]
    if probleme:
        print("Nicht alles ließ sich zurücksetzen:")
        zeigen(root, rest)
        return 1
    os.remove(stand_pfad(root))
    print("Fertig. Der Arbeitsstand ist wie beim Merken.")
    return 0


def main(argv=None):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    ap = argparse.ArgumentParser(prog="arbeitsstand.py", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="befehl", required=True)
    sub.add_parser("merken")
    sub.add_parser("zeigen")
    au = sub.add_parser("aufraeumen")
    au.add_argument("--ja", action="store_true", help="wirklich ändern; ohne --ja nur zeigen")
    args = ap.parse_args(argv)
    try:
        root = wurzel()
        if args.befehl == "merken":
            return merken(root)
        alt = lade(root)
        p = plan(root, alt)
        if args.befehl == "zeigen" or not args.ja:
            zeigen(root, p)
            return 1 if p["neue_commits"] else 0
        return aufraeumen(root, alt, p)
    except Fehler as e:
        print(f"Fehler: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
