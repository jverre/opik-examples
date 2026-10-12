#!/usr/bin/env python3
"""Configure a freshly started Dify stack, end to end, with no clicking.

Everything the Dify UI does, it does through the console API — so this script
does the same: create the admin account, install the OpenAI plugin, store the
OpenAI key, import the housing-assistant app from the committed DSL, point the app's
tracing at Opik, and mint a service API key for demo.sh.

Idempotent: every step checks before it creates, so re-running is safe.
Standard library only — no dependencies to install.
"""

import base64
import configparser
import http.cookiejar
import json
import os
import pathlib
import sys
import time
import urllib.error
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent
DIFY_URL = os.environ.get("DIFY_URL", "http://localhost:4290").rstrip("/")
CONSOLE = f"{DIFY_URL}/console/api"

ADMIN_EMAIL = os.environ.get("DIFY_ADMIN_EMAIL", "admin@larkspur.example")
ADMIN_NAME = os.environ.get("DIFY_ADMIN_NAME", "Larkspur Admin")
ADMIN_PASSWORD = os.environ.get("DIFY_ADMIN_PASSWORD", "LarkspurHousing2026")

APP_NAME = "Larkspur Housing Assistant"
DSL_PATH = HERE / "app" / "larkspur-housing-assistant.yml"
STATE_PATH = HERE / ".dify-state.json"

OPENAI_PROVIDER = "langgenius/openai/openai"
MARKETPLACE_PLUGIN_API = "https://marketplace.dify.ai/api/v1/plugins/langgenius/openai"
# Pinned fallback if the marketplace lookup fails (content-addressed, stable).
OPENAI_PLUGIN_FALLBACK = (
    "langgenius/openai:1.0.5@51583313a5988d5dca405063831ffeeacdc1f2e95f32a8c10b4c281ceef39ebb"
)

# Dify's Opik config validator insists the URL ends with "/api/" (the Opik SDK
# does not care), so normalise whatever OPIK_URL_OVERRIDE holds.
OPIK_URL = os.environ.get("OPIK_URL_OVERRIDE", "https://www.comet.com/opik/api/").rstrip("/") + "/"
OPIK_PROJECT = os.environ.get("DIFY_OPIK_PROJECT", "dify-student-housing-assistant")


def log(msg: str) -> None:
    print(f"  - {msg}", flush=True)


# Dify's console auth lives in cookies: login sets access_token, refresh_token
# and csrf_token, and every later write must echo the CSRF token in a header —
# the same contract the Dify web UI follows.
_COOKIES = http.cookiejar.CookieJar()
_OPENER = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(_COOKIES))


def _csrf_token() -> str | None:
    for cookie in _COOKIES:
        if cookie.name == "csrf_token":
            return cookie.value
    return None


def request(method: str, url: str, body: dict | None = None) -> tuple[int, dict]:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    csrf = _csrf_token()
    if csrf:
        req.add_header("X-CSRF-Token", csrf)
    try:
        with _OPENER.open(req, timeout=120) as resp:
            raw = resp.read().decode() or "{}"
            return resp.status, json.loads(raw)
    except urllib.error.HTTPError as e:
        raw = e.read().decode() or "{}"
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = {"raw": raw}
        return e.code, payload


def require_env(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        sys.exit(f"ERROR: {name} is not set. Export it (see .env.example) and re-run.")
    return value


def opik_credentials() -> tuple[str, str]:
    """OPIK_API_KEY / OPIK_WORKSPACE from the environment, falling back to ~/.opik.config."""
    api_key = os.environ.get("OPIK_API_KEY", "")
    workspace = os.environ.get("OPIK_WORKSPACE", "")
    cfg_path = pathlib.Path.home() / ".opik.config"
    if (not api_key or not workspace) and cfg_path.exists():
        cfg = configparser.ConfigParser()
        cfg.read(cfg_path)
        if cfg.has_section("opik"):
            api_key = api_key or cfg.get("opik", "api_key", fallback="")
            workspace = workspace or cfg.get("opik", "workspace", fallback="")
    if not api_key or not workspace:
        sys.exit("ERROR: OPIK_API_KEY / OPIK_WORKSPACE not set and ~/.opik.config not found.")
    return api_key, workspace


def wait_for_dify(timeout_s: int = 600) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            status, body = request("GET", f"{CONSOLE}/setup")
            if status == 200 and body.get("step") in ("not_started", "finished"):
                log(f"Dify console is up (setup step: {body['step']})")
                return
        except OSError:
            pass
        time.sleep(5)
    sys.exit(f"ERROR: Dify did not become healthy at {DIFY_URL} within {timeout_s}s.")


def ensure_admin() -> None:
    _, body = request("GET", f"{CONSOLE}/setup")
    if body.get("step") == "finished":
        log("Admin account already exists")
        return
    status, body = request("POST", f"{CONSOLE}/setup", body={
        "email": ADMIN_EMAIL, "name": ADMIN_NAME, "password": ADMIN_PASSWORD,
    })
    if status not in (200, 201):
        sys.exit(f"ERROR: setup failed ({status}): {body}")
    log(f"Created admin account {ADMIN_EMAIL}")


def login() -> None:
    # The console expects the password base64-encoded in transit (what the
    # Dify web UI does); the response sets the session + CSRF cookies.
    status, body = request("POST", f"{CONSOLE}/login", body={
        "email": ADMIN_EMAIL,
        "password": base64.b64encode(ADMIN_PASSWORD.encode()).decode(),
        "remember_me": True,
    })
    if status != 200 or body.get("result") != "success" or not _csrf_token():
        sys.exit(f"ERROR: login failed ({status}): {body}")
    log("Logged in to the console API (session + CSRF cookies set)")


def ensure_openai_plugin() -> None:
    _, body = request("GET", f"{CONSOLE}/workspaces/current/plugin/list")
    installed = {p.get("plugin_id") for p in body.get("plugins", [])}
    if "langgenius/openai" in installed:
        log("OpenAI model-provider plugin already installed")
        return

    identifier = OPENAI_PLUGIN_FALLBACK
    try:
        # The marketplace rejects Python's default User-Agent with a 403.
        mkt_req = urllib.request.Request(MARKETPLACE_PLUGIN_API, headers={"User-Agent": "dify-student-housing-assistant-setup"})
        with urllib.request.urlopen(mkt_req, timeout=30) as resp:
            mkt = json.loads(resp.read().decode())
        identifier = mkt["data"]["plugin"]["latest_package_identifier"]
    except Exception:
        log("Marketplace lookup failed; using the pinned plugin version")

    status, body = request("POST", f"{CONSOLE}/workspaces/current/plugin/install/marketplace",
                           body={"plugin_unique_identifiers": [identifier]})
    if status != 200:
        sys.exit(f"ERROR: plugin install request failed ({status}): {body}")
    task_id = body.get("task_id")
    if body.get("all_installed") or not task_id:
        log(f"Installed OpenAI plugin ({identifier.split('@')[0]})")
        return
    deadline = time.time() + 300
    while time.time() < deadline:
        _, task = request("GET", f"{CONSOLE}/workspaces/current/plugin/tasks/{task_id}")
        task_status = (task.get("task") or {}).get("status")
        if task_status == "success":
            log(f"Installed OpenAI plugin ({identifier.split('@')[0]})")
            return
        if task_status == "failed":
            sys.exit(f"ERROR: plugin install task failed: {task}")
        time.sleep(3)
    sys.exit("ERROR: plugin install timed out after 300s.")


def ensure_openai_credential(openai_api_key: str) -> None:
    status, body = request(
        "GET", f"{CONSOLE}/workspaces/current/model-providers/{OPENAI_PROVIDER}/credentials")
    if status == 200 and body.get("credentials"):
        log("OpenAI provider credential already configured")
        return
    status, body = request(
        "POST", f"{CONSOLE}/workspaces/current/model-providers/{OPENAI_PROVIDER}/credentials",
        body={"credentials": {"openai_api_key": openai_api_key}, "name": "default"})
    if status not in (200, 201):
        sys.exit(f"ERROR: adding the OpenAI credential failed ({status}): {body}")
    log("Stored the OpenAI API key as the provider credential (Dify validated it)")


def ensure_app() -> str:
    status, body = request("GET", f"{CONSOLE}/apps?page=1&limit=100")
    for app in body.get("data", []):
        if app.get("name") == APP_NAME:
            log(f"App already imported (id {app['id']})")
            return app["id"]
    yaml_content = DSL_PATH.read_text()
    status, body = request("POST", f"{CONSOLE}/apps/imports",
                           body={"mode": "yaml-content", "yaml_content": yaml_content})
    app_id = body.get("app_id")
    if status not in (200, 201) or not app_id:
        sys.exit(f"ERROR: app import failed ({status}): {body}")
    log(f"Imported '{APP_NAME}' from the committed DSL (id {app_id}, status {body.get('status')})")
    return app_id


def ensure_opik_tracing(app_id: str, opik_api_key: str, opik_workspace: str) -> None:
    tracing_config = {
        "api_key": opik_api_key,
        "project": OPIK_PROJECT,
        "workspace": opik_workspace,
        "url": OPIK_URL,
    }
    status, body = request("GET", f"{CONSOLE}/apps/{app_id}/trace-config?tracing_provider=opik")
    already = status == 200 and body.get("tracing_provider") == "opik" and not body.get("has_not_configured")
    method = "PATCH" if already else "POST"
    payload = {"tracing_provider": "opik", "tracing_config": tracing_config}
    status, body = request(method, f"{CONSOLE}/apps/{app_id}/trace-config", body=payload)
    if status not in (200, 201):
        sys.exit(f"ERROR: writing the Opik trace config failed ({status}): {body}")
    log(f"Opik trace config saved (project '{OPIK_PROJECT}', workspace '{opik_workspace}')"
        + (" [updated]" if already else " [created, Dify verified the key]"))

    status, body = request("POST", f"{CONSOLE}/apps/{app_id}/trace",
                           body={"enabled": True, "tracing_provider": "opik"})
    if status != 200:
        sys.exit(f"ERROR: enabling tracing failed ({status}): {body}")
    log("Tracing enabled for the app (provider: opik)")


def ensure_service_key(app_id: str) -> str:
    if STATE_PATH.exists():
        state = json.loads(STATE_PATH.read_text())
        if state.get("app_id") == app_id and state.get("app_api_key"):
            log("Service API key already in .dify-state.json")
            return state["app_api_key"]
    status, body = request("POST", f"{CONSOLE}/apps/{app_id}/api-keys", body={})
    key = body.get("token")
    if status not in (200, 201) or not key:
        sys.exit(f"ERROR: creating the app API key failed ({status}): {body}")
    log("Created a service API key for demo.sh")
    return key


def main() -> None:
    openai_api_key = require_env("OPENAI_API_KEY")
    opik_api_key, opik_workspace = opik_credentials()

    print(f"Configuring Dify at {DIFY_URL}", flush=True)
    wait_for_dify()
    ensure_admin()
    login()
    ensure_openai_plugin()
    ensure_openai_credential(openai_api_key)
    app_id = ensure_app()
    ensure_opik_tracing(app_id, opik_api_key, opik_workspace)
    app_api_key = ensure_service_key(app_id)

    STATE_PATH.write_text(json.dumps({
        "dify_url": DIFY_URL,
        "app_id": app_id,
        "app_api_key": app_api_key,
    }, indent=2) + "\n")
    print(f"\nDone. App ready at {DIFY_URL}/app/{app_id}/configuration")
    print(f"State written to {STATE_PATH.name} (git-ignored). Run ./demo.sh next.")


if __name__ == "__main__":
    main()
