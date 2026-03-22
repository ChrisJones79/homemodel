"""
Demonstration test showing generated StructureEntity matching the contract.

This test demonstrates that the StructureBuilder generates entities that
match the StructureEntity contract defined in contracts/domains_to_schema.yaml.
"""
from __future__ import annotations

import pytest

from structures.tests.conftest import (
    builder,
    complex_floorplan,
    image_records,
    laser_measurements,
    simple_floorplan,
    store,
)


def test_demonstrate_structure_entity_output(builder, store, complex_floorplan, laser_measurements):
    """
    Demonstration: Generate a complete StructureEntity with walls and openings
    matching the contract.
    """
    # Compile the floor plan
    build_record = builder.compile(complex_floorplan, laser_measurements, [])

    # Show the BuildRecord
    print("\n" + "=" * 70)
    print("BuildRecord:")
    print("=" * 70)
    print(f"Domain: {build_record['domain']}")
    print(f"Timestamp: {build_record['timestamp']}")
    print(f"Entities written: {build_record['entities_written']}")
    print(f"Entities updated: {build_record['entities_updated']}")
    print(f"Errors: {build_record['errors']}")
    print(f"Source inputs: {len(build_record['source_inputs'])} inputs")

    # Show the main structure entity
    structure = store.get_entity("structure-002")
    print("\n" + "=" * 70)
    print("Structure Entity:")
    print("=" * 70)
    print(f"ID: {structure['id']}")
    print(f"Type: {structure['type']}")
    print(f"Position GPS: {structure['position_gps']}")
    print(f"Floor level: {structure['properties']['floor_level']}")
    print(f"Material: {structure['properties']['material']}")
    print(f"Parent ID: {structure['properties']['parent_id']}")

    # Show a wall entity with openings
    wall_north = store.get_entity("wall-north")
    print("\n" + "=" * 70)
    print("Wall Entity (with openings):")
    print("=" * 70)
    print(f"ID: {wall_north['id']}")
    print(f"Type: {wall_north['type']}")
    print(f"Parent ID: {wall_north['properties']['parent_id']}")
    print(f"Position GPS: {wall_north['position_gps']}")
    print(f"Floor level: {wall_north['properties']['floor_level']}")
    print(f"Material: {wall_north['properties']['material']}")
    print(f"Dimensions: {wall_north['properties']['dimensions']}")
    print(f"Openings ({len(wall_north['properties']['openings'])}):")
    for opening in wall_north["properties"]["openings"]:
        print(f"  - Type: {opening['type']}, Width: {opening['width_m']}m, Height: {opening['height_m']}m")
    print(f"Geometry vertices: {len(wall_north['geometry']['vertices'])} vertices")
    print(f"Geometry faces: {len(wall_north['geometry']['faces'])} faces")

    # Show a room entity
    room_living = store.get_entity("room-living")
    print("\n" + "=" * 70)
    print("Room Entity:")
    print("=" * 70)
    print(f"ID: {room_living['id']}")
    print(f"Type: {room_living['type']}")
    print(f"Parent ID: {room_living['properties']['parent_id']}")
    print(f"Position GPS: {room_living['position_gps']}")
    print(f"Floor level: {room_living['properties']['floor_level']}")
    print(f"Dimensions: {room_living['properties']['dimensions']}")
    print(f"Geometry vertices: {len(room_living['geometry']['vertices'])} vertices")
    print(f"Geometry faces: {len(room_living['geometry']['faces'])} faces")

    # Verify contract compliance
    print("\n" + "=" * 70)
    print("Contract Validation:")
    print("=" * 70)

    # Verify structure entity matches contract
    assert structure["type"] == "structure"
    assert "geometry" in structure
    assert "position_gps" in structure
    assert "parent_id" in structure["properties"]
    assert "floor_level" in structure["properties"]
    assert structure["properties"]["parent_id"] is None
    print("✓ Structure entity matches StructureEntity contract")

    # Verify wall entity matches contract
    assert wall_north["type"] == "wall"
    assert "geometry" in wall_north
    assert "position_gps" in wall_north
    assert wall_north["properties"]["parent_id"] == "structure-002"
    assert "floor_level" in wall_north["properties"]
    assert "material" in wall_north["properties"]
    assert "dimensions" in wall_north["properties"]
    assert "openings" in wall_north["properties"]
    assert len(wall_north["properties"]["openings"]) == 2
    for opening in wall_north["properties"]["openings"]:
        assert opening["type"] in ["door", "window"]
        assert "position_offset" in opening
        assert "width_m" in opening
        assert "height_m" in opening
    print("✓ Wall entity matches StructureEntity contract with openings")

    # Verify room entity matches contract
    assert room_living["type"] == "room"
    assert "geometry" in room_living
    assert "position_gps" in room_living
    assert room_living["properties"]["parent_id"] == "structure-002"
    assert "floor_level" in room_living["properties"]
    assert "dimensions" in room_living["properties"]
    print("✓ Room entity matches StructureEntity contract")

    # Verify hierarchical relationship
    assert wall_north["properties"]["parent_id"] == structure["id"]
    assert room_living["properties"]["parent_id"] == structure["id"]
    print("✓ parent_id correctly links walls/rooms to structure")

    # Verify all dimensions are in meters
    assert wall_north["properties"]["dimensions"]["width_m"] == pytest.approx(10.0)
    assert wall_north["properties"]["dimensions"]["height_m"] == pytest.approx(2.7)
    assert room_living["properties"]["dimensions"]["width_m"] == pytest.approx(6.0)
    assert room_living["properties"]["dimensions"]["depth_m"] == pytest.approx(8.0)
    print("✓ All dimensions are in meters")

    # Verify floor_level values
    assert structure["properties"]["floor_level"] == 0  # ground
    assert wall_north["properties"]["floor_level"] == 0
    assert room_living["properties"]["floor_level"] == 0
    print("✓ floor_level: 0=ground (correct)")

    # Verify provenance tracking
    assert "provenance" in structure
    assert "source_type" in structure["provenance"]
    assert "source_id" in structure["provenance"]
    assert "timestamp" in structure["provenance"]
    assert "accuracy_m" in structure["provenance"]
    assert structure["provenance"]["source_type"] == "laser"  # From laser_measurements
    print("✓ Provenance tracks which measurements contributed to entities")

    print("\n" + "=" * 70)
    print("✓ All acceptance criteria met!")
    print("=" * 70)
