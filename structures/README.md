# Structures

Compiles floor plans, laser measurements, and images into hierarchical
`StructureEntity` records (structure → walls → rooms) written to `SchemaStore`.

---

## Overview

`structures/builder.py` provides `StructureBuilder` — the single entry point
for turning a floor plan dict into 3D geometry entities.
`structures/extrude.py` handles 2D-to-3D extrusion for walls and rooms.

Entities are hierarchical:

```
structure  (building / house)
  ├── wall     (parent_id → structure.id)
  └── room     (parent_id → structure.id)
```

Openings (doors and windows) are stored inside wall properties.  All
dimensions are in metres.

---

## API Reference

### StructureBuilder

| Method | Signature | Returns |
|---|---|---|
| `compile` | `(floorplan, measurements, images) -> dict` | `BuildRecord` |

#### `compile` parameters

| Parameter | Type | Description |
|---|---|---|
| `floorplan` | `dict` | Floor plan with `position_gps`, `walls`, `rooms`, `floor_level`, `material` |
| `measurements` | `list[dict]` | `Measurement` records from the ingestion pipeline |
| `images` | `list[dict]` | `ImageRecord` records from the ingestion pipeline |

#### Entity types produced

| Type | Key fields |
|---|---|
| `structure` | `position_gps`, `floor_level`, `material`, `dimensions`, `openings=[]` |
| `wall` | `parent_id`, `floor_level`, `material`, `dimensions`, `openings` |
| `room` | `parent_id`, `floor_level`, `material`, `dimensions`, `openings=[]` |

---

## Quick Usage

```python
from schema.store import SchemaStore
from structures.builder import StructureBuilder

store = SchemaStore(":memory:")
builder = StructureBuilder(store)

floorplan = {
    "id": "house-001",
    "position_gps": {"lat": 42.987, "lon": -70.987, "alt_m": 26.8},
    "floor_level": 0,
    "walls": [
        {
            "id": "wall-001",
            "start_point": [0.0, 0.0],
            "end_point": [5.0, 0.0],
            "height_m": 2.4,
        }
    ],
    "rooms": [
        {
            "id": "room-001",
            "boundary_points": [[0,0],[5,0],[5,4],[0,4]],
            "ceiling_height_m": 2.4,
        }
    ],
}

result = builder.compile(floorplan, measurements=[], images=[])
# result → {"domain": "structures", "entities_written": 3, "errors": [], ...}
```

---

## Running Tests

```bash
HOMEMODEL_MODE=stub pytest structures/ --tb=short -v
```

### Test Coverage

| File | Tests | Coverage |
|---|---|---|
| `structures/builder.py` | 39 | 90% |
| `structures/extrude.py` | — | 94% |
| **Module total** | **39** | **91%** |

Tests span two files: `test_builder.py` (StructureBuilder contract) and
`test_demo.py` (full floor plan scenario with walls, rooms, and openings).

---

## Contract Reference

- `contracts/domains_to_schema.yaml` — `StructureEntity` shape, `BuildRecord`
  schema, and provenance rules

---

## Code Layout

```
structures/
├── builder.py       # StructureBuilder — compile()
├── extrude.py       # extrude_wall(), extrude_room(), calculate_*_dimensions()
└── tests/
    ├── conftest.py      # store, builder, floorplan and measurement fixtures
    ├── test_builder.py  # 33 tests: entity types, provenance, openings, errors
    └── test_demo.py     # 6 tests: full floor plan integration scenario
```
