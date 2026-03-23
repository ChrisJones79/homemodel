# Backend

FastAPI server that implements the `backend_to_viewer` and `schema_to_backend`
contract surfaces.  It is the single HTTP entry point for the viewer and for
any external tool that needs to read or write entities.

---

## Endpoints

| Method | Path | Returns | Notes |
|---|---|---|---|
| `GET` | `/scene/manifest` | `SceneManifest` | Scene bounds, origin GPS, entity count |
| `GET` | `/nav/viewpoints` | `ViewpointList` | Named camera positions |
| `GET` | `/entities` | `EntityList` | Requires `?bbox=sw_lat,sw_lon,ne_lat,ne_lon` |
| `GET` | `/entities/{id}` | `Entity` | Full entity with geometry and properties |
| `POST` | `/entities` | `UpsertResult` | Create or update an entity (**add to store**) |
| `GET` | `/scene/tiles/{z}/{x}/{y}.glb` | GLB binary | Terrain tile mesh (stub returns minimal GLB) |
| `GET` | `/entities/{id}/mesh` | GLB binary | Entity mesh (stub returns minimal GLB) |

Full request/response shapes are in `contracts/backend_to_viewer.yaml` and
`contracts/schema_to_backend.yaml`.

---

## Modes

The server behaviour is controlled by `HOMEMODEL_MODE`:

- **stub** (default) — every endpoint returns hardcoded fixture data from the
  contract. No database is needed. Safe for local development and CI.
- **real** — `GET /entities*` and `POST /entities` delegate to `SchemaStore`.
  Requires `SCHEMASTORE_DB_PATH` to point to a writable SQLite file.

```bash
# Stub mode
HOMEMODEL_MODE=stub uvicorn backend.main:app --port 8000 --reload

# Real mode
HOMEMODEL_MODE=real \
  SCHEMASTORE_DB_PATH=/path/to/homemodel.db \
  uvicorn backend.main:app --port 8000 --reload
```

---

## Running Tests

```bash
HOMEMODEL_MODE=stub pytest backend/ --tb=short -v
```

Tests cover both stub and real mode via `stub_client` / `real_client` fixtures
in `backend/tests/`.

### Testing POST /entities (add to store)

**Stub mode** — confirms the endpoint accepts a valid body and returns a
well-formed `UpsertResult`:

```bash
HOMEMODEL_MODE=stub pytest backend/tests/test_entities.py -k "post" -v
```

**Real mode end-to-end**:

```bash
# 1. Start real-mode server
HOMEMODEL_MODE=real SCHEMASTORE_DB_PATH=/tmp/test.db \
  uvicorn backend.main:app --port 8000 &

# 2. POST a new entity
curl -s -X POST http://localhost:8000/entities \
  -H "Content-Type: application/json" \
  -d '{
    "id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
    "type": "tree",
    "geometry": {"type": "Point", "coordinates": [-70.987, 42.988]},
    "position_gps": {"lat": 42.988, "lon": -70.987, "alt_m": 27.0},
    "provenance": "manual",
    "version": 1,
    "properties": {}
  }'
# → {"id": "aaaaaaaa-...", "version": 1, "status": "created"}

# 3. Confirm persistence
curl -s http://localhost:8000/entities/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee
# → full Entity JSON
```

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `HOMEMODEL_MODE` | `stub` | `stub` or `real` |
| `SCHEMASTORE_DB_PATH` | `:memory:` | SQLite file path (real mode) |
| `CORS_ALLOW_ORIGINS` | `*` | Comma-separated allowed origins |

---

## Code Layout

```
backend/
├── main.py        # FastAPI app, all endpoints, Pydantic models
├── __init__.py
└── tests/
    ├── test_manifest.py   # /scene/manifest, /nav/viewpoints
    ├── test_entities.py   # /entities CRUD
    └── test_glb.py        # /scene/tiles, /entities/{id}/mesh
```

---

## See Also

- Root `README.md` for full local setup instructions
- `contracts/backend_to_viewer.yaml` — viewer-facing response shapes
- `contracts/schema_to_backend.yaml` — SchemaStore method contracts
- `schema/README.md` — SchemaStore API
