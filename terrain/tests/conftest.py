"""
terrain/tests/conftest.py — shared pytest fixtures for terrain tests.
"""
import pytest

from schema.store import SchemaStore


@pytest.fixture
def terrain_patch():
    """Canonical TerrainPatch fixture from domains_to_schema contract."""
    return {
        "type": "terrain_patch",
        "geometry": {
            "vertices": [[0, 0, 26.5], [10, 0, 26.7], [0, 10, 27.4]],
            "faces": [[0, 1, 2]],
        },
        "position_gps": {"lat": 42.98743, "lon": -70.98709, "alt_m": 26.8},
        "bounds_gps": {
            "sw": {"lat": 42.98693, "lon": -70.98759},
            "ne": {"lat": 42.98793, "lon": -70.98659},
        },
        "resolution_m": 1.0,
        "properties": {
            "elevation_source": "usgs_ned",
            "texture_source": None,
            "slope_avg_deg": 4.2,
        },
    }


@pytest.fixture
def store():
    """Fresh in-memory SchemaStore for terrain tests."""
    with SchemaStore(":memory:") as s:
        yield s
