#!/usr/bin/env bash
# Ask the Larkspur housing assistant three resident questions through Dify's
# service API, the same API a housing portal or chat widget would call.
# All three share one Dify conversation; each answer becomes a trace in the
# Opik project "dify-student-housing-assistant".
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STATE="$HERE/.dify-state.json"

if [ ! -f "$STATE" ]; then
  echo "No .dify-state.json found. Run ./setup.sh first." >&2
  exit 1
fi

python3 - "$STATE" <<'PY'
import json, sys, urllib.request

state = json.load(open(sys.argv[1]))
url, key = state["dify_url"], state["app_api_key"]

QUESTIONS = [
    "The heat in my room in Alder Hall stopped working last night. How fast will someone come, and who do I call?",
    "My boyfriend wants to visit from out of town in November. Can he stay in my room, and for how many nights?",
    "Back to the heat: if I move out for good on the last day of the fall term, what time do I have to be gone and what happens to my deposit?",
]

conversation_id = ""  # reuse one conversation so the three questions form a thread
for i, q in enumerate(QUESTIONS, 1):
    print(f"\n[{i}/3] Resident: {q}")
    req = urllib.request.Request(
        f"{url}/v1/chat-messages",
        data=json.dumps({
            "inputs": {},
            "query": q,
            "response_mode": "blocking",
            "conversation_id": conversation_id,
            "user": "demo-resident",
        }).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        body = json.load(resp)
    conversation_id = body.get("conversation_id", conversation_id)
    usage = (body.get("metadata") or {}).get("usage") or {}
    print(f"\nHousing assistant: {body['answer']}")
    print(f"  (prompt tokens: {usage.get('prompt_tokens')}, completion tokens: {usage.get('completion_tokens')})")

print(f"\nDone. Dify conversation id: {conversation_id}")
print("Open the 'dify-student-housing-assistant' project in Opik to see the traces.")
PY
