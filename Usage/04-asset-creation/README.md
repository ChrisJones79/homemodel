# Usage 04 — Asset Creation

Create a new entity record in the database directly via the REST API.  
This is the simplest programmatic write path — a single HTTP request adds or updates one entity.

For creating an entirely new database (rather than adding to an existing one), see  
[`POST /databases`](#post-databases--new-database-with-first-entity) below.

---

## What it does

- Accepts a full entity payload via `POST /entities`.
- Validates and writes the entity to `SchemaStore` via `upsert_entity()`.
- Returns `"status": "created"` for new entities and `"status": "updated"` for existing ones  
  (version is incremented automatically in real mode).

---

## Components involved

| Component | File | Role |
|-----------|------|------|
| Backend endpoint | `backend/main.py` | `POST /entities` → `UpsertResult` |
| SchemaStore | `schema/store.py` | `upsert_entity(entity)` |
| Pydantic models | `schema/models.py` | `Entity`, `UpsertResult` |

---

## POST /entities — create or update a single entity

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

`status` is `"created"` for a new entity and `"updated"` for an existing one  
(version increments automatically in real mode).

### Full curl example

```bash
# Start backend in real mode
HOMEMODEL_MODE=real \
  SCHEMASTORE_DB_PATH=homemodel.db \
  uvicorn backend.main:app --port 8000 --reload

# Create the entity
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

# Confirm it was persisted
curl http://localhost:8000/entities/550e8400-e29b-41d4-a716-446655440001
```

---

## POST /databases — new database with first entity

Creates a new `.db` file and writes the provided entity into it as its first record.  
Useful for starting a new, isolated dataset without affecting an existing database.

### Request body

```json
{
  "db_name": "survey_2024",
  "entity": {
    "id": "...",
    "type": "structure",
    ...
  }
}
```

### Expected response

```json
{
  "db_name": "survey_2024",
  "entity_id": "...",
  "status": "created"
}
```

---

## Required entity fields

Every entity written to `SchemaStore` must include:

| Field | Type | Notes |
|-------|------|-------|
| `id` | UUID string | Unique identifier |
| `type` | string | e.g. `tree`, `structure`, `terrain_patch` |
| `geometry` | GeoJSON object | `Point`, `Polygon`, etc. |
| `position_gps` | `{lat, lon, alt_m}` | WGS84; alt_m in metres |
| `provenance` | string | Source of the data (e.g. `manual`, `drone`) |
| `version` | int | Starts at 1; auto-incremented on update |
| `properties` | dict | Domain-specific key/value pairs |

---

## Relevant contracts

- `contracts/schema_to_backend.yaml` — `Entity`, `UpsertResult`
- `contracts/backend_to_viewer.yaml` — `Entity` shape served back to the viewer
