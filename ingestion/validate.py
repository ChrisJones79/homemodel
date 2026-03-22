"""
Validation logic for ingestion pipeline.

All payloads are validated before submission to SchemaStore.
Validation checks for required fields, enum values, and data types.
"""
from __future__ import annotations

from typing import Any


class ValidationResult:
    """Result of validating a payload.

    Attributes
    ----------
    valid : bool
        True if the payload is valid
    errors : list[dict[str, str]]
        List of error dicts with 'field' and 'message' keys
    warnings : list[dict[str, str]]
        List of warning dicts with 'field' and 'message' keys
    """

    def __init__(self) -> None:
        self.valid: bool = True
        self.errors: list[dict[str, str]] = []
        self.warnings: list[dict[str, str]] = []

    def add_error(self, field: str, message: str) -> None:
        """Add an error and mark the result as invalid."""
        self.errors.append({"field": field, "message": message})
        self.valid = False

    def add_warning(self, field: str, message: str) -> None:
        """Add a warning (does not affect validity)."""
        self.warnings.append({"field": field, "message": message})

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict matching the ValidationResult contract."""
        return {
            "valid": self.valid,
            "errors": self.errors,
            "warnings": self.warnings,
        }


def validate(payload: Any, payload_type: str) -> ValidationResult:
    """Validate a payload before submission.

    Parameters
    ----------
    payload : dict
        The payload to validate
    payload_type : str
        Type of payload: 'measurement', 'image', or 'batch'

    Returns
    -------
    ValidationResult
        Result indicating whether the payload is valid
    """
    result = ValidationResult()

    if not isinstance(payload, dict):
        result.add_error("payload", "Payload must be a dict")
        return result

    if payload_type == "measurement":
        _validate_measurement(payload, result)
    elif payload_type == "image":
        _validate_image(payload, result)
    elif payload_type == "batch":
        _validate_batch(payload, result)
    else:
        result.add_error("payload_type", f"Unknown payload type: {payload_type}")

    return result


def _validate_measurement(payload: dict, result: ValidationResult) -> None:
    """Validate a Measurement payload."""
    # Required fields
    required = ["measurement_type", "value", "unit", "provenance"]
    for field in required:
        if field not in payload:
            result.add_error(field, f"Missing required field: {field}")

    # entity_id is optional (null for new entities)
    if "entity_id" in payload and payload["entity_id"] is not None:
        if not isinstance(payload["entity_id"], str):
            result.add_error("entity_id", "entity_id must be a string or null")

    # Validate measurement_type enum
    if "measurement_type" in payload:
        valid_types = ["laser_p2p", "gps_point", "image_derived", "drone_telemetry"]
        if payload["measurement_type"] not in valid_types:
            result.add_error(
                "measurement_type",
                f"Invalid measurement_type. Must be one of: {', '.join(valid_types)}"
            )

    # Validate value is float or list of floats
    if "value" in payload:
        value = payload["value"]
        if not isinstance(value, (int, float, list)):
            result.add_error("value", "value must be a float or list of floats")
        elif isinstance(value, list):
            if not all(isinstance(v, (int, float)) for v in value):
                result.add_error("value", "All elements in value list must be floats")

    # Validate unit enum
    if "unit" in payload:
        valid_units = ["m", "cm", "mm", "inch", "deg"]
        if payload["unit"] not in valid_units:
            result.add_error(
                "unit",
                f"Invalid unit. Must be one of: {', '.join(valid_units)}"
            )

    # Validate provenance (mandatory)
    if "provenance" in payload:
        prov = payload["provenance"]
        if not isinstance(prov, dict):
            result.add_error("provenance", "provenance must be a dict")
        else:
            required_prov = ["source_type", "source_id", "timestamp", "accuracy_m"]
            for field in required_prov:
                if field not in prov:
                    result.add_error(f"provenance.{field}", f"Missing provenance field: {field}")

    # Validate reference_points if present
    if "reference_points" in payload:
        ref_points = payload["reference_points"]
        if not isinstance(ref_points, list):
            result.add_error("reference_points", "reference_points must be a list")
        else:
            for i, point in enumerate(ref_points):
                if not isinstance(point, dict):
                    result.add_error(f"reference_points[{i}]", "reference_point must be a dict")
                else:
                    if "label" not in point:
                        result.add_error(f"reference_points[{i}].label", "Missing label")
                    if "position_gps" not in point:
                        result.add_error(f"reference_points[{i}].position_gps", "Missing position_gps")
                    elif not isinstance(point["position_gps"], dict):
                        result.add_error(f"reference_points[{i}].position_gps", "position_gps must be a dict")
                    else:
                        gps = point["position_gps"]
                        for gps_field in ["lat", "lon", "alt_m"]:
                            if gps_field not in gps:
                                result.add_error(
                                    f"reference_points[{i}].position_gps.{gps_field}",
                                    f"Missing GPS field: {gps_field}"
                                )


def _validate_image(payload: dict, result: ValidationResult) -> None:
    """Validate an ImageRecord payload."""
    # Required fields
    required = [
        "file_path",
        "format",
        "size_bytes",
        "capture_gps",
        "capture_timestamp",
        "source_type"
    ]
    for field in required:
        if field not in payload:
            result.add_error(field, f"Missing required field: {field}")

    # Validate format enum
    if "format" in payload:
        valid_formats = ["jpeg", "png", "tiff", "raw"]
        if payload["format"] not in valid_formats:
            result.add_error(
                "format",
                f"Invalid format. Must be one of: {', '.join(valid_formats)}"
            )

    # Validate size_bytes is integer
    if "size_bytes" in payload:
        if not isinstance(payload["size_bytes"], int):
            result.add_error("size_bytes", "size_bytes must be an integer")

    # Validate capture_gps
    if "capture_gps" in payload:
        gps = payload["capture_gps"]
        if not isinstance(gps, dict):
            result.add_error("capture_gps", "capture_gps must be a dict")
        else:
            for field in ["lat", "lon", "alt_m"]:
                if field not in gps:
                    result.add_error(f"capture_gps.{field}", f"Missing GPS field: {field}")

    # Validate capture_heading if present (nullable)
    if "capture_heading" in payload and payload["capture_heading"] is not None:
        heading = payload["capture_heading"]
        if not isinstance(heading, dict):
            result.add_error("capture_heading", "capture_heading must be a dict or null")
        else:
            for field in ["yaw_deg", "pitch_deg", "roll_deg"]:
                if field not in heading:
                    result.add_error(f"capture_heading.{field}", f"Missing heading field: {field}")

    # Validate source_type enum
    if "source_type" in payload:
        valid_sources = ["phone", "drone_aerial", "drone_ground", "dslr", "scan"]
        if payload["source_type"] not in valid_sources:
            result.add_error(
                "source_type",
                f"Invalid source_type. Must be one of: {', '.join(valid_sources)}"
            )

    # Validate linked_entity_ids if present
    if "linked_entity_ids" in payload:
        ids = payload["linked_entity_ids"]
        if not isinstance(ids, list):
            result.add_error("linked_entity_ids", "linked_entity_ids must be a list")
        else:
            if not all(isinstance(id, str) for id in ids):
                result.add_error("linked_entity_ids", "All entity IDs must be strings")


def _validate_batch(payload: dict, result: ValidationResult) -> None:
    """Validate an EntityBatch payload."""
    # Required fields
    required = ["source", "entities", "conflict_strategy"]
    for field in required:
        if field not in payload:
            result.add_error(field, f"Missing required field: {field}")

    # Validate conflict_strategy enum
    if "conflict_strategy" in payload:
        valid_strategies = ["skip", "overwrite", "version_bump"]
        if payload["conflict_strategy"] not in valid_strategies:
            result.add_error(
                "conflict_strategy",
                f"Invalid conflict_strategy. Must be one of: {', '.join(valid_strategies)}"
            )

    # Validate entities is a list
    if "entities" in payload:
        entities = payload["entities"]
        if not isinstance(entities, list):
            result.add_error("entities", "entities must be a list")
        else:
            # Each entity should match the schema Entity contract
            for i, entity in enumerate(entities):
                if not isinstance(entity, dict):
                    result.add_error(f"entities[{i}]", "entity must be a dict")
                else:
                    entity_required = ["id", "type", "geometry", "position_gps", "provenance"]
                    for field in entity_required:
                        if field not in entity:
                            result.add_error(f"entities[{i}].{field}", f"Missing entity field: {field}")
