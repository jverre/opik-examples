#!/usr/bin/env bash
# Bring up Dify (pinned to release 1.17.1) and configure it headlessly.
# Idempotent: safe to re-run; each step checks before it creates.
#
# Requires: Docker running, OPENAI_API_KEY exported, and Opik credentials
# (OPIK_API_KEY + OPIK_WORKSPACE exported, or a ~/.opik.config from `opik configure`).
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOCKER_DIR="$HERE/dify-docker"

# Load keys from a local .env if there is one (exported variables also work).
if [ -f "$HERE/.env" ]; then
  set -a; . "$HERE/.env"; set +a
fi

# Dify's web UI and APIs are served by its nginx on this port.
DIFY_PORT="${DIFY_PORT:-4290}"
DIFY_SSL_PORT="${DIFY_SSL_PORT:-4291}"
export DIFY_ADMIN_EMAIL="${DIFY_ADMIN_EMAIL:-admin@larkspur.example}"
export DIFY_ADMIN_PASSWORD="${DIFY_ADMIN_PASSWORD:-LarkspurHousing2026}"

# 1. Create dify-docker/.env from the vendored upstream template on first run.
#    Only a few lines are appended: a stable compose project name and host
#    ports chosen so this stack cannot collide with another Dify on the machine.
if [ ! -f "$DOCKER_DIR/.env" ]; then
  cp "$DOCKER_DIR/env.example" "$DOCKER_DIR/.env"
  {
    echo ""
    echo "# --- dify-student-housing-assistant overrides ---"
    echo "COMPOSE_PROJECT_NAME=dify-student-housing-assistant"
    echo "EXPOSE_NGINX_PORT=$DIFY_PORT"
    echo "EXPOSE_NGINX_SSL_PORT=$DIFY_SSL_PORT"
    echo "EXPOSE_PLUGIN_DAEMON_PORT=4292"
    echo "EXPOSE_PLUGIN_DEBUGGING_PORT=4293"
  } >> "$DOCKER_DIR/.env"
  echo "Created dify-docker/.env (HTTP port $DIFY_PORT)"
fi

# 2. Start the stack (first run pulls ~10 images; takes a few minutes).
echo "Starting the Dify stack..."
docker compose -f "$DOCKER_DIR/docker-compose.yaml" --project-directory "$DOCKER_DIR" up -d

# 3. Configure everything through the console API: admin account, OpenAI
#    plugin + credential, app import from the committed DSL, Opik tracing,
#    and a service API key for demo.sh.
DIFY_URL="http://localhost:$DIFY_PORT" python3 "$HERE/configure_dify.py"

echo ""
echo "Dify UI:  http://localhost:$DIFY_PORT  (login: $DIFY_ADMIN_EMAIL / $DIFY_ADMIN_PASSWORD)"
echo "Stop:     docker compose -p dify-student-housing-assistant stop     (keeps the data)"
echo "Start:    docker compose -p dify-student-housing-assistant start"
echo "Teardown: docker compose -f dify-docker/docker-compose.yaml --project-directory dify-docker down -v"
