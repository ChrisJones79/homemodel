"""
Shared pytest fixtures for the ingestion test suite.

Fixtures mirror the test_fixtures defined in contracts/ingestion_to_schema.yaml.
"""
from __future__ import annotations

import pytest


@pytest.fixture
def laser_measurement() -> dict:
    """Canonical laser measurement from the ingestion_to_schema contract fixture."""
    return {
        "entity_id": "550e8400-e29b-41d4-a716-446655440000",
        "measurement_type": "laser_p2p",
        "value": 3.048,
        "unit": "m",
        "provenance": {
            "source_type": "laser",
            "source_id": "bosch_glm50",
            "timestamp": "2026-03-19T10:30:00Z",
            "accuracy_m": 0.003
        },
        "reference_points": [
            {
                "label": "north_wall_base",
                "position_gps": {"lat": 42.98745, "lon": -70.98705, "alt_m": 26.8}
            },
            {
                "label": "south_wall_base",
                "position_gps": {"lat": 42.98742, "lon": -70.98705, "alt_m": 26.8}
            }
        ]
    }


@pytest.fixture
def drone_image() -> dict:
    """Canonical drone image from the ingestion_to_schema contract fixture."""
    return {
        "file_path": "/data/images/drone/aerial_001.jpg",
        "format": "jpeg",
        "size_bytes": 8500000,
        "capture_gps": {"lat": 42.98743, "lon": -70.98709, "alt_m": 63.4},
        "capture_heading": {"yaw_deg": 180.0, "pitch_deg": -90.0, "roll_deg": 0.0},
        "capture_timestamp": "2026-03-19T11:00:00Z",
        "source_type": "drone_aerial",
        "linked_entity_ids": []
    }
