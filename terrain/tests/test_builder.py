"""
terrain/tests/test_builder.py — Tests for TerrainBuilder.

All tests run with HOMEMODEL_MODE=stub (no network or file I/O).
"""
from __future__ import annotations

import os

import pytest

from terrain.builder import TerrainBuilder


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_builder(store):
    return TerrainBuilder(store)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestGeneratePatches:
    """TerrainBuilder.generate_patches() contract tests."""

    def test_generate_patches_returns_terrain_patch(self, store):
        """generate_patches() must return ≥1 entity with the expected shape."""
        builder = _make_builder(store)
        patches = builder.generate_patches(None)

        assert isinstance(patches, list), "result must be a list"
        assert len(patches) >= 1, "at least one patch must be returned"

        p = patches[0]
        assert p["type"] == "terrain_patch"

        # geometry
        assert "vertices" in p["geometry"]
        assert "faces" in p["geometry"]
        assert len(p["geometry"]["vertices"]) >= 4, "3×3 grid → 9 vertices"
        assert len(p["geometry"]["faces"]) >= 2,    "3×3 grid → ≥2 faces"

        # position_gps
        gps = p["position_gps"]
        assert "lat" in gps
        assert "lon" in gps
        assert "alt_m" in gps

        # properties
        props = p["properties"]
        assert "elevation_source" in props
        assert "texture_source" in props
        assert "slope_avg_deg" in props
        assert isinstance(props["slope_avg_deg"], float)

    def test_patch_shape_matches_fixture(self, store, terrain_patch):
        """Top-level keys of the generated patch must match the fixture."""
        builder = _make_builder(store)
        patches = builder.generate_patches(None)
        generated = patches[0]

        # Every key in the fixture (except 'id' which the fixture lacks)
        # must be present in the generated patch.
        fixture_keys = set(terrain_patch.keys())
        generated_keys = set(generated.keys())

        assert fixture_keys.issubset(generated_keys), (
            f"Generated patch is missing keys: {fixture_keys - generated_keys}"
        )

    def test_patch_stored_in_schema(self, store):
        """The patch returned by generate_patches() must be retrievable by id."""
        builder = _make_builder(store)
        patches = builder.generate_patches(None)
        patch_id = patches[0]["id"]

        retrieved = store.get_entity(patch_id)
        assert retrieved["id"] == patch_id
        assert retrieved["type"] == "terrain_patch"

    def test_build_record_logged(self, store):
        """generate_patches() must log at least one BuildRecord."""
        builder = _make_builder(store)
        builder.generate_patches(None)

        records = store.get_build_records(domain="terrain")
        assert len(records) >= 1, "expected ≥1 build record for domain 'terrain'"

        rec = records[0]
        assert rec["domain"] == "terrain"
        assert rec["entities_written"] == 1
        assert isinstance(rec["errors"], list)

    def test_stub_mode_no_network(self, store):
        """In stub mode, generate_patches(None) must complete without error."""
        assert os.getenv("HOMEMODEL_MODE") == "stub", (
            "This test must run with HOMEMODEL_MODE=stub"
        )
        builder = _make_builder(store)
        # Should not raise even with no elevation file and no images
        patches = builder.generate_patches(None, aerial_images=None)
        assert patches, "expected at least one patch in stub mode"
