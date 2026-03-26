"""Architectural dimension parser.

Converts common architectural notation strings to meters.

Supported formats
-----------------
Feet-inches:  ``12'-6"``  ``12'6"``  ``12 ft 6 in``  ``12'-6 1/2"``  ``24' - 8 1/2"``
Feet only:    ``12'``     ``12.5'``   ``8 ft``
Inches only:  ``6"``      ``6.5"``    ``6 1/2"``       ``1/2"``        ``1 1/4"``
Metric:       ``3.5m``    ``3m``      ``35cm``          ``350mm``       ``3500mm``

All functions are pure; no I/O or external dependencies.
"""

from __future__ import annotations

import re
from typing import Optional

_FT_TO_M: float = 0.3048
_IN_TO_M: float = 0.0254
_CM_TO_M: float = 0.01
_MM_TO_M: float = 0.001

# Public aliases for external use
FEET_TO_METERS = _FT_TO_M
INCHES_TO_METERS = _IN_TO_M

# Inch value: whole number, decimal, mixed fraction ("6 1/2"), or pure fraction ("1/2")
_INCH_VALUE = r"(?:\d+(?:\.\d+)?\s+\d+/\d+|\d+/\d+|\d+(?:\.\d+)?)"

# Feet-inches:  12'-6"  12'6"  12 ft 6 in  12'-6 1/2"  24' - 8 1/2"
_FT_IN_RE = re.compile(
    rf"(\d+(?:\.\d+)?)\s*(?:'|ft\.?)\s*[-\s]*\s*({_INCH_VALUE})\s*(?:\"|in\.?)",
    re.IGNORECASE,
)

# Feet only:  12'  12.5'  8 ft
_FT_ONLY_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*(?:'|ft\.?)",
    re.IGNORECASE,
)

# Inches only:  6"  6.5"  6 1/2"  1/2"  1 1/4"
_IN_ONLY_RE = re.compile(
    rf"({_INCH_VALUE})\s*(?:\"|in\.?)",
    re.IGNORECASE,
)

# Metric:  3.5m  350mm  35cm  (comma decimal allowed: 3,5m)
_METRIC_RE = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*(mm|cm|m)\b",
    re.IGNORECASE,
)

_METRIC_FACTORS = {"m": 1.0, "cm": _CM_TO_M, "mm": _MM_TO_M}


def _parse_inch_value(s: str) -> float:
    """Convert an inch value string (may include fractions) to a float."""
    s = s.strip()
    mixed = re.fullmatch(r"(\d+)\s+(\d+)/(\d+)", s)
    if mixed:
        return int(mixed.group(1)) + int(mixed.group(2)) / int(mixed.group(3))
    pure = re.fullmatch(r"(\d+)/(\d+)", s)
    if pure:
        return int(pure.group(1)) / int(pure.group(2))
    return float(s)


def parse_dimension(text: str) -> Optional[float]:
    """Parse an architectural dimension string and return metres.

    Returns ``None`` if *text* cannot be parsed.
    """
    if not isinstance(text, str):
        return None
    text = text.strip()
    if not text:
        return None

    # Metric must be tried first so "3.5m" is not consumed as feet
    m = _METRIC_RE.fullmatch(text.replace(",", "."))
    if m:
        value = float(m.group(1).replace(",", "."))
        unit = m.group(2).lower()
        return value * _METRIC_FACTORS[unit]

    # Feet-inches (order matters: try before feet-only)
    m = _FT_IN_RE.fullmatch(text)
    if m:
        feet = float(m.group(1))
        inches = _parse_inch_value(m.group(2))
        return feet * _FT_TO_M + inches * _IN_TO_M

    # Feet only
    m = _FT_ONLY_RE.fullmatch(text)
    if m:
        return float(m.group(1)) * _FT_TO_M

    # Inches only
    m = _IN_ONLY_RE.fullmatch(text)
    if m:
        return _parse_inch_value(m.group(1)) * _IN_TO_M

    return None


def validate_dimensions(
    extracted: list,
    annotated: list,
    tolerance_m: float = 0.025,
) -> dict:
    """Cross-check vision-extracted dimensions against annotated reference values.

    Each annotated dimension is paired with the closest unused extracted value.
    A pair is a *match* when the difference is within *tolerance_m*; otherwise
    it is a *mismatch*.  Extracted values with no annotated counterpart are
    reported as *unmatched_extracted*.

    Args:
        extracted:    Dimensions from vision model, in metres.
        annotated:    Reference/annotated dimensions, in metres.
        tolerance_m:  Maximum acceptable difference for a match (default 25 mm).

    Returns:
        dict with keys:
        - ``matched``             — list of ``{extracted, annotated}`` pairs
        - ``mismatches``          — list of ``{annotated, closest_extracted, delta_m}``
        - ``unmatched_extracted`` — extracted values not claimed by any annotated dim
        - ``ok``                  — ``True`` iff no mismatches and no unmatched_extracted
    """
    used: set[int] = set()
    matched: list[dict] = []
    mismatches: list[dict] = []

    for ann in annotated:
        best_idx: Optional[int] = None
        best_delta = float("inf")
        for i, ext in enumerate(extracted):
            if i in used:
                continue
            delta = abs(ext - ann)
            if delta < best_delta:
                best_delta = delta
                best_idx = i

        if best_idx is not None and best_delta <= tolerance_m:
            used.add(best_idx)
            matched.append({"extracted": extracted[best_idx], "annotated": ann})
        else:
            closest = extracted[best_idx] if best_idx is not None else None
            mismatches.append(
                {
                    "annotated": ann,
                    "closest_extracted": closest,
                    "delta_m": round(best_delta, 4) if closest is not None else None,
                }
            )

    unmatched_extracted = [extracted[i] for i in range(len(extracted)) if i not in used]

    return {
        "matched": matched,
        "mismatches": mismatches,
        "unmatched_extracted": unmatched_extracted,
        "ok": len(mismatches) == 0 and len(unmatched_extracted) == 0,
    }


def feet_inches_to_meters(feet: float, inches: float = 0.0) -> float:
    """Convert feet and inches to metres.

    Parameters
    ----------
    feet : float
        Number of feet.
    inches : float
        Number of inches (default 0).

    Returns
    -------
    float
        Value in metres.
    """
    return feet * _FT_TO_M + inches * _IN_TO_M


def meters_to_feet_inches(meters: float) -> tuple:
    """Convert metres to whole feet and remaining inches.

    Returns
    -------
    tuple[int, float]
        ``(whole_feet, remaining_inches)``
    """
    total_inches = meters / _IN_TO_M
    whole_feet = int(total_inches // 12)
    remaining_inches = round(total_inches % 12, 2)
    return whole_feet, remaining_inches


def format_feet_inches(meters: float) -> str:
    """Format a metre value as an architectural feet-inches string.

    Examples
    --------
    >>> format_feet_inches(3.81)
    "12'-6\\""
    >>> format_feet_inches(3.048)
    "10'-0\\""
    """
    ft, inches = meters_to_feet_inches(meters)
    if inches == 0:
        return f"{ft}'-0\""
    if inches == int(inches):
        return f"{ft}'-{int(inches)}\""
    return f"{ft}'-{inches:.1f}\""
