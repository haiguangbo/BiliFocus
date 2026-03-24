#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
FRONTEND_DIR="$ROOT_DIR/apps/frontend"

cd "$ROOT_DIR"

cleanup() {
  docker-compose down >/dev/null 2>&1 || true
}

trap cleanup EXIT

docker-compose up --build -d

for _ in $(seq 1 30); do
  if curl -sf http://127.0.0.1:8000/health >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

curl -sf http://127.0.0.1:8000/health >/dev/null

for _ in $(seq 1 30); do
  if curl -sf http://127.0.0.1:3000 >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

curl -sf http://127.0.0.1:3000 >/dev/null

cd "$FRONTEND_DIR"
PLAYWRIGHT_BASE_URL="http://127.0.0.1:3000" npm run test:e2e
