# HomeModel — Repository Instructions

## What This Project Is
A locally-hosted, LAN-accessible 3D navigable model of a house and
surrounding five-acre property. GPS coordinates and altitude are the
absolute positioning system.

## Architecture
- Hybrid model: structured data (JSON/SQLite) → build step → glTF → Three.js
- WebXR path for Valve Index VR
- Interface contracts in `contracts/` are the source of truth between areas
- Every datum tracks provenance and version

## Conventions
- Python 3.11+, FastAPI for backend
- Three.js for browser rendering
- SQLite for local data store
- All GPS coordinates use WGS84: {lat, lon, alt_m}
- Scene origin: lat 42.98743, lon -70.98709, alt_m 26.8
- `HOMEMODEL_MODE=stub` or `=real` toggles mock/live dependencies
- Individual trees are first-class entities

## Testing
- Every module must pass with `HOMEMODEL_MODE=stub`
- Test fixtures are in `fixtures/` and in the contract YAML files
- Run: `pytest --tb=short`

## What NOT To Do
- Do not hardcode file paths outside the project root
- Do not bypass the schema layer — all data goes through SchemaStore
- Do not merge geometry formats — always output glTF for the viewer