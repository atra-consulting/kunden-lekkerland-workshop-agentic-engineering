"""Jira comments in one shape for both routes, and Jira over REST (Cloud and Data Center)."""
import base64
import http.client
import json
import re
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from . import copied, config
from . import ticket as ticket_mod


# --- Jira comments: one shape for both layers (REST here, MCP in jira_mcp.py) ---------------------------------------

JIRA_TIME = ("%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z")  # 2026-11-24T22:12:56.692+0100, +01:00, or Z


def utc_iso(created):
    """Jira's timestamp as UTC 'YYYY-MM-DDTHH:MM:SS.fffZ', so sorting the strings sorts by time. Unparseable: as is."""
    if not isinstance(created, str):
        return ""
    for fmt in JIRA_TIME:
        try:
            dt = datetime.strptime(created.strip(), fmt)
        except ValueError:
            continue
        dt = dt.astimezone(timezone.utc)
        return dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{dt.microsecond // 1000:03d}Z"
    return created


AUTHOR_CLOUD = ("accountId",)  # Jira Cloud over REST and over MCP
AUTHOR_DC = ("key", "name")  # Data Center: the user key, else the user name


def author_id(author, keys):
    """The author's id from Jira's author object: the first of keys that is a non-empty string. "" when unknown."""
    if isinstance(author, dict):
        for k in keys:
            v = author.get(k)
            if isinstance(v, str) and v.strip():
                return v.strip()
    return ""


def make_comment(id, created, body, author="", updated=None):
    """{id, created, updated, author, body}: id a string, created and updated in UTC (updated "" when the source
    doesn't send it), author the account's id ("" when unknown), body plain text (ADF flattened) in NFC. author and
    updated are only compared (decide whether to trust a proposal); they never go into a prompt or a posted
    comment."""
    if body is None:
        text = ""
    elif isinstance(body, (dict, list)):
        text = ticket_mod.adf_text(body)
    else:
        text = str(body)
    return {"id": str(id), "created": utc_iso(created), "updated": utc_iso(updated),
            "author": author if isinstance(author, str) else "", "body": unicodedata.normalize("NFC", text)}


def load_comments_file(path):
    """--comments-file: a JSON list of {body, created?, id?, author?, updated?}; body is a string or ADF, author a
    string."""
    d = config.read_json(path)
    if not isinstance(d, list):
        raise config.Stop(f"{path}: expected a JSON list of comments")
    out = []
    for n, c in enumerate(d, 1):
        if not isinstance(c, dict) or "body" not in c:
            raise config.Stop(f"{path}: comment {n} must be an object with a \"body\"")
        out.append(make_comment(c.get("id", n), c.get("created"), c["body"], c.get("author") or "", c.get("updated")))
    return sorted(out, key=lambda c: c["created"])


# --- Jira REST --------------------------------------------------------------------------------------------------------
# Cloud (JIRA_EMAIL set): API v3, Basic auth, ADF. Data Center: API v2, Bearer with a personal access token, wiki markup.


FENCE_LINE = re.compile(r"`{3,}")  # a fence opens and closes on a line of backticks only, the closing run as long as the opening
NOFORMAT = re.compile(r"\{noformat\}\n?(.*?)\n?\{noformat\}\n?", re.S)
WIKI_SPECIAL = r"\\{}\[\]*_+\-^~?|!#"


def segments(text):
    """Comment text as [('p', paragraph), ('code', fenced text)]. Paragraphs end at blank lines; a fence is only a
    fence when its closing line exists, and blank lines inside it stay inside."""
    lines = text.replace("\r\n", "\n").split("\n")
    out, para, i = [], [], 0
    while i < len(lines):
        run = lines[i].rstrip()
        end = None
        if FENCE_LINE.fullmatch(run):
            end = next((k for k in range(i + 1, len(lines)) if lines[k].rstrip() == run), None)
        if end is not None:
            if para:
                out.append(("p", "\n".join(para)))
                para = []
            out.append(("code", "\n".join(lines[i + 1:end])))
            i = end + 1
            continue
        if lines[i].strip():
            para.append(lines[i])
        elif para:
            out.append(("p", "\n".join(para)))
            para = []
        i += 1
    if para:
        out.append(("p", "\n".join(para)))
    return out


def adf_para(text):
    content = []
    for n, line in enumerate(text.split("\n")):
        if n:
            content.append({"type": "hardBreak"})
        content.append({"type": "text", "text": line})
    return {"type": "paragraph", "content": content}


def adf_code(text):
    node = {"type": "codeBlock"}
    if text:
        node["content"] = [{"type": "text", "text": text}]
    return node


def text_to_adf(text):
    return {"type": "doc", "version": 1,
            "content": [adf_para(t) if kind == "p" else adf_code(t) for kind, t in segments(text)]}


def wiki_escape(s):
    """Backslash before every character Jira wiki markup reads as markup."""
    return re.sub(f"([{WIKI_SPECIAL}])", r"\\\1", s)


def text_to_wiki(text):
    parts = []
    for kind, t in segments(text):
        if kind == "p":
            parts.append(wiki_escape(t))
        elif "{noformat}" in t:
            raise config.Stop("a code block containing {noformat} can't be written as Jira wiki markup")
        else:
            parts.append(f"{{noformat}}\n{t}\n{{noformat}}")
    return "\n\n".join(parts)


def wiki_text(s):
    """What text_to_wiki wrote, as plain text again: escapes removed, {noformat} blocks as their code. Without
    this, a Data Center comment would read back as '\\[KI\\] agentic\\-factory ...' and never match a marker."""
    out, pos = [], 0
    for m in NOFORMAT.finditer(s):
        out.append(re.sub(f"\\\\([{WIKI_SPECIAL}])", r"\1", s[pos:m.start()]))
        out.append(m.group(1) + "\n")
        pos = m.end()
    out.append(re.sub(f"\\\\([{WIKI_SPECIAL}])", r"\1", s[pos:]))
    return "".join(out)


class JiraRest:
    """Jira over REST, with the same methods as the MCP layer: read, add_comment, set_description."""
    HINTS = {401: "check JIRA_EMAIL and JIRA_API_TOKEN", 403: "no permission for this ticket",
             404: "ticket not found, or no permission"}

    def __init__(self, env, urlopen=urllib.request.urlopen):
        self.base = (env.get("JIRA_BASE_URL") or "").rstrip("/")
        self.token = env.get("JIRA_API_TOKEN") or ""
        if not self.base:
            raise config.Stop("JIRA_BASE_URL is not set (or use --ticket-file)")
        if not self.token:
            raise config.Stop("JIRA_API_TOKEN is not set (see local.example.json's comment, or use --ticket-file)")
        email = env.get("JIRA_EMAIL") or ""
        self.cloud = bool(email)
        self.api = "3" if self.cloud else "2"
        self.auth = ("Basic " + base64.b64encode(f"{email}:{self.token}".encode()).decode()) if self.cloud \
            else "Bearer " + self.token
        self.urlopen = urlopen
        self.me = None

    def clean(self, text):
        return copied.redact(text.replace(self.token, "[REDACTED]") if len(self.token) >= 8 else text)

    def call(self, method, path, body=None):
        url = f"{self.base}/rest/api/{self.api}{path}"
        headers = {"Authorization": self.auth, "Accept": "application/json"}
        data = None
        if body is not None:
            data = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        shown = url.split("?")[0]
        try:
            with self.urlopen(req, timeout=60) as r:
                raw = r.read()
        except urllib.error.HTTPError as e:
            try:
                detail = jira_error_text(e.read().decode("utf-8", "replace"))
            except (OSError, http.client.HTTPException):
                detail = ""
            why = " - ".join(p for p in (self.HINTS.get(e.code, ""), detail) if p)
            raise config.Stop(self.clean(f"Jira {method} {shown} -> HTTP {e.code}{': ' + why if why else ''}"))
        except urllib.error.URLError as e:
            raise config.Stop(self.clean(f"Jira not reachable at {self.base}: {e.reason}"))
        except OSError as e:
            raise config.Stop(self.clean(f"Jira not reachable at {self.base}: {e}"))
        except http.client.HTTPException as e:  # such as IncompleteRead: the answer broke off
            raise config.Stop(self.clean(f"Jira {method} {shown} sent a broken answer: {type(e).__name__}: {e}"))
        try:
            return json.loads(raw) if raw.strip() else {}
        except ValueError:
            raise config.Stop(self.clean(f"Jira {method} {shown} did not answer with JSON; is JIRA_BASE_URL right?"))

    def ticket(self, key):
        issue = self.call("GET", f"/issue/{urllib.parse.quote(key, safe='')}?fields=summary,description,labels,status")
        f = (issue or {}).get("fields") or {}
        config.say(f"{key}: fetched from Jira, status {((f.get('status') or {}).get('name'))!r}, labels {f.get('labels') or []}")
        return {"key": key, "summary": (f.get("summary") or "").strip(), "description": ticket_mod.adf_text(f.get("description")).strip(),
                "labels": f.get("labels") or []}

    def comments(self, key):
        """All comments, oldest first. Pages of 100; Jira may send fewer, so the next page starts after what came."""
        out, start = [], 0
        for _ in range(1000):
            d = self.call("GET", f"/issue/{urllib.parse.quote(key, safe='')}/comment?startAt={start}&maxResults=100") or {}
            page = d.get("comments") or []
            for c in page:
                body = c.get("body")
                if not self.cloud and isinstance(body, str):
                    body = wiki_text(body)
                out.append(make_comment(c.get("id"), c.get("created"), body,
                                        author_id(c.get("author"), AUTHOR_CLOUD if self.cloud else AUTHOR_DC),
                                        c.get("updated")))
            start += len(page)
            if not page or (d.get("total") is not None and start >= d["total"]):
                break
        return sorted(out, key=lambda c: c["created"])  # stable

    def read(self, key):
        return self.ticket(key), self.comments(key)

    def myself(self):
        """The id of the token's own account (GET /myself, once per process), as author_id reads a comment's author:
        Cloud accountId, Data Center key, else name. Only compared, never shown."""
        if self.me is None:
            keys = AUTHOR_CLOUD if self.cloud else AUTHOR_DC
            me = author_id(self.call("GET", "/myself"), keys)
            if not me:
                raise config.Stop(f"can't tell which account the Jira token belongs to: GET /myself sent no "
                                  f"{' or '.join(keys)}; nothing is set or posted")
            self.me = me
        return self.me

    def add_comment(self, key, text):
        if not text.strip():
            raise config.Stop("refusing to post an empty comment")
        body = text_to_adf(text) if self.cloud else text_to_wiki(text)
        d = self.call("POST", f"/issue/{urllib.parse.quote(key, safe='')}/comment", {"body": body})
        if not isinstance(d, dict) or not d.get("id"):
            raise config.Stop(f"Jira did not return an id for the new comment on {key}")
        return str(d["id"])

    def set_description(self, key, md):
        desc = copied.als_adf(md) if self.cloud else copied.als_wiki(md)
        self.call("PUT", f"/issue/{urllib.parse.quote(key, safe='')}", {"fields": {"description": desc}})


def jira_error_text(raw):
    """One line from Jira's error JSON; the start of the raw text when it isn't JSON."""
    try:
        d = json.loads(raw)
        parts = list(d.get("errorMessages") or []) + [f"{k}: {v}" for k, v in (d.get("errors") or {}).items()]
        return "; ".join(str(p) for p in parts)[:300]
    except (ValueError, AttributeError):
        return raw.strip()[:200]
