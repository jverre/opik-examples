#!/usr/bin/env bash
# One-shot, headless setup:
#   1. builds and starts n8n with the Opik OpenTelemetry hooks baked in
#   2. claims the instance (owner account) and mints an n8n API key
#   3. creates the OpenAI credential from $OPENAI_API_KEY (never from a file)
#   4. imports workflow/grant-screening.json and activates it, all through the n8n API
#
# Requires: docker, curl, python3. Keys come from the shell environment or a
# local .env file (OPIK_API_KEY, OPIK_WORKSPACE, OPENAI_API_KEY).
set -euo pipefail
cd "$(dirname "$0")"

N8N_URL="http://localhost:4280"
# Local-only owner account for the demo instance (n8n requires one).
OWNER_EMAIL="demo@example.com"
OWNER_PASSWORD="GrantScreen-demo-1"
WORKFLOW_NAME="Grant application screening"

# --- 0. Resolve keys --------------------------------------------------------
if [ -f .env ]; then set -a; . ./.env; set +a; fi
: "${OPIK_API_KEY:?Set OPIK_API_KEY (shell env or .env)}"
: "${OPENAI_API_KEY:?Set OPENAI_API_KEY (shell env or .env)}"
export OPIK_WORKSPACE="${OPIK_WORKSPACE:-default}"
export OPIK_URL_OVERRIDE="${OPIK_URL_OVERRIDE:-https://www.comet.com/opik/api}"

json() { python3 -c "import json,sys; d=json.load(sys.stdin); print(d$1)"; }

# --- 1. Start n8n -----------------------------------------------------------
echo "==> Building and starting n8n (bakes n8n-observability into the image)"
docker compose up -d --build

echo -n "==> Waiting for n8n to be ready"
for _ in $(seq 1 90); do
  if curl -sf "$N8N_URL/healthz/readiness" >/dev/null 2>&1; then echo " - up"; break; fi
  echo -n "."; sleep 2
done
curl -sf "$N8N_URL/healthz/readiness" >/dev/null || { echo "n8n did not come up"; exit 1; }

# --- 2. Owner account + API key (REST API, no browser) ----------------------
# n8n binds the session cookie to a browser id, so every /rest call sends the
# same browser-id header; that stands in for the browser.
COOKIES="$(mktemp)"; trap 'rm -f "$COOKIES"' EXIT
BROWSER_ID="setup-script"

echo "==> Claiming the instance (owner setup)"
SETUP_BODY=$(printf '{"email":"%s","firstName":"Demo","lastName":"Owner","password":"%s"}' \
  "$OWNER_EMAIL" "$OWNER_PASSWORD")
LOGIN_BODY=$(printf '{"emailOrLdapLoginId":"%s","password":"%s"}' \
  "$OWNER_EMAIL" "$OWNER_PASSWORD")
AUTHED=""
for _ in $(seq 1 15); do
  # The /rest routes can lag the health check by a few seconds on first boot,
  # so retry. Owner setup returns the session cookie; if the instance is
  # already claimed, fall back to a normal login.
  if curl -sf -c "$COOKIES" -H 'Content-Type: application/json' -H "browser-id: $BROWSER_ID" \
       -X POST "$N8N_URL/rest/owner/setup" -d "$SETUP_BODY" >/dev/null 2>&1; then
    AUTHED=yes; break
  fi
  if curl -sf -c "$COOKIES" -H 'Content-Type: application/json' -H "browser-id: $BROWSER_ID" \
       -X POST "$N8N_URL/rest/login" -d "$LOGIN_BODY" >/dev/null 2>&1; then
    echo "    already claimed - logged in"
    AUTHED=yes; break
  fi
  sleep 2
done
[ -n "$AUTHED" ] || { echo "could not authenticate against n8n"; exit 1; }

echo "==> Minting an n8n API key (unique label, so re-running setup.sh works)"
API_KEY=$(curl -sf -b "$COOKIES" -H 'Content-Type: application/json' -H "browser-id: $BROWSER_ID" \
  -X POST "$N8N_URL/rest/api-keys" \
  -d '{"label":"setup-'"$(date +%s)"'","expiresAt":null,"scopes":["workflow:create","workflow:read","workflow:update","workflow:delete","workflow:list","workflow:activate","workflow:deactivate","credential:create","credential:delete","execution:read","execution:list"]}' \
  | json "['data']['rawApiKey']")

api() { # method path [json-body]
  local method="$1" path="$2" body="${3:-}"
  if [ -n "$body" ]; then
    curl -sf -X "$method" "$N8N_URL/api/v1$path" \
      -H "X-N8N-API-KEY: $API_KEY" -H 'Content-Type: application/json' -d "$body"
  else
    curl -sf -X "$method" "$N8N_URL/api/v1$path" -H "X-N8N-API-KEY: $API_KEY"
  fi
}

# --- 3. OpenAI credential (value injected from env, never committed) --------
echo "==> Creating the OpenAI credential"
CRED_BODY=$(printf '{"name":"OpenAI (grant screening)","type":"openAiApi","data":{"apiKey":"%s"}}' \
  "$OPENAI_API_KEY")
CRED_ID=$(api POST /credentials "$CRED_BODY" | json "['id']")

# --- 4. Import + activate the workflow --------------------------------------
echo "==> Removing any previous copy of the workflow"
api GET "/workflows?name=$(python3 -c "import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1]))" "$WORKFLOW_NAME")" \
  | python3 -c "import json,sys; [print(w['id']) for w in json.load(sys.stdin).get('data',[])]" \
  | while read -r wid; do
      # n8n refuses to delete a published workflow, so unpublish it first.
      api POST "/workflows/$wid/deactivate" "" >/dev/null || true
      for _ in 1 2 3 4 5; do
        api DELETE "/workflows/$wid" >/dev/null && break || sleep 2
      done
      echo "    removed $wid"
    done

echo "==> Importing workflow/grant-screening.json"
WF_BODY=$(python3 - "$CRED_ID" <<'PY'
import json, sys
wf = json.load(open("workflow/grant-screening.json"))
print(json.dumps(wf).replace("__OPENAI_CREDENTIAL_ID__", sys.argv[1]))
PY
)
WF_ID=$(api POST /workflows "$WF_BODY" | json "['id']")

echo "==> Activating the workflow"
api POST "/workflows/$WF_ID/activate" "" >/dev/null

# The webhook registers a few seconds after activation;
# demo.sh retries its first request to absorb that delay.
echo
echo "Done. n8n UI: $N8N_URL  (login: $OWNER_EMAIL / $OWNER_PASSWORD)"
echo "Stop with: docker compose stop   |   Start again with: docker compose up -d"
