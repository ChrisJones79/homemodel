#!/usr/bin/env bash
# HomeModel – stub mode launcher
#
# Starts the backend in stub mode (no database required), waits until the
# backend is reachable, then opens Firefox at http://127.0.0.1:8000.
# Closing the terminal or pressing Ctrl-C stops the backend cleanly.
#
# Usage:
#   bash <SCRIPT_DIR>/homemodel-stub.sh
#
# Required: set REPO_ROOT to your local clone of the homemodel repository.

set -euo pipefail

# ── Configuration ────────────────────────────────────────────────────────────
REPO_ROOT="${HOMEMODEL_REPO_ROOT:-<REPO_ROOT>}"
APP_URL="http://127.0.0.1:8000"

# ── Environment ──────────────────────────────────────────────────────────────
export HOMEMODEL_MODE=stub
export CORS_ALLOW_ORIGINS="http://localhost:8000,http://127.0.0.1:8000"

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
echo "Starting HomeModel backend in stub mode…"
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
