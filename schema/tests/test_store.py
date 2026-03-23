"""
Tests for SchemaStore — covers all four contract surfaces from
contracts/schema_to_backend.yaml:

  Surface 1 — get_entity
  Surface 2 — query_region
  Surface 3 — upsert_entity
  Surface 4 — get_history
"""
from __future__ import annotations

import copy

import pytest

from schema.store import SchemaStore


# ===========================================================================
# Surface 3 — upsert_entity
# ===========================================================================


class TestUpsertEntity:
    def test_create_returns_created_status(self, store, entity_tree):
        result = store.upsert_entity(entity_tree)
        assert result["status"] == "created"
        assert result["id"] == "550e8400-e29b-41d4-a716-446655440000"

    def test_create_sets_version_to_1(self, store, entity_tree):
        result = store.upsert_entity(entity_tree)
        assert result["version"] == 1

    def test_second_upsert_returns_updated_status(self, store, entity_tree):
        store.upsert_entity(entity_tree)
        result = store.upsert_entity(entity_tree)
        assert result["status"] == "updated"

    def test_second_upsert_increments_version(self, store, entity_tree):
        store.upsert_entity(entity_tree)
        result = store.upsert_entity(entity_tree)
        assert result["version"] == 2

    def test_third_upsert_increments_version_again(self, store, entity_tree):
        store.upsert_entity(entity_tree)
        store.upsert_entity(entity_tree)
        result = store.upsert_entity(entity_tree)
        assert result["version"] == 3

    def test_upsert_missing_required_field_raises(self, store, entity_tree):
        bad = copy.deepcopy(entity_tree)
        del bad["provenance"]
        with pytest.raises(ValueError, match="missing required fields"):
            store.upsert_entity(bad)

    def test_upsert_bad_position_gps_raises(self, store, entity_tree):
        bad = copy.deepcopy(entity_tree)
        bad["position_gps"] = {"lat": 42.0}  # missing lon + alt_m
        with pytest.raises(ValueError, match="position_gps"):
            store.upsert_entity(bad)


# ===========================================================================
# Surface 1 — get_entity
# ===========================================================================


class TestGetEntity:
    def test_roundtrip_id(self, store, entity_tree):
        store.upsert_entity(entity_tree)
        fetched = store.get_entity(entity_tree["id"])
        assert fetched["id"] == entity_tree["id"]

    def test_roundtrip_type(self, store, entity_tree):
        store.upsert_entity(entity_tree)
        fetched = store.get_entity(entity_tree["id"])
        assert fetched["type"] == entity_tree["type"]

    def test_roundtrip_geometry(self, store, entity_tree):
        store.upsert_entity(entity_tree)
        fetched = store.get_entity(entity_tree["id"])
        assert fetched["geometry"] == entity_tree["geometry"]

    def test_roundtrip_position_gps(self, store, entity_tree):
        store.upsert_entity(entity_tree)
        fetched = store.get_entity(entity_tree["id"])
        gps = fetched["position_gps"]
        expected = entity_tree["position_gps"]
        assert gps["lat"] == pytest.approx(expected["lat"])
        assert gps["lon"] == pytest.approx(expected["lon"])
        assert gps["alt_m"] == pytest.approx(expected["alt_m"])

    def test_roundtrip_provenance(self, store, entity_tree):
        store.upsert_entity(entity_tree)
        fetched = store.get_entity(entity_tree["id"])
        assert fetched["provenance"] == entity_tree["provenance"]

    def test_roundtrip_properties(self, store, entity_tree):
        store.upsert_entity(entity_tree)
        fetched = store.get_entity(entity_tree["id"])
        assert fetched["properties"] == entity_tree["properties"]

    def test_version_is_1_after_create(self, store, entity_tree):
        store.upsert_entity(entity_tree)
        fetched = store.get_entity(entity_tree["id"])
        assert fetched["version"] == 1

    def test_version_is_2_after_update(self, store, entity_tree):
        store.upsert_entity(entity_tree)
        store.upsert_entity(entity_tree)
        fetched = store.get_entity(entity_tree["id"])
        assert fetched["version"] == 2

    def test_unknown_id_raises_key_error(self, store):
        with pytest.raises(KeyError):
            store.get_entity("00000000-0000-0000-0000-000000000000")

    def test_get_entity_reflects_latest_properties(self, store, entity_tree):
        store.upsert_entity(entity_tree)
        updated = copy.deepcopy(entity_tree)
        updated["properties"]["dbh_cm"] = 90
        store.upsert_entity(updated)
        fetched = store.get_entity(entity_tree["id"])
        assert fetched["properties"]["dbh_cm"] == 90


# ===========================================================================
# Surface 2 — query_region
# ===========================================================================


class TestQueryRegion:
    def test_entity_inside_bbox_is_returned(self, store, entity_tree):
        store.upsert_entity(entity_tree)
        bbox = {
            "sw_lat": 42.98700,
            "sw_lon": -70.98800,
            "ne_lat": 42.98800,
            "ne_lon": -70.98600,
        }
        result = store.query_region(bbox)
        assert result["total_count"] == 1
        assert result["entities"][0]["id"] == entity_tree["id"]

    def test_entity_outside_bbox_not_returned(self, store, entity_tree):
        store.upsert_entity(entity_tree)
        bbox = {
            "sw_lat": 41.0,
            "sw_lon": -71.0,
            "ne_lat": 41.5,
            "ne_lon": -70.5,
        }
        result = store.query_region(bbox)
        assert result["total_count"] == 0
        assert result["entities"] == []

    def test_query_region_result_shape(self, store, entity_tree):
        store.upsert_entity(entity_tree)
        bbox = {
            "sw_lat": 42.98700,
            "sw_lon": -70.98800,
            "ne_lat": 42.98800,
            "ne_lon": -70.98600,
        }
        result = store.query_region(bbox)
        entity = result["entities"][0]
        assert set(entity.keys()) == {"id", "type", "bounds", "version"}

    def test_query_region_missing_bbox_key_raises(self, store):
        with pytest.raises(ValueError, match="bbox is missing keys"):
            store.query_region({"sw_lat": 42.0, "sw_lon": -71.0})

    def test_empty_store_returns_empty_list(self, store):
        bbox = {
            "sw_lat": 42.0,
            "sw_lon": -71.0,
            "ne_lat": 43.0,
            "ne_lon": -70.0,
        }
        result = store.query_region(bbox)
        assert result == {"entities": [], "total_count": 0}

    def test_multiple_entities_in_bbox(self, store, entity_tree):
        store.upsert_entity(entity_tree)
        second = copy.deepcopy(entity_tree)
        second["id"] = "660e8400-e29b-41d4-a716-446655440001"
        second["position_gps"] = {"lat": 42.98755, "lon": -70.98715, "alt_m": 29.0}
        store.upsert_entity(second)
        bbox = {
            "sw_lat": 42.98700,
            "sw_lon": -70.98800,
            "ne_lat": 42.98800,
            "ne_lon": -70.98600,
        }
        result = store.query_region(bbox)
        assert result["total_count"] == 2


# ===========================================================================
# Surface 4 — get_history
# ===========================================================================


class TestGetHistory:
    def test_history_after_create_has_one_revision(self, store, entity_tree):
        store.upsert_entity(entity_tree)
        history = store.get_history(entity_tree["id"])
        assert history["id"] == entity_tree["id"]
        assert len(history["revisions"]) == 1

    def test_history_revision_version_is_1(self, store, entity_tree):
        store.upsert_entity(entity_tree)
        history = store.get_history(entity_tree["id"])
        assert history["revisions"][0]["version"] == 1

    def test_history_after_update_has_two_revisions(self, store, entity_tree):
        store.upsert_entity(entity_tree)
        store.upsert_entity(entity_tree)
        history = store.get_history(entity_tree["id"])
        assert len(history["revisions"]) == 2

    def test_history_revisions_ordered_by_version(self, store, entity_tree):
        store.upsert_entity(entity_tree)
        store.upsert_entity(entity_tree)
        store.upsert_entity(entity_tree)
        history = store.get_history(entity_tree["id"])
        versions = [r["version"] for r in history["revisions"]]
        assert versions == sorted(versions)

    def test_history_revision_shape(self, store, entity_tree):
        store.upsert_entity(entity_tree)
        history = store.get_history(entity_tree["id"])
        revision = history["revisions"][0]
        assert set(revision.keys()) == {"version", "timestamp", "provenance", "diff_summary"}

    def test_history_revision_provenance_matches_entity(self, store, entity_tree):
        store.upsert_entity(entity_tree)
        history = store.get_history(entity_tree["id"])
        assert history["revisions"][0]["provenance"] == entity_tree["provenance"]

    def test_history_unknown_id_raises_key_error(self, store):
        with pytest.raises(KeyError):
            store.get_history("00000000-0000-0000-0000-000000000000")

    def test_history_timestamp_comes_from_provenance(self, store, entity_tree):
        store.upsert_entity(entity_tree)
        history = store.get_history(entity_tree["id"])
        assert history["revisions"][0]["timestamp"] == entity_tree["provenance"]["timestamp"]


# ===========================================================================
# Surface 6 — attach_image
# ===========================================================================


class TestAttachImage:
    def test_attach_image_to_entity_returns_image_id(self, store, entity_tree):
        store.upsert_entity(entity_tree)
        image_record = {
            "file_path": "/data/images/test.jpg",
            "format": "jpeg",
            "size_bytes": 1000000,
            "capture_gps": {"lat": 42.98743, "lon": -70.98709, "alt_m": 63.4},
            "capture_heading": {"yaw_deg": 180.0, "pitch_deg": -90.0, "roll_deg": 0.0},
            "capture_timestamp": "2026-03-19T11:00:00Z",
            "source_type": "drone_aerial",
            "linked_entity_ids": []
        }
        image_id = store.attach_image(entity_tree["id"], image_record)
        assert image_id is not None
        assert isinstance(image_id, str)

    def test_attach_standalone_image_without_entity(self, store):
        image_record = {
            "file_path": "/data/images/standalone.jpg",
            "format": "jpeg",
            "size_bytes": 500000,
            "capture_gps": {"lat": 42.98743, "lon": -70.98709, "alt_m": 63.4},
            "capture_timestamp": "2026-03-19T12:00:00Z",
            "source_type": "phone"
        }
        image_id = store.attach_image(None, image_record)
        assert image_id is not None

    def test_attach_image_missing_required_field_raises(self, store, entity_tree):
        store.upsert_entity(entity_tree)
        bad_image = {
            "file_path": "/data/images/test.jpg",
            "format": "jpeg",
            # missing size_bytes, capture_gps, capture_timestamp, source_type
        }
        with pytest.raises(ValueError, match="missing required fields"):
            store.attach_image(entity_tree["id"], bad_image)

    def test_attach_image_to_nonexistent_entity_raises(self, store):
        image_record = {
            "file_path": "/data/images/test.jpg",
            "format": "jpeg",
            "size_bytes": 1000000,
            "capture_gps": {"lat": 42.98743, "lon": -70.98709, "alt_m": 63.4},
            "capture_timestamp": "2026-03-19T11:00:00Z",
            "source_type": "drone_aerial"
        }
        with pytest.raises(KeyError, match="Entity not found"):
            store.attach_image("nonexistent-id", image_record)

    def test_attach_image_with_linked_entities(self, store, entity_tree):
        store.upsert_entity(entity_tree)
        image_record = {
            "file_path": "/data/images/test.jpg",
            "format": "jpeg",
            "size_bytes": 1000000,
            "capture_gps": {"lat": 42.98743, "lon": -70.98709, "alt_m": 63.4},
            "capture_timestamp": "2026-03-19T11:00:00Z",
            "source_type": "drone_aerial",
            "linked_entity_ids": [entity_tree["id"]]
        }
        image_id = store.attach_image(entity_tree["id"], image_record)
        assert image_id is not None


# ===========================================================================
# Surface 7 — bulk_upsert
# ===========================================================================


class TestBulkUpsert:
    def test_bulk_upsert_creates_new_entities(self, store, entity_tree):
        batch = {
            "source": "test_import",
            "entities": [entity_tree],
            "conflict_strategy": "skip"
        }
        result = store.bulk_upsert(batch)
        assert result["created"] == 1
        assert result["updated"] == 0
        assert result["skipped"] == 0
        assert result["total"] == 1

    def test_bulk_upsert_skip_strategy_skips_existing(self, store, entity_tree):
        # Create entity first
        store.upsert_entity(entity_tree)
        # Try to bulk upsert with skip strategy
        batch = {
            "source": "test_import",
            "entities": [entity_tree],
            "conflict_strategy": "skip"
        }
        result = store.bulk_upsert(batch)
        assert result["created"] == 0
        assert result["updated"] == 0
        assert result["skipped"] == 1

    def test_bulk_upsert_overwrite_strategy_updates_existing(self, store, entity_tree):
        # Create entity first
        store.upsert_entity(entity_tree)
        # Modify entity and bulk upsert with overwrite strategy
        modified = copy.deepcopy(entity_tree)
        modified["properties"]["dbh_cm"] = 100
        batch = {
            "source": "test_import",
            "entities": [modified],
            "conflict_strategy": "overwrite"
        }
        result = store.bulk_upsert(batch)
        assert result["created"] == 0
        assert result["updated"] == 1
        assert result["skipped"] == 0
        # Verify entity was updated
        fetched = store.get_entity(entity_tree["id"])
        assert fetched["properties"]["dbh_cm"] == 100
        assert fetched["version"] == 2

    def test_bulk_upsert_version_bump_strategy_updates_existing(self, store, entity_tree):
        # Create entity first
        store.upsert_entity(entity_tree)
        # Modify entity and bulk upsert with version_bump strategy
        modified = copy.deepcopy(entity_tree)
        modified["properties"]["dbh_cm"] = 95
        batch = {
            "source": "test_import",
            "entities": [modified],
            "conflict_strategy": "version_bump"
        }
        result = store.bulk_upsert(batch)
        assert result["created"] == 0
        assert result["updated"] == 1
        assert result["skipped"] == 0
        # Verify entity was updated and version incremented
        fetched = store.get_entity(entity_tree["id"])
        assert fetched["properties"]["dbh_cm"] == 95
        assert fetched["version"] == 2

    def test_bulk_upsert_multiple_entities(self, store, entity_tree):
        second = copy.deepcopy(entity_tree)
        second["id"] = "660e8400-e29b-41d4-a716-446655440001"
        third = copy.deepcopy(entity_tree)
        third["id"] = "770e8400-e29b-41d4-a716-446655440002"

        batch = {
            "source": "test_import",
            "entities": [entity_tree, second, third],
            "conflict_strategy": "skip"
        }
        result = store.bulk_upsert(batch)
        assert result["created"] == 3
        assert result["total"] == 3

    def test_bulk_upsert_invalid_conflict_strategy_raises(self, store):
        batch = {
            "source": "test_import",
            "entities": [],
            "conflict_strategy": "invalid_strategy"
        }
        with pytest.raises(ValueError, match="Invalid conflict_strategy"):
            store.bulk_upsert(batch)

    def test_bulk_upsert_missing_required_field_raises(self, store):
        batch = {
            "source": "test_import",
            "entities": []
            # missing conflict_strategy
        }
        with pytest.raises(ValueError, match="missing required fields"):
            store.bulk_upsert(batch)

    def test_bulk_upsert_with_invalid_entity_records_errors(self, store):
        bad_entity = {
            "id": "invalid-entity",
            "type": "tree",
            # missing required fields
        }
        batch = {
            "source": "test_import",
            "entities": [bad_entity],
            "conflict_strategy": "skip"
        }
        result = store.bulk_upsert(batch)
        assert result["created"] == 0
        assert len(result["errors"]) == 1
        assert result["errors"][0]["id"] == "invalid-entity"

    def test_bulk_upsert_mixed_new_and_existing(self, store, entity_tree):
        # Create first entity
        store.upsert_entity(entity_tree)
        # Create second new entity
        second = copy.deepcopy(entity_tree)
        second["id"] = "660e8400-e29b-41d4-a716-446655440001"

        batch = {
            "source": "test_import",
            "entities": [entity_tree, second],
            "conflict_strategy": "skip"
        }
        result = store.bulk_upsert(batch)
        assert result["created"] == 1  # only second is new
        assert result["skipped"] == 1  # first already exists
        assert result["total"] == 2

