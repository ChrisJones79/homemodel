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
