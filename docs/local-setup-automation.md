# HomeModel — Local Setup Automation

This document explains how to run HomeModel on a Linux desktop with a single
click (or terminal command).  It covers three launcher modes, shell script
patterns, `.desktop` file setup, and environment variable reference.

---

## Table of Contents

1. [Directory Layout](#directory-layout)
2. [Prerequisites](#prerequisites)
3. [Launcher Modes](#launcher-modes)
4. [Shell Scripts](#shell-scripts)
5. [Desktop Entries (.desktop files)](#desktop-entries-desktop-files)
6. [Environment Variables](#environment-variables)
7. [Readiness Check](#readiness-check)
8. [Cleanup Behavior](#cleanup-behavior)
9. [Quick Reference](#quick-reference)

---

## Directory Layout

The scripts use generic placeholders.  Replace each placeholder with the
corresponding path on your machine before use.

| Placeholder | Description | Example |
|---|---|---|
| `<REPO_ROOT>` | Local clone of the homemodel repository | `/home/alice/local/homemodel` |
| `<VENV_DIR>` | Python virtual environment inside the repo | `<REPO_ROOT>/venv` |
| `<SCRIPT_DIR>` | Directory where you store the launcher scripts | `/home/alice/Documents/scripts` |
| `<DATA_DIR>` | Directory for SQLite database files | `/home/alice/local/homemodel-data` |
| `<DB_PATH>` | Production database file | `<DATA_DIR>/homemodel.db` |
| `<DB_DEV_PATH>` | Development database file | `<DATA_DIR>/homemodel-dev.db` |
| `<APP_URL>` | Local browser URL | `http://127.0.0.1:8000` |

> **Note:** The `<DATA_DIR>` directory must exist before you run a real or dev
> launcher.  Create it once with `mkdir -p <DATA_DIR>`.  The database file
> itself is created automatically by SchemaStore on first startup.

---

## Prerequisites

- Python virtual environment at `<REPO_ROOT>/venv`
  (`python -m venv venv && pip install -r requirements.txt`)
- `curl` (used by the readiness poll)
- `firefox` (opened automatically after backend readiness)

---

## Launcher Modes

Three launcher variants are provided in `scripts/launchers/`.

| Mode | Script | Database | Use when |
|---|---|---|---|
| **stub** | `homemodel-stub.sh` | none | fast startup, UI smoke tests, demos |
| **real** | `homemodel-real.sh` | `<DB_PATH>` | production local use |
| **dev** | `homemodel-dev.sh` | `<DB_DEV_PATH>` | development — isolated from real data |

### Stub mode

- `HOMEMODEL_MODE=stub`
- No database required.
- Backend returns hardcoded fixture data.
- Best for quick UI checks and demoing without touching any database.

### Real mode

- `HOMEMODEL_MODE=real`
- `SCHEMASTORE_DB_PATH=<DB_PATH>`
- Uses a persistent SQLite database.
- SchemaStore creates schema tables automatically on first startup.

### Dev mode

- `HOMEMODEL_MODE=real`
- `SCHEMASTORE_DB_PATH=<DB_DEV_PATH>`
- Identical to real mode but uses a separate file so development work never
  affects production data.

---

## Shell Scripts

The three scripts are in `scripts/launchers/`.  Copy them to `<SCRIPT_DIR>`
and make them executable:

```bash
cp <REPO_ROOT>/scripts/launchers/homemodel-*.sh <SCRIPT_DIR>/
chmod +x <SCRIPT_DIR>/homemodel-*.sh
```

Each script accepts its paths via environment variables so you can set them
once in your shell profile instead of editing the scripts:

```bash
# add to ~/.bashrc or ~/.profile
export HOMEMODEL_REPO_ROOT="<REPO_ROOT>"
export HOMEMODEL_DATA_DIR="<DATA_DIR>"
```

If these variables are not set, the scripts fall back to the literal
`<REPO_ROOT>` / `<DATA_DIR>` placeholders and will exit with an error until
you replace them.

### What each script does

1. Sets required environment variables (`HOMEMODEL_MODE`, `SCHEMASTORE_DB_PATH`,
   `CORS_ALLOW_ORIGINS`).
2. Changes directory to `<REPO_ROOT>` so that `backend.main:app` resolves
   correctly.
3. Starts `<VENV_DIR>/bin/uvicorn backend.main:app --port 8000 --reload` in
   the background and records its PID.
4. Registers a `cleanup` function via `trap cleanup EXIT` that kills the
   backend when the script exits.
5. Polls `<APP_URL>/scene/manifest` with `curl` once per second until it
   responds.
6. Opens Firefox at `<APP_URL>`.
7. Waits on the backend process; the script (and terminal) stay open until
   the backend exits or the terminal is closed.

### Why `<VENV_DIR>/bin/uvicorn` directly

Running the venv's `uvicorn` binary directly (without activating the venv)
works correctly as long as the working directory is `<REPO_ROOT>`.  Python
imports like `backend.main:app` resolve from the working directory, so no
`source venv/bin/activate` step is needed in the script.

---

## Desktop Entries (.desktop files)

Desktop entries let you launch HomeModel from your application menu or file
manager.

### Install

```bash
# Copy .desktop files to your local applications directory
cp <REPO_ROOT>/scripts/launchers/homemodel-*.desktop \
   ~/.local/share/applications/

# Edit each file — replace <SCRIPT_DIR> with your actual script directory
nano ~/.local/share/applications/homemodel-stub.desktop
nano ~/.local/share/applications/homemodel-real.desktop
nano ~/.local/share/applications/homemodel-dev.desktop

# Refresh the application database (GNOME/KDE)
update-desktop-database ~/.local/share/applications/
```

### Example entry (stub)

```ini
[Desktop Entry]
Type=Application
Name=HomeModel (Stub)
Comment=Start HomeModel backend in stub mode and open Firefox (no database required)
Exec=bash /home/alice/Documents/scripts/homemodel-stub.sh
Terminal=true
Categories=Development;
```

Replace `/home/alice/Documents/scripts/homemodel-stub.sh` with the actual
path to the script on your machine.

### Terminal=true vs Terminal=false

| Setting | Behavior |
|---|---|
| `Terminal=true` *(recommended)* | A terminal window opens showing backend logs.  Closing the window stops the backend cleanly via the `cleanup` trap. |
| `Terminal=false` | No terminal window.  The backend keeps running silently until the process is killed manually. |

`Terminal=true` is recommended for all three modes because it gives you
visible logs and a straightforward way to stop the backend.

---

## Environment Variables

| Variable | Values | Default | Purpose |
|---|---|---|---|
| `HOMEMODEL_MODE` | `stub` \| `real` | `stub` | Stub returns fixture data; real queries SchemaStore |
| `SCHEMASTORE_DB_PATH` | filesystem path | `:memory:` | SQLite database file (real/dev mode only) |
| `CORS_ALLOW_ORIGINS` | comma-separated origins | `*` | Restricts CORS; set to `http://localhost:8000,http://127.0.0.1:8000` for local desktop use |

### CORS for local desktop use

Set `CORS_ALLOW_ORIGINS` to include both `localhost` and `127.0.0.1` to avoid
origin mismatch errors regardless of how the browser resolves the host:

```
CORS_ALLOW_ORIGINS=http://localhost:8000,http://127.0.0.1:8000
```

All three launcher scripts set this automatically.

---

## Readiness Check

Each launcher polls the backend before opening Firefox:

```bash
WAIT_SECS=0
MAX_WAIT=60
until curl -fs http://127.0.0.1:8000/scene/manifest > /dev/null 2>&1; do
    sleep 1
    WAIT_SECS=$((WAIT_SECS + 1))
    if [ "$WAIT_SECS" -ge "$MAX_WAIT" ]; then
        echo "ERROR: Backend did not become ready after ${MAX_WAIT}s."
        exit 1
    fi
done
```

This prevents the browser from opening a blank page while the backend is still
initializing.  The loop polls once per second and gives up after 60 seconds —
if the backend fails to start, check the terminal output for error messages.

---

## Cleanup Behavior

Each script registers a cleanup function that is called when the script exits
for any reason (normal exit, `Ctrl-C`, terminal close):

```bash
BACKEND_PID=""
cleanup() {
    if [ -n "$BACKEND_PID" ] && kill -0 "$BACKEND_PID" 2>/dev/null; then
        echo "Stopping backend (PID $BACKEND_PID)…"
        kill "$BACKEND_PID"
    fi
}
trap cleanup EXIT
```

`cleanup` is a plain shell function — it becomes the exit handler only because
of `trap cleanup EXIT`.  The backend process is stopped cleanly whenever:

- the terminal window is closed (`Terminal=true` desktop entry)
- you press `Ctrl-C` in the terminal
- the script reaches its end

---

## Quick Reference

```bash
# Create the data directory once (real and dev modes)
mkdir -p <DATA_DIR>

# Install scripts
cp <REPO_ROOT>/scripts/launchers/homemodel-*.sh <SCRIPT_DIR>/
chmod +x <SCRIPT_DIR>/homemodel-*.sh

# Set env vars in your shell profile
echo 'export HOMEMODEL_REPO_ROOT="<REPO_ROOT>"' >> ~/.bashrc
echo 'export HOMEMODEL_DATA_DIR="<DATA_DIR>"'   >> ~/.bashrc
source ~/.bashrc

# Run directly from the terminal
bash <SCRIPT_DIR>/homemodel-stub.sh    # stub mode
bash <SCRIPT_DIR>/homemodel-real.sh    # real mode
bash <SCRIPT_DIR>/homemodel-dev.sh     # dev mode

# Install desktop entries
cp <REPO_ROOT>/scripts/launchers/homemodel-*.desktop ~/.local/share/applications/
# edit each file to replace <SCRIPT_DIR> with your actual path
update-desktop-database ~/.local/share/applications/
```
