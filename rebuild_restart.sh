#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

if docker compose version >/dev/null 2>&1; then
  COMPOSE=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE=(docker-compose)
else
  echo "[error] docker compose 또는 docker-compose 명령을 찾을 수 없습니다." >&2
  exit 1
fi

BUILD_FLAGS=()
if [[ "${1:-}" == "--no-cache" ]]; then
  BUILD_FLAGS+=(--no-cache)
fi

echo "[step] Rebuilding all services..."
"${COMPOSE[@]}" build "${BUILD_FLAGS[@]}"

echo "[step] Restarting all services..."
"${COMPOSE[@]}" up -d --force-recreate --remove-orphans

echo "[step] Service status"
"${COMPOSE[@]}" ps

if ! command -v curl >/dev/null 2>&1; then
  echo "[warn] curl 이 없어 헬스체크를 건너뜁니다."
  exit 0
fi

echo "[step] Waiting for web health check: http://127.0.0.1:8645/health"
for _ in $(seq 1 30); do
  if curl -fsS http://127.0.0.1:8645/health >/dev/null 2>&1; then
    echo "[ok] Health check passed."
    exit 0
  fi
  sleep 2
done

echo "[error] Health check failed after restart." >&2
exit 1
