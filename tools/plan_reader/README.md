# Plan Reader

Standalone dimension parser for architectural drawing annotations.  Converts
feet-inches, metric, and fractional notation strings into metres.  This is
phase 1 of the vision pipeline that will eventually extract full `StructureEntity`
records from photographs of floor plans.

See `DESIGN.md` for the full pipeline design and future phases.

---

## Overview

`tools/plan_reader/dimensions.py` is a pure-Python module with no dependencies
beyond the standard library.  It handles every common US and metric annotation
format found on hand-drawn and printed architectural plans.

---

## API Reference

### parse_dimension

```python
from tools.plan_reader.dimensions import parse_dimension

parse_dimension("12'-6\"")   # → 3.81
parse_dimension("3.5m")      # → 3.5
parse_dimension("350mm")     # → 0.35
```

Returns the dimension in **metres** as a `float`.  Raises `ValueError` for
unrecognised or malformed input.

### validate_dimensions

```python
from tools.plan_reader.dimensions import validate_dimensions

result = validate_dimensions(
    extracted=[3.81, 2.44],
    annotated=[3.81, 2.44],
    tolerance_m=0.025,
)
# result → {"matched": [...], "mismatches": [], "unmatched_extracted": [], "ok": True}
```

Cross-checks vision-extracted dimensions against reference values.  Returns a
`ValidationResult` dict with `matched`, `mismatches`, `unmatched_extracted`,
and `ok` (bool).

### Supported notation formats

| Notation | Example | Notes |
|---|---|---|
| Feet-inches | `12'-6"` | Standard US architectural |
| No separator | `12'6"` | Compact form |
| Word form | `12 ft 6 in` | OCR-friendly |
| Fractional inches | `12'-6 1/2"` | Mixed number |
| Spaced dash | `24' - 8 1/2"` | Hand-drawn plans |
| Zero inches | `3'-0"` | Even-foot dimension |
| Feet only | `12'` | Apostrophe or `ft` |
| Decimal feet | `12.5'` | Less common |
| Inches only | `6"` | Small dimensions |
| Inch fraction | `6 1/2"` | Mixed number |
| Pure fraction | `1/2"` | Sub-inch clearance |
| Metres | `3.5m` | European plans |
| Centimetres | `35cm` | Smaller European dims |
| Millimetres | `350mm` | Engineering / metric |

### Conversion constants

| Unit | Exact value |
|---|---|
| 1 foot | 0.3048 m |
| 1 inch | 0.0254 m |
| 1 cm | 0.01 m |
| 1 mm | 0.001 m |

---

## Running Tests

```bash
HOMEMODEL_MODE=stub pytest tools/ --tb=short -v
```

### Test Coverage

| File | Tests | Coverage |
|---|---|---|
| `tools/plan_reader/dimensions.py` | 38 | 99% |
| **Module total** | **38** | **99%** |

---

## Contract Reference

The full pipeline design (including future `vision.py` and `geometry.py`
modules) is documented in `DESIGN.md`.

---

## Code Layout

```
tools/plan_reader/
├── __init__.py          # exports: parse_dimension, validate_dimensions
├── dimensions.py        # dimension string → metres (stdlib only)
├── DESIGN.md            # full pipeline design and future phases
└── tests/
    ├── conftest.py          # shared dimension test fixtures
    └── test_dimensions.py   # 38 tests: all notations, edge cases, validate_dimensions
```
