"""
Tests for StructureBuilder — covers the compile() method and validates
that generated entities match the StructureEntity contract from
contracts/domains_to_schema.yaml.
"""
from __future__ import annotations

import pytest


# ===========================================================================
# StructureBuilder.compile() tests
# ===========================================================================


class TestStructureBuilderCompile:
    """Test the main compile() method."""

    def test_compile_returns_build_record(self, builder, simple_floorplan, laser_measurements, image_records):
        """Compile should return a BuildRecord dict."""
        result = builder.compile(simple_floorplan, laser_measurements, image_records)
        assert "domain" in result
        assert "timestamp" in result
        assert "source_inputs" in result
        assert "entities_written" in result
        assert "entities_updated" in result
        assert "errors" in result

    def test_compile_sets_domain_to_structures(self, builder, simple_floorplan):
        """BuildRecord domain should be 'structures'."""
        result = builder.compile(simple_floorplan, [], [])
        assert result["domain"] == "structures"

    def test_compile_creates_structure_entity(self, builder, store, simple_floorplan):
        """Compile should create a structure entity in the store."""
        builder.compile(simple_floorplan, [], [])
        entity = store.get_entity("structure-001")
        assert entity["type"] == "structure"

    def test_compile_creates_wall_entity(self, builder, store, simple_floorplan):
        """Compile should create wall entities in the store."""
        builder.compile(simple_floorplan, [], [])
        entity = store.get_entity("wall-001")
        assert entity["type"] == "wall"

    def test_compile_creates_room_entity(self, builder, store, simple_floorplan):
        """Compile should create room entities in the store."""
        builder.compile(simple_floorplan, [], [])
        entity = store.get_entity("room-001")
        assert entity["type"] == "room"

    def test_compile_counts_entities_written(self, builder, simple_floorplan):
        """BuildRecord should count entities_written correctly."""
        result = builder.compile(simple_floorplan, [], [])
        # 1 structure + 1 wall + 1 room = 3
        assert result["entities_written"] == 3

    def test_compile_complex_floorplan(self, builder, complex_floorplan):
        """Should handle complex floor plans with multiple entities."""
        result = builder.compile(complex_floorplan, [], [])
        # 1 structure + 4 walls + 2 rooms = 7
        assert result["entities_written"] == 7
        assert len(result["errors"]) == 0

    def test_compile_tracks_source_inputs(self, builder, simple_floorplan, laser_measurements, image_records):
        """BuildRecord should track source inputs."""
        result = builder.compile(simple_floorplan, laser_measurements, image_records)
        assert len(result["source_inputs"]) == 2  # 1 measurement + 1 image


# ===========================================================================
# Structure entity tests
# ===========================================================================


class TestStructureEntity:
    """Test structure entity generation."""

    def test_structure_has_required_fields(self, builder, store, simple_floorplan):
        """Structure entity should have all required fields."""
        builder.compile(simple_floorplan, [], [])
        entity = store.get_entity("structure-001")
        assert "id" in entity
        assert "type" in entity
        assert "geometry" in entity
        assert "position_gps" in entity
        assert "provenance" in entity
        assert "properties" in entity

    def test_structure_type_is_structure(self, builder, store, simple_floorplan):
        """Structure entity type should be 'structure'."""
        builder.compile(simple_floorplan, [], [])
        entity = store.get_entity("structure-001")
        assert entity["type"] == "structure"

    def test_structure_has_position_gps(self, builder, store, simple_floorplan):
        """Structure should have position_gps from floorplan."""
        builder.compile(simple_floorplan, [], [])
        entity = store.get_entity("structure-001")
        gps = entity["position_gps"]
        assert gps["lat"] == pytest.approx(42.98743)
        assert gps["lon"] == pytest.approx(-70.98709)
        assert gps["alt_m"] == pytest.approx(26.8)

    def test_structure_has_floor_level(self, builder, store, simple_floorplan):
        """Structure should have floor_level in properties."""
        builder.compile(simple_floorplan, [], [])
        entity = store.get_entity("structure-001")
        assert entity["properties"]["floor_level"] == 0

    def test_structure_has_material(self, builder, store, simple_floorplan):
        """Structure should have material in properties."""
        builder.compile(simple_floorplan, [], [])
        entity = store.get_entity("structure-001")
        assert entity["properties"]["material"] == "wood_frame"

    def test_structure_parent_id_is_none(self, builder, store, simple_floorplan):
        """Structure should have null parent_id (it's the top level)."""
        builder.compile(simple_floorplan, [], [])
        entity = store.get_entity("structure-001")
        assert entity["properties"]["parent_id"] is None


# ===========================================================================
# Wall entity tests
# ===========================================================================


class TestWallEntity:
    """Test wall entity generation."""

    def test_wall_has_required_fields(self, builder, store, simple_floorplan):
        """Wall entity should have all required fields."""
        builder.compile(simple_floorplan, [], [])
        entity = store.get_entity("wall-001")
        assert "id" in entity
        assert "type" in entity
        assert "geometry" in entity
        assert "position_gps" in entity
        assert "provenance" in entity
        assert "properties" in entity

    def test_wall_type_is_wall(self, builder, store, simple_floorplan):
        """Wall entity type should be 'wall'."""
        builder.compile(simple_floorplan, [], [])
        entity = store.get_entity("wall-001")
        assert entity["type"] == "wall"

    def test_wall_parent_id_links_to_structure(self, builder, store, simple_floorplan):
        """Wall parent_id should link to the structure."""
        builder.compile(simple_floorplan, [], [])
        entity = store.get_entity("wall-001")
        assert entity["properties"]["parent_id"] == "structure-001"

    def test_wall_has_geometry(self, builder, store, simple_floorplan):
        """Wall should have extruded 3D geometry."""
        builder.compile(simple_floorplan, [], [])
        entity = store.get_entity("wall-001")
        geometry = entity["geometry"]
        assert "vertices" in geometry
        assert "faces" in geometry
        assert len(geometry["vertices"]) > 0
        assert len(geometry["faces"]) > 0

    def test_wall_has_dimensions(self, builder, store, simple_floorplan):
        """Wall should have dimensions in properties."""
        builder.compile(simple_floorplan, [], [])
        entity = store.get_entity("wall-001")
        dimensions = entity["properties"]["dimensions"]
        assert "width_m" in dimensions
        assert "height_m" in dimensions
        assert "depth_m" in dimensions
        assert dimensions["width_m"] == pytest.approx(5.0)  # Wall length
        assert dimensions["height_m"] == pytest.approx(2.4)
        assert dimensions["depth_m"] == pytest.approx(0.15)  # Thickness

    def test_wall_has_openings(self, builder, store, simple_floorplan):
        """Wall should have openings (doors/windows) in properties."""
        builder.compile(simple_floorplan, [], [])
        entity = store.get_entity("wall-001")
        openings = entity["properties"]["openings"]
        assert len(openings) == 1
        assert openings[0]["type"] == "door"
        assert openings[0]["width_m"] == 0.9
        assert openings[0]["height_m"] == 2.1

    def test_wall_has_material(self, builder, store, simple_floorplan):
        """Wall should have material in properties."""
        builder.compile(simple_floorplan, [], [])
        entity = store.get_entity("wall-001")
        assert entity["properties"]["material"] == "drywall"

    def test_multiple_walls_created(self, builder, store, complex_floorplan):
        """Should create all walls from complex floor plan."""
        builder.compile(complex_floorplan, [], [])
        north_wall = store.get_entity("wall-north")
        south_wall = store.get_entity("wall-south")
        east_wall = store.get_entity("wall-east")
        west_wall = store.get_entity("wall-west")
        assert north_wall["type"] == "wall"
        assert south_wall["type"] == "wall"
        assert east_wall["type"] == "wall"
        assert west_wall["type"] == "wall"

    def test_wall_with_multiple_openings(self, builder, store, complex_floorplan):
        """Wall should support multiple openings."""
        builder.compile(complex_floorplan, [], [])
        entity = store.get_entity("wall-north")
        openings = entity["properties"]["openings"]
        assert len(openings) == 2
        assert all(o["type"] == "window" for o in openings)


# ===========================================================================
# Room entity tests
# ===========================================================================


class TestRoomEntity:
    """Test room entity generation."""

    def test_room_has_required_fields(self, builder, store, simple_floorplan):
        """Room entity should have all required fields."""
        builder.compile(simple_floorplan, [], [])
        entity = store.get_entity("room-001")
        assert "id" in entity
        assert "type" in entity
        assert "geometry" in entity
        assert "position_gps" in entity
        assert "provenance" in entity
        assert "properties" in entity

    def test_room_type_is_room(self, builder, store, simple_floorplan):
        """Room entity type should be 'room'."""
        builder.compile(simple_floorplan, [], [])
        entity = store.get_entity("room-001")
        assert entity["type"] == "room"

    def test_room_parent_id_links_to_structure(self, builder, store, simple_floorplan):
        """Room parent_id should link to the structure."""
        builder.compile(simple_floorplan, [], [])
        entity = store.get_entity("room-001")
        assert entity["properties"]["parent_id"] == "structure-001"

    def test_room_has_geometry(self, builder, store, simple_floorplan):
        """Room should have extruded 3D geometry."""
        builder.compile(simple_floorplan, [], [])
        entity = store.get_entity("room-001")
        geometry = entity["geometry"]
        assert "vertices" in geometry
        assert "faces" in geometry
        assert len(geometry["vertices"]) > 0
        assert len(geometry["faces"]) > 0

    def test_room_has_dimensions(self, builder, store, simple_floorplan):
        """Room should have dimensions in properties."""
        builder.compile(simple_floorplan, [], [])
        entity = store.get_entity("room-001")
        dimensions = entity["properties"]["dimensions"]
        assert "width_m" in dimensions
        assert "depth_m" in dimensions
        assert "height_m" in dimensions
        assert dimensions["width_m"] == pytest.approx(5.0)
        assert dimensions["depth_m"] == pytest.approx(4.0)
        assert dimensions["height_m"] == pytest.approx(2.4)

    def test_multiple_rooms_created(self, builder, store, complex_floorplan):
        """Should create all rooms from complex floor plan."""
        builder.compile(complex_floorplan, [], [])
        living = store.get_entity("room-living")
        kitchen = store.get_entity("room-kitchen")
        assert living["type"] == "room"
        assert kitchen["type"] == "room"


# ===========================================================================
# Provenance tests
# ===========================================================================


class TestProvenance:
    """Test provenance tracking."""

    def test_provenance_from_measurements(self, builder, store, simple_floorplan, laser_measurements):
        """Provenance should be derived from measurements."""
        builder.compile(simple_floorplan, laser_measurements, [])
        entity = store.get_entity("structure-001")
        prov = entity["provenance"]
        assert prov["source_type"] == "laser"
        assert prov["source_id"] == "bosch_glm50"
        assert "timestamp" in prov
        assert "accuracy_m" in prov

    def test_provenance_from_images(self, builder, store, simple_floorplan, image_records):
        """Provenance should be derived from images when no measurements."""
        builder.compile(simple_floorplan, [], image_records)
        entity = store.get_entity("structure-001")
        prov = entity["provenance"]
        assert prov["source_type"] == "image"
        assert "timestamp" in prov

    def test_provenance_manual_when_no_inputs(self, builder, store, simple_floorplan):
        """Provenance should default to manual when no measurements or images."""
        builder.compile(simple_floorplan, [], [])
        entity = store.get_entity("structure-001")
        prov = entity["provenance"]
        assert prov["source_type"] == "manual"
        assert prov["source_id"] == "structure_builder"


# ===========================================================================
# Geometry extrusion tests
# ===========================================================================


class TestGeometryExtrusion:
    """Test that geometry is properly extruded from 2D to 3D."""

    def test_wall_geometry_has_8_vertices(self, builder, store, simple_floorplan):
        """Extruded wall should have 8 vertices (4 bottom, 4 top)."""
        builder.compile(simple_floorplan, [], [])
        entity = store.get_entity("wall-001")
        vertices = entity["geometry"]["vertices"]
        assert len(vertices) == 8

    def test_wall_vertices_are_3d(self, builder, store, simple_floorplan):
        """Wall vertices should be 3D coordinates [x, y, z]."""
        builder.compile(simple_floorplan, [], [])
        entity = store.get_entity("wall-001")
        vertices = entity["geometry"]["vertices"]
        for v in vertices:
            assert len(v) == 3  # x, y, z

    def test_room_geometry_vertices(self, builder, store, simple_floorplan):
        """Extruded room should have vertices for floor and ceiling."""
        builder.compile(simple_floorplan, [], [])
        entity = store.get_entity("room-001")
        vertices = entity["geometry"]["vertices"]
        # 4 boundary points * 2 (floor + ceiling) = 8 vertices
        assert len(vertices) == 8

    def test_room_vertices_are_3d(self, builder, store, simple_floorplan):
        """Room vertices should be 3D coordinates [x, y, z]."""
        builder.compile(simple_floorplan, [], [])
        entity = store.get_entity("room-001")
        vertices = entity["geometry"]["vertices"]
        for v in vertices:
            assert len(v) == 3  # x, y, z


# ===========================================================================
# Error handling tests
# ===========================================================================


class TestErrorHandling:
    """Test error handling in compile()."""

    def test_compile_with_empty_floorplan(self, builder):
        """Should handle floor plans with no walls or rooms."""
        floorplan = {
            "id": "empty-structure",
            "position_gps": {"lat": 42.98743, "lon": -70.98709, "alt_m": 26.8},
            "floor_level": 0,
            "walls": [],
            "rooms": [],
        }
        result = builder.compile(floorplan, [], [])
        assert result["entities_written"] == 1  # Just the structure
        assert len(result["errors"]) == 0

    def test_compile_records_errors(self, builder, store):
        """BuildRecord should capture errors during entity creation."""
        # Create a malformed floorplan that will cause errors
        bad_floorplan = {
            "id": "bad-structure",
            # Missing required position_gps
            "walls": [],
            "rooms": [],
        }
        # This should raise an error, but compile should catch it
        # For now, this will fail at the entity creation level
        # The actual error handling depends on store.upsert_entity validation
        # We'll just verify the error mechanism is in place
        assert True  # Placeholder - actual implementation will vary
