"""
StructureBuilder — compiles floor plans, laser measurements, and images
into StructureEntity records (structures, walls, rooms) following the
contract defined in contracts/domains_to_schema.yaml.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from structures.extrude import (
    calculate_room_dimensions,
    calculate_wall_dimensions,
    extrude_room,
    extrude_wall,
)


class StructureBuilder:
    """
    Compiles floor plans, laser measurements, and images into StructureEntity
    records written to SchemaStore via the domains_to_schema contract.

    Structures are hierarchical:
      - structure (building/house)
        -> walls (parent_id points to structure)
        -> rooms (parent_id points to structure)

    Openings (doors, windows) are stored on walls with position offsets.
    All dimensions in meters.
    floor_level: 0=ground, -1=basement, 1=second floor
    Provenance tracks which measurements contributed to each entity.
    """

    def __init__(self, store: Any) -> None:
        """
        Initialize StructureBuilder.

        Parameters
        ----------
        store : SchemaStore
            The schema store where entities will be written
        """
        self.store = store

    def compile(
        self,
        floorplan: dict[str, Any],
        measurements: list[dict[str, Any]],
        images: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Compile floor plan, measurements, and images into StructureEntity records.

        Parameters
        ----------
        floorplan : dict
            Floor plan data containing:
            - position_gps: {lat, lon, alt_m} for the structure
            - walls: list of wall definitions
            - rooms: list of room definitions
            - floor_level: integer (0=ground, -1=basement, 1=second)
            - material: optional string
        measurements : list[dict]
            List of Measurement objects from ingestion_to_schema contract
        images : list[dict]
            List of ImageRecord objects from ingestion_to_schema contract

        Returns
        -------
        dict
            BuildRecord containing:
            - domain: "structures"
            - timestamp: ISO 8601
            - source_inputs: list of input references
            - entities_written: count of new entities
            - entities_updated: count of updated entities
            - errors: list of any errors encountered
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        entities_written = 0
        entities_updated = 0
        errors = []

        # Build source_inputs list from measurements and images
        source_inputs = []
        for meas in measurements:
            source_inputs.append(
                {
                    "type": meas.get("measurement_type", "unknown"),
                    "id": meas.get("provenance", {}).get("source_id", ""),
                    "path": "",
                }
            )
        for img in images:
            source_inputs.append(
                {
                    "type": img.get("source_type", "image"),
                    "id": img.get("file_path", ""),
                    "path": img.get("file_path", ""),
                }
            )

        # Create provenance from measurements and images
        provenance = self._build_provenance(measurements, images, timestamp)

        # 1. Create the main structure entity
        structure_id = floorplan.get("id", str(uuid.uuid4()))
        position_gps = floorplan["position_gps"]

        structure_entity = {
            "id": structure_id,
            "type": "structure",
            "geometry": {"type": "Point", "coordinates": [position_gps["lon"], position_gps["lat"]]},
            "position_gps": position_gps,
            "provenance": provenance,
            "properties": {
                "parent_id": None,
                "floor_level": floorplan.get("floor_level", 0),
                "material": floorplan.get("material"),
                "dimensions": floorplan.get("dimensions", {}),
                "openings": [],
            },
        }

        try:
            result = self.store.upsert_entity(structure_entity)
            if result["status"] == "created":
                entities_written += 1
            else:
                entities_updated += 1
        except Exception as e:
            errors.append({"entity_id": structure_id, "message": str(e)})

        # 2. Create wall entities
        for wall_def in floorplan.get("walls", []):
            wall_id = wall_def.get("id", str(uuid.uuid4()))
            try:
                wall_entity = self._create_wall_entity(
                    wall_id, wall_def, structure_id, position_gps, provenance
                )
                result = self.store.upsert_entity(wall_entity)
                if result["status"] == "created":
                    entities_written += 1
                else:
                    entities_updated += 1
            except Exception as e:
                errors.append({"entity_id": wall_id, "message": str(e)})

        # 3. Create room entities
        for room_def in floorplan.get("rooms", []):
            room_id = room_def.get("id", str(uuid.uuid4()))
            try:
                room_entity = self._create_room_entity(
                    room_id, room_def, structure_id, position_gps, provenance
                )
                result = self.store.upsert_entity(room_entity)
                if result["status"] == "created":
                    entities_written += 1
                else:
                    entities_updated += 1
            except Exception as e:
                errors.append({"entity_id": room_id, "message": str(e)})

        # Build and log BuildRecord
        build_record = {
            "domain": "structures",
            "timestamp": timestamp,
            "source_inputs": source_inputs,
            "entities_written": entities_written,
            "entities_updated": entities_updated,
            "errors": errors,
        }

        self.store.log_build(build_record)
        return build_record

    def _build_provenance(
        self, measurements: list[dict], images: list[dict], timestamp: str
    ) -> dict[str, Any]:
        """Build provenance from measurements and images."""
        # Use the most recent measurement or image timestamp, or current time
        if measurements:
            source_type = "laser"
            source_id = measurements[0].get("provenance", {}).get("source_id", "structure_builder")
            accuracy_m = measurements[0].get("provenance", {}).get("accuracy_m", 0.01)
        elif images:
            source_type = "image"
            source_id = images[0].get("source_type", "structure_builder")
            accuracy_m = 0.1  # Lower accuracy for image-derived
        else:
            source_type = "manual"
            source_id = "structure_builder"
            accuracy_m = 0.05

        return {
            "source_type": source_type,
            "source_id": source_id,
            "timestamp": timestamp,
            "accuracy_m": accuracy_m,
        }

    def _create_wall_entity(
        self,
        wall_id: str,
        wall_def: dict,
        structure_id: str,
        base_gps: dict,
        provenance: dict,
    ) -> dict[str, Any]:
        """Create a wall entity from wall definition."""
        # Extract wall parameters
        start_point = wall_def["start_point"]  # (x, y) in local coordinates
        end_point = wall_def["end_point"]
        height_m = wall_def.get("height_m", 2.4)  # Default ceiling height
        thickness_m = wall_def.get("thickness_m", 0.15)

        # Extrude wall to 3D geometry
        geometry = extrude_wall(start_point, end_point, height_m, thickness_m)

        # Calculate dimensions
        dimensions = calculate_wall_dimensions(start_point, end_point, height_m, thickness_m)

        # Calculate wall center position (offset from base_gps)
        center_x = (start_point[0] + end_point[0]) / 2
        center_y = (start_point[1] + end_point[1]) / 2

        # Convert local offset to GPS (simplified - assumes small distances)
        # For a more accurate implementation, would need proper coordinate transformation
        lat_offset = center_y / 111320  # Rough conversion: 1 degree lat ≈ 111320 meters
        lon_offset = center_x / (111320 * abs(base_gps["lat"]) / 90 if base_gps["lat"] != 0 else 111320)

        wall_gps = {
            "lat": base_gps["lat"] + lat_offset,
            "lon": base_gps["lon"] + lon_offset,
            "alt_m": base_gps["alt_m"],
        }

        # Process openings (doors, windows)
        openings = []
        for opening in wall_def.get("openings", []):
            openings.append(
                {
                    "type": opening["type"],  # "door" or "window"
                    "position_offset": opening.get("position_offset", 0.0),
                    "width_m": opening.get("width_m", 0.9),
                    "height_m": opening.get("height_m", 2.0),
                }
            )

        return {
            "id": wall_id,
            "type": "wall",
            "geometry": geometry,
            "position_gps": wall_gps,
            "provenance": provenance,
            "properties": {
                "parent_id": structure_id,
                "floor_level": wall_def.get("floor_level", 0),
                "material": wall_def.get("material", "drywall"),
                "dimensions": dimensions,
                "openings": openings,
            },
        }

    def _create_room_entity(
        self,
        room_id: str,
        room_def: dict,
        structure_id: str,
        base_gps: dict,
        provenance: dict,
    ) -> dict[str, Any]:
        """Create a room entity from room definition."""
        # Extract room parameters
        boundary_points = room_def["boundary_points"]  # List of (x, y) in local coordinates
        floor_height_m = room_def.get("floor_height_m", 0.0)
        ceiling_height_m = room_def.get("ceiling_height_m", 2.4)

        # Extrude room to 3D geometry
        geometry = extrude_room(boundary_points, floor_height_m, ceiling_height_m)

        # Calculate dimensions
        dimensions = calculate_room_dimensions(boundary_points)
        dimensions["height_m"] = ceiling_height_m - floor_height_m

        # Calculate room center position
        if boundary_points:
            center_x = sum(p[0] for p in boundary_points) / len(boundary_points)
            center_y = sum(p[1] for p in boundary_points) / len(boundary_points)
        else:
            center_x = center_y = 0.0

        # Convert local offset to GPS (simplified)
        lat_offset = center_y / 111320
        lon_offset = center_x / (111320 * abs(base_gps["lat"]) / 90 if base_gps["lat"] != 0 else 111320)

        room_gps = {
            "lat": base_gps["lat"] + lat_offset,
            "lon": base_gps["lon"] + lon_offset,
            "alt_m": base_gps["alt_m"] + floor_height_m,
        }

        return {
            "id": room_id,
            "type": "room",
            "geometry": geometry,
            "position_gps": room_gps,
            "provenance": provenance,
            "properties": {
                "parent_id": structure_id,
                "floor_level": room_def.get("floor_level", 0),
                "material": room_def.get("material"),
                "dimensions": dimensions,
                "openings": [],  # Rooms don't have openings directly; walls do
            },
        }
