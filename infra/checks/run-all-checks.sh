#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

"$ROOT_DIR/infra/checks/run-backend-tests.sh"
"$ROOT_DIR/infra/checks/run-mvp-smoke.sh"
"$ROOT_DIR/infra/checks/run-ui-e2e.sh"
