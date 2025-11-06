#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT_DIR"

log() {
  printf '%s\n' "[worktree-startup] $1"
}

sync_main() {
  if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    log "Skipping git sync because this is not a git repository."
    return
  fi

  log "Fetching latest changes from origin/main..."
  git fetch --prune origin main

  if git show-ref --verify --quiet refs/heads/main; then
    current_branch="$(git rev-parse --abbrev-ref HEAD)"
    if [[ "$current_branch" != "main" ]]; then
      log "Checking out local main branch for refresh."
      git checkout main
    fi
  else
    log "Creating local main branch tracking origin/main."
    git checkout -b main origin/main
  fi

  log "Pulling latest origin/main..."
  git pull --ff-only origin main
}

ensure_uv() {
  if command -v uv >/dev/null 2>&1; then
    return
  fi

  log "uv is required but was not found on PATH."
  log "Install uv from https://docs.astral.sh/uv/ and re-run this script."
  exit 1
}

sync_backend() {
  ensure_uv
  log "Syncing backend dependencies with uv..."
  (
    cd "$ROOT_DIR/poke-backend"
    uv sync
  )
}

sync_frontend() {
  if ! command -v npm >/dev/null 2>&1; then
    log "npm is required but was not found on PATH."
    exit 1
  fi

  log "Installing frontend dependencies..."
  (
    cd "$ROOT_DIR/poke-frontend"
    npm install
  )
}

start_backend() {
  local port="${BACKEND_PORT:-8000}"
  log "Starting FastAPI backend on port ${port}..."
  (
    cd "$ROOT_DIR/poke-backend"
    uv run uvicorn server.api:app --host 0.0.0.0 --port "$port" --reload
  )
}

start_frontend() {
  local port="${FRONTEND_PORT:-5173}"
  log "Starting Vite frontend on port ${port}..."
  (
    cd "$ROOT_DIR/poke-frontend"
    npm run dev -- --host 0.0.0.0 --port "$port"
  )
}

cleanup_and_exit() {
  local code="${1:-0}"

  if [[ -n "${backend_pid:-}" ]] && kill -0 "$backend_pid" >/dev/null 2>&1; then
    log "Stopping backend (pid ${backend_pid})..."
    kill "$backend_pid" >/dev/null 2>&1 || true
    wait "$backend_pid" >/dev/null 2>&1 || true
  fi

  if [[ -n "${frontend_pid:-}" ]] && kill -0 "$frontend_pid" >/dev/null 2>&1; then
    log "Stopping frontend (pid ${frontend_pid})..."
    kill "$frontend_pid" >/dev/null 2>&1 || true
    wait "$frontend_pid" >/dev/null 2>&1 || true
  fi

  exit "$code"
}

monitor_processes() {
  while true; do
    if [[ -n "${backend_pid:-}" ]] && ! kill -0 "$backend_pid" >/dev/null 2>&1; then
      wait "$backend_pid"
      local status=$?
      log "Backend exited with status ${status}."
      cleanup_and_exit "$status"
    fi

    if [[ -n "${frontend_pid:-}" ]] && ! kill -0 "$frontend_pid" >/dev/null 2>&1; then
      wait "$frontend_pid"
      local status=$?
      log "Frontend exited with status ${status}."
      cleanup_and_exit "$status"
    fi

    sleep 1
  done
}

main() {
  sync_main
  sync_backend
  sync_frontend

  start_backend &
  backend_pid=$!

  start_frontend &
  frontend_pid=$!

  log "Backend PID: ${backend_pid}"
  log "Frontend PID: ${frontend_pid}"
  log "Press Ctrl+C to stop both processes."

  trap 'cleanup_and_exit 130' INT
  trap 'cleanup_and_exit 143' TERM

  monitor_processes
}

main "$@"

