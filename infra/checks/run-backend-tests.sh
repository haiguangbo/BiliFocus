#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

cd "$ROOT_DIR"

if command -v pytest >/dev/null 2>&1; then
  pytest apps/backend/tests/test_smoke.py
  exit 0
fi

if command -v docker-compose >/dev/null 2>&1; then
  docker-compose build backend
  docker-compose run --rm backend pytest /app/tests/test_smoke.py
  exit 0
fi

echo "Neither pytest nor docker-compose is available." >&2
exit 1
