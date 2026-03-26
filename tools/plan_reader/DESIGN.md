# Plan Reader — Vision Pipeline Design

## Overview

The plan reader converts physical architectural drawings (photos of floor
plans) into homemodel `StructureEntity` records.  The user photographs a
plan at known scale, an AI vision model extracts dimension annotations and
room labels, the dimension parser converts them to meters, and the geometry
reconstructor builds wall/room polygons that feed `StructureBuilder.compile()`.

## Full Pipeline

```
Photo(s)
  │
  ▼
scale_calibrate()        — user supplies known reference length
  │                         (e.g. door width = 0.914 m → px/m ratio)
  ▼
vision_extract()         — Claude Vision API: bounding boxes + labels
  │                         returns: dimensions[], room_labels[], opening_types[]
  ▼
parse_dimension()        — dimensions.py: "12'-6"" → 3.810 m
  │
  ▼
validate_dimensions()    — cross-check extracted vs annotated (optional)
  │
  ▼
reconstruct_geometry()   — assemble wall segments into closed polygons
  │                         units: meters, origin at first corner
  ▼
gps_anchor()             — apply GPS offset from scene origin
  │                         (lat 42.98743, lon -70.98709, alt_m 26.8)
  ▼
StructureBuilder.compile(floorplan, measurements, images)
  │
  ▼
Ingestion.submit_bulk()  → SchemaStore
```

## v1 MVP Scope

- **One photo per floor** (single-image workflow; multi-image stitching deferred)
- **User-provided scale**: user measures one known distance in the photo and
  provides the real-world value; no automatic scale detection
- **Claude Vision** for dimension and label extraction (via Anthropic API);
  local model fallback is future work
- **Human review before submission**: `validate_dimensions()` result shown
  to user; submission blocked if `ok == False` unless user overrides
- **Imperial and metric** annotations both supported

## Module Structure

```
tools/plan_reader/
├── __init__.py          # exports: parse_dimension, validate_dimensions
├── dimensions.py        # dimension string → meters (no dependencies)
├── vision.py            # Claude Vision extraction (future — not in v1 stub)
├── geometry.py          # 2D geometry reconstruction (future)
├── DESIGN.md            # this file
└── tests/
    ├── __init__.py
    ├── conftest.py
    └── test_dimensions.py
```

## Dimension Parser (`dimensions.py`)

Standalone module, no dependencies beyond Python stdlib.
Handles all common architectural notations and converts to meters.

### Supported formats

| Notation       | Example         | Notes                         |
|----------------|-----------------|-------------------------------|
| Feet-inches    | `12'-6"`        | Standard US architectural     |
| No separator   | `12'6"`         | Compact form                  |
| Word form      | `12 ft 6 in`    | OCR-friendly long form        |
| Fractional in  | `12'-6 1/2"`    | Mixed number inches           |
| Spaced dash    | `24' - 8 1/2"`  | Common on hand-drawn plans    |
| Zero inches    | `3'-0"`         | Even-foot dimension           |
| Feet only      | `12'`           | Apostrophe or `ft`            |
| Decimal feet   | `12.5'`         | Less common but valid         |
| Inches only    | `6"`            | Small dimensions              |
| Inch fraction  | `6 1/2"`        | Mixed number                  |
| Pure fraction  | `1/2"`          | Less-than-one-inch clearances |
| Meters         | `3.5m`          | European plans                |
| Centimeters    | `35cm`          | Smaller European dims         |
| Millimeters    | `350mm`         | Engineering / metric plans    |

### Conversion constants

- 1 foot = 0.3048 m (exact)
- 1 inch = 0.0254 m (exact)
- 1 cm = 0.01 m
- 1 mm = 0.001 m

## `validate_dimensions()` contract

```python
validate_dimensions(
    extracted: list[float],   # meters, from vision model
    annotated: list[float],   # meters, from user or reference
    tolerance_m: float = 0.025,  # 25 mm default
) -> {
    "matched":              list[{"extracted": float, "annotated": float}],
    "mismatches":           list[{"annotated": float, "closest_extracted": float|None, "delta_m": float|None}],
    "unmatched_extracted":  list[float],
    "ok":                   bool,  # True iff no mismatches and no unmatched
}
```

## Future Phases

| Phase | Feature                                    |
|-------|--------------------------------------------|
| v1.1  | `vision.py` — Claude Vision extraction     |
| v1.2  | `geometry.py` — wall segment reconstruction|
| v1.3  | Multi-photo stitching                      |
| v2    | Automatic scale detection (ruler in photo) |
| v3    | Local vision model support                 |
