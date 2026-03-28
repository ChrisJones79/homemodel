#!/usr/bin/env bash
# HomeModel – dev mode launcher
#
# Starts the backend in real mode using a separate development SQLite database,
# waits until the backend is reachable, then opens Firefox at
# http://127.0.0.1:8000.  The dev database is kept separate from the real
# database so development work never touches production data.
# Closing the terminal or pressing Ctrl-C stops the backend cleanly.
#
# Usage:
#   bash <SCRIPT_DIR>/homemodel-dev.sh
#
# Required: set REPO_ROOT and DATA_DIR to match your local layout.
# The directory at DATA_DIR must exist before running this script.
# The dev database file is created automatically on first run.

set -euo pipefail

# ── Configuration ────────────────────────────────────────────────────────────
REPO_ROOT="${HOMEMODEL_REPO_ROOT:-<REPO_ROOT>}"
DATA_DIR="${HOMEMODEL_DATA_DIR:-<DATA_DIR>}"
DB_DEV_PATH="$DATA_DIR/homemodel-dev.db"
APP_URL="http://127.0.0.1:8000"

# ── Environment ──────────────────────────────────────────────────────────────
export HOMEMODEL_MODE=real
export SCHEMASTORE_DB_PATH="$DB_DEV_PATH"
export CORS_ALLOW_ORIGINS="http://localhost:8000,http://127.0.0.1:8000"

# ── Preflight check ───────────────────────────────────────────────────────────
if [ ! -d "$DATA_DIR" ]; then
    echo "ERROR: DATA_DIR does not exist: $DATA_DIR"
    echo "Create it first: mkdir -p \"$DATA_DIR\""
    exit 1
fi

# ── Cleanup ──────────────────────────────────────────────────────────────────
BACKEND_PID=""
cleanup() {
    if [ -n "$BACKEND_PID" ] && kill -0 "$BACKEND_PID" 2>/dev/null; then
        echo "Stopping backend (PID $BACKEND_PID)…"
        kill "$BACKEND_PID"
    fi
}
trap cleanup EXIT

# ── Start backend ─────────────────────────────────────────────────────────────
cd "$REPO_ROOT"
echo "Starting HomeModel backend in dev mode (DB: $DB_DEV_PATH)…"
"$REPO_ROOT/venv/bin/uvicorn" backend.main:app --port 8000 --reload &
BACKEND_PID=$!

# ── Wait for readiness ────────────────────────────────────────────────────────
echo "Waiting for backend to become ready at $APP_URL …"
WAIT_SECS=0
MAX_WAIT=60
until curl -fs "$APP_URL/scene/manifest" > /dev/null 2>&1; do
    sleep 1
    WAIT_SECS=$((WAIT_SECS + 1))
    if [ "$WAIT_SECS" -ge "$MAX_WAIT" ]; then
        echo "ERROR: Backend did not become ready after ${MAX_WAIT}s. Check terminal output above."
        exit 1
    fi
done
echo "Backend is ready."

# ── Open browser ──────────────────────────────────────────────────────────────
if ! command -v firefox > /dev/null 2>&1; then
    echo "WARNING: firefox not found. Open $APP_URL manually in your browser."
else
    echo "Opening Firefox at $APP_URL"
    firefox "$APP_URL" &
fi

# ── Keep running ─────────────────────────────────────────────────────────────
wait "$BACKEND_PID"
