# Vegetation

Catalogs individual trees as `VegetationEntity` records in `SchemaStore`.
Every catalog run is audited with a `BuildRecord`.

---

## Overview

`vegetation/builder.py` provides `VegetationBuilder` — the single entry point
for converting tree survey data into first-class entities.
`vegetation/canopy.py` defines the `CanopyShape` and `HealthStatus`
enumerations used in entity validation.

---

## API Reference

### VegetationBuilder

| Method | Signature | Returns |
|---|---|---|
| `catalog` | `(survey_data, aerial_images=None) -> dict` | `{entities, build_record}` |

#### `catalog` parameters

| Parameter | Required fields | Notes |
|---|---|---|
| `survey_data` | `position_gps`, `properties.height_m`, `properties.canopy_radius_m`, `properties.canopy_shape` | `id` is generated if absent |
| `aerial_images` | — | Optional; reserved for future crown extraction |

#### `CanopyShape` values

`round` · `conical` · `spreading` · `columnar` · `irregular`

#### `HealthStatus` values

`healthy` · `stressed` · `dead` · `unknown` (default when omitted)

---

## Quick Usage

```python
from schema.store import SchemaStore
from vegetation.builder import VegetationBuilder

store = SchemaStore(":memory:")
builder = VegetationBuilder(store)

survey_data = [
    {
        "id": "tree-uuid-001",
        "position_gps": {"lat": 42.988, "lon": -70.987, "alt_m": 27.0},
        "properties": {
            "species": "white_pine",
            "height_m": 18.0,
            "canopy_radius_m": 3.5,
            "canopy_shape": "conical",
            "health": "healthy",
        },
    }
]

result = builder.catalog(survey_data)
# result → {
#   "entities": [{...}],
#   "build_record": {"domain": "vegetation", "entities_written": 1, "errors": [], ...}
# }
```

---

## Running Tests

```bash
HOMEMODEL_MODE=stub pytest vegetation/ --tb=short -v
```

### Test Coverage

| File | Tests | Coverage |
|---|---|---|
| `vegetation/builder.py` | 61 | 98% |
| `vegetation/canopy.py` | — | 100% |
| **Module total** | **61** | **98%** |

---

## Contract Reference

- `contracts/domains_to_schema.yaml` — `VegetationEntity` shape,
  `CanopyShape` and `HealthStatus` vocabularies, `BuildRecord` schema

---

## Code Layout

```
vegetation/
├── builder.py       # VegetationBuilder — catalog()
├── canopy.py        # CanopyShape and HealthStatus enums
└── tests/
    ├── conftest.py          # store, builder, single-tree survey fixtures
    └── test_builder.py      # 61 tests: entity fields, enums, build records, edge cases
```
