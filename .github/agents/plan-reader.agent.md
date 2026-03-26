# Plan Reader Agent

## Goal

Complete the `tools/plan_reader/` vision pipeline so that a user can go from
a floor-plan photograph to a validated `StructureEntity` ready for
`StructureBuilder.compile()`.

The dimension parser (`dimensions.py`) and its tests are already implemented
and green.  This agent implements the next layer: vision extraction, geometry
reconstruction, GPS anchoring, and the end-to-end submission workflow.

## Contracts

- `contracts/domains_to_schema.yaml` — StructureEntity and BuildRecord shapes
- `contracts/ingestion_to_schema.yaml` — Measurement, EntityBatch surfaces
- `tools/plan_reader/DESIGN.md` — full pipeline design and v1 MVP scope

## Process

1. **`tools/plan_reader/vision.py`** — `VisionExtractor` class:
   - `extract(image_path, scale_m_per_px) -> ExtractionResult`
   - `ExtractionResult` dataclass: `dimensions_raw`, `room_labels`,
     `opening_types`, `raw_response`
   - In stub mode: return a deterministic fixture extraction without calling
     the Claude API; guard with `os.getenv("HOMEMODEL_MODE") == "stub"`
   - In live mode: call Anthropic Messages API with the image encoded as
     base64; use model `claude-opus-4-5`; prompt requests JSON with keys
     `dimensions`, `room_labels`, `opening_types`
   - Parse each raw dimension string with `parse_dimension()` from
     `dimensions.py`; skip strings that return `None`

2. **`tools/plan_reader/geometry.py`** — `reconstruct_walls(dims, labels)`:
   - Accept a list of dimension floats (metres) and room labels
   - Return a list of wall segment dicts `{start, end, length_m, label}`
   - Use a simple linear layout for v1: walls arranged left-to-right along
     the X axis; first wall origin at `(0, 0)`
   - Return an empty list for empty input

3. **`tools/plan_reader/pipeline.py`** — `PlanReader(store: SchemaStore)`:
   - `read(image_path, scale_m_per_px, annotated_dims=None) -> dict`:
     1. Call `VisionExtractor.extract()`
     2. Parse extracted dimensions with `parse_dimension()`
     3. If `annotated_dims` provided, call `validate_dimensions()` and raise
        `ValueError` if `ok == False` (caller must override explicitly)
     4. Call `reconstruct_walls()`
     5. Anchor to GPS: apply scene origin offset
        (lat 42.98743, lon -70.98709, alt_m 26.8)
     6. Build a `StructureEntity`-shaped dict; submit via
        `Ingestion.submit_bulk()` with `conflict_strategy: overwrite`
     7. Log a BuildRecord via `store.log_build()`
     8. Return `{extraction, validation, walls, upsert_result, build_record}`

4. **Tests** (`tools/plan_reader/tests/`):
   - `test_vision.py` — stub extraction returns parseable dimensions;
     `parse_dimension` round-trip on all returned strings
   - `test_geometry.py` — walls have correct lengths; empty input → empty list
   - `test_pipeline.py` — end-to-end in stub mode: read() returns all keys;
     BuildRecord logged; ValidationError raised on mismatch

## Validation

```
HOMEMODEL_MODE=stub pytest tools/ --tb=short -v
```

## Constraints

- `dimensions.py` is read-only — do not modify it
- In stub mode: no Anthropic API calls, no filesystem reads of images
- Anthropic SDK (`anthropic`) must only be imported inside the live-mode
  branch; keep it optional so tests run without it installed
- All wall positions in metres, WGS84 GPS for anchored output
- Follow the class-based test layout used across the repo
- Do not add new runtime dependencies; `anthropic` is already in
  `requirements.txt`
