"""
Tests for the Ingestion pipeline.

Covers validation logic and all three submission methods:
- submit_measurement
- submit_image
- submit_bulk

In stub mode (HOMEMODEL_MODE=stub), SchemaStore calls are mocked but
pipeline logic executes fully.
"""
from __future__ import annotations

import copy
import os

import pytest

from ingestion.pipeline import Ingestion
from ingestion.validate import validate, ValidationResult


# ===========================================================================
# Validation Tests — Measurement
# ===========================================================================


class TestValidateMeasurement:
    def test_valid_measurement_passes(self, laser_measurement):
        result = validate(laser_measurement, "measurement")
        assert result.valid is True
        assert result.errors == []

    def test_missing_measurement_type_fails(self, laser_measurement):
        bad = copy.deepcopy(laser_measurement)
        del bad["measurement_type"]
        result = validate(bad, "measurement")
        assert result.valid is False
        assert any("measurement_type" in e["field"] for e in result.errors)

    def test_missing_value_fails(self, laser_measurement):
        bad = copy.deepcopy(laser_measurement)
        del bad["value"]
        result = validate(bad, "measurement")
        assert result.valid is False
        assert any("value" in e["field"] for e in result.errors)

    def test_missing_unit_fails(self, laser_measurement):
        bad = copy.deepcopy(laser_measurement)
        del bad["unit"]
        result = validate(bad, "measurement")
        assert result.valid is False
        assert any("unit" in e["field"] for e in result.errors)

    def test_missing_provenance_fails(self, laser_measurement):
        bad = copy.deepcopy(laser_measurement)
        del bad["provenance"]
        result = validate(bad, "measurement")
        assert result.valid is False
        assert any("provenance" in e["field"] for e in result.errors)

    def test_invalid_measurement_type_fails(self, laser_measurement):
        bad = copy.deepcopy(laser_measurement)
        bad["measurement_type"] = "invalid_type"
        result = validate(bad, "measurement")
        assert result.valid is False
        assert any("measurement_type" in e["field"] for e in result.errors)

    def test_valid_measurement_types(self, laser_measurement):
        valid_types = ["laser_p2p", "gps_point", "image_derived", "drone_telemetry"]
        for mtype in valid_types:
            measurement = copy.deepcopy(laser_measurement)
            measurement["measurement_type"] = mtype
            result = validate(measurement, "measurement")
            assert result.valid is True, f"{mtype} should be valid"

    def test_invalid_unit_fails(self, laser_measurement):
        bad = copy.deepcopy(laser_measurement)
        bad["unit"] = "invalid_unit"
        result = validate(bad, "measurement")
        assert result.valid is False
        assert any("unit" in e["field"] for e in result.errors)

    def test_valid_units(self, laser_measurement):
        valid_units = ["m", "cm", "mm", "inch", "deg"]
        for unit in valid_units:
            measurement = copy.deepcopy(laser_measurement)
            measurement["unit"] = unit
            result = validate(measurement, "measurement")
            assert result.valid is True, f"{unit} should be valid"

    def test_value_as_list_of_floats(self, laser_measurement):
        measurement = copy.deepcopy(laser_measurement)
        measurement["value"] = [1.0, 2.0, 3.0]
        result = validate(measurement, "measurement")
        assert result.valid is True

    def test_incomplete_provenance_fails(self, laser_measurement):
        bad = copy.deepcopy(laser_measurement)
        bad["provenance"] = {"source_type": "laser"}  # missing other fields
        result = validate(bad, "measurement")
        assert result.valid is False
        assert any("provenance" in e["field"] for e in result.errors)

    def test_entity_id_null_is_valid(self, laser_measurement):
        measurement = copy.deepcopy(laser_measurement)
        measurement["entity_id"] = None
        result = validate(measurement, "measurement")
        assert result.valid is True

    def test_missing_entity_id_is_valid(self, laser_measurement):
        measurement = copy.deepcopy(laser_measurement)
        if "entity_id" in measurement:
            del measurement["entity_id"]
        result = validate(measurement, "measurement")
        assert result.valid is True


# ===========================================================================
# Validation Tests — Image
# ===========================================================================


class TestValidateImage:
    def test_valid_image_passes(self, drone_image):
        result = validate(drone_image, "image")
        assert result.valid is True
        assert result.errors == []

    def test_missing_file_path_fails(self, drone_image):
        bad = copy.deepcopy(drone_image)
        del bad["file_path"]
        result = validate(bad, "image")
        assert result.valid is False
        assert any("file_path" in e["field"] for e in result.errors)

    def test_missing_format_fails(self, drone_image):
        bad = copy.deepcopy(drone_image)
        del bad["format"]
        result = validate(bad, "image")
        assert result.valid is False
        assert any("format" in e["field"] for e in result.errors)

    def test_missing_size_bytes_fails(self, drone_image):
        bad = copy.deepcopy(drone_image)
        del bad["size_bytes"]
        result = validate(bad, "image")
        assert result.valid is False
        assert any("size_bytes" in e["field"] for e in result.errors)

    def test_missing_capture_gps_fails(self, drone_image):
        bad = copy.deepcopy(drone_image)
        del bad["capture_gps"]
        result = validate(bad, "image")
        assert result.valid is False
        assert any("capture_gps" in e["field"] for e in result.errors)

    def test_missing_capture_timestamp_fails(self, drone_image):
        bad = copy.deepcopy(drone_image)
        del bad["capture_timestamp"]
        result = validate(bad, "image")
        assert result.valid is False
        assert any("capture_timestamp" in e["field"] for e in result.errors)

    def test_missing_source_type_fails(self, drone_image):
        bad = copy.deepcopy(drone_image)
        del bad["source_type"]
        result = validate(bad, "image")
        assert result.valid is False
        assert any("source_type" in e["field"] for e in result.errors)

    def test_invalid_format_fails(self, drone_image):
        bad = copy.deepcopy(drone_image)
        bad["format"] = "invalid_format"
        result = validate(bad, "image")
        assert result.valid is False
        assert any("format" in e["field"] for e in result.errors)

    def test_valid_formats(self, drone_image):
        valid_formats = ["jpeg", "png", "tiff", "raw"]
        for fmt in valid_formats:
            image = copy.deepcopy(drone_image)
            image["format"] = fmt
            result = validate(image, "image")
            assert result.valid is True, f"{fmt} should be valid"

    def test_invalid_source_type_fails(self, drone_image):
        bad = copy.deepcopy(drone_image)
        bad["source_type"] = "invalid_source"
        result = validate(bad, "image")
        assert result.valid is False
        assert any("source_type" in e["field"] for e in result.errors)

    def test_valid_source_types(self, drone_image):
        valid_sources = ["phone", "drone_aerial", "drone_ground", "dslr", "scan"]
        for source in valid_sources:
            image = copy.deepcopy(drone_image)
            image["source_type"] = source
            result = validate(image, "image")
            assert result.valid is True, f"{source} should be valid"

    def test_incomplete_capture_gps_fails(self, drone_image):
        bad = copy.deepcopy(drone_image)
        bad["capture_gps"] = {"lat": 42.0}  # missing lon and alt_m
        result = validate(bad, "image")
        assert result.valid is False
        assert any("capture_gps" in e["field"] for e in result.errors)

    def test_capture_heading_null_is_valid(self, drone_image):
        image = copy.deepcopy(drone_image)
        image["capture_heading"] = None
        result = validate(image, "image")
        assert result.valid is True


# ===========================================================================
# Validation Tests — EntityBatch
# ===========================================================================


class TestValidateBatch:
    def test_valid_batch_passes(self):
        batch = {
            "source": "test_import",
            "entities": [
                {
                    "id": "550e8400-e29b-41d4-a716-446655440001",
                    "type": "tree",
                    "geometry": [[42.98750, -70.98720]],
                    "position_gps": {"lat": 42.98750, "lon": -70.98720, "alt_m": 28.0},
                    "provenance": {
                        "source_type": "manual",
                        "source_id": "test",
                        "timestamp": "2026-03-19T10:00:00Z",
                        "accuracy_m": 1.0
                    }
                }
            ],
            "conflict_strategy": "skip"
        }
        result = validate(batch, "batch")
        assert result.valid is True
        assert result.errors == []

    def test_missing_source_fails(self):
        batch = {
            "entities": [],
            "conflict_strategy": "skip"
        }
        result = validate(batch, "batch")
        assert result.valid is False
        assert any("source" in e["field"] for e in result.errors)

    def test_missing_entities_fails(self):
        batch = {
            "source": "test_import",
            "conflict_strategy": "skip"
        }
        result = validate(batch, "batch")
        assert result.valid is False
        assert any("entities" in e["field"] for e in result.errors)

    def test_missing_conflict_strategy_fails(self):
        batch = {
            "source": "test_import",
            "entities": []
        }
        result = validate(batch, "batch")
        assert result.valid is False
        assert any("conflict_strategy" in e["field"] for e in result.errors)

    def test_invalid_conflict_strategy_fails(self):
        batch = {
            "source": "test_import",
            "entities": [],
            "conflict_strategy": "invalid_strategy"
        }
        result = validate(batch, "batch")
        assert result.valid is False
        assert any("conflict_strategy" in e["field"] for e in result.errors)

    def test_valid_conflict_strategies(self):
        valid_strategies = ["skip", "overwrite", "version_bump"]
        for strategy in valid_strategies:
            batch = {
                "source": "test_import",
                "entities": [],
                "conflict_strategy": strategy
            }
            result = validate(batch, "batch")
            assert result.valid is True, f"{strategy} should be valid"

    def test_entity_missing_required_field_fails(self):
        batch = {
            "source": "test_import",
            "entities": [
                {
                    "id": "550e8400-e29b-41d4-a716-446655440001",
                    "type": "tree",
                    # missing geometry, position_gps, provenance
                }
            ],
            "conflict_strategy": "skip"
        }
        result = validate(batch, "batch")
        assert result.valid is False
        assert any("entities[0]" in e["field"] for e in result.errors)


# ===========================================================================
# Pipeline Tests — submit_measurement
# ===========================================================================


class TestSubmitMeasurement:
    def test_submit_valid_measurement_succeeds(self, laser_measurement):
        pipeline = Ingestion()
        result = pipeline.submit_measurement(laser_measurement)
        assert "id" in result
        assert "version" in result
        assert "status" in result

    def test_submit_invalid_measurement_raises(self, laser_measurement):
        bad = copy.deepcopy(laser_measurement)
        del bad["measurement_type"]
        pipeline = Ingestion()
        with pytest.raises(ValueError, match="validation failed"):
            pipeline.submit_measurement(bad)

    def test_submit_measurement_with_null_entity_id(self, laser_measurement):
        measurement = copy.deepcopy(laser_measurement)
        measurement["entity_id"] = None
        pipeline = Ingestion()
        result = pipeline.submit_measurement(measurement)
        assert "id" in result
        # In stub mode, should generate a new entity ID

    def test_submit_measurement_generates_entity_id_when_missing(self, laser_measurement):
        measurement = copy.deepcopy(laser_measurement)
        del measurement["entity_id"]
        pipeline = Ingestion()
        result = pipeline.submit_measurement(measurement)
        assert "id" in result
        assert result["id"] is not None


# ===========================================================================
# Pipeline Tests — submit_image
# ===========================================================================


class TestSubmitImage:
    def test_submit_valid_image_succeeds(self, drone_image):
        pipeline = Ingestion()
        result = pipeline.submit_image(drone_image)
        assert "file_path" in result
        assert result["file_path"] == drone_image["file_path"]

    def test_submit_invalid_image_raises(self, drone_image):
        bad = copy.deepcopy(drone_image)
        del bad["format"]
        pipeline = Ingestion()
        with pytest.raises(ValueError, match="validation failed"):
            pipeline.submit_image(bad)

    def test_submit_image_with_linked_entities(self, drone_image):
        image = copy.deepcopy(drone_image)
        image["linked_entity_ids"] = ["550e8400-e29b-41d4-a716-446655440000"]
        pipeline = Ingestion()
        result = pipeline.submit_image(image)
        assert "image_id" in result
        assert result["status"] == "attached"


# ===========================================================================
# Pipeline Tests — submit_bulk
# ===========================================================================


class TestSubmitBulk:
    def test_submit_valid_batch_succeeds(self):
        batch = {
            "source": "test_import",
            "entities": [
                {
                    "id": "550e8400-e29b-41d4-a716-446655440001",
                    "type": "tree",
                    "geometry": [[42.98750, -70.98720]],
                    "position_gps": {"lat": 42.98750, "lon": -70.98720, "alt_m": 28.0},
                    "provenance": {
                        "source_type": "manual",
                        "source_id": "test",
                        "timestamp": "2026-03-19T10:00:00Z",
                        "accuracy_m": 1.0
                    }
                }
            ],
            "conflict_strategy": "skip"
        }
        pipeline = Ingestion()
        result = pipeline.submit_bulk(batch)
        assert "total" in result
        assert result["total"] == 1

    def test_submit_invalid_batch_raises(self):
        bad = {
            "source": "test_import",
            "entities": [],
            # missing conflict_strategy
        }
        pipeline = Ingestion()
        with pytest.raises(ValueError, match="validation failed"):
            pipeline.submit_bulk(bad)

    def test_submit_batch_with_multiple_entities(self):
        batch = {
            "source": "test_import",
            "entities": [
                {
                    "id": f"550e8400-e29b-41d4-a716-44665544000{i}",
                    "type": "tree",
                    "geometry": [[42.98750, -70.98720]],
                    "position_gps": {"lat": 42.98750, "lon": -70.98720, "alt_m": 28.0},
                    "provenance": {
                        "source_type": "manual",
                        "source_id": "test",
                        "timestamp": "2026-03-19T10:00:00Z",
                        "accuracy_m": 1.0
                    }
                }
                for i in range(3)
            ],
            "conflict_strategy": "overwrite"
        }
        pipeline = Ingestion()
        result = pipeline.submit_bulk(batch)
        assert result["total"] == 3


# ===========================================================================
# Pipeline Tests — validate method
# ===========================================================================


class TestPipelineValidate:
    def test_pipeline_validate_returns_dict(self, laser_measurement):
        pipeline = Ingestion()
        result = pipeline.validate(laser_measurement, "measurement")
        assert isinstance(result, dict)
        assert "valid" in result
        assert "errors" in result
        assert "warnings" in result

    def test_pipeline_validate_measurement(self, laser_measurement):
        pipeline = Ingestion()
        result = pipeline.validate(laser_measurement, "measurement")
        assert result["valid"] is True

    def test_pipeline_validate_image(self, drone_image):
        pipeline = Ingestion()
        result = pipeline.validate(drone_image, "image")
        assert result["valid"] is True

    def test_pipeline_validate_invalid_returns_errors(self, laser_measurement):
        bad = copy.deepcopy(laser_measurement)
        del bad["measurement_type"]
        pipeline = Ingestion()
        result = pipeline.validate(bad, "measurement")
        assert result["valid"] is False
        assert len(result["errors"]) > 0


# ===========================================================================
# Stub Mode Tests
# ===========================================================================


class TestStubMode:
    def test_stub_mode_enabled_via_env(self, laser_measurement, monkeypatch):
        monkeypatch.setenv("HOMEMODEL_MODE", "stub")
        pipeline = Ingestion()
        result = pipeline.submit_measurement(laser_measurement)
        # In stub mode, should return a mock result
        assert result["status"] == "created"
        assert "id" in result

    def test_stub_mode_measurement_logic_executes(self, laser_measurement, monkeypatch):
        monkeypatch.setenv("HOMEMODEL_MODE", "stub")
        pipeline = Ingestion()
        # Validation should still run
        bad = copy.deepcopy(laser_measurement)
        del bad["measurement_type"]
        with pytest.raises(ValueError, match="validation failed"):
            pipeline.submit_measurement(bad)


# ===========================================================================
# ValidationResult Tests
# ===========================================================================


class TestValidationResult:
    def test_validation_result_starts_valid(self):
        result = ValidationResult()
        assert result.valid is True
        assert result.errors == []
        assert result.warnings == []

    def test_add_error_makes_invalid(self):
        result = ValidationResult()
        result.add_error("field", "message")
        assert result.valid is False
        assert len(result.errors) == 1

    def test_add_warning_keeps_valid(self):
        result = ValidationResult()
        result.add_warning("field", "warning")
        assert result.valid is True
        assert len(result.warnings) == 1

    def test_to_dict_returns_correct_structure(self):
        result = ValidationResult()
        result.add_error("field1", "error1")
        result.add_warning("field2", "warning1")
        d = result.to_dict()
        assert d["valid"] is False
        assert len(d["errors"]) == 1
        assert len(d["warnings"]) == 1
        assert d["errors"][0] == {"field": "field1", "message": "error1"}
        assert d["warnings"][0] == {"field": "field2", "message": "warning1"}
