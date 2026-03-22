# 04 — Skill Files

## What Skill Files Are

Each work area has a skill file that defines:
- **Goal** — what "done" looks like for the current increment
- **Contracts** — which YAML files govern inputs/outputs
- **Validation** — commands that prove the increment works
- **Present** — what to show yourself (the "manager") to confirm quality

Skill files serve double duty:
1. **In the repo** as `.github/agents/*.agent.md` — agents read them
2. **In Spaces** as instruction text — you reference them when planning

## Template

```markdown
---
name: [Area Name]
description: [One-line purpose]
---

# [Area Name] Agent

## Goal
[What "done" looks like for the current increment]

## Contracts
- `contracts/[relevant].yaml` — [which surfaces]

## Process
1. Read the contract surface relevant to the issue
2. [Area-specific implementation step]
3. Write tests using fixtures from the contract YAML
4. Run validation commands
5. Only open the PR if all checks pass

## Validation
```
[exact commands to run]
```

## Present
[What artifact proves this works — test output, curl response, screenshot]

## Constraints
- [Hard rules for this area]
```

## Work Area 1: Schema & Data Store

File: `.github/agents/schema-builder.agent.md`

```markdown
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
```

## Work Area 7: Backend API

File: `.github/agents/backend-builder.agent.md`

```markdown
---
name: Backend Builder
description: FastAPI server bridging SchemaStore to the 3D viewer
---

# Backend Builder Agent

## Goal
A FastAPI server that exposes the backend_to_viewer contract surfaces
as REST endpoints, reading from SchemaStore.

## Contracts
- `contracts/backend_to_viewer.yaml` — SceneManifest, SceneTile, EntityMesh, ViewpointList
- `contracts/schema_to_backend.yaml` — Entity, EntityList (what SchemaStore returns)

## Process
1. Read both contract files
2. Implement FastAPI app in `backend/main.py`
3. In stub mode, return fixture data from contracts
4. In real mode, query SchemaStore
5. Run: `HOMEMODEL_MODE=stub pytest backend/ --tb=short -v`
6. Also: `HOMEMODEL_MODE=stub uvicorn backend.main:app &; curl localhost:8000/scene/manifest`

## Validation
```bash
HOMEMODEL_MODE=stub pytest backend/ --tb=short -v
HOMEMODEL_MODE=stub uvicorn backend.main:app --port 8000 &
curl -s localhost:8000/scene/manifest | python -m json.tool
kill %1
```

## Present
- pytest output
- curl output showing valid SceneManifest JSON matching contract

## Constraints
- FastAPI + uvicorn
- CORS enabled for LAN access
- All responses match contract field names exactly
- No direct SQLite access — always go through SchemaStore
```

## Remaining Skill Files to Create

- [ ] `.github/agents/terrain-builder.agent.md` (Area 2)
- [ ] `.github/agents/structure-builder.agent.md` (Area 3)
- [ ] `.github/agents/vegetation-builder.agent.md` (Area 4)
- [ ] `.github/agents/viewer-builder.agent.md` (Area 5)
- [ ] `.github/agents/ingestion-builder.agent.md` (Area 6)

These follow the same template. Create them as you start each area.

## Checkpoint

- [ ] Schema and Backend agent files committed
- [ ] Template understood — can create new skill files as needed
- [ ] Same instructions pasted into corresponding Copilot Spaces

→ Next: [[05-progress-log]]
