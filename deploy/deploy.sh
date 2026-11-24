#!/usr/bin/env bash
# One-step deploy of the whole stack (web + API + worker + Postgres + Redis + MinIO).
#
#   ./deploy/deploy.sh            build, start, wait until healthy, smoke-test
#   ./deploy/deploy.sh --reseed   same, then reset data to the demo story
#                                 (also moves prices forward to end yesterday)
#
# Run from anywhere on the server; needs Docker with the compose plugin and a
# filled-in env file (see .env.example).
#
# Where the env file can live. The first one found wins:
#   1. $ENV_FILE                 (explicit path, e.g. /home/ubuntu/.env)
#   2. <repo>/.env               (next to docker-compose.yml)
#   3. <repo>/../.env            (the folder that contains the checkout)
#   4. $HOME/.env
# If it is outside the repo, it is symlinked in as <repo>/.env. Docker Compose
# reads .env from the project folder, and git ignores the link, so
# `git reset --hard` on deploy never touches your secrets.
set -euo pipefail

cd "$(dirname "$0")/.."
REPO_DIR="$(pwd)"

RESEED=0
[[ "${1:-}" == "--reseed" ]] && RESEED=1

SRC=""
for cand in "${ENV_FILE:-}" "$REPO_DIR/.env" "$REPO_DIR/../.env" "$HOME/.env"; do
  [[ -n "$cand" && -f "$cand" ]] && { SRC="$(cd "$(dirname "$cand")" && pwd)/$(basename "$cand")"; break; }
done
if [[ -z "$SRC" ]]; then
  echo "ERROR: no env file found. Looked at: \${ENV_FILE:-unset}, $REPO_DIR/.env, $REPO_DIR/../.env, $HOME/.env" >&2
  echo "       Create one from .env.example (JWT_SECRET, SARVAM_API_KEY, POSTGRES_PASSWORD)." >&2
  exit 1
fi
if [[ "$SRC" != "$REPO_DIR/.env" ]]; then
  ln -sfn "$SRC" "$REPO_DIR/.env"
  echo "env: using $SRC (linked as $REPO_DIR/.env)"
else
  echo "env: using $SRC"
fi
if ! grep -Eq '^JWT_SECRET=' .env \
   || grep -Eq '^JWT_SECRET=[[:space:]]*(#.*)?$|^JWT_SECRET=(change-me|local-dev-secret)' .env; then
  echo "ERROR: set a real JWT_SECRET in .env  (e.g. openssl rand -hex 32)." >&2
  exit 1
fi

PORT="$(grep -E '^HTTP_PORT=' .env | cut -d= -f2 | sed 's/#.*//; s/[[:space:]]//g' || true)"
PORT="${PORT:-80}"

echo "=== 1/4 Building and starting containers ==="
docker compose up -d --build --remove-orphans

echo "=== 2/4 Waiting for the API (first boot seeds the database) ==="
for i in $(seq 1 90); do
  status="$(docker inspect -f '{{.State.Health.Status}}' "$(docker compose ps -q api)" 2>/dev/null || echo starting)"
  [[ "$status" == "healthy" ]] && { echo "api healthy"; break; }
  if [[ $i -eq 90 ]]; then
    echo "ERROR: API did not become healthy." >&2
    docker compose logs --tail 60 api >&2
    exit 1
  fi
  sleep 2
done

if [[ $RESEED -eq 1 ]]; then
  echo "=== Reseeding demo data ==="
  docker compose exec -T api python -m scripts.seed_demo
fi

echo "=== 3/4 Waiting for nginx on :$PORT ==="
for i in $(seq 1 30); do
  curl -fsS "http://localhost:$PORT/health" >/dev/null 2>&1 && { echo "gateway healthy"; break; }
  if [[ $i -eq 30 ]]; then
    echo "ERROR: nginx gateway not answering." >&2
    docker compose logs --tail 40 nginx >&2
    exit 1
  fi
  sleep 1
done

echo "=== 4/4 Smoke test ==="
B="http://localhost:$PORT/api/v1"
curl -fsS "$B/meta/health" >/dev/null
curl -fsS "$B/ref/commodities" | grep -q cmd_onion
curl -fsS "$B/market/overview?commodity_id=cmd_onion&market_id=mkt_lasalgaon" | grep -q '"latest"'
curl -fsS "http://localhost:$PORT/" | grep -qi '<html'
docker compose ps --status running --services | grep -qx celery_worker \
  || { echo "ERROR: celery worker not running" >&2; docker compose logs --tail 30 celery_worker >&2; exit 1; }

echo
echo "Deploy complete:"
echo "  web   http://<server>:$PORT/"
echo "  api   http://<server>:$PORT/api/v1   (docs at /docs)"
docker compose ps
