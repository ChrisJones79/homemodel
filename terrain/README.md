# Terrain

Generates `TerrainPatch` entities from USGS NED elevation data and optional
aerial imagery.  Patches are written to `SchemaStore` and a `BuildRecord` is
logged after every generation run.

---

## Overview

`terrain/builder.py` provides `TerrainBuilder` — the single entry point for
producing terrain geometry.  `terrain/elevation.py` handles GeoTIFF parsing,
triangulation, and slope calculation.  In stub mode (`HOMEMODEL_MODE=stub`) a
built-in fixture grid is used so no real data files are required.

---

## API Reference

### TerrainBuilder

| Method | Signature | Returns |
|---|---|---|
| `generate_patches` | `(elevation_data=None, aerial_images=None) -> list[dict]` | List of `TerrainPatch` entity dicts |

`elevation_data` is an `ElevationGrid` from `terrain.elevation`.  Pass `None`
in stub mode to use the built-in fixture grid.

`aerial_images` is an optional list of image records from the ingestion
pipeline; currently used only to populate `texture_source` metadata.

Each returned entity has type `"terrain_patch"` and includes:

- `geometry` — `{vertices, faces}` from triangulation
- `position_gps` — patch centre `{lat, lon, alt_m}`
- `bounds_gps` — `{sw, ne}` bounding box
- `resolution_m` — grid cell size in metres
- `provenance` — source type `"usgs_ned"`, timestamp
- `properties` — `elevation_source`, `texture_source`, `slope_avg_deg`

---

## Quick Usage

```python
from schema.store import SchemaStore
from terrain.builder import TerrainBuilder

store = SchemaStore(":memory:")
builder = TerrainBuilder(store)

# Stub mode — uses built-in fixture grid
patches = builder.generate_patches()
print(patches[0]["type"])           # "terrain_patch"
print(patches[0]["properties"])     # elevation_source, slope_avg_deg, ...
```

---

## Running Tests

```bash
HOMEMODEL_MODE=stub pytest terrain/ --tb=short -v
```

### Test Coverage

| File | Tests | Coverage |
|---|---|---|
| `terrain/builder.py` | 5 | 90% |
| `terrain/elevation.py` | — | 85% |
| **Module total** | **5** | **87%** |

All five tests run without network access or real elevation files.

---

## Contract Reference

- `contracts/domains_to_schema.yaml` — `TerrainPatch` entity shape and
  `BuildRecord` schema

---

## Code Layout

```
terrain/
├── builder.py       # TerrainBuilder — generate_patches()
├── elevation.py     # ElevationGrid, parse_geotiff(), triangulate(), compute_slope_avg_deg()
└── tests/
    ├── conftest.py      # store + terrain_patch fixtures
    └── test_builder.py  # 5 tests: patch shape, storage, build record, stub mode
```
