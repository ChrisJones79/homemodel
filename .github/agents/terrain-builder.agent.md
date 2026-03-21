---
name: Terrain Builder
description: Generates terrain mesh patches from elevation and aerial data
---

# Terrain Builder Agent

## Goal
A TerrainBuilder class that generates TerrainPatch entities from USGS
elevation data and aerial imagery, writing them into SchemaStore via
the domains_to_schema contract.

## Contracts
- `contracts/domains_to_schema.yaml` — TerrainPatch, BuildRecord
- `contracts/ingestion_to_schema.yaml` — ImageRecord (aerial images as input)

## Process
1. Read the TerrainPatch and BuildRecord surfaces in domains_to_schema.yaml
2. Implement TerrainBuilder in `terrain/builder.py`
3. Implement elevation grid parsing in `terrain/elevation.py`
4. Write tests in `terrain/tests/test_builder.py` using the terrain_patch fixture
5. Run: `HOMEMODEL_MODE=stub pytest terrain/ --tb=short -v`
6. Only open the PR if all tests pass

## Validation
```bash
HOMEMODEL_MODE=stub pytest terrain/ --tb=short -v
```

## Present
- pytest output showing all tests green
- A generated TerrainPatch entity matching the contract format

## Constraints
- USGS NED elevation data as primary source (GeoTIFF)
- Output triangulated mesh as vertices + faces
- All positions in WGS84 GPS coordinates {lat, lon, alt_m}
- Scene origin: lat 42.98743, lon -70.98709, alt_m 26.8
- In stub mode, use fixture elevation values — no network calls
- Log a BuildRecord for every generation run
