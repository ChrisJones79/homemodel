"""
Dimension text parser for architectural plans.

Converts US architectural dimension notations (feet-inches) to meters.
Handles common formats found on residential floor plans.

Examples
--------
>>> parse_dimension("12'-6\"")
3.81
>>> parse_dimension("24' - 8 1/2\"")
7.5311
>>> parse_dimension("3'-0\"")
0.9144
"""
from __future__ import annotations

import re
from typing import Any

# Conversion constants
FEET_TO_METERS = 0.3048
INCHES_TO_METERS = 0.0254


def parse_dimension(text: str) -> float:
    """Parse an architectural dimension string and return meters.

    Supports these formats:
        12'-6"          → 12 ft 6 in
        12' - 6"        → 12 ft 6 in (with spaces)
        12'-6 1/2"      → 12 ft 6.5 in (fractions)
        12' 6"          → 12 ft 6 in (no dash)
        12'             → 12 ft 0 in
        6"              → 0 ft 6 in
        12.5'           → 12.5 ft
        3.048m          → 3.048 meters (passthrough)
        3048mm          → 3.048 meters

    Parameters
    ----------
    text : str
        Dimension string from an architectural plan

    Returns
    -------
    float
        Dimension in meters

    Raises
    ------
    ValueError
        If the text cannot be parsed as a dimension
    """
    cleaned = text.strip()

    if not cleaned:
        raise ValueError("Empty dimension string")

    # Try metric first
    metric = _try_metric(cleaned)
    if metric is not None:
        return metric

    # Try feet-inches
    imperial = _try_imperial(cleaned)
    if imperial is not None:
        return imperial

    # Try bare number (assume feet)
    try:
        value = float(cleaned)
        return value * FEET_TO_METERS
    except ValueError:
        pass

    raise ValueError(f"Cannot parse dimension: {text!r}")


def _try_metric(text: str) -> float | None:
    """Try to parse as metric (meters or millimeters)."""
    # 3.048m or 3.048 m
    m = re.match(r'^(\d+(?:\.\d+)?)\s*m$', text, re.IGNORECASE)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            return None

    # 3048mm or 3048 mm
    m = re.match(r'^(\d+(?:\.\d+)?)\s*mm$', text, re.IGNORECASE)
    if m:
        try:
            return float(m.group(1)) / 1000.0
        except ValueError:
            return None

    # 304.8cm or 304.8 cm
    m = re.match(r'^(\d+(?:\.\d+)?)\s*cm$', text, re.IGNORECASE)
    if m:
        try:
            return float(m.group(1)) / 100.0
        except ValueError:
            return None

    return None


def _try_imperial(text: str) -> float | None:
    """Try to parse as feet-inches notation."""
    # Normalize fancy quotes and dashes
    normalized = text.replace('\u2032', "'").replace('\u2033', '"')
    normalized = normalized.replace('\u2018', "'").replace('\u2019', "'")
    normalized = normalized.replace('\u201c', '"').replace('\u201d', '"')
    normalized = normalized.replace('\u2013', '-').replace('\u2014', '-')

    feet = 0.0
    inches = 0.0

    # Pattern: 12'-6 1/2" or 12' - 6 1/2" or 12'-6" or 12' 6"
    m = re.match(
        r'^(\d+(?:\.\d+)?)\s*[\x27\u2032]\s*-?\s*(\d+(?:\.\d+)?)?(?:\s+(\d+)/(\d+))?\s*(?:[\x22\u201c\u201d\u2033])?\s*$',
        normalized,
    )
    if m:
        feet = float(m.group(1))
        if m.group(2):
            inches = float(m.group(2))
        if m.group(3) and m.group(4):
            inches += float(m.group(3)) / float(m.group(4))
        return feet * FEET_TO_METERS + inches * INCHES_TO_METERS

    # Pattern: just feet with decimal: 12.5'
    m = re.match(r"^(\d+(?:\.\d+)?)\s*['\u2032]\s*$", normalized)
    if m:
        feet = float(m.group(1))
        return feet * FEET_TO_METERS

    # Pattern: just inches: 6" or 6 1/2"
    m = re.match(
        r'^(\d+(?:\.\d+)?)\s*(?:\s+(\d+)/(\d+))?\s*[\x22\u201c\u201d\u2033]\s*$',
        normalized,
    )
    if m:
        inches = float(m.group(1))
        if m.group(2) and m.group(3):
            inches += float(m.group(2)) / float(m.group(3))
        return inches * INCHES_TO_METERS

    return None


def feet_inches_to_meters(feet: float, inches: float = 0.0) -> float:
    """Convert feet and inches to meters.

    Parameters
    ----------
    feet : float
    inches : float

    Returns
    -------
    float
        Value in meters
    """
    return feet * FEET_TO_METERS + inches * INCHES_TO_METERS


def meters_to_feet_inches(meters: float) -> tuple[int, float]:
    """Convert meters to feet and inches.

    Returns
    -------
    tuple[int, float]
        (whole_feet, remaining_inches)
    """
    total_inches = meters / INCHES_TO_METERS
    whole_feet = int(total_inches // 12)
    remaining_inches = total_inches % 12
    return whole_feet, round(remaining_inches, 2)


def format_feet_inches(meters: float) -> str:
    """Format a meter value as an architectural feet-inches string.

    >>> format_feet_inches(3.81)
    "12'-6\""
    """
    ft, inches = meters_to_feet_inches(meters)
    if inches == 0:
        return f"{ft}'-0\""
    if inches == int(inches):
        return f"{ft}'-{int(inches)}\""
    return f"{ft}'-{inches:.1f}\""


def validate_dimensions(
    extracted: dict[str, float],
    annotated: dict[str, float],
    tolerance_m: float = 0.05,
) -> list[dict[str, Any]]:
    """Cross-check extracted dimensions against annotated ones.

    Parameters
    ----------
    extracted : dict
        Dimension name → extracted value in meters
    annotated : dict
        Dimension name → annotated value in meters (from plan text)
    tolerance_m : float
        Maximum acceptable difference in meters (default 5cm / ~2in)

    Returns
    -------
    list[dict]
        List of discrepancies: {"name", "extracted_m", "annotated_m", "diff_m"}
    """
    discrepancies = []
    for name in sorted(set(extracted) & set(annotated)):
        diff = abs(extracted[name] - annotated[name])
        if diff > tolerance_m:
            discrepancies.append({
                "name": name,
                "extracted_m": round(extracted[name], 4),
                "annotated_m": round(annotated[name], 4),
                "diff_m": round(diff, 4),
            })
    return discrepancies
