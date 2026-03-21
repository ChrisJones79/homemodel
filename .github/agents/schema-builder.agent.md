---
name: Schema Builder
description: Implements and tests the SchemaStore data layer
---

# Schema Builder Agent

## Goal
A working SchemaStore class backed by SQLite that implements all four
surfaces from schema_to_backend.yaml: get_entity, query_region,
upsert_entity, get_history.

## Contracts
- `contracts/schema_to_backend.yaml` — Entity, EntityList, UpsertResult, EntityHistory
- `contracts/domains_to_schema.yaml` — TerrainPatch, StructureEntity, VegetationEntity, BuildRecord
- `contracts/ingestion_to_schema.yaml` — Measurement, ImageRecord, EntityBatch, ValidationResult

## Process
1. Read all three contract files before writing any code
2. Implement SchemaStore in `schema/store.py`
3. Define Entity dataclass/TypedDict in `schema/models.py`
4. Write tests in `schema/tests/test_store.py`
5. Run: `HOMEMODEL_MODE=stub pytest schema/ --tb=short -v`
6. Only open the PR if all tests pass

## Validation
```bash
cd /path/to/homemodel
HOMEMODEL_MODE=stub pytest schema/ --tb=short -v
```

## Present
- pytest output showing all tests green
- A short summary of which contract surfaces are now implemented

## Constraints
- Python 3.11+, SQLite via built-in sqlite3 module
- Every entity: id (UUID), type, geometry, position_gps, provenance, version
- Version increments on update — never overwrite without bumping
- Provenance is required on every write
- geometry stored as JSON text in SQLite
- position_gps stored as three columns: lat REAL, lon REAL, alt_m REAL
