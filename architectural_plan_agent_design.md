# Source 2: Architectural Plans → Vision Agent

## Problem

Physical architectural drawings (large format) showing each floor and the
exterior of the house need to be digitized. The drawings are too large to
scan whole, so the input will be **photos of sections** of the plans.

## Goal

A tool that accepts photos of architectural plan sections, extracts
structural geometry (walls, rooms, openings, dimensions), and produces
floorplan dicts that feed directly into `StructureBuilder.compile()`.

## What StructureBuilder Already Accepts

```python
builder.compile(floorplan, measurements, images)
```

### floorplan dict shape (from structures/tests/conftest.py)

```python
{
    "id": "structure-001",
    "position_gps": {"lat": 42.98743, "lon": -70.98709, "alt_m": 26.8},
    "floor_level": 0,          # 0=ground, -1=basement, 1=second
    "material": "wood_frame",
    "walls": [
        {
            "id": "wall-001",
            "start_point": (0.0, 0.0),   # local coords in meters
            "end_point": (5.0, 0.0),
            "height_m": 2.4,
            "thickness_m": 0.15,
            "floor_level": 0,
            "material": "drywall",
            "openings": [
                {
                    "type": "door",          # or "window"
                    "position_offset": 1.0,  # meters from start_point
                    "width_m": 0.9,
                    "height_m": 2.1,
                }
            ],
        }
    ],
    "rooms": [
        {
            "id": "room-001",
            "boundary_points": [(0.0, 0.0), (5.0, 0.0), (5.0, 4.0), (0.0, 4.0)],
            "floor_height_m": 0.0,
            "ceiling_height_m": 2.4,
            "floor_level": 0,
        }
    ],
}
```

## Pipeline Design

```
┌──────────────────┐
│  Photo(s) of     │
│  plan section    │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ 1. CALIBRATE     │  Detect scale bar / known dimension
│    scale         │  → pixels_per_foot or pixels_per_meter
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ 2. EXTRACT       │  Vision model identifies:
│    features      │  - Wall segments (lines + thickness)
│                  │  - Dimension annotations (e.g. "12'-6\"")
│                  │  - Room labels ("KITCHEN", "BEDROOM 2")
│                  │  - Openings (door swings, window marks)
│                  │  - Stair symbols, fixture locations
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ 3. DIMENSION     │  Parse dimension text → numeric values
│    parse         │  Convert ft-in to meters
│                  │  Cross-check extracted lengths vs annotations
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ 4. GEOMETRY      │  Build wall segments as (start, end) pairs
│    reconstruct   │  Identify room boundaries from enclosed walls
│                  │  Assign openings to walls with offsets
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ 5. GPS ANCHOR    │  Align local coords to GPS using:
│                  │  - Known house position from town map (Source 1)
│                  │  - Orientation from aerial photo / compass
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ 6. VALIDATE      │  Human review of extracted floorplan
│    + submit      │  → StructureBuilder.compile()
│                  │  → SchemaStore via ingestion pipeline
└──────────────────┘
```

## Key Design Decisions

### Multi-photo stitching

Architectural plans are large. The agent must handle:
- **Single section**: one photo covers one room or one wall run
- **Overlapping sections**: multiple photos of the same floor, stitched
- **Per-floor**: each floor is a separate set of photos

The simplest v1 approach: **one photo per floor, user confirms scale**.
Stitching can come later.

### Scale calibration

Architectural plans always have either:
- A scale bar (e.g. "1/4\" = 1'-0\"")
- Explicit dimensions on walls (e.g. "24'-8\"")
- A title block with scale notation

**v1**: User provides scale factor or one known dimension.
**v2**: Vision model detects scale bar automatically.

### Dimension parsing

Architectural dimensions use formats like:
- `12'-6"` (12 feet 6 inches)
- `12' - 6"` (with spaces)
- `3.048m` (metric, rare in US residential)
- `24'-8 1/2"` (with fractions)

Conversion: `feet + inches/12` → meters × 0.3048

### Vision model strategy

Two approaches, not mutually exclusive:

**A. Claude Vision (structured extraction)**
- Send photo to Claude with a system prompt describing architectural
  plan conventions
- Ask for structured JSON output: walls, rooms, openings, dimensions
- Pro: understands context, can read annotations, handles ambiguity
- Con: may hallucinate dimensions, needs validation

**B. CV pipeline (line detection + OCR)**
- OpenCV Hough line detection for wall segments
- Tesseract/EasyOCR for dimension text extraction
- Template matching for door swings and window symbols
- Pro: deterministic, verifiable
- Con: brittle with photo quality, perspective distortion

**Recommended v1**: Claude Vision for extraction, with human validation
before submission. The structured output format matches the floorplan
dict directly.

### GPS anchoring

The house position is already known from homemodel's scene origin
(lat 42.98743, lon -70.98709, alt_m 26.8). What we need is:
- **Rotation**: which direction does the front of the house face?
  (from aerial photo or compass bearing)
- **Offset**: where is the house origin relative to the GPS anchor?
  (from Source 1 parcel/building footprint data)

Source 1 (town map) will provide the building footprint polygon, which
gives us both position and orientation. The vision agent aligns the
extracted floor plan to that footprint.

## Module Layout

```
tools/
└── plan_reader/
    ├── SKILL.md           # Agent skill file
    ├── reader.py          # Main pipeline: photo → floorplan dict
    ├── calibrate.py       # Scale detection and calibration
    ├── extract.py         # Vision model feature extraction
    ├── dimensions.py      # Dimension text parsing (ft-in → meters)
    ├── geometry.py        # Wall/room geometry reconstruction
    ├── anchor.py          # GPS alignment from building footprint
    ├── validate.py        # Human review helpers
    └── tests/
        ├── conftest.py
        ├── test_dimensions.py
        ├── test_extract.py
        └── fixtures/
            └── sample_plan.jpg  # Test photo of a simple plan
```

## Contract: plan_reader → StructureBuilder

The plan_reader module outputs a dict matching the existing
`StructureBuilder.compile()` input format. No new contracts needed.

```python
from tools.plan_reader.reader import PlanReader

reader = PlanReader()

# Step 1: Load and calibrate
plan = reader.load("photos/ground_floor_01.jpg", scale="1/4in = 1ft")

# Step 2: Extract (calls vision model)
extracted = reader.extract(plan)
# Returns: {"walls": [...], "rooms": [...], "dimensions": {...}}

# Step 3: Review (prints summary, asks for confirmation)
reader.review(extracted)

# Step 4: Build floorplan dict
floorplan = reader.to_floorplan(
    extracted,
    floor_level=0,
    position_gps={"lat": 42.98743, "lon": -70.98709, "alt_m": 26.8},
    rotation_deg=45.0,  # from aerial photo alignment
)

# Step 5: Submit to StructureBuilder
from structures.builder import StructureBuilder
from schema.store import SchemaStore

store = SchemaStore("homemodel.db")
builder = StructureBuilder(store)
result = builder.compile(floorplan, measurements=[], images=[photo_record])
```

## Provenance

Every entity created from architectural plans carries provenance:
```python
{
    "source_type": "architectural_plan",
    "source_id": "ground_floor_plan_photo_01",
    "timestamp": "2026-03-25T...",
    "accuracy_m": 0.05  # ~2 inches, typical for plan extraction
}
```

## Error-prone areas (why tooling matters)

1. **Dimension misreads**: "12'-6\"" read as "12'-8\"" — 2 inch error
   propagates to every downstream wall. Validation step catches this
   by cross-checking: do opposite walls of a room agree on room width?

2. **Scale miscalibration**: wrong scale factor makes everything
   proportionally wrong. Mitigated by checking extracted dimensions
   against the annotated dimensions on the plan.

3. **Photo perspective**: phone photos have barrel distortion and
   perspective skew. v1 assumes user takes a reasonably flat photo.
   v2 could add perspective correction.

4. **Multi-floor alignment**: stairs/elevator shafts must align
   vertically between floors. Validation checks that stair positions
   on floor N match floor N+1.

## v1 Scope (MVP)

- Single photo per floor
- User provides scale (or one known dimension)
- Claude Vision extracts walls, rooms, openings, dimensions
- Human reviews extracted data before submission
- GPS anchor from scene origin + user-provided rotation
- Output: floorplan dict → StructureBuilder.compile()

## Future (v2+)

- Multi-photo stitching per floor
- Automatic scale bar detection
- Perspective correction
- Building footprint alignment from Source 1
- Exterior elevation views → roof geometry
- MEP (mechanical/electrical/plumbing) extraction
