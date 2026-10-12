#!/usr/bin/env bash
# Send four fictional grant applications through the workflow's webhook, then
# wait until the matching traces show up in Opik. Each request is one workflow
# execution and so one trace.
set -euo pipefail
cd "$(dirname "$0")"

if [ -f .env ]; then set -a; . ./.env; set +a; fi
WEBHOOK="${WEBHOOK:-http://localhost:4280/webhook/grant-screening}"
PROJECT="n8n-grant-screening"
OPIK_URL="${OPIK_URL_OVERRIDE:-https://www.comet.com/opik/api}"
EXPECTED=4

trace_count() {
  curl -sf "$OPIK_URL/v1/private/traces?project_name=$PROJECT&size=1" \
    -H "Authorization: $OPIK_API_KEY" -H "Comet-Workspace: ${OPIK_WORKSPACE:-default}" \
    | python3 -c "import json,sys; print(json.load(sys.stdin).get('total', 0))" 2>/dev/null || echo 0
}  # a project that does not exist yet answers 404, which counts as 0 traces

BEFORE=""
if [ -n "${OPIK_API_KEY:-}" ]; then BEFORE=$(trace_count); fi

send() {
  echo "-- Application: $2"
  # Retry for up to ~30s: right after setup.sh the webhook can take a few
  # seconds to register.
  for _ in $(seq 1 15); do
    if OUT=$(curl -sf -X POST "$WEBHOOK" -H 'Content-Type: application/json' -d "$1"); then
      echo "$OUT" | python3 -m json.tool
      echo
      return 0
    fi
    sleep 2
  done
  echo "webhook did not answer at $WEBHOOK. Did setup.sh finish?" >&2
  exit 1
}

send '{
  "applicant": "Marisol Okafor",
  "project_title": "Saturday Mural Lab",
  "amount_requested": 9000,
  "summary": "Eight free Saturday mural workshops for teenagers from the Eastgate housing estate, run in the empty bus depot the council has lent us. Teens design and paint a 30 metre wall together, and the finished mural is unveiled at a free neighbourhood evening in month eight. I am a first-time lead artist; two of the facilitators are recent art-school graduates.",
  "budget_notes": "Paint and brushes 2,400; scaffold hire 1,800; two facilitators at 1,200 each for 8 sessions 2,400; materials for teens 600; unveiling evening (sound, lighting, printing) 1,100; insurance 700. Total 9,000."
}' "Saturday Mural Lab (9,000 USD, free teen workshops)"

send '{
  "applicant": "Harbour Street Players",
  "project_title": "The Lamp Keeper: a touring community play",
  "amount_requested": 22000,
  "summary": "A registered nonprofit theatre company in the Lantern region will commission a new play from local writer Idris Vale and tour it to six village halls over nine months, with pay-what-you-can tickets and a free script-writing workshop for teens at each stop. Four of the six cast members are early-career actors from the region.",
  "budget_notes": "Playwright commission 4,000; director 3,500; six actors for 9 weeks 9,000; set and costumes 2,200; van hire and fuel 1,700; village hall fees 900; accessibility captioning 700. Total 22,000."
}' "Harbour Street Players (22,000 USD, strong but over the cap)"

send '{
  "applicant": "Tidepool Collective",
  "project_title": "Something big on the waterfront",
  "amount_requested": 12000,
  "summary": "We are a group of local artists who want to do a big art thing on the waterfront next year. It will be bold and bring people together. We are still working out what form it will take and who will be involved.",
  "budget_notes": "Materials, some fees, and a bit for marketing."
}' "Tidepool Collective (12,000 USD, vague plan)"

send '{
  "applicant": "Fennick Brand Studio",
  "project_title": "Autumn catalogue reprint",
  "amount_requested": 7500,
  "summary": "We are a clothing label and we already printed 3,000 copies of our autumn lookbook last month. We would like the foundation to reimburse the printing bill so we can spend more on advertising our new jacket line.",
  "budget_notes": "Printing invoice 7,500 (paid 14 September)."
}' "Fennick Brand Studio (7,500 USD, reimbursement for a commercial brand)"

if [ -n "$BEFORE" ]; then
  echo "==> Waiting for the traces to reach Opik (project: $PROJECT)"
  for _ in $(seq 1 30); do
    NOW=$(trace_count)
    if [ $((NOW - BEFORE)) -ge $EXPECTED ]; then
      echo "    $((NOW - BEFORE)) new traces in $PROJECT"
      exit 0
    fi
    sleep 3
  done
  echo "    traces not visible yet; the OTLP exporter batches, check Opik in a minute" >&2
else
  echo "(No OPIK_API_KEY in this shell, so skipping the trace check.)"
fi
