"""Shared pytest fixtures for the vegetation test suite.

The ``tree_white_pine`` fixture mirrors the ``test_fixtures.tree_white_pine``
entry in contracts/domains_to_schema.yaml and is expressed as the survey-data
input format expected by ``VegetationBuilder.catalog()``.
"""
from __future__ import annotations

import pytest

from schema.store import SchemaStore
from vegetation.builder import VegetationBuilder


@pytest.fixture
def tree_white_pine() -> dict:
    """Canonical white-pine survey entry from domains_to_schema.yaml fixtures."""
    return {
        "id": "aa000000-1111-2222-3333-444444444444",
        "position_gps": {"lat": 42.98760, "lon": -70.98730, "alt_m": 28.4},
        "source_type": "field_survey",
        "source_id": "survey_2026_spring",
        "accuracy_m": 0.5,
        "properties": {
            "species": "white_pine",
            "dbh_cm": 62,
            "height_m": 22.5,
            "canopy_radius_m": 6.0,
            "canopy_shape": "conical",
            "health": "healthy",
            "tags": ["driveway_line", "landmark"],
        },
    }


@pytest.fixture
def store() -> SchemaStore:
    """Fresh in-memory SchemaStore for each test."""
    with SchemaStore(":memory:") as s:
        yield s


@pytest.fixture
def builder(store: SchemaStore) -> VegetationBuilder:
    """VegetationBuilder backed by an in-memory SchemaStore."""
    return VegetationBuilder(store)
