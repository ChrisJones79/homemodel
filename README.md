# HomeModel

A locally-hosted, LAN-accessible 3D navigable model of a house and 5-acre property.
GPS-anchored at **lat 42.98743, lon -70.98709, alt 26.8 m**. Rendered in Three.js
with WebXR (Valve Index) support. Backend is FastAPI + SQLite.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [Environment Variables](#environment-variables)
4. [Running the Backend](#running-the-backend)
5. [Running the Viewer](#running-the-viewer)
6. [Add to Store — POST /entities](#add-to-store--post-entities)
7. [Test Strategy](#test-strategy)
8. [Project Layout](#project-layout)
9. [Contracts and Fixtures](#contracts-and-fixtures)
10. [Troubleshooting](#troubleshooting)

---

## Prerequisites

| Dependency | Version | Notes |
|---|---|---|
| Python | 3.11+ | `python --version` |
| pip | latest | ships with Python |
| SQLite | 3.x | ships with Python |
| A modern browser | — | Chrome/Edge for WebXR; any browser for stub mode |

JavaScript runs directly in the browser — no Node.js, no bundler required.

---

## Quick Start

```bash
# 1. Clone and enter the repo
git clone https://github.com/ChrisJones79/homemodel.git
cd homemodel

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Start the backend (serves the viewer + API on one port)
HOMEMODEL_MODE=stub uvicorn backend.main:app --port 8000 --reload

# 4. Open the viewer in your browser
open http://localhost:8000          # macOS
xdg-open http://localhost:8000      # Linux
# Windows: navigate to http://localhost:8000 in any browser
```

The backend now serves the viewer HTML/JS at `http://localhost:8000/`, so all
API calls (`/scene/manifest`, `/nav/viewpoints`, etc.) are on the same origin —
no CORS or `file://` issues.

**Stub mode in the viewer:** append `?stub=1` to the URL
(`http://localhost:8000/?stub=1`) to bypass the backend entirely and load all
data from local `viewer/fixtures/` files.  This works even if the backend is
not running.

---

## Environment Variables

| Variable | Values | Default | Purpose |
|---|---|---|---|
| `HOMEMODEL_MODE` | `stub` \| `real` | `stub` | Stub returns hardcoded fixtures; real queries SchemaStore |
| `SCHEMASTORE_DB_PATH` | filesystem path | `:memory:` | SQLite database file path (real mode only) |
| `CORS_ALLOW_ORIGINS` | comma-separated origins | `*` | Restrict CORS for production LAN deployments |

### Stub vs Real Mode

- **stub** — All backend endpoints return hardcoded fixture data. No database
  required. Viewer fixture files in `viewer/fixtures/` are used when the viewer
  is opened with `?stub=1` or without a running backend.
- **real** — Backend queries a live SQLite database via `SchemaStore`. Set
  `SCHEMASTORE_DB_PATH` to a writable file path. The database schema is created
  automatically on first startup.

---

## Running the Backend

### Stub mode (recommended for development)

```bash
HOMEMODEL_MODE=stub uvicorn backend.main:app --port 8000 --reload
```

### Real mode (live database)

```bash
HOMEMODEL_MODE=real \
  SCHEMASTORE_DB_PATH=/path/to/homemodel.db \
  uvicorn backend.main:app --port 8000 --reload
```

Verify the backend is running:

```bash
curl http://localhost:8000/scene/manifest
```

Expected response (stub):

```json
{
  "bounds_gps": {"sw": {"lat": 42.985, "lon": -70.989}, "ne": {"lat": 42.990, "lon": -70.985}},
  "origin_gps": {"lat": 42.98743, "lon": -70.98709, "alt_m": 26.8},
  "entity_count": 1,
  "lod_levels": [...],
  "last_updated": "..."
}
```

---

## Running the Viewer

The viewer is a plain HTML page — no build step, no Node.js needed.

**Recommended (same-origin, all browsers):**

```bash
# Start the backend — it serves the viewer at the root path
HOMEMODEL_MODE=stub uvicorn backend.main:app --port 8000 --reload
# then open http://localhost:8000 in Firefox or Chrome
```

**Stub-only (no backend):**

```bash
cd viewer
python -m http.server 8080
# then open http://localhost:8080/?stub=1
```

Or open `viewer/index.html` directly as a `file://` URL **with `?stub=1`** — the
`file://` protocol works in both Firefox and Chrome for local fixture fetches.

**Recommended browser:** Firefox or Chrome.  WebXR (VR button) requires
Chrome/Edge with an attached headset; all other features work in Firefox.

**On-screen debug overlay:** a small panel appears in the bottom-left showing
loading status for the manifest, tiles, and viewpoints.  Press `` ` `` (backtick)
or click the panel header to toggle it.

**Stub mode in the viewer:** append `?stub=1` to the URL (e.g.
`http://localhost:8000/?stub=1`) or set `window.HOMEMODEL_MODE = 'stub'` in the
browser console. Stub mode loads from `viewer/fixtures/` without hitting the
backend.

**Click any mesh** in the scene to open the entity inspect panel (shows entity
id, type, and properties). Press **Escape** or click × to close it.

---

## Add to Store — POST /entities

The critical "add to store" feature writes a new entity (or updates an existing
one) to SchemaStore via `POST /entities`.

### Endpoint

```
POST http://localhost:8000/entities
Content-Type: application/json
```

### Minimal request body

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440001",
  "type": "tree",
  "geometry": {
    "type": "Point",
    "coordinates": [-70.987, 42.988]
  },
  "position_gps": {
    "lat": 42.988,
    "lon": -70.987,
    "alt_m": 27.0
  },
  "provenance": "manual",
  "version": 1,
  "properties": {
    "species": "white_pine",
    "height_m": 18.0
  }
}
```

### Expected response

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440001",
  "version": 1,
  "status": "created"
}
```

`status` is `"created"` for new entities and `"updated"` for existing ones
(version is incremented automatically in real mode).

### Full curl example

```bash
curl -s -X POST http://localhost:8000/entities \
  -H "Content-Type: application/json" \
  -d '{
    "id": "550e8400-e29b-41d4-a716-446655440001",
    "type": "tree",
    "geometry": {"type": "Point", "coordinates": [-70.987, 42.988]},
    "position_gps": {"lat": 42.988, "lon": -70.987, "alt_m": 27.0},
    "provenance": "manual",
    "version": 1,
    "properties": {"species": "white_pine", "height_m": 18.0}
  }'
```

In stub mode the endpoint acknowledges the request but does **not** persist the
entity. Switch to real mode to write to the database:

```bash
HOMEMODEL_MODE=real SCHEMASTORE_DB_PATH=homemodel.db \
  uvicorn backend.main:app --port 8000 --reload
```

Then re-run the `curl` above and verify persistence:

```bash
curl http://localhost:8000/entities/550e8400-e29b-41d4-a716-446655440001
```

---

## Test Strategy

### Run all tests

```bash
HOMEMODEL_MODE=stub pytest --tb=short -v
```

### Test summary

All 324 tests pass with 96% overall coverage.

| Module | Tests | Coverage | Command |
|---|---|---|---|
| `backend` | 82 | 92% | `HOMEMODEL_MODE=stub pytest backend/ --tb=short -v` |
| `schema` | 46 | 82% | `HOMEMODEL_MODE=stub pytest schema/ --tb=short -v` |
| `ingestion` | 53 | 85% | `HOMEMODEL_MODE=stub pytest ingestion/ --tb=short -v` |
| `terrain` | 5 | 87% | `HOMEMODEL_MODE=stub pytest terrain/ --tb=short -v` |
| `structures` | 39 | 91% | `HOMEMODEL_MODE=stub pytest structures/ --tb=short -v` |
| `vegetation` | 61 | 98% | `HOMEMODEL_MODE=stub pytest vegetation/ --tb=short -v` |
| `tools/plan_reader` | 38 | 99% | `HOMEMODEL_MODE=stub pytest tools/ --tb=short -v` |
| **Total** | **324** | **96%** | `HOMEMODEL_MODE=stub pytest --tb=short -v` |

### Run tests for a specific module

```bash
# Backend (entity endpoints, manifests, GLB serving)
HOMEMODEL_MODE=stub pytest backend/ --tb=short -v

# Schema store (upsert, get, query_region, get_history, bulk_upsert)
HOMEMODEL_MODE=stub pytest schema/ --tb=short -v

# Ingestion pipeline (measurements, images, bulk import)
HOMEMODEL_MODE=stub pytest ingestion/ --tb=short -v

# Domain builders
HOMEMODEL_MODE=stub pytest terrain/ structures/ vegetation/ --tb=short -v

# Plan reader (dimension parser)
HOMEMODEL_MODE=stub pytest tools/ --tb=short -v
```

### Verify "add to store" through the API

1. Start the backend in real mode (see above).
2. `POST /entities` with a new entity body (see [curl example](#full-curl-example)).
3. `GET /entities/<id>` — confirms the entity was persisted.
4. `POST /entities` again with the same `id` but different `properties` — response
   should show `"status": "updated"` and an incremented `version`.
5. `GET /entities/<id>/history` — shows the full revision history (if implemented).

---

## Project Layout

```
homemodel/
├── backend/          # FastAPI server (main.py) — see backend/README.md
├── schema/           # SchemaStore (SQLite) — see schema/README.md
├── ingestion/        # Measurement/image ingestion pipeline — see ingestion/README.md
├── terrain/          # TerrainBuilder (elevation grid → patches) — see terrain/README.md
├── structures/       # StructureBuilder (floor plans → walls/rooms) — see structures/README.md
├── vegetation/       # VegetationBuilder (tree survey → VegetationEntity) — see vegetation/README.md
├── viewer/           # Three.js + WebXR browser viewer — see viewer/README.md
├── tools/
│   └── plan_reader/  # Dimension parser for architectural drawings — see tools/plan_reader/README.md
├── contracts/        # Interface contracts (source of truth for all data shapes)
├── scripts/          # Manager script + tasks.yaml (agent task tracking)
├── planning/         # Project planning documents and progress log
├── requirements.txt
└── copilot-instructions.md
```

---

## Contracts and Fixtures

All data shapes are defined as YAML contracts in `contracts/`. These are the
canonical source of truth for request/response bodies, entity fields, and
inter-module interfaces.

| File | Governs |
|---|---|
| `contracts/backend_to_viewer.yaml` | REST endpoint shapes served to the viewer |
| `contracts/schema_to_backend.yaml` | SchemaStore → Backend method signatures |
| `contracts/domains_to_schema.yaml` | Domain builders → SchemaStore entity shapes |
| `contracts/ingestion_to_schema.yaml` | Ingestion pipeline → SchemaStore contracts |
| `contracts/viewer_to_webxr.yaml` | Viewer → WebXR session handoff |

Test fixtures live in:

- `viewer/fixtures/` — scene manifest, entity tree, and viewpoints for stub
  mode
- Each module's `tests/` directory — domain-specific fixtures (see conftest.py)

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `ModuleNotFoundError: fastapi` | Dependencies not installed | `pip install -r requirements.txt` |
| Backend returns `{"detail":"Not Found"}` | Wrong URL or endpoint | Check `GET /scene/manifest` first |
| Viewer shows blank / black scene | Backend not running, or viewer opened as `file://` without `?stub=1` | Start backend then open `http://localhost:8000` |
| Debug overlay shows ❌ manifest | Viewer not served from backend | Open `http://localhost:8000` or add `?stub=1` |
| `POST /entities` returns `200` but data not persisted | Running in stub mode | Set `HOMEMODEL_MODE=real` |
| `OperationalError: unable to open database` | DB path not writable | Check `SCHEMASTORE_DB_PATH` |
| CORS errors in browser console | Backend CORS not configured | Set `CORS_ALLOW_ORIGINS=http://localhost:8080` |
| WebXR button disabled | Browser doesn't support WebXR | Use Chrome/Edge on desktop or a WebXR-capable device |

### Further reading

- `copilot-instructions.md` — project conventions, coordinate system, agent rules
- `planning/05-progress-log.md` — development history and current state
- `planning/00-master-plan.md` — architecture overview and phased plan
- `contracts/` — authoritative data shape definitions
- `backend/README.md` — backend endpoints and mode details
- `viewer/README.md` — viewer usage, stub mode, and WebXR
- `schema/README.md` — SchemaStore API reference
- `ingestion/README.md` — ingestion pipeline and bulk import
- `terrain/README.md` — TerrainBuilder and elevation data
- `structures/README.md` — StructureBuilder and floor plan compilation
- `vegetation/README.md` — VegetationBuilder and tree survey catalog
- `tools/plan_reader/README.md` — dimension parser for architectural drawings
