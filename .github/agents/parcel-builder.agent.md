# Parcel Builder Agent

## Goal

Implement the `parcels/` domain package that ingests vector features from the
Exeter town WMS into homemodel.  The primary data source is the public
MapServer WMS at `https://www.mapsonline.net/cgi-bin/mapserv`.

## Contracts

- `contracts/map_to_ingestion.yaml` — ParcelFeature and MapFeature shapes,
  WMS layer index, coordinate transform requirements
- `contracts/ingestion_to_schema.yaml` — EntityBatch / ValidationResult
  (bulk submission surface)
- `contracts/schema_to_backend.yaml` — Entity shape stored in SchemaStore

## Process

1. Create `parcels/` package with:
   - `parcels/__init__.py`
   - `parcels/builder.py` — `ParcelBuilder` class
   - `parcels/wms.py` — WMS client (GetCapabilities, GetFeatureInfo)
   - `parcels/transform.py` — coordinate reprojection (EPSG:3437 → WGS84)
   - `parcels/tests/conftest.py`, `parcels/tests/test_builder.py`

2. `parcels/wms.py` — `WMSClient`:
   - `get_capabilities() -> dict` — parse WMS 1.1.1 GetCapabilities XML
   - `get_feature_info(layer, bbox, x, y, width, height) -> dict` — parse JSON response
   - In stub mode return fixture responses immediately (no HTTP)

3. `parcels/transform.py`:
   - `web_mercator_to_wgs84(x, y) -> (lon, lat)` — EPSG:900913 → EPSG:4326
   - `nh_stateplane_to_wgs84(x, y) -> (lon, lat)` — EPSG:3437 → EPSG:4326
   - Use `pyproj.Transformer`; cache transformer instances

4. `parcels/builder.py` — `ParcelBuilder(store: SchemaStore)`:
   - `fetch_parcel(lat, lon) -> dict` — build BBOX, call GetFeatureInfo,
     transform geometry, return ParcelFeature dict
   - `fetch_features(layer_id, bbox_wgs84) -> list[dict]` — generic layer fetch
   - `ingest(lat, lon) -> UpsertResult` — fetch + validate + submit via
     `Ingestion.submit_bulk()` with `conflict_strategy: overwrite`
   - Log a BuildRecord after every ingest run

5. Tests (`parcels/tests/`):
   - Fixtures: stub WMS JSON response, sample BBOX, sample lat/lon
   - `test_transform_web_mercator` — round-trip accuracy < 1m
   - `test_transform_nh_stateplane` — round-trip accuracy < 1m
   - `test_fetch_parcel_stub` — returns valid ParcelFeature in stub mode
   - `test_ingest_stub` — end-to-end: fetch → validate → upsert

## Validation

```
HOMEMODEL_MODE=stub pytest parcels/ --tb=short -v
```

## Constraints

- Option A (pure WMS) is the primary path — no Playwright dependency
- `pyproj` is already in `requirements.txt`; do not add new dependencies
- All positions stored as WGS84 `{lat, lon, alt_m}`; alt_m defaults to scene
  alt (26.8 m) when not available from WMS response
- In stub mode: no HTTP requests, no pyproj calls; return fixture data
- Provenance must include `source: "exeter_wms"` and `fetched_at` timestamp
- Rate-limit live WMS calls to 1 request/second (use `time.sleep`)
- Cache `GetCapabilities` response for the process lifetime
- Follow the class-based test layout used by terrain/, vegetation/, structures/
