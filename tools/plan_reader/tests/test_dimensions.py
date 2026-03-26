"""29 tests for tools/plan_reader/dimensions.py."""

import pytest

from tools.plan_reader.dimensions import (
    parse_dimension,
    validate_dimensions,
    feet_inches_to_meters,
    meters_to_feet_inches,
    format_feet_inches,
    FEET_TO_METERS,
    INCHES_TO_METERS,
)

_FT = 0.3048
_IN = 0.0254


class TestParseDimensionFeetInches:
    """Feet-inches notation: 12'-6", 12'6", word form, fractions."""

    def test_standard(self):
        assert parse_dimension('12\'-6"') == pytest.approx(12 * _FT + 6 * _IN)

    def test_no_separator(self):
        assert parse_dimension('12\'6"') == pytest.approx(12 * _FT + 6 * _IN)

    def test_word_form(self):
        assert parse_dimension("12 ft 6 in") == pytest.approx(12 * _FT + 6 * _IN)

    def test_fractional_inches(self):
        assert parse_dimension('12\'-6 1/2"') == pytest.approx(12 * _FT + 6.5 * _IN)

    def test_spaced_dash_fraction(self):
        assert parse_dimension('24\' - 8 1/2"') == pytest.approx(24 * _FT + 8.5 * _IN)

    def test_zero_inches(self):
        assert parse_dimension('3\'-0"') == pytest.approx(3 * _FT)


class TestParseDimensionFeetOnly:
    """Feet-only notation: apostrophe, decimal, word."""

    def test_apostrophe(self):
        assert parse_dimension("12'") == pytest.approx(12 * _FT)

    def test_decimal_feet(self):
        assert parse_dimension("12.5'") == pytest.approx(12.5 * _FT)

    def test_word_ft(self):
        assert parse_dimension("8 ft") == pytest.approx(8 * _FT)


class TestParseDimensionInchesOnly:
    """Inches-only notation: standard, decimal, fractions."""

    def test_standard(self):
        assert parse_dimension('6"') == pytest.approx(6 * _IN)

    def test_decimal_inches(self):
        assert parse_dimension('6.5"') == pytest.approx(6.5 * _IN)

    def test_mixed_fraction(self):
        assert parse_dimension('6 1/2"') == pytest.approx(6.5 * _IN)

    def test_pure_fraction(self):
        assert parse_dimension('1/2"') == pytest.approx(0.5 * _IN)

    def test_whole_and_fraction(self):
        assert parse_dimension('1 1/4"') == pytest.approx(1.25 * _IN)


class TestParseDimensionMetric:
    """Metric notation: metres, centimetres, millimetres."""

    def test_metres_decimal(self):
        assert parse_dimension("3.5m") == pytest.approx(3.5)

    def test_metres_whole(self):
        assert parse_dimension("3m") == pytest.approx(3.0)

    def test_centimetres(self):
        assert parse_dimension("35cm") == pytest.approx(0.35)

    def test_millimetres(self):
        assert parse_dimension("350mm") == pytest.approx(0.35)

    def test_millimetres_large(self):
        assert parse_dimension("3500mm") == pytest.approx(3.5)


class TestParseDimensionEdgeCases:
    """Edge cases: None, empty string, invalid text, zero."""

    def test_none_returns_none(self):
        assert parse_dimension(None) is None

    def test_empty_string_returns_none(self):
        assert parse_dimension("") is None

    def test_invalid_text_returns_none(self):
        assert parse_dimension("invalid") is None

    def test_zero_feet(self):
        assert parse_dimension("0'") == pytest.approx(0.0)


class TestValidateDimensions:
    """validate_dimensions: matching, mismatches, tolerance, empty."""

    def test_all_match(self, sample_extracted, sample_annotated):
        result = validate_dimensions(sample_extracted, sample_annotated)
        assert result["ok"] is True
        assert len(result["matched"]) == 3
        assert result["mismatches"] == []
        assert result["unmatched_extracted"] == []

    def test_within_tolerance(self):
        # 2 mm off — within default 25 mm tolerance
        result = validate_dimensions([3.812], [3.810], tolerance_m=0.025)
        assert result["ok"] is True
        assert len(result["matched"]) == 1

    def test_mismatch_beyond_tolerance(self):
        result = validate_dimensions([3.810], [2.438], tolerance_m=0.025)
        assert result["ok"] is False
        assert len(result["mismatches"]) == 1
        assert result["mismatches"][0]["annotated"] == pytest.approx(2.438)
        assert result["mismatches"][0]["closest_extracted"] == pytest.approx(3.810)

    def test_unmatched_extracted(self):
        result = validate_dimensions([3.810, 2.438], [3.810])
        assert result["ok"] is False
        assert len(result["unmatched_extracted"]) == 1
        assert result["unmatched_extracted"][0] == pytest.approx(2.438)

    def test_unmatched_annotated_is_mismatch(self):
        result = validate_dimensions([3.810], [3.810, 2.438])
        assert result["ok"] is False
        assert len(result["mismatches"]) == 1
        assert result["mismatches"][0]["annotated"] == pytest.approx(2.438)

    def test_empty_lists(self):
        result = validate_dimensions([], [])
        assert result["ok"] is True
        assert result["matched"] == []
        assert result["mismatches"] == []
        assert result["unmatched_extracted"] == []


class TestConstants:
    """Public conversion constants are exposed for external use."""

    def test_feet_to_meters_constant(self):
        assert FEET_TO_METERS == pytest.approx(0.3048)

    def test_inches_to_meters_constant(self):
        assert INCHES_TO_METERS == pytest.approx(0.0254)


class TestFeetInchesToMeters:
    """feet_inches_to_meters: feet + inches → metres."""

    def test_feet_and_inches(self):
        assert feet_inches_to_meters(12, 6) == pytest.approx(12 * _FT + 6 * _IN)

    def test_feet_only(self):
        assert feet_inches_to_meters(10) == pytest.approx(10 * _FT)

    def test_zero(self):
        assert feet_inches_to_meters(0, 0) == pytest.approx(0.0)


class TestMetersToFeetInches:
    """meters_to_feet_inches: metres → (whole_feet, remaining_inches)."""

    def test_round_trip(self):
        ft, inches = meters_to_feet_inches(3.81)
        assert ft == 12
        assert inches == pytest.approx(6.0, abs=0.1)

    def test_zero(self):
        ft, inches = meters_to_feet_inches(0.0)
        assert ft == 0
        assert inches == pytest.approx(0.0)


class TestFormatFeetInches:
    """format_feet_inches: metres → architectural string."""

    def test_even_inches(self):
        assert format_feet_inches(3.81) == "12'-6\""

    def test_zero_inches(self):
        assert format_feet_inches(3.048) == "10'-0\""
