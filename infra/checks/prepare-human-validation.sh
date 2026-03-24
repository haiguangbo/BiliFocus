#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

cd "$ROOT_DIR"
docker-compose up --build -d

cat <<EOF
BiliFocus local services are running.

Frontend: http://127.0.0.1:3000
Backend:  http://127.0.0.1:8000
Health:   http://127.0.0.1:8000/health

Manual validation checklist:
  docs/manual-validation.md

Stop services when finished:
  docker-compose down
EOF
