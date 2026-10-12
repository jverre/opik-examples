#!/usr/bin/env bash
# Build the app, start it, ask a few scripted questions over HTTP, stop it, exit 0.
# Usage: ./run.sh            (scripted demo)
#        ./run.sh serve      (build and run in the foreground so you can curl it yourself)
set -euo pipefail
cd "$(dirname "$0")"

if [[ -f .env ]]; then set -a; source .env; set +a; fi
: "${OPENAI_API_KEY:?Set OPENAI_API_KEY (see .env.example)}"
: "${OPIK_API_KEY:?Set OPIK_API_KEY (see .env.example)}"
: "${OPIK_WORKSPACE:?Set OPIK_WORKSPACE (see .env.example)}"
export PORT="${PORT:-4261}"

mvn -q -B package -DskipTests

if [[ "${1:-demo}" == "serve" ]]; then
  exec java -jar target/quarkus-app/quarkus-run.jar
fi

java -jar target/quarkus-app/quarkus-run.jar > target/app.log 2>&1 &
APP_PID=$!
trap 'kill "$APP_PID" 2>/dev/null || true' EXIT

echo "Waiting for the app on port $PORT (it indexes the FAQ files on startup)..."
for _ in $(seq 1 60); do
  # Plain TCP probe, so the readiness check does not show up as a trace.
  (exec 3<>"/dev/tcp/127.0.0.1/$PORT") 2>/dev/null && break
  kill -0 "$APP_PID" 2>/dev/null || { echo "App exited early, see target/app.log"; exit 1; }
  sleep 1
done

QUESTIONS=(
  "My debit card was stolen. What do I do, and how much does expedited replacement cost?"
  "What APR would I get on a 72 month auto loan, and is there a discount for autopay?"
  "What are the Downtown branch hours on Saturday?"
  "How much is the overdraft fee, and how many can you charge me in one day?"
  "Can I buy Bitcoin through Larkspur?"
)
for q in "${QUESTIONS[@]}"; do
  echo
  echo "Q: $q"
  echo "A: $(curl -s --get --data-urlencode "q=$q" --max-time 90 "http://localhost:$PORT/ask")"
done

# Give the batch span processor a moment, then stop; Quarkus flushes the exporter on shutdown.
sleep 3
kill "$APP_PID"
wait "$APP_PID" 2>/dev/null || true
trap - EXIT
echo
echo "Done. Open the quarkus-langchain4j-banking-faq project in Opik."
