# Usage 05 — Data Ingestion

Everything that feeds data *into* the database at scale or through an automated pipeline lives  
here.  There are six distinct ingestion varieties, each targeting a different source or format.  
All of them ultimately write through `SchemaStore` (`schema/store.py`).

---

## Overview

| # | Variety | Entry point | What it ingests |
|---|---------|-------------|-----------------|
| A | [Measurement submission](#a-measurement-submission) | `Ingestion.submit_measurement()` | Laser, GPS, image-derived, or drone-telemetry point measurements |
| B | [Image attachment](#b-image-attachment) | `Ingestion.submit_image()` | Photo / drone imagery metadata linked to an entity |
| C | [Bulk import](#c-bulk-import) | `Ingestion.submit_bulk()` | A batch of entities with a conflict-resolution strategy |
| D | [Domain builders](#d-domain-builders) | `TerrainBuilder`, `StructureBuilder`, `VegetationBuilder` | Procedurally generated entity records from raw source data |
| E | [Map / parcel ingestion](#e-map--parcel-ingestion) | Parcel Builder | Parcel and feature data from the Exeter town WMS |
| F | [Plan reader pipeline](#f-plan-reader-pipeline) | `tools/plan_reader/` | Floor-plan photographs → `StructureEntity` records via Claude Vision |

All six varieties validate data before it reaches `SchemaStore`.  
In stub mode (`HOMEMODEL_MODE=stub`) `SchemaStore` calls are mocked — pipeline logic still runs.

---

## A — Measurement Submission

Submits a single field measurement (taken with a laser, GPS, drone, or derived from an image)  
into the store as an entity.

**Entry point:** `ingestion/pipeline.py` → `Ingestion.submit_measurement(measurement: dict)`  
**Measurement types:** `laser_p2p`, `gps_point`, `image_derived`, `drone_telemetry`

```python
from ingestion.pipeline import Ingestion
from schema.store import SchemaStore

store = SchemaStore(db_path="homemodel.db")
ingestion = Ingestion(store)

result = ingestion.submit_measurement({
    "id": "...",
    "type": "laser_p2p",
    "value_m": 4.32,
    "position_gps": {"lat": 42.9874, "lon": -70.9871, "alt_m": 26.8},
    "provenance": "laser_disto_d2",
    "timestamp": "2024-06-01T10:00:00Z"
})
# result → {"id": "...", "version": 1, "status": "created"}
```

**Validation:** `ingestion/validate.py` — required fields, numeric range checks, provenance required.  
**Contract:** `contracts/ingestion_to_schema.yaml` — `Measurement` shape.

---

## B — Image Attachment

Attaches image metadata (from a phone, drone, DSLR, or 3-D scan) to an existing entity.  
Stores a record in the `images` table linked by `entity_id` and returns an `image_id` UUID.

**Entry point:** `ingestion/pipeline.py` → `Ingestion.submit_image(image: dict)`  
**Source types:** `phone`, `drone_aerial`, `drone_ground`, `dslr`, `scan`

```python
result = ingestion.submit_image({
    "entity_id": "550e8400-...",
    "source": "drone_aerial",
    "file_path": "/data/images/aerial_north.jpg",
    "captured_at": "2024-06-01T09:30:00Z",
    "provenance": "dji_mini3"
})
# result → {"image_id": "<uuid>"}
```

**SchemaStore call:** `SchemaStore.attach_image(entity_id, image_record)` → image_id (UUID).  
**Contract:** `contracts/ingestion_to_schema.yaml` — `ImageRecord`.

---

## C — Bulk Import

Imports a list of entities in one call with a **conflict-resolution strategy** for any that  
already exist in the store.

**Entry point:** `ingestion/pipeline.py` → `Ingestion.submit_bulk(batch: dict)`  
**SchemaStore call:** `SchemaStore.bulk_upsert(batch)`

### Conflict strategies

| Strategy | Behaviour |
|----------|-----------|
| `skip` | Ignore any entity that already exists — do not overwrite. |
| `overwrite` | Always replace the existing record with the new data. |
| `version_bump` | Increment the version number and keep the old record as history. |

```python
result = ingestion.submit_bulk({
    "entities": [ { ...entity1... }, { ...entity2... } ],
    "conflict_strategy": "version_bump",
    "provenance": "survey_2024_batch"
})
# result → {"created": 12, "updated": 3, "skipped": 0}
```

**Contract:** `contracts/ingestion_to_schema.yaml` — `EntityBatch`, `ValidationResult`.

---

## D — Domain Builders

Three specialised builders translate raw source data into fully-formed `Entity` records and  
write them into `SchemaStore` via a `BuildRecord` that logs every run.

### TerrainBuilder (`terrain/`)

Converts USGS NED elevation data (GeoTIFF) into triangulated mesh patches.

```python
from terrain.builder import TerrainBuilder
builder = TerrainBuilder(store)
builder.build(elevation_path="ned_data.tif", bounds_gps={...})
```

Output: `TerrainPatch` entities stored with `type="terrain_patch"`.  
Contract: `contracts/domains_to_schema.yaml` — `TerrainPatch`, `BuildRecord`.

### StructureBuilder (`structures/`)

Compiles laser and image-derived measurements into a hierarchical structure entity tree  
(structure → walls → rooms) with openings (doors, windows) stored on walls.

```python
from structures.builder import StructureBuilder
builder = StructureBuilder(store)
builder.build(measurements=[...])
```

Output: `StructureEntity` records with `parent_id` links, `floor_level`, and opening lists.  
Contract: `contracts/domains_to_schema.yaml` — `StructureEntity`, `BuildRecord`.

### VegetationBuilder (`vegetation/`)

Catalogs individual trees and vegetation from a field survey into first-class entities.  
Every tree is stored as its own record — no grouping or simplification.

```python
from vegetation.builder import VegetationBuilder
builder = VegetationBuilder(store)
builder.build(survey=[...])
```

Required fields: `position_gps`, `height_m`, `canopy_radius_m`, `canopy_shape`.  
Optional: `species`, `dbh_cm`, `health`, `tags`.  
Contract: `contracts/domains_to_schema.yaml` — `VegetationEntity`, `BuildRecord`.

---

## E — Map / Parcel Ingestion

Fetches parcel boundaries and map features from the **Exeter, NH town WMS** (mapsonline.net)  
and writes them to `SchemaStore` as `EntityBatch` records.

**Builder:** Parcel Builder (skill id `parcel-builder`, area 8).  
**Contracts:** `contracts/map_to_ingestion.yaml` — `ParcelFeature`, `MapFeature`; then normal  
`EntityBatch` path into `SchemaStore`.

Key constraints:
- Uses WMS `GetFeatureInfo` (no Playwright dependency).
- All positions stored as WGS84 `{lat, lon, alt_m=26.8}`.
- Provenance includes `source: "exeter_wms"` and a `fetched_at` timestamp.
- Live WMS calls are rate-limited to 1 request/second.
- `GetCapabilities` response is cached for the process lifetime.
- In stub mode no HTTP requests are made; fixture data is returned instead.

**Recon document:** `planning/06-exeter-map-recon.md`

---

## F — Plan Reader Pipeline

Converts a **photograph of an architectural floor plan** into `StructureEntity` records  
using Claude Vision for layout extraction and `dimensions.py` for unit parsing.

**Module:** `tools/plan_reader/`  
**Contracts:** `contracts/domains_to_schema.yaml` — `StructureEntity`, `BuildRecord`;  
`contracts/ingestion_to_schema.yaml` — `Measurement`, `EntityBatch`.

Pipeline stages:

1. **Vision** (`vision.py`) — sends the plan image to the Anthropic Claude API; receives  
   a structured layout description with room labels and raw dimension strings.
2. **Dimension parser** (`dimensions.py`) — converts feet/inches strings (e.g. `12'6"`)  
   to metres.  29 unit tests cover edge cases; this file is read-only.
3. **Geometry** (`geometry.py`) — assembles wall polygons and room boundaries from the  
   parsed dimensions.
4. **Pipeline** (`pipeline.py`) — orchestrates the above stages and emits an `EntityBatch`  
   ready for `Ingestion.submit_bulk()`.

In stub mode no Anthropic API calls are made and no image files are read.  
The Anthropic SDK is imported only inside the live-mode branch.

**Design document:** `tools/plan_reader/DESIGN.md`

---

## Relevant contracts

| Contract file | Covers |
|---------------|--------|
| `contracts/ingestion_to_schema.yaml` | `Measurement`, `ImageRecord`, `EntityBatch`, `ValidationResult` |
| `contracts/domains_to_schema.yaml` | `TerrainPatch`, `StructureEntity`, `VegetationEntity`, `BuildRecord` |
| `contracts/map_to_ingestion.yaml` | `ParcelFeature`, `MapFeature`, WMS layer index |
| `contracts/schema_to_backend.yaml` | `Entity`, `EntityList`, `UpsertResult` |
