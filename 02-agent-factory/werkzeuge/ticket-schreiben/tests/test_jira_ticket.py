"""Tests für jira_ticket.py gegen einen lokalen Fake-Jira-Server. Kein Netz nötig.

    python3 -I -m unittest discover -s tests      # im Ordner ticket-schreiben
"""

import base64
import contextlib
import http.server
import io
import json
import os
import sys
import tempfile
import threading
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import jira_ticket as jt  # noqa: E402

TOKEN = "ATATT-geheim-1234567890"
ENTWURF = """# Lesezeit auf der Artikelseite anzeigen

## Ziel
Leser sehen vor dem Lesen, wie lange ein Artikel dauert.

## Akzeptanzkriterien
- Wenn ein Artikel 400 Wörter hat, dann zeigt die Seite `2 Min. Lesezeit`.
- Wenn ein Artikel weniger als 200 Wörter hat,
  dann zeigt die Seite `1 Min. Lesezeit`.

## Nicht Teil des Tickets
- Die Startseite.

## Hinweise
Betroffene Route: /blog/posts/{slug}.
Tests: `./bin/phpunit`.
"""


class FakeJira(http.server.BaseHTTPRequestHandler):
    anfragen = []
    antworten = {}

    def log_message(self, *a):
        pass

    def _antworte(self):
        laenge = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(laenge) if laenge else b""
        FakeJira.anfragen.append({"method": self.command, "path": self.path, "headers": dict(self.headers),
                                  "body": json.loads(body) if body else None})
        status, daten = FakeJira.antworten.get((self.command, self.path.split("?")[0]), (404, {"errorMessages": ["nicht da"]}))
        roh = daten if isinstance(daten, bytes) else json.dumps(daten).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(roh)))
        self.end_headers()
        self.wfile.write(roh)

    do_GET = do_POST = _antworte


class Basis(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = http.server.HTTPServer(("127.0.0.1", 0), FakeJira)
        cls.url = f"http://127.0.0.1:{cls.server.server_port}"
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        FakeJira.anfragen = []
        FakeJira.antworten = {}
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.config = os.path.join(self.tmp.name, "ticket-schreiben.json")
        self.schreibe_config({"framework": "speckit", "jira_project": "FLAB", "issue_type": "Task",
                              "labels": ["test-nacht"]})
        self.entwurf = os.path.join(self.tmp.name, "ticket-entwurf.md")
        with open(self.entwurf, "w", encoding="utf-8") as f:
            f.write(ENTWURF)

    def schreibe_config(self, cfg):
        with open(self.config, "w", encoding="utf-8") as f:
            json.dump(cfg, f)

    def env(self, cloud=True):
        e = {"JIRA_BASE_URL": self.url + "/", "JIRA_API_TOKEN": TOKEN}
        if cloud:
            e["JIRA_EMAIL"] = "bot@example.com"
        return e

    def run_main(self, argv, env):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = jt.main(argv, env)
        return code, out.getvalue(), err.getvalue()


class AuthTest(Basis):
    def test_cloud_nutzt_basic_und_api3(self):
        FakeJira.antworten[("POST", "/rest/api/3/issue")] = (201, {"key": "FLAB-99"})
        FakeJira.antworten[("GET", "/rest/api/3/issue/FLAB-99")] = (200, {"fields": {"status": {"name": "Definition"}, "labels": ["sdd-speckit"]}})
        code, out, err = self.run_main(["anlegen", "--config", self.config, "--entwurf", self.entwurf], self.env(cloud=True))
        self.assertEqual(code, 0, err)
        auth = FakeJira.anfragen[0]["headers"]["Authorization"]
        self.assertEqual(auth, "Basic " + base64.b64encode(f"bot@example.com:{TOKEN}".encode()).decode())
        self.assertIn("Angelegt: FLAB-99", out)
        self.assertIn(f"URL: {self.url}/browse/FLAB-99", out)
        self.assertIn("Status: Definition", out)
        self.assertNotIn(TOKEN, out + err)

    def test_link_nutzt_site_aus_serverinfo(self):
        FakeJira.antworten[("POST", "/rest/api/3/issue")] = (201, {"key": "FLAB-5"})
        FakeJira.antworten[("GET", "/rest/api/3/serverInfo")] = (200, {"baseUrl": "https://lab.atlassian.net"})
        code, out, err = self.run_main(["anlegen", "--config", self.config, "--entwurf", self.entwurf], self.env())
        self.assertEqual(code, 0, err)
        self.assertIn("URL: https://lab.atlassian.net/browse/FLAB-5", out)

    def test_data_center_nutzt_bearer_und_api2(self):
        FakeJira.antworten[("POST", "/rest/api/2/issue")] = (201, {"key": "FLAB-7"})
        FakeJira.antworten[("GET", "/rest/api/2/issue/FLAB-7")] = (200, {"fields": {"status": {"name": "Definition"}}})
        code, out, err = self.run_main(["anlegen", "--config", self.config, "--entwurf", self.entwurf], self.env(cloud=False))
        self.assertEqual(code, 0, err)
        self.assertEqual(FakeJira.anfragen[0]["headers"]["Authorization"], "Bearer " + TOKEN)
        beschreibung = FakeJira.anfragen[0]["body"]["fields"]["description"]
        self.assertIsInstance(beschreibung, str)
        self.assertIn("h3. Ziel", beschreibung)
        self.assertIn("* Die Startseite.", beschreibung)
        self.assertIn("{{./bin/phpunit}}", beschreibung)

    def test_http_nur_lokal(self):
        env = self.env()
        env["JIRA_BASE_URL"] = "http://jira.example.com"
        code, out, err = self.run_main(["pruefen", "--config", self.config], env)
        self.assertEqual(code, 2)
        self.assertIn("https://", err)
        self.assertEqual(FakeJira.anfragen, [])

    def test_fehlende_variablen_nennt_namen_nicht_werte(self):
        code, out, err = self.run_main(["anlegen", "--config", self.config, "--entwurf", self.entwurf],
                                       {"JIRA_BASE_URL": self.url})
        self.assertEqual(code, 2)
        self.assertIn("JIRA_API_TOKEN", err)
        self.assertEqual(FakeJira.anfragen, [])


class PayloadTest(Basis):
    def test_felder_und_labels(self):
        FakeJira.antworten[("POST", "/rest/api/3/issue")] = (201, {"key": "FLAB-1"})
        self.run_main(["anlegen", "--config", self.config, "--entwurf", self.entwurf, "--label", "extra"], self.env())
        felder = FakeJira.anfragen[0]["body"]["fields"]
        self.assertEqual(felder["project"], {"key": "FLAB"})
        self.assertEqual(felder["issuetype"], {"name": "Task"})
        self.assertEqual(felder["summary"], "Lesezeit auf der Artikelseite anzeigen")
        self.assertEqual(felder["labels"], ["sdd-speckit", "test-nacht", "extra"])
        self.assertNotIn("parent", felder)

    def test_adf_struktur(self):
        doc = jt.als_adf(jt.lese_entwurf(self.entwurf)[1])
        self.assertEqual(doc["type"], "doc")
        typen = [b["type"] for b in doc["content"]]
        self.assertEqual(typen, ["heading", "paragraph", "heading", "bulletList", "heading", "bulletList",
                                 "heading", "paragraph"])
        kriterien = doc["content"][3]["content"]
        self.assertEqual(len(kriterien), 2)
        zweites = kriterien[1]["content"][0]["content"]
        self.assertEqual("".join(k["text"] for k in zweites),
                         "Wenn ein Artikel weniger als 200 Wörter hat, dann zeigt die Seite 1 Min. Lesezeit.")
        self.assertEqual(zweites[1], {"type": "text", "text": "1 Min. Lesezeit", "marks": [{"type": "code"}]})
        # Absätze ohne Leerzeile werden zu einem Absatz
        self.assertEqual(doc["content"][7]["content"][0]["text"], "Betroffene Route: /blog/posts/{slug}. Tests: ")

    def test_parent_und_typ(self):
        FakeJira.antworten[("POST", "/rest/api/3/issue")] = (201, {"key": "FLAB-2"})
        self.run_main(["anlegen", "--config", self.config, "--entwurf", self.entwurf, "--typ", "Epic",
                       "--parent", "FLAB-1"], self.env())
        felder = FakeJira.anfragen[0]["body"]["fields"]
        self.assertEqual(felder["issuetype"], {"name": "Epic"})
        self.assertEqual(felder["parent"], {"key": "FLAB-1"})

    def test_epic_ohne_sdd_label(self):
        FakeJira.antworten[("POST", "/rest/api/3/issue")] = (201, {"key": "FLAB-3"})
        self.run_main(["anlegen", "--config", self.config, "--entwurf", self.entwurf, "--typ", "Epic",
                       "--ohne-sdd-label"], self.env())
        self.assertEqual(FakeJira.anfragen[0]["body"]["fields"]["labels"], ["test-nacht"])

    def test_pruefdatei_fuer_local_py(self):
        out = os.path.join(self.tmp.name, "pruef.json")
        code, stdout, err = self.run_main(["pruefdatei", "--config", self.config, "--entwurf", self.entwurf,
                                           "--out", out], {})
        self.assertEqual(code, 0, err)
        self.assertEqual(FakeJira.anfragen, [])
        with open(out, encoding="utf-8") as f:
            d = json.load(f)
        self.assertEqual(sorted(d), ["description", "key", "labels", "summary"])
        self.assertRegex(d["key"], r"^[A-Z][A-Z0-9]+-[0-9]+$")
        self.assertEqual(d["summary"], "Lesezeit auf der Artikelseite anzeigen")
        self.assertEqual(d["labels"], ["sdd-speckit", "test-nacht"])
        # Klartext wie ihn die Factory aus ADF liest: Überschriften und Listenpunkte als eigene Zeilen
        self.assertTrue(d["description"].startswith("Ziel\nLeser sehen vor dem Lesen"))
        self.assertIn("\nWenn ein Artikel 400 Wörter hat, dann zeigt die Seite 2 Min. Lesezeit.\n", d["description"])
        self.assertNotIn("##", d["description"])

    def test_zweites_sdd_label_wird_abgelehnt(self):
        code, _, err = self.run_main(["anlegen", "--config", self.config, "--entwurf", self.entwurf,
                                      "--label", "sdd-bmad"], self.env())
        self.assertEqual(code, 2)
        self.assertIn("Genau ein sdd-Label", err)
        self.assertEqual(FakeJira.anfragen, [])

    def test_dry_run_sendet_nichts(self):
        code, out, _ = self.run_main(["anlegen", "--config", self.config, "--entwurf", self.entwurf, "--dry-run"],
                                     {"JIRA_EMAIL": "x@example.com"})
        self.assertEqual(code, 0)
        self.assertEqual(FakeJira.anfragen, [])
        self.assertEqual(json.loads(out)["fields"]["description"]["type"], "doc")

    def test_entwurf_ohne_titel(self):
        with open(self.entwurf, "w", encoding="utf-8") as f:
            f.write("Ziel\nOhne Titelzeile\n")
        code, _, err = self.run_main(["anlegen", "--config", self.config, "--entwurf", self.entwurf], self.env())
        self.assertEqual(code, 2)
        self.assertIn("# <Zusammenfassung>", err)

    def test_config_falsches_framework(self):
        self.schreibe_config({"framework": "aidlc", "jira_project": "FLAB"})
        code, _, err = self.run_main(["anlegen", "--config", self.config, "--entwurf", self.entwurf], self.env())
        self.assertEqual(code, 2)
        self.assertIn("framework", err)


class FehlerTest(Basis):
    def test_jira_fehler_wird_lesbar_und_ohne_token(self):
        FakeJira.antworten[("POST", "/rest/api/3/issue")] = (
            400, {"errorMessages": [], "errors": {"issuetype": f"ungültig, Token {TOKEN}"}})
        code, out, err = self.run_main(["anlegen", "--config", self.config, "--entwurf", self.entwurf], self.env())
        self.assertEqual(code, 1)
        self.assertIn("HTTP 400", err)
        self.assertIn("issuetype: ungültig", err)
        self.assertNotIn(TOKEN, out + err)
        self.assertIn("***", err)

    def test_401_ohne_json(self):
        FakeJira.antworten[("GET", "/rest/api/3/myself")] = (401, b"Unauthorized")
        code, _, err = self.run_main(["pruefen", "--config", self.config], self.env())
        self.assertEqual(code, 1)
        self.assertIn("HTTP 401: Unauthorized", err)

    def test_nicht_erreichbar(self):
        env = self.env()
        env["JIRA_BASE_URL"] = "http://127.0.0.1:9"
        code, _, err = self.run_main(["pruefen", "--config", self.config], env)
        self.assertEqual(code, 1)
        self.assertIn("nicht erreichbar", err)


class PruefenTest(Basis):
    def test_pruefen_ok(self):
        FakeJira.antworten[("GET", "/rest/api/3/myself")] = (200, {"displayName": "Factory Test"})
        FakeJira.antworten[("GET", "/rest/api/3/project/FLAB")] = (
            200, {"key": "FLAB", "name": "Factory Lab", "issueTypes": [{"name": "Task"}, {"name": "Sub-task", "subtask": True}]})
        code, out, err = self.run_main(["pruefen", "--config", self.config], self.env())
        self.assertEqual(code, 0, err)
        self.assertIn("Angemeldet als: Factory Test", out)
        self.assertIn("Labels beim Anlegen: sdd-speckit, test-nacht", out)

    def test_pruefen_falscher_typ(self):
        self.schreibe_config({"framework": "bmad", "jira_project": "FLAB", "issue_type": "Story"})
        FakeJira.antworten[("GET", "/rest/api/3/myself")] = (200, {"displayName": "x"})
        FakeJira.antworten[("GET", "/rest/api/3/project/FLAB")] = (200, {"key": "FLAB", "issueTypes": [{"name": "Task"}]})
        code, _, err = self.run_main(["pruefen", "--config", self.config], self.env())
        self.assertEqual(code, 2)
        self.assertIn("Vorhanden: Task", err)


if __name__ == "__main__":
    unittest.main()
