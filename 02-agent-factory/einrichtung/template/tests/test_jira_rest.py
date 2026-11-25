"""Tests for agentic_factory/jira_rest.py: Jira over REST against a local fake Jira, and the comment shape."""
import base64
import contextlib
import http.client
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from agentic_factory import copied, config, jira_rest, clarify
from .fakes import Fake, KEY


CLOUD = {"JIRA_EMAIL": "a@example.invalid", "JIRA_API_TOKEN": "tok"}
DC = {"JIRA_API_TOKEN": "pat"}


class JiraRest(unittest.TestCase):
    def rest(self, fake, env):
        return jira_rest.JiraRest({"JIRA_BASE_URL": fake.url + "/", **env})

    def run_quiet(self, fn, *args):
        with mock.patch.dict(os.environ, {"no_proxy": "*", "NO_PROXY": "*"}), contextlib.redirect_stdout(io.StringIO()):
            return fn(*args)

    def test_cloud_basic(self):
        fake = Fake(self, description={"type": "doc", "content": [
            {"type": "paragraph", "content": [{"type": "text", "text": "Text"}]}]})
        t, comments = self.run_quiet(self.rest(fake, CLOUD).read, KEY)
        method, path, auth, _ = fake.seen[0]
        self.assertTrue(path.startswith(f"/rest/api/3/issue/{KEY}?"))
        self.assertEqual(auth, "Basic " + base64.b64encode(b"a@example.invalid:tok").decode())
        self.assertEqual(t, {"key": KEY, "summary": "S", "description": "Text", "labels": ["sdd-bmad"]})
        self.assertEqual(comments, [])
        self.assertTrue(fake.seen[1][1].startswith(f"/rest/api/3/issue/{KEY}/comment?"))

    def test_broken_answer_stops(self):  # M4
        class Resp:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def read(self):
                raise http.client.IncompleteRead(b"{\"fie", 200)

        jira = jira_rest.JiraRest({"JIRA_BASE_URL": "https://jira.example.invalid", "JIRA_API_TOKEN": "secret-tok-123"},
                           urlopen=lambda req, timeout: Resp())
        with self.assertRaisesRegex(config.Stop, r"^Jira GET https://jira.example.invalid/rest/api/2/issue/FLAB-7 sent a "
                                             r"broken answer: IncompleteRead"):
            self.run_quiet(jira.ticket, KEY)

        def remote_closed(req, timeout):
            raise http.client.RemoteDisconnected("Remote end closed connection without response")

        jira.urlopen = remote_closed
        with self.assertRaisesRegex(config.Stop, "^Jira not reachable at https://jira.example.invalid: Remote end closed"):
            self.run_quiet(jira.ticket, KEY)

    def test_data_center_bearer(self):
        fake = Fake(self, description="Plain *wiki* text")
        t = self.run_quiet(self.rest(fake, DC).ticket, KEY)
        _, path, auth, _ = fake.seen[0]
        self.assertTrue(path.startswith(f"/rest/api/2/issue/{KEY}?"))
        self.assertEqual(auth, "Bearer pat")
        self.assertEqual(t["description"], "Plain *wiki* text")

    def test_401_without_token(self):
        fake = Fake(self, status=401, error_body=b'{"errorMessages":["token secret-tok is bad"]}')
        with self.assertRaises(config.Stop) as e:
            self.run_quiet(self.rest(fake, {**CLOUD, "JIRA_API_TOKEN": "secret-tok"}).ticket, KEY)
        self.assertIn("HTTP 401", str(e.exception))
        self.assertIn("check JIRA_EMAIL and JIRA_API_TOKEN", str(e.exception))
        self.assertNotIn("secret-tok", str(e.exception))

    def test_other_hints_and_write_errors(self):
        for status, hint in ((403, "no permission"), (404, "not found")):
            with self.subTest(status=status):
                fake = Fake(self, status=status)
                with self.assertRaisesRegex(config.Stop, f"HTTP {status}: .*{hint}"):
                    self.run_quiet(self.rest(fake, DC).ticket, KEY)
        fake = Fake(self, status=400, error_body=b'{"errorMessages":[],"errors":{"comment":"zu lang"}}')
        with self.assertRaisesRegex(config.Stop, "POST .*HTTP 400.*comment: zu lang"):
            self.run_quiet(self.rest(fake, DC).add_comment, KEY, "x")

    def test_not_reachable(self):
        with self.assertRaisesRegex(config.Stop, "not reachable"):
            self.run_quiet(jira_rest.JiraRest({"JIRA_BASE_URL": "http://127.0.0.1:9", "JIRA_API_TOKEN": "token-12345678"}).ticket, KEY)

    def test_missing_settings(self):
        with self.assertRaisesRegex(config.Stop, "JIRA_API_TOKEN"):
            jira_rest.JiraRest({"JIRA_BASE_URL": "http://127.0.0.1:9"})
        with self.assertRaisesRegex(config.Stop, "JIRA_BASE_URL"):
            jira_rest.JiraRest({"JIRA_API_TOKEN": "t"})

    def test_urlopen_is_injectable(self):
        calls = []

        def fake_open(req, timeout=None):
            calls.append((req.get_method(), req.full_url, timeout))
            return io.BytesIO(json.dumps({"fields": {"summary": "x"}}).encode())

        rest = jira_rest.JiraRest({"JIRA_BASE_URL": "https://j.example.invalid", "JIRA_API_TOKEN": "t"}, urlopen=fake_open)
        t = self.run_quiet(rest.ticket, KEY)
        self.assertEqual(calls[0][:2], ("GET", f"https://j.example.invalid/rest/api/2/issue/{KEY}"
                                               "?fields=summary,description,labels,status"))
        self.assertEqual(t["summary"], "x")

    def test_comments_paged_and_sorted(self):
        raw = [{"id": str(i), "created": f"2026-11-24T{(i * 7) % 24:02d}:{i % 60:02d}:00.000+0100", "body": f"c{i}"}
               for i in range(150)]
        order = sorted(range(150), key=lambda i: (i * 37) % 150)  # out of order
        fake = Fake(self, comments=[raw[i] for i in order])
        got = self.run_quiet(self.rest(fake, DC).comments, KEY)
        self.assertEqual(len(got), 150)
        self.assertEqual({c["id"] for c in got}, {str(i) for i in range(150)})
        self.assertEqual([c["created"] for c in got], sorted(c["created"] for c in got))
        pages = [p for m, p, _, _ in fake.seen]
        self.assertEqual(len(pages), 2)
        self.assertIn("startAt=0&maxResults=100", pages[0])
        self.assertIn("startAt=100&maxResults=100", pages[1])

    def test_comments_cloud_adf_bodies_and_utc(self):
        adf = {"type": "doc", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "[KI] hallo"}]}]}
        fake = Fake(self, comments=[{"id": 2, "created": "2026-11-24T22:12:56.692+0100", "body": adf},
                                    {"id": 1, "created": "2026-11-24T21:30:00.000+0000", "body": None}])
        got = self.run_quiet(self.rest(fake, CLOUD).comments, KEY)
        self.assertEqual(got, [{"id": "2", "created": "2026-11-24T21:12:56.692Z", "updated": "", "author": "",
                                "body": "[KI] hallo\n"},
                               {"id": "1", "created": "2026-11-24T21:30:00.000Z", "updated": "", "author": "", "body": ""}])

    def test_null_fields(self):
        fake = Fake(self)
        fake.fields = {"summary": None, "description": None, "labels": None, "status": None}
        t = self.run_quiet(self.rest(fake, CLOUD).ticket, KEY)
        self.assertEqual(t, {"key": KEY, "summary": "", "description": "", "labels": []})
        fake.fields = None  # "fields": null
        self.assertEqual(self.run_quiet(self.rest(fake, DC).ticket, KEY)["labels"], [])

    def test_add_comment_cloud_adf(self):
        text = "[KI] agentic-factory spec key=FLAB-7\nZeile zwei\n\nAbsatz\n\n```\ncode\n\nmehr\n```"
        fake = Fake(self)
        cid = self.run_quiet(self.rest(fake, CLOUD).add_comment, KEY, text)
        self.assertEqual(cid, "10050")
        method, path, auth, body = fake.seen[0]
        self.assertEqual((method, path), ("POST", f"/rest/api/3/issue/{KEY}/comment"))
        self.assertEqual(body, {"body": jira_rest.text_to_adf(text)})
        self.assertTrue(auth.startswith("Basic "))

    def test_add_comment_dc_wiki(self):
        text = "[KI] agentic-factory spec key=FLAB-7\n\nAbsatz *fett*\n\n```\n{code} x\n```"
        fake = Fake(self)
        cid = self.run_quiet(self.rest(fake, DC).add_comment, KEY, text)
        self.assertEqual(cid, "10050")
        method, path, auth, body = fake.seen[0]
        self.assertEqual((method, path), ("POST", f"/rest/api/2/issue/{KEY}/comment"))
        self.assertEqual(body, {"body": jira_rest.text_to_wiki(text)})
        self.assertEqual(body["body"], "\\[KI\\] agentic\\-factory spec key=FLAB\\-7\n\nAbsatz \\*fett\\*\n\n"
                                       "{noformat}\n{code} x\n{noformat}")
        self.assertEqual(auth, "Bearer pat")

    def test_add_comment_refuses_empty_text(self):
        with self.assertRaises(config.Stop):
            self.run_quiet(self.rest(Fake(self), DC).add_comment, KEY, "  \n")

    def test_comment_authors(self):
        fake = Fake(self, comments=[
            {"id": "1", "created": "2026-11-24T10:00:00.000+0100", "body": "a",
             "author": {"accountId": "acc-1", "key": "k-1", "name": "n-1"}},
            {"id": "2", "created": "2026-11-24T10:01:00.000+0100", "body": "b", "author": {"name": "n-2", "key": ""}},
            {"id": "3", "created": "2026-11-24T10:02:00.000+0100", "body": "c"}])
        cloud = self.run_quiet(self.rest(fake, CLOUD).comments, KEY)
        self.assertEqual([c["author"] for c in cloud], ["acc-1", "", ""])
        dc = self.run_quiet(self.rest(fake, DC).comments, KEY)
        self.assertEqual([c["author"] for c in dc], ["k-1", "n-2", ""])

    def test_comment_updated_times(self):  # final review 2, I1: an edited proposal is refused
        fake = Fake(self, comments=[
            {"id": "1", "created": "2026-11-24T10:00:00.000+0100", "updated": "2026-11-24T10:05:00.000+0100", "body": "a"},
            {"id": "2", "created": "2026-11-24T10:01:00.000+0100", "body": "b"}])
        for env in (CLOUD, DC):
            with self.subTest(cloud=env is CLOUD):
                got = self.run_quiet(self.rest(fake, env).comments, KEY)
                self.assertEqual([c["updated"] for c in got], ["2026-11-24T09:05:00.000Z", ""])

    def test_myself(self):  # final review 2, I1: the token's own account, fetched once
        fake = Fake(self)
        fake.myself = {"accountId": "acc-1", "key": "k-1", "name": "n-1"}
        cloud, dc = self.rest(fake, CLOUD), self.rest(fake, DC)
        self.assertEqual(self.run_quiet(cloud.myself), "acc-1")
        self.assertEqual(self.run_quiet(cloud.myself), "acc-1")
        self.assertEqual(self.run_quiet(dc.myself), "k-1")
        self.assertEqual([p for _, p, _, _ in fake.seen], ["/rest/api/3/myself", "/rest/api/2/myself"])
        fake.myself = {"name": "n-2", "key": ""}
        self.assertEqual(self.run_quiet(self.rest(fake, DC).myself), "n-2")
        for me, env in (({"key": "k-1"}, CLOUD), ({"accountId": "acc-1"}, DC), ({}, DC), ([], CLOUD)):
            with self.subTest(me=me):
                fake.myself = me
                with self.assertRaisesRegex(config.Stop, "can't tell which account the Jira token belongs to"):
                    self.run_quiet(self.rest(fake, env).myself)

    def test_dc_marker_survives_the_round_trip(self):
        text = "[KI] agentic-factory klärung runde=1 key=FLAB-7\nAnnahme A1: nur *das* Formular_\n\n```\nx\n```\n"
        wiki = jira_rest.text_to_wiki(text)
        fake = Fake(self, comments=[{"id": "5", "created": "2026-11-24T10:00:00.000+0100", "body": wiki}])
        (c,) = self.run_quiet(self.rest(fake, DC).comments, KEY)
        self.assertTrue(c["body"].startswith("[KI] agentic-factory klärung runde=1 key=FLAB-7\n"))
        self.assertIn("\nAnnahme A1: nur *das* Formular_\n", c["body"])
        self.assertNotIn("{noformat}", c["body"])
        self.assertEqual(clarify.ROUND_RE.match(c["body"]).group(2), "FLAB-7")

    def test_set_description_cloud_and_dc(self):
        md = "## Ziel\n\nTags `klein` schreiben.\n\n- eins\n- zwei\n"
        fake = Fake(self)
        self.assertIsNone(self.run_quiet(self.rest(fake, CLOUD).set_description, KEY, md))
        method, path, _, body = fake.seen[0]
        self.assertEqual((method, path), ("PUT", f"/rest/api/3/issue/{KEY}"))
        self.assertEqual(body, {"fields": {"description": copied.als_adf(md)}})
        fake = Fake(self)
        self.assertIsNone(self.run_quiet(self.rest(fake, DC).set_description, KEY, md))
        method, path, _, body = fake.seen[0]
        self.assertEqual((method, path), ("PUT", f"/rest/api/2/issue/{KEY}"))
        self.assertEqual(body, {"fields": {"description": copied.als_wiki(md)}})
        self.assertEqual(body["fields"]["description"], "h3. Ziel\n\nTags {{klein}} schreiben.\n\n* eins\n* zwei")


class MakeComment(unittest.TestCase):
    def test_offsets_become_utc(self):
        for created in ("2026-11-24T22:12:56.692+0100", "2026-11-24T22:12:56.692+01:00", "2026-11-24T21:12:56.692Z",
                        "2026-11-24T21:12:56.692+0000"):
            with self.subTest(created=created):
                self.assertEqual(jira_rest.make_comment(7, created, "x")["created"], "2026-11-24T21:12:56.692Z")

    def test_string_order_is_time_order_across_offsets(self):
        a = jira_rest.make_comment(1, "2026-11-24T23:30:00.000+0100", "a")  # 22:30 UTC
        b = jira_rest.make_comment(2, "2026-11-24T22:45:00.000+0000", "b")  # 22:45 UTC
        self.assertLess(a["created"], b["created"])

    def test_shape_and_normalization(self):
        c = jira_rest.make_comment(12, "2026-01-02T03:04:05.000Z", "Bär")
        self.assertEqual(c, {"id": "12", "created": "2026-01-02T03:04:05.000Z", "updated": "", "author": "", "body": "Bär"})
        self.assertEqual(jira_rest.make_comment(1, "", "x", "acc-1")["author"], "acc-1")
        self.assertEqual(jira_rest.make_comment(1, "", "x", "", "2026-01-02T04:04:05.000+0100")["updated"],
                         "2026-01-02T03:04:05.000Z")

    def test_unparseable_created_is_kept(self):
        self.assertEqual(jira_rest.make_comment("1", "gestern", "x")["created"], "gestern")
        self.assertEqual(jira_rest.make_comment("1", None, "x")["created"], "")

    def test_bodies(self):
        adf = {"type": "doc", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "A"}]}]}
        self.assertEqual(jira_rest.make_comment(1, "", adf)["body"], "A\n")
        self.assertEqual(jira_rest.make_comment(1, "", "plain")["body"], "plain")
        self.assertEqual(jira_rest.make_comment(1, "", None)["body"], "")


class LoadCommentsFile(unittest.TestCase):
    def load(self, data):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "c.json"
            p.write_text(json.dumps(data), encoding="utf-8")
            return jira_rest.load_comments_file(p)

    def test_loads_and_sorts(self):
        adf = {"type": "doc", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "B"}]}]}
        got = self.load([{"body": adf, "created": "2026-11-24T10:00:00.000+0100", "id": 5},
                         {"body": "A", "created": "2026-11-24T08:00:00.000Z"}])
        self.assertEqual([c["body"] for c in got], ["A", "B\n"])
        self.assertEqual([c["created"] for c in got], ["2026-11-24T08:00:00.000Z", "2026-11-24T09:00:00.000Z"])
        self.assertEqual(got[1]["id"], "5")
        self.assertTrue(got[0]["id"])

    def test_author_and_updated(self):
        got = self.load([{"body": "A", "created": "2026-11-24T08:00:00.000Z", "author": "acc-1",
                          "updated": "2026-11-24T10:00:00.000+0100"}, {"body": "B"}])
        self.assertEqual([(c["author"], c["updated"]) for c in got], [("", ""), ("acc-1", "2026-11-24T09:00:00.000Z")])

    def test_bad_files(self):
        for data in ({"body": "x"}, ["x"], [{"created": "z"}]):
            with self.subTest(data=data), self.assertRaises(config.Stop):
                self.load(data)


class AdfAndWiki(unittest.TestCase):
    def test_paragraphs_and_hard_breaks(self):
        self.assertEqual(jira_rest.text_to_adf("eins\nzwei\n\n\ndrei"), {"type": "doc", "version": 1, "content": [
            {"type": "paragraph", "content": [{"type": "text", "text": "eins"}, {"type": "hardBreak"},
                                              {"type": "text", "text": "zwei"}]},
            {"type": "paragraph", "content": [{"type": "text", "text": "drei"}]}]})

    def test_fenced_block_keeps_blank_lines_and_fences(self):
        text = "vorher\n\n````\nzeile\n\n```\ninnen\n```\n````\n\nnachher"
        c = jira_rest.text_to_adf(text)["content"]
        self.assertEqual([n["type"] for n in c], ["paragraph", "codeBlock", "paragraph"])
        self.assertEqual(c[1], {"type": "codeBlock", "content": [{"type": "text", "text": "zeile\n\n```\ninnen\n```"}]})

    def test_fence_without_blank_lines_around_it(self):
        c = jira_rest.text_to_adf("a\n```\nx\n```\nb")["content"]
        self.assertEqual([n["type"] for n in c], ["paragraph", "codeBlock", "paragraph"])

    def test_unclosed_fence_is_plain_text(self):
        c = jira_rest.text_to_adf("```\nx")["content"]
        self.assertEqual([n["type"] for n in c], ["paragraph"])

    def test_fence_helper_output_round_trips(self):
        code = "a\n\n```\nb\n```"
        c = jira_rest.text_to_adf("Text\n\n" + clarify.fence(code))["content"]
        self.assertEqual(c[1]["content"][0]["text"], code)
        self.assertEqual(jira_rest.text_to_wiki("Text\n\n" + clarify.fence("a\n\nb")), "Text\n\n{noformat}\na\n\nb\n{noformat}")

    def test_wiki_escape(self):
        specials = "\\{}[]*_+-^~?|!#"
        self.assertEqual(jira_rest.wiki_escape(specials), "".join("\\" + ch for ch in specials))
        self.assertEqual(jira_rest.wiki_escape("Plain text 1.2, (x) & y"), "Plain text 1.2, (x) & y")

    def test_wiki_paragraphs(self):
        self.assertEqual(jira_rest.text_to_wiki("a_b\nc\n\n\nd!"), "a\\_b\nc\n\nd\\!")

    def test_wiki_code_with_noformat_stops(self):
        with self.assertRaises(config.Stop):
            jira_rest.text_to_wiki("```\n{noformat}\n```")

    def test_wiki_text_inverts_escape(self):
        s = "\\{}[]*_+-^~?|!# und [KI] key=A-1"
        self.assertEqual(jira_rest.wiki_text(jira_rest.wiki_escape(s)), s)
        self.assertEqual(jira_rest.wiki_text("a\n{noformat}\nx {y}\n{noformat}\nb"), "a\nx {y}\nb")
