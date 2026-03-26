"""
Tests for plan_reader/dimensions.py — architectural dimension parsing.
"""
from __future__ import annotations

import pytest

from dimensions import (
    parse_dimension,
    feet_inches_to_meters,
    meters_to_feet_inches,
    format_feet_inches,
    validate_dimensions,
    FEET_TO_METERS,
    INCHES_TO_METERS,
)


# ===========================================================================
# parse_dimension — feet-inches formats
# ===========================================================================


class TestParseFeetInches:
    def test_standard_format(self):
        # 12'-6" = 12 ft 6 in = 3.81 m
        assert parse_dimension("12'-6\"") == pytest.approx(3.81, abs=0.001)

    def test_with_spaces(self):
        assert parse_dimension("12' - 6\"") == pytest.approx(3.81, abs=0.001)

    def test_no_dash(self):
        assert parse_dimension("12' 6\"") == pytest.approx(3.81, abs=0.001)

    def test_zero_inches(self):
        # 3'-0" = 3 ft = 0.9144 m
        assert parse_dimension("3'-0\"") == pytest.approx(0.9144, abs=0.001)

    def test_feet_only(self):
        assert parse_dimension("12'") == pytest.approx(3.6576, abs=0.001)

    def test_inches_only(self):
        # 6" = 0.1524 m
        assert parse_dimension("6\"") == pytest.approx(0.1524, abs=0.001)

    def test_fraction_inches(self):
        # 12'-6 1/2" = 12 ft 6.5 in = 3.8227 m
        assert parse_dimension("12'-6 1/2\"") == pytest.approx(3.8227, abs=0.001)

    def test_decimal_feet(self):
        # 12.5' = 3.81 m
        assert parse_dimension("12.5'") == pytest.approx(3.81, abs=0.001)

    def test_large_dimension(self):
        # 24'-8" = 24 ft 8 in = 7.5184 m
        assert parse_dimension("24'-8\"") == pytest.approx(7.5184, abs=0.001)

    def test_small_dimension(self):
        # 2'-6" = 2 ft 6 in = 0.762 m
        assert parse_dimension("2'-6\"") == pytest.approx(0.762, abs=0.001)

    def test_common_door_width(self):
        # 3'-0" = 0.9144 m
        assert parse_dimension("3'-0\"") == pytest.approx(0.9144, abs=0.001)

    def test_common_ceiling_height(self):
        # 8'-0" = 2.4384 m
        assert parse_dimension("8'-0\"") == pytest.approx(2.4384, abs=0.001)

    def test_whitespace_handling(self):
        assert parse_dimension("  12'-6\"  ") == pytest.approx(3.81, abs=0.001)


# ===========================================================================
# parse_dimension — metric formats
# ===========================================================================


class TestParseMetric:
    def test_meters(self):
        assert parse_dimension("3.048m") == pytest.approx(3.048)

    def test_meters_with_space(self):
        assert parse_dimension("3.048 m") == pytest.approx(3.048)

    def test_millimeters(self):
        assert parse_dimension("3048mm") == pytest.approx(3.048)

    def test_centimeters(self):
        assert parse_dimension("304.8cm") == pytest.approx(3.048)


# ===========================================================================
# parse_dimension — error handling
# ===========================================================================


class TestParseErrors:
    def test_empty_string_raises(self):
        with pytest.raises(ValueError, match="Empty"):
            parse_dimension("")

    def test_garbage_raises(self):
        with pytest.raises(ValueError, match="Cannot parse"):
            parse_dimension("hello")


# ===========================================================================
# Conversion helpers
# ===========================================================================


class TestConversions:
    def test_feet_inches_to_meters(self):
        assert feet_inches_to_meters(12, 6) == pytest.approx(3.81, abs=0.001)

    def test_feet_only_to_meters(self):
        assert feet_inches_to_meters(10) == pytest.approx(3.048, abs=0.001)

    def test_meters_to_feet_inches(self):
        ft, inches = meters_to_feet_inches(3.81)
        assert ft == 12
        assert inches == pytest.approx(6.0, abs=0.1)

    def test_roundtrip(self):
        original_m = 3.81
        ft, inches = meters_to_feet_inches(original_m)
        back = feet_inches_to_meters(ft, inches)
        assert back == pytest.approx(original_m, abs=0.001)


# ===========================================================================
# format_feet_inches
# ===========================================================================


class TestFormat:
    def test_even_inches(self):
        assert format_feet_inches(3.81) == "12'-6\""

    def test_zero_inches(self):
        assert format_feet_inches(3.048) == "10'-0\""


# ===========================================================================
# validate_dimensions
# ===========================================================================


class TestValidate:
    def test_no_discrepancies(self):
        extracted = {"wall_north": 5.0, "wall_east": 3.0}
        annotated = {"wall_north": 5.02, "wall_east": 3.01}
        result = validate_dimensions(extracted, annotated)
        assert result == []

    def test_discrepancy_detected(self):
        extracted = {"wall_north": 5.0}
        annotated = {"wall_north": 5.2}
        result = validate_dimensions(extracted, annotated)
        assert len(result) == 1
        assert result[0]["name"] == "wall_north"
        assert result[0]["diff_m"] == pytest.approx(0.2)

    def test_custom_tolerance(self):
        extracted = {"wall_north": 5.0}
        annotated = {"wall_north": 5.08}
        # Default 0.05m tolerance → discrepancy
        assert len(validate_dimensions(extracted, annotated)) == 1
        # Relaxed 0.10m tolerance → no discrepancy
        assert len(validate_dimensions(extracted, annotated, tolerance_m=0.10)) == 0
