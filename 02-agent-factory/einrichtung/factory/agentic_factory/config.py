"""The base every module uses: Stop, say, the shared constants, config.json and local.json, and the Jira route."""
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent  # the folder with agentic-factory.py, config.json, and agentic_factory/
FACTORY_FOLDER = "factory"  # HERE must be <project>/factory/: fetch.project_of
LOCAL_KEYS = {"model", "copilot", "jira_mcp_server", "jira_site"}  # machine settings only
MOVED_KEYS = {"test_command": "config.json (key test_command)", "stack_hint": "AGENTS.md (describe the stack there)"}
JIRA_MCP_SERVER = re.compile(r"[A-Za-z0-9_.-]{1,64}")  # local.json jira_mcp_server, default "atlassian"
JIRA_SITE = re.compile(r"https://[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*(?::[0-9]{1,5})?/?")  # no userinfo, path, or query
QUESTIONS = "FACTORY-QUESTIONS.md"
ASSESSMENT = "FACTORY-ASSESSMENT.json"
EXIT_NOT_READY, EXIT_QUESTIONS = 4, 5


class Stop(Exception):
    pass


def say(msg):
    print(f"[agentic-factory] {msg}", flush=True)


# --- configuration --------------------------------------------------------------------------------------------------

def check_config(cfg):
    """Stops on a config.json with a rules block: team rules were removed, AGENTS.md carries the team's guidance."""
    if "rules" in cfg:
        raise Stop("config.json has a rules block: team rules were removed; move them to AGENTS.md")


REQUIRED_KEYS = ("key_pattern", "model", "agent_timeout_s", "frameworks", "default_framework", "enabled_frameworks",
                 "label_frameworks", "framework_label_prefix", "protected_paths", "deny_tools", "forbidden_flags",
                 "forbidden_env")  # read without a default; assess, clarify, and init have their own checks


def check_required(cfg, path):
    """Stops on a config.json without one of REQUIRED_KEYS, naming the key, instead of a KeyError later."""
    if not isinstance(cfg, dict):
        raise Stop(f"{path} must be a JSON object")
    for k in REQUIRED_KEYS:
        if k not in cfg:
            raise Stop(f"{path} has no key {k}; copy it from the workshop's factory/config.json")


def test_command(cfg):
    """config.json's test_command: a string, "" when unset. The one accessor (copilot, fetch, init). Not in check_config:
    assess, clarify and spec run with an old config whose test_command is a list."""
    cmd = cfg.get("test_command")
    if cmd is None:
        return ""
    if not isinstance(cmd, str):
        raise Stop('config.json: test_command must be a string such as "make test"; an old config has a list — write '
                   "it as one string")
    return cmd


def read_json(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        raise Stop(f"{path} not found")
    except ValueError as e:
        raise Stop(f"{path} is not valid JSON: {e}")


def load_local(path):
    """local.json: this machine's settings. Missing file means none. Moved keys and unknown keys (typos) stop."""
    if path is None or not Path(path).exists():
        return {}
    d = read_json(path)
    moved = sorted(k for k in d if k in MOVED_KEYS)
    if moved:
        raise Stop(f"{path}: {', '.join(f'{k} moved to {MOVED_KEYS[k]}' for k in moved)}; remove it from local.json")
    unknown = sorted(k for k in d if k not in LOCAL_KEYS and not k.startswith("comment"))
    if unknown:
        raise Stop(f"{path}: unknown keys {unknown}; allowed: {sorted(LOCAL_KEYS)}")
    cp = d.get("copilot")
    if cp is not None and not (isinstance(cp, list) and cp and all(isinstance(x, str) and x for x in cp)):
        raise Stop(f"{path}: copilot must be a list of strings, such as [\"copilot\"]")
    srv = d.get("jira_mcp_server")
    if srv is not None and not (isinstance(srv, str) and JIRA_MCP_SERVER.fullmatch(srv)):
        raise Stop(f"{path}: jira_mcp_server must be the name of your Atlassian MCP server in `copilot mcp list`, "
                   "such as \"atlassian\" (letters, digits, _ . -)")
    site = d.get("jira_site")
    if site is not None:
        if not (isinstance(site, str) and JIRA_SITE.fullmatch(site)):
            raise Stop(f"{path}: jira_site must be your Jira Cloud address with no path, such as "
                       "\"https://example.atlassian.net\"")
        d = {**d, "jira_site": site.rstrip("/")}
    return {k: v for k, v in d.items() if k in LOCAL_KEYS and v not in (None, "")}


# --- route ----------------------------------------------------------------------------------------------------------
# --jira mcp|api: how this script reaches Jira. The caller prints say(f"Jira route: {route} ({route_reason(...)})").

def in_pipeline(env):
    return bool(env.get("BITBUCKET_PIPELINE_UUID"))


def choose_route(option, env, offline):
    """'offline', 'mcp', or 'api'. A pipeline never uses mcp; api needs JIRA_BASE_URL and JIRA_API_TOKEN."""
    if offline:
        return "offline"
    if option not in (None, "mcp", "api"):
        raise Stop(f"--jira must be mcp or api, not {option!r}")
    if option == "mcp" and in_pipeline(env):
        raise Stop("the mcp route is refused inside a pipeline")
    route = option or ("api" if in_pipeline(env) else "mcp")
    if route == "api":
        missing = [k for k in ("JIRA_BASE_URL", "JIRA_API_TOKEN") if not env.get(k)]
        if missing:
            raise Stop(f"the api route needs {' and '.join(missing)} (see local.example.json's comment)")
    return route


def route_reason(option, env, offline):
    if offline:
        return "offline input"
    if option:
        return "--jira"
    return "default in a pipeline" if in_pipeline(env) else "default outside a pipeline"
