"""Tests for VegetationBuilder.

Covers the VegetationEntity and BuildRecord surfaces from
contracts/domains_to_schema.yaml using the ``tree_white_pine`` fixture.

Test classes
------------
TestCatalogEntities     — entity shape, required/nullable fields, persistence
TestBuildRecord         — BuildRecord logging and field accuracy
TestCanopyShapeEnum     — canopy_shape validation
TestHealthStatusEnum    — health validation
TestMultipleTrees       — batch catalog behaviour
"""
from __future__ import annotations

import copy

import pytest

from schema.store import SchemaStore
from vegetation.builder import VegetationBuilder
from vegetation.canopy import CanopyShape, HealthStatus


# ===========================================================================
# VegetationEntity surface — individual tree as a first-class entity
# ===========================================================================


class TestCatalogEntities:
    """catalog() produces correctly shaped VegetationEntity dicts."""

    def test_catalog_returns_one_entity_for_one_input(
        self, builder: VegetationBuilder, tree_white_pine: dict
    ) -> None:
        result = builder.catalog([tree_white_pine])
        assert len(result["entities"]) == 1

    def test_entity_type_is_tree(
        self, builder: VegetationBuilder, tree_white_pine: dict
    ) -> None:
        result = builder.catalog([tree_white_pine])
        assert result["entities"][0]["type"] == "tree"

    def test_entity_id_matches_survey_id(
        self, builder: VegetationBuilder, tree_white_pine: dict
    ) -> None:
        result = builder.catalog([tree_white_pine])
        assert result["entities"][0]["id"] == tree_white_pine["id"]

    # --- position_gps ---

    def test_entity_position_gps_lat(
        self, builder: VegetationBuilder, tree_white_pine: dict
    ) -> None:
        result = builder.catalog([tree_white_pine])
        assert result["entities"][0]["position_gps"]["lat"] == pytest.approx(42.98760)

    def test_entity_position_gps_lon(
        self, builder: VegetationBuilder, tree_white_pine: dict
    ) -> None:
        result = builder.catalog([tree_white_pine])
        assert result["entities"][0]["position_gps"]["lon"] == pytest.approx(-70.98730)

    def test_entity_position_gps_alt_m(
        self, builder: VegetationBuilder, tree_white_pine: dict
    ) -> None:
        result = builder.catalog([tree_white_pine])
        assert result["entities"][0]["position_gps"]["alt_m"] == pytest.approx(28.4)

    # --- geometry ---

    def test_entity_geometry_type_is_point(
        self, builder: VegetationBuilder, tree_white_pine: dict
    ) -> None:
        result = builder.catalog([tree_white_pine])
        assert result["entities"][0]["geometry"]["type"] == "Point"

    def test_entity_geometry_coordinates_lon(
        self, builder: VegetationBuilder, tree_white_pine: dict
    ) -> None:
        coords = builder.catalog([tree_white_pine])["entities"][0]["geometry"][
            "coordinates"
        ]
        assert coords[0] == pytest.approx(-70.98730)  # GeoJSON: [lon, lat]

    def test_entity_geometry_coordinates_lat(
        self, builder: VegetationBuilder, tree_white_pine: dict
    ) -> None:
        coords = builder.catalog([tree_white_pine])["entities"][0]["geometry"][
            "coordinates"
        ]
        assert coords[1] == pytest.approx(42.98760)

    # --- required properties ---

    def test_entity_height_m(
        self, builder: VegetationBuilder, tree_white_pine: dict
    ) -> None:
        result = builder.catalog([tree_white_pine])
        assert result["entities"][0]["properties"]["height_m"] == pytest.approx(22.5)

    def test_entity_canopy_radius_m(
        self, builder: VegetationBuilder, tree_white_pine: dict
    ) -> None:
        result = builder.catalog([tree_white_pine])
        assert result["entities"][0]["properties"]["canopy_radius_m"] == pytest.approx(
            6.0
        )

    def test_entity_canopy_shape(
        self, builder: VegetationBuilder, tree_white_pine: dict
    ) -> None:
        result = builder.catalog([tree_white_pine])
        assert result["entities"][0]["properties"]["canopy_shape"] == "conical"

    # --- nullable properties ---

    def test_entity_species(
        self, builder: VegetationBuilder, tree_white_pine: dict
    ) -> None:
        result = builder.catalog([tree_white_pine])
        assert result["entities"][0]["properties"]["species"] == "white_pine"

    def test_entity_species_is_nullable(
        self, builder: VegetationBuilder, tree_white_pine: dict
    ) -> None:
        survey = copy.deepcopy(tree_white_pine)
        del survey["properties"]["species"]
        result = builder.catalog([survey])
        assert result["entities"][0]["properties"]["species"] is None

    def test_entity_dbh_cm(
        self, builder: VegetationBuilder, tree_white_pine: dict
    ) -> None:
        result = builder.catalog([tree_white_pine])
        assert result["entities"][0]["properties"]["dbh_cm"] == pytest.approx(62)

    def test_entity_dbh_cm_is_nullable(
        self, builder: VegetationBuilder, tree_white_pine: dict
    ) -> None:
        survey = copy.deepcopy(tree_white_pine)
        del survey["properties"]["dbh_cm"]
        result = builder.catalog([survey])
        assert result["entities"][0]["properties"]["dbh_cm"] is None

    # --- health and tags ---

    def test_entity_health(
        self, builder: VegetationBuilder, tree_white_pine: dict
    ) -> None:
        result = builder.catalog([tree_white_pine])
        assert result["entities"][0]["properties"]["health"] == "healthy"

    def test_entity_tags(
        self, builder: VegetationBuilder, tree_white_pine: dict
    ) -> None:
        result = builder.catalog([tree_white_pine])
        assert result["entities"][0]["properties"]["tags"] == [
            "driveway_line",
            "landmark",
        ]

    def test_entity_tags_default_to_empty_list(
        self, builder: VegetationBuilder, tree_white_pine: dict
    ) -> None:
        survey = copy.deepcopy(tree_white_pine)
        del survey["properties"]["tags"]
        result = builder.catalog([survey])
        assert result["entities"][0]["properties"]["tags"] == []

    # --- provenance ---

    def test_entity_provenance_has_timestamp(
        self, builder: VegetationBuilder, tree_white_pine: dict
    ) -> None:
        result = builder.catalog([tree_white_pine])
        assert result["entities"][0]["provenance"]["timestamp"]

    def test_entity_provenance_source_type(
        self, builder: VegetationBuilder, tree_white_pine: dict
    ) -> None:
        result = builder.catalog([tree_white_pine])
        assert result["entities"][0]["provenance"]["source_type"] == "field_survey"

    # --- persistence ---

    def test_entity_is_persisted_in_store(
        self,
        builder: VegetationBuilder,
        store: SchemaStore,
        tree_white_pine: dict,
    ) -> None:
        result = builder.catalog([tree_white_pine])
        entity_id = result["entities"][0]["id"]
        fetched = store.get_entity(entity_id)
        assert fetched["id"] == entity_id

    def test_persisted_entity_properties_match(
        self,
        builder: VegetationBuilder,
        store: SchemaStore,
        tree_white_pine: dict,
    ) -> None:
        result = builder.catalog([tree_white_pine])
        entity_id = result["entities"][0]["id"]
        fetched = store.get_entity(entity_id)
        assert fetched["properties"]["species"] == "white_pine"
        assert fetched["properties"]["canopy_shape"] == "conical"


# ===========================================================================
# BuildRecord surface — audit every catalog run
# ===========================================================================


class TestBuildRecord:
    """catalog() logs a BuildRecord via store.log_build() every run."""

    def test_build_record_key_present(
        self, builder: VegetationBuilder, tree_white_pine: dict
    ) -> None:
        result = builder.catalog([tree_white_pine])
        assert "build_record" in result

    def test_build_record_domain_is_vegetation(
        self, builder: VegetationBuilder, tree_white_pine: dict
    ) -> None:
        result = builder.catalog([tree_white_pine])
        assert result["build_record"]["domain"] == "vegetation"

    def test_build_record_entities_written_on_first_run(
        self, builder: VegetationBuilder, tree_white_pine: dict
    ) -> None:
        result = builder.catalog([tree_white_pine])
        assert result["build_record"]["entities_written"] == 1

    def test_build_record_entities_updated_zero_on_first_run(
        self, builder: VegetationBuilder, tree_white_pine: dict
    ) -> None:
        result = builder.catalog([tree_white_pine])
        assert result["build_record"]["entities_updated"] == 0

    def test_build_record_entities_updated_on_second_run(
        self, builder: VegetationBuilder, tree_white_pine: dict
    ) -> None:
        builder.catalog([tree_white_pine])
        result = builder.catalog([tree_white_pine])
        assert result["build_record"]["entities_updated"] == 1

    def test_build_record_entities_written_zero_on_second_run(
        self, builder: VegetationBuilder, tree_white_pine: dict
    ) -> None:
        builder.catalog([tree_white_pine])
        result = builder.catalog([tree_white_pine])
        assert result["build_record"]["entities_written"] == 0

    def test_build_record_timestamp_is_non_empty(
        self, builder: VegetationBuilder, tree_white_pine: dict
    ) -> None:
        result = builder.catalog([tree_white_pine])
        assert result["build_record"]["timestamp"] != ""

    def test_build_record_errors_empty_for_valid_data(
        self, builder: VegetationBuilder, tree_white_pine: dict
    ) -> None:
        result = builder.catalog([tree_white_pine])
        assert result["build_record"]["errors"] == []

    def test_build_record_source_inputs_contains_survey(
        self, builder: VegetationBuilder, tree_white_pine: dict
    ) -> None:
        result = builder.catalog([tree_white_pine])
        inputs = result["build_record"]["source_inputs"]
        assert any(inp["type"] == "survey_data" for inp in inputs)

    def test_build_record_source_inputs_count_matches_survey(
        self, builder: VegetationBuilder, tree_white_pine: dict
    ) -> None:
        second = copy.deepcopy(tree_white_pine)
        second["id"] = "bbbbbbbb-1111-2222-3333-444444444444"
        second["position_gps"] = {"lat": 42.98770, "lon": -70.98740, "alt_m": 29.0}
        result = builder.catalog([tree_white_pine, second])
        survey_inputs = [
            i for i in result["build_record"]["source_inputs"]
            if i["type"] == "survey_data"
        ]
        assert len(survey_inputs) == 2

    def test_build_record_logged_to_store(
        self,
        builder: VegetationBuilder,
        store: SchemaStore,
        tree_white_pine: dict,
    ) -> None:
        builder.catalog([tree_white_pine])
        records = store.get_build_records(domain="vegetation")
        assert len(records) == 1

    def test_two_runs_produce_two_build_records(
        self,
        builder: VegetationBuilder,
        store: SchemaStore,
        tree_white_pine: dict,
    ) -> None:
        builder.catalog([tree_white_pine])
        builder.catalog([tree_white_pine])
        records = store.get_build_records(domain="vegetation")
        assert len(records) == 2

    def test_stored_build_record_domain(
        self,
        builder: VegetationBuilder,
        store: SchemaStore,
        tree_white_pine: dict,
    ) -> None:
        builder.catalog([tree_white_pine])
        record = store.get_build_records(domain="vegetation")[0]
        assert record["domain"] == "vegetation"

    def test_aerial_images_added_to_source_inputs(
        self, builder: VegetationBuilder, tree_white_pine: dict
    ) -> None:
        result = builder.catalog([tree_white_pine], aerial_images=["img_001.tif"])
        inputs = result["build_record"]["source_inputs"]
        assert any(inp["type"] == "aerial_image" for inp in inputs)


# ===========================================================================
# canopy_shape enum validation
# ===========================================================================


class TestCanopyShapeEnum:
    """canopy_shape must be one of the five defined values."""

    @pytest.mark.parametrize(
        "shape",
        ["round", "conical", "spreading", "columnar", "irregular"],
    )
    def test_all_valid_shapes_accepted(
        self, builder: VegetationBuilder, tree_white_pine: dict, shape: str
    ) -> None:
        survey = copy.deepcopy(tree_white_pine)
        survey["properties"]["canopy_shape"] = shape
        result = builder.catalog([survey])
        assert result["build_record"]["errors"] == []

    def test_invalid_shape_recorded_as_error(
        self, builder: VegetationBuilder, tree_white_pine: dict
    ) -> None:
        survey = copy.deepcopy(tree_white_pine)
        survey["properties"]["canopy_shape"] = "blob"
        result = builder.catalog([survey])
        assert len(result["build_record"]["errors"]) == 1

    def test_invalid_shape_error_references_entity_id(
        self, builder: VegetationBuilder, tree_white_pine: dict
    ) -> None:
        survey = copy.deepcopy(tree_white_pine)
        survey["properties"]["canopy_shape"] = "blob"
        result = builder.catalog([survey])
        error = result["build_record"]["errors"][0]
        assert error["entity_id"] == tree_white_pine["id"]

    def test_invalid_shape_entity_not_in_entities_list(
        self, builder: VegetationBuilder, tree_white_pine: dict
    ) -> None:
        survey = copy.deepcopy(tree_white_pine)
        survey["properties"]["canopy_shape"] = "blob"
        result = builder.catalog([survey])
        assert result["entities"] == []

    def test_canopy_shape_enum_has_five_values(self) -> None:
        assert len(CanopyShape) == 5

    def test_canopy_shape_values(self) -> None:
        values = {s.value for s in CanopyShape}
        assert values == {"round", "conical", "spreading", "columnar", "irregular"}


# ===========================================================================
# health enum validation
# ===========================================================================


class TestHealthStatusEnum:
    """health must be one of the four defined values; defaults to 'unknown'."""

    @pytest.mark.parametrize("health", ["healthy", "stressed", "dead", "unknown"])
    def test_all_valid_health_values_accepted(
        self, builder: VegetationBuilder, tree_white_pine: dict, health: str
    ) -> None:
        survey = copy.deepcopy(tree_white_pine)
        survey["properties"]["health"] = health
        result = builder.catalog([survey])
        assert result["build_record"]["errors"] == []

    def test_missing_health_defaults_to_unknown(
        self, builder: VegetationBuilder, tree_white_pine: dict
    ) -> None:
        survey = copy.deepcopy(tree_white_pine)
        del survey["properties"]["health"]
        result = builder.catalog([survey])
        assert result["entities"][0]["properties"]["health"] == "unknown"

    def test_invalid_health_recorded_as_error(
        self, builder: VegetationBuilder, tree_white_pine: dict
    ) -> None:
        survey = copy.deepcopy(tree_white_pine)
        survey["properties"]["health"] = "excellent"
        result = builder.catalog([survey])
        assert len(result["build_record"]["errors"]) == 1

    def test_health_status_enum_has_four_values(self) -> None:
        assert len(HealthStatus) == 4

    def test_health_status_values(self) -> None:
        values = {h.value for h in HealthStatus}
        assert values == {"healthy", "stressed", "dead", "unknown"}


# ===========================================================================
# Multiple trees in one catalog run
# ===========================================================================


class TestMultipleTrees:
    """catalog() handles batches of trees correctly."""

    def test_two_trees_produces_two_entities(
        self, builder: VegetationBuilder, tree_white_pine: dict
    ) -> None:
        second = copy.deepcopy(tree_white_pine)
        second["id"] = "cccccccc-1111-2222-3333-444444444444"
        second["position_gps"] = {"lat": 42.98770, "lon": -70.98740, "alt_m": 29.0}
        result = builder.catalog([tree_white_pine, second])
        assert len(result["entities"]) == 2

    def test_two_trees_both_entities_written(
        self, builder: VegetationBuilder, tree_white_pine: dict
    ) -> None:
        second = copy.deepcopy(tree_white_pine)
        second["id"] = "cccccccc-1111-2222-3333-444444444444"
        second["position_gps"] = {"lat": 42.98770, "lon": -70.98740, "alt_m": 29.0}
        result = builder.catalog([tree_white_pine, second])
        assert result["build_record"]["entities_written"] == 2

    def test_one_valid_one_invalid_partial_success(
        self, builder: VegetationBuilder, tree_white_pine: dict
    ) -> None:
        bad = copy.deepcopy(tree_white_pine)
        bad["id"] = "dddddddd-1111-2222-3333-444444444444"
        bad["properties"]["canopy_shape"] = "blob"
        result = builder.catalog([tree_white_pine, bad])
        assert len(result["entities"]) == 1
        assert len(result["build_record"]["errors"]) == 1

    def test_empty_survey_data_produces_zero_entities(
        self, builder: VegetationBuilder
    ) -> None:
        result = builder.catalog([])
        assert result["entities"] == []
        assert result["build_record"]["entities_written"] == 0

    def test_empty_survey_data_still_logs_build_record(
        self,
        builder: VegetationBuilder,
        store: SchemaStore,
    ) -> None:
        builder.catalog([])
        records = store.get_build_records(domain="vegetation")
        assert len(records) == 1

    def test_generated_id_used_when_absent(
        self, builder: VegetationBuilder, tree_white_pine: dict
    ) -> None:
        survey = copy.deepcopy(tree_white_pine)
        del survey["id"]
        result = builder.catalog([survey])
        assert result["entities"][0]["id"] != ""
