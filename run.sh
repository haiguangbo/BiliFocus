#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/apps/backend"
FRONTEND_DIR="$ROOT_DIR/apps/frontend"
VENV_DIR="$BACKEND_DIR/.venv"
RUN_DIR="$ROOT_DIR/.run"
BACKEND_PID_FILE="$RUN_DIR/backend.pid"
FRONTEND_PID_FILE="$RUN_DIR/frontend.pid"
BACKEND_LOG_FILE="$RUN_DIR/backend.log"
FRONTEND_LOG_FILE="$RUN_DIR/frontend.log"
BACKEND_REQUIREMENTS="$BACKEND_DIR/requirements.txt"
BACKEND_CREWAI_REQUIREMENTS="$BACKEND_DIR/requirements-crewai.txt"
FRONTEND_LOCKFILE="$FRONTEND_DIR/package-lock.json"
BACKEND_STAMP="$RUN_DIR/backend.requirements.sha256"
BACKEND_CREWAI_STAMP="$RUN_DIR/backend.crewai.sha256"
FRONTEND_STAMP="$RUN_DIR/frontend.lock.sha256"
BACKEND_DB_URL="sqlite:///$ROOT_DIR/data/bilifocus.db"

usage() {
  cat <<'EOF'
Usage:
  ./run.sh setup      Prepare local backend venv and frontend node_modules
  ./run.sh backend    Start backend in the foreground on http://127.0.0.1:8000
  ./run.sh frontend   Start frontend in the foreground on http://127.0.0.1:3000
  ./run.sh dev        Start backend and frontend in the background
  ./run.sh stop       Stop background services started by ./run.sh dev
  ./run.sh status     Show current background service status

This script is executable from fish directly:
  ./run.sh setup
  ./run.sh backend
  ./run.sh frontend
EOF
}

hash_file() {
  sha256sum "$1" | awk '{print $1}'
}

ensure_dirs() {
  mkdir -p "$ROOT_DIR/data" "$RUN_DIR"
}

ensure_backend_setup() {
  ensure_dirs

  if [[ ! -d "$VENV_DIR" ]]; then
    python3 -m venv "$VENV_DIR"
  fi

  local current_hash
  current_hash="$(hash_file "$BACKEND_REQUIREMENTS")"

  if [[ ! -f "$BACKEND_STAMP" ]] || [[ "$(cat "$BACKEND_STAMP")" != "$current_hash" ]]; then
    "$VENV_DIR/bin/pip" install --upgrade pip >/dev/null
    "$VENV_DIR/bin/pip" install -r "$BACKEND_REQUIREMENTS"
    printf '%s' "$current_hash" >"$BACKEND_STAMP"
  fi

  local crewai_enabled="false"
  if [[ -f "$BACKEND_DIR/.env" ]] && grep -q '^CREWAI_ENABLED=true' "$BACKEND_DIR/.env"; then
    crewai_enabled="true"
  fi

  if [[ "$crewai_enabled" == "true" ]]; then
    local crewai_hash
    crewai_hash="$(hash_file "$BACKEND_CREWAI_REQUIREMENTS")"

    if [[ ! -f "$BACKEND_CREWAI_STAMP" ]] || [[ "$(cat "$BACKEND_CREWAI_STAMP")" != "$crewai_hash" ]]; then
      "$VENV_DIR/bin/pip" install -r "$BACKEND_CREWAI_REQUIREMENTS"
      "$VENV_DIR/bin/pip" install \
        starlette==0.38.6 \
        uvicorn==0.42.0 \
        httpx==0.28.1 \
        pydantic==2.11.10 \
        pydantic-settings==2.10.1 \
        python-dotenv==1.1.1
      printf '%s' "$crewai_hash" >"$BACKEND_CREWAI_STAMP"
    fi
  fi
}

ensure_frontend_setup() {
  ensure_dirs

  local current_hash
  current_hash="$(hash_file "$FRONTEND_LOCKFILE")"

  if [[ ! -d "$FRONTEND_DIR/node_modules" ]] || [[ ! -f "$FRONTEND_STAMP" ]] || [[ "$(cat "$FRONTEND_STAMP")" != "$current_hash" ]]; then
    (cd "$FRONTEND_DIR" && npm install)
    printf '%s' "$current_hash" >"$FRONTEND_STAMP"
  fi
}

start_backend_foreground() {
  ensure_backend_setup
  cd "$BACKEND_DIR"
  export DATABASE_URL="$BACKEND_DB_URL"
  exec "$VENV_DIR/bin/python" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
}

start_frontend_foreground() {
  ensure_frontend_setup
  cd "$FRONTEND_DIR"
  export API_BASE_URL="http://127.0.0.1:8000"
  export NEXT_PUBLIC_API_BASE_URL="/backend-api"
  exec npm run dev
}

start_backend_background() {
  if [[ -f "$BACKEND_PID_FILE" ]] && kill -0 "$(cat "$BACKEND_PID_FILE")" 2>/dev/null; then
    echo "backend already running with pid $(cat "$BACKEND_PID_FILE")"
    return
  fi

  ensure_backend_setup
  (
    cd "$BACKEND_DIR"
    export DATABASE_URL="$BACKEND_DB_URL"
    nohup "$VENV_DIR/bin/python" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload >"$BACKEND_LOG_FILE" 2>&1 &
    echo $! >"$BACKEND_PID_FILE"
  )
}

start_frontend_background() {
  if [[ -f "$FRONTEND_PID_FILE" ]] && kill -0 "$(cat "$FRONTEND_PID_FILE")" 2>/dev/null; then
    echo "frontend already running with pid $(cat "$FRONTEND_PID_FILE")"
    return
  fi

  ensure_frontend_setup
  (
    cd "$FRONTEND_DIR"
    export API_BASE_URL="http://127.0.0.1:8000"
    export NEXT_PUBLIC_API_BASE_URL="/backend-api"
    nohup npm run dev >"$FRONTEND_LOG_FILE" 2>&1 &
    echo $! >"$FRONTEND_PID_FILE"
  )
}

stop_service() {
  local pid_file="$1"
  local name="$2"

  if [[ ! -f "$pid_file" ]]; then
    echo "$name is not tracked"
    return
  fi

  local pid
  pid="$(cat "$pid_file")"
  if kill -0 "$pid" 2>/dev/null; then
    kill "$pid"
    echo "stopped $name ($pid)"
  else
    echo "$name pid file exists but process is not running"
  fi
  rm -f "$pid_file"
}

show_status() {
  for entry in "backend:$BACKEND_PID_FILE:$BACKEND_LOG_FILE" "frontend:$FRONTEND_PID_FILE:$FRONTEND_LOG_FILE"; do
    IFS=":" read -r name pid_file log_file <<<"$entry"
    if [[ -f "$pid_file" ]] && kill -0 "$(cat "$pid_file")" 2>/dev/null; then
      echo "$name running: pid=$(cat "$pid_file") log=$log_file"
    else
      echo "$name not running"
    fi
  done
}

command="${1:-help}"

case "$command" in
  setup)
    ensure_backend_setup
    ensure_frontend_setup
    echo "local dependencies are ready"
    ;;
  backend)
    start_backend_foreground
    ;;
  frontend)
    start_frontend_foreground
    ;;
  dev)
    start_backend_background
    start_frontend_background
    echo "frontend: http://127.0.0.1:3000"
    echo "health:   http://127.0.0.1:3000/backend-api/health"
    echo "backend:  http://127.0.0.1:8000 (local direct access only)"
    echo "logs:"
    echo "  $BACKEND_LOG_FILE"
    echo "  $FRONTEND_LOG_FILE"
    ;;
  stop)
    stop_service "$BACKEND_PID_FILE" "backend"
    stop_service "$FRONTEND_PID_FILE" "frontend"
    ;;
  status)
    show_status
    ;;
  help|-h|--help)
    usage
    ;;
  *)
    echo "unknown command: $command" >&2
    usage
    exit 1
    ;;
esac
