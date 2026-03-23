# Schema

SQLite-backed entity store (`SchemaStore`) used by the backend, domain
builders, and ingestion pipeline.

---

## Overview

`schema/store.py` implements `SchemaStore` — a thin wrapper around a SQLite
database that manages entities, their revision history, images, and build
records.  The database schema is created automatically on construction.

---

## API Reference

### Core entity methods

| Method | Signature | Returns |
|---|---|---|
| `upsert_entity` | `(entity: dict) -> dict` | `UpsertResult` — `{id, version, status}` |
| `get_entity` | `(id: str) -> dict` | `Entity` dict or `None` |
| `query_region` | `(bbox: tuple) -> dict` | `EntityList` — `{entities, total_count}` |
| `get_history` | `(id: str) -> dict` | `EntityHistory` — revisions newest-first |

### Image and bulk methods

| Method | Signature | Returns |
|---|---|---|
| `attach_image` | `(entity_id: str, image_record: dict) -> str` | Image UUID |
| `bulk_upsert` | `(batch: dict) -> dict` | `{created, updated, skipped, errors}` |

`bulk_upsert` supports three conflict strategies (set via `batch["conflict_strategy"]`):

- `skip` — leave existing entities unchanged
- `overwrite` — always replace
- `version_bump` — increment version and keep revision history

### Build record methods

| Method | Signature | Returns |
|---|---|---|
| `log_build` | `(build_record: dict) -> None` | — |
| `get_build_records` | `(domain: str \| None) -> list` | List of `BuildRecord` dicts |

---

## Quick Usage

```python
from schema.store import SchemaStore

store = SchemaStore(":memory:")          # or a file path for persistence

result = store.upsert_entity({
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "type": "tree",
    "geometry": {"type": "Point", "coordinates": [-70.987, 42.988]},
    "position_gps": {"lat": 42.988, "lon": -70.987, "alt_m": 27.0},
    "provenance": "manual",
    "version": 1,
    "properties": {"species": "white_pine"},
})
# result → {"id": "...", "version": 1, "status": "created"}

entity = store.get_entity("550e8400-e29b-41d4-a716-446655440000")
history = store.get_history("550e8400-e29b-41d4-a716-446655440000")
```

---

## Running Tests

```bash
HOMEMODEL_MODE=stub pytest schema/ --tb=short -v
```

Test fixtures and helpers are in `schema/tests/conftest.py`.

---

## Contract Reference

- `contracts/schema_to_backend.yaml` — entity method signatures used by the
  backend
- `contracts/domains_to_schema.yaml` — entity shapes produced by domain
  builders
- `contracts/ingestion_to_schema.yaml` — image and bulk import contracts

---

## Code Layout

```
schema/
├── store.py        # SchemaStore class — all database logic
├── models.py       # Shared data models / constants
└── tests/
    ├── conftest.py     # store fixture (in-memory SchemaStore)
    └── test_store.py   # Full test suite
```
