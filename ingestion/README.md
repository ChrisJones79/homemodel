# Ingestion

Data ingestion pipeline for measurements, images, and bulk entity imports.
Validation runs before every submission — no unvalidated data enters
`SchemaStore`.

---

## Overview

`ingestion/pipeline.py` provides the `Ingestion` class, which validates and
routes data to the correct `SchemaStore` methods.  `ingestion/validate.py`
implements all validation logic independently so it can be tested without a
store.

---

## Pipeline Methods

| Method | Delegates to | Notes |
|---|---|---|
| `submit_measurement(measurement)` | `SchemaStore.upsert_entity` | Validates measurement type and provenance |
| `submit_image(entity_id, image_record)` | `SchemaStore.attach_image` | Validates image source type and file path |
| `submit_bulk(batch)` | `SchemaStore.bulk_upsert` | Requires `conflict_strategy` in batch |
| `validate(data, schema)` | — | Returns `ValidationResult` `{valid, errors, warnings}` |

---

## Measurement Types

`laser_p2p` · `gps_point` · `image_derived` · `drone_telemetry`

## Image Source Types

`phone` · `drone_aerial` · `drone_ground` · `dslr` · `scan`

## Bulk Conflict Strategies

| Strategy | Behaviour |
|---|---|
| `skip` | Leave existing entity unchanged |
| `overwrite` | Always replace with incoming data |
| `version_bump` | Increment version number and keep revision history |

---

## Add to Store via Bulk Import

The bulk import endpoint is the recommended way to load multiple entities at
once (e.g. after a drone survey):

```python
from schema.store import SchemaStore
from ingestion.pipeline import Ingestion

store = SchemaStore("/path/to/homemodel.db")
ingestion = Ingestion(store)

batch = {
    "source": "drone_survey_2026",
    "conflict_strategy": "version_bump",
    "entities": [
        {
            "id": "tree-uuid-001",
            "type": "tree",
            "geometry": {"type": "Point", "coordinates": [-70.987, 42.988]},
            "position_gps": {"lat": 42.988, "lon": -70.987, "alt_m": 27.0},
            "provenance": "drone_survey_2026",
            "version": 1,
            "properties": {"species": "white_pine", "height_m": 18.0},
        },
    ],
}

result = ingestion.submit_bulk(batch)
# result → {"created": 1, "updated": 0, "skipped": 0, "errors": []}
```

---

## Running Tests

```bash
HOMEMODEL_MODE=stub pytest ingestion/ --tb=short -v
```

In stub mode, `SchemaStore` calls are mocked but all pipeline and validation
logic executes fully, so tests run without a database.

Test fixtures (`laser_measurement`, `drone_image`) are defined in
`ingestion/tests/conftest.py`.

### Test Coverage

| File | Tests | Coverage |
|---|---|---|
| `ingestion/pipeline.py` | 53 | 88% |
| `ingestion/validate.py` | — | 84% |
| **Module total** | **53** | **85%** |

---

## Contract Reference

- `contracts/ingestion_to_schema.yaml` — authoritative shapes for
  `Measurement`, `ImageRecord`, `EntityBatch`, and `ValidationResult`

---

## Code Layout

```
ingestion/
├── pipeline.py     # Ingestion class — submit_measurement, submit_image, submit_bulk
├── validate.py     # Validation logic — validate()
└── tests/
    ├── conftest.py     # Fixtures: laser_measurement, drone_image, store mock
    └── test_pipeline.py
```
