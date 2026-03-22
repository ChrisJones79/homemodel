"""
Shared pytest fixtures for the structures test suite.

Fixtures provide test data for StructureBuilder tests following the
contracts defined in contracts/domains_to_schema.yaml.
"""
from __future__ import annotations

import pytest

from schema.store import SchemaStore
from structures.builder import StructureBuilder


@pytest.fixture
def store() -> SchemaStore:
    """Fresh in-memory SchemaStore for each test."""
    with SchemaStore(":memory:") as s:
        yield s


@pytest.fixture
def builder(store) -> StructureBuilder:
    """StructureBuilder instance with a fresh store."""
    return StructureBuilder(store)


@pytest.fixture
def simple_floorplan() -> dict:
    """
    Simple floor plan with one wall and one room.

    Follows the contract from contracts/domains_to_schema.yaml.
    """
    return {
        "id": "structure-001",
        "position_gps": {"lat": 42.98743, "lon": -70.98709, "alt_m": 26.8},
        "floor_level": 0,
        "material": "wood_frame",
        "walls": [
            {
                "id": "wall-001",
                "start_point": (0.0, 0.0),
                "end_point": (5.0, 0.0),
                "height_m": 2.4,
                "thickness_m": 0.15,
                "floor_level": 0,
                "material": "drywall",
                "openings": [
                    {
                        "type": "door",
                        "position_offset": 1.0,
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


@pytest.fixture
def complex_floorplan() -> dict:
    """
    Complex floor plan with multiple walls, rooms, and openings.
    """
    return {
        "id": "structure-002",
        "position_gps": {"lat": 42.98750, "lon": -70.98720, "alt_m": 27.0},
        "floor_level": 0,
        "material": "brick",
        "walls": [
            {
                "id": "wall-north",
                "start_point": (0.0, 0.0),
                "end_point": (10.0, 0.0),
                "height_m": 2.7,
                "thickness_m": 0.20,
                "floor_level": 0,
                "material": "brick",
                "openings": [
                    {"type": "window", "position_offset": 2.0, "width_m": 1.2, "height_m": 1.5},
                    {"type": "window", "position_offset": 7.0, "width_m": 1.2, "height_m": 1.5},
                ],
            },
            {
                "id": "wall-south",
                "start_point": (0.0, 8.0),
                "end_point": (10.0, 8.0),
                "height_m": 2.7,
                "thickness_m": 0.20,
                "floor_level": 0,
                "material": "brick",
                "openings": [
                    {"type": "door", "position_offset": 4.5, "width_m": 0.9, "height_m": 2.1}
                ],
            },
            {
                "id": "wall-east",
                "start_point": (10.0, 0.0),
                "end_point": (10.0, 8.0),
                "height_m": 2.7,
                "thickness_m": 0.20,
                "floor_level": 0,
                "material": "brick",
                "openings": [],
            },
            {
                "id": "wall-west",
                "start_point": (0.0, 0.0),
                "end_point": (0.0, 8.0),
                "height_m": 2.7,
                "thickness_m": 0.20,
                "floor_level": 0,
                "material": "brick",
                "openings": [],
            },
        ],
        "rooms": [
            {
                "id": "room-living",
                "boundary_points": [(0.0, 0.0), (6.0, 0.0), (6.0, 8.0), (0.0, 8.0)],
                "floor_height_m": 0.0,
                "ceiling_height_m": 2.7,
                "floor_level": 0,
            },
            {
                "id": "room-kitchen",
                "boundary_points": [(6.0, 0.0), (10.0, 0.0), (10.0, 8.0), (6.0, 8.0)],
                "floor_height_m": 0.0,
                "ceiling_height_m": 2.7,
                "floor_level": 0,
            },
        ],
    }


@pytest.fixture
def laser_measurements() -> list[dict]:
    """
    Sample laser measurements following ingestion_to_schema contract.
    """
    return [
        {
            "entity_id": "wall-001",
            "measurement_type": "laser_p2p",
            "value": 5.0,
            "unit": "m",
            "provenance": {
                "source_type": "laser",
                "source_id": "bosch_glm50",
                "timestamp": "2026-03-19T10:30:00Z",
                "accuracy_m": 0.003,
            },
            "reference_points": [
                {
                    "label": "wall_start",
                    "position_gps": {"lat": 42.98743, "lon": -70.98709, "alt_m": 26.8},
                },
                {
                    "label": "wall_end",
                    "position_gps": {"lat": 42.98743, "lon": -70.98704, "alt_m": 26.8},
                },
            ],
        }
    ]


@pytest.fixture
def image_records() -> list[dict]:
    """
    Sample image records following ingestion_to_schema contract.
    """
    return [
        {
            "file_path": "/data/images/floorplan_001.jpg",
            "format": "jpeg",
            "size_bytes": 2500000,
            "capture_gps": {"lat": 42.98743, "lon": -70.98709, "alt_m": 27.5},
            "capture_heading": {"yaw_deg": 0.0, "pitch_deg": -90.0, "roll_deg": 0.0},
            "capture_timestamp": "2026-03-19T11:00:00Z",
            "source_type": "phone",
            "linked_entity_ids": [],
        }
    ]
