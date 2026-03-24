#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
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

curl -sf -X POST \
  -H "Content-Type: application/json" \
  -d '{"query":"fastapi","filter_text":"只看教程，排除直播切片","limit":3,"offset":0,"source":"default"}' \
  http://127.0.0.1:8000/api/search >/dev/null

curl -sf -X POST \
  -H "Content-Type: application/json" \
  -d '{"query":"fastapi","filter_text":"只看教程，排除直播切片","limit":3,"source":"default"}' \
  http://127.0.0.1:8000/api/sync/search >/dev/null

VIDEOS_RESPONSE="$(curl -sf http://127.0.0.1:8000/api/videos)"
VIDEO_BVID="$(printf '%s' "$VIDEOS_RESPONSE" | python3 -c 'import json,sys; payload=json.load(sys.stdin); print(payload["items"][0]["bvid"])')"

curl -sf "http://127.0.0.1:8000/api/videos?q=fastapi&sort=published_at" >/dev/null
curl -sf "http://127.0.0.1:8000/api/videos/$VIDEO_BVID" >/dev/null

curl -sf -X PUT \
  -H "Content-Type: application/json" \
  -d '{"default_search_limit":8,"default_source":"default","default_filter_text":"只看教程","theme":"system","language":"zh-CN","library_sort":"published_at","hide_watched_placeholder":false}' \
  http://127.0.0.1:8000/api/preferences >/dev/null

curl -sf http://127.0.0.1:8000/api/preferences >/dev/null
curl -sf http://127.0.0.1:3000 >/dev/null
curl -sf http://127.0.0.1:3000/library >/dev/null
curl -sf "http://127.0.0.1:3000/library?q=fastapi&sort=published_at" >/dev/null
curl -sf http://127.0.0.1:3000/settings >/dev/null
curl -sf "http://127.0.0.1:3000/videos/$VIDEO_BVID" >/dev/null

echo "BiliFocus MVP smoke check passed."
