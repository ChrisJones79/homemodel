"""
terrain/builder.py — TerrainBuilder: generates TerrainPatch entities from
USGS NED elevation data and (optionally) aerial imagery.

Writes entities into SchemaStore via upsert_entity() and logs a
BuildRecord via log_build() after every generation run.
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Any

from terrain.elevation import (
    ElevationGrid,
    SCENE_LAT,
    compute_slope_avg_deg,
    parse_geotiff,
    triangulate,
)

# Approximate metres-per-degree at the scene latitude.
# 1° latitude  ≈ 111 320 m (uniform globally to <0.3 %).
# 1° longitude ≈ 111 320 m × cos(lat).  cos(42.98743°) computed at import time.
import math as _math
_M_PER_DEG_LAT = 111_320.0
_M_PER_DEG_LON = 111_320.0 * _math.cos(_math.radians(SCENE_LAT))


# ---------------------------------------------------------------------------
# TerrainBuilder
# ---------------------------------------------------------------------------

class TerrainBuilder:
    """Generates TerrainPatch entities from elevation data.

    Parameters
    ----------
    store:
        A SchemaStore instance that exposes ``upsert_entity()`` and
        ``log_build()``.
    """

    def __init__(self, store: Any) -> None:
        self._store = store

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def generate_patches(
        self,
        elevation_data: ElevationGrid | None = None,
        aerial_images: list | None = None,
    ) -> list[dict]:
        """Generate TerrainPatch entities from *elevation_data*.

        Parameters
        ----------
        elevation_data:
            An :class:`~terrain.elevation.ElevationGrid` instance.  When
            ``None`` (or when ``HOMEMODEL_MODE=stub``) the built-in fixture
            grid is used.
        aerial_images:
            Optional list of image records from the ingestion pipeline.
            Currently used only to populate ``texture_source`` metadata;
            the images themselves are not processed.

        Returns
        -------
        List of TerrainPatch entity dicts that were written to the store.
        """
        stub_mode = os.getenv("HOMEMODEL_MODE") == "stub"

        # ------------------------------------------------------------------
        # 1. Resolve elevation grid
        # ------------------------------------------------------------------
        if elevation_data is None:
            if stub_mode:
                grid = parse_geotiff("")   # stub ignores the path
            else:
                raise ValueError(
                    "elevation_data must be provided in non-stub mode"
                )
        else:
            grid = elevation_data

        # ------------------------------------------------------------------
        # 2. Triangulate
        # ------------------------------------------------------------------
        vertices, faces = triangulate(grid)

        # ------------------------------------------------------------------
        # 3. Compute derived metadata
        # ------------------------------------------------------------------
        slope_avg = compute_slope_avg_deg(vertices, faces)

        # Bounding box in GPS
        res = grid.resolution_m
        # SW corner = origin
        sw_lat = grid.origin_lat
        sw_lon = grid.origin_lon
        # NE corner: offset by grid extent
        height_m = (grid.rows - 1) * res
        width_m  = (grid.cols - 1) * res
        ne_lat = sw_lat + height_m / _M_PER_DEG_LAT
        ne_lon = sw_lon + width_m  / _M_PER_DEG_LON

        # Patch centre (position_gps)
        centre_lat = (sw_lat + ne_lat) / 2
        centre_lon = (sw_lon + ne_lon) / 2
        centre_alt = grid.origin_alt_m

        # Texture source from first aerial image (if any)
        texture_source: str | None = None
        if aerial_images:
            first = aerial_images[0]
            texture_source = first.get("id") or first.get("path")

        # ------------------------------------------------------------------
        # 4. Build TerrainPatch entity
        # ------------------------------------------------------------------
        now_iso = datetime.now(timezone.utc).isoformat()
        patch_id = str(uuid.uuid4())

        patch: dict[str, Any] = {
            "id": patch_id,
            "type": "terrain_patch",
            "geometry": {
                "vertices": vertices,
                "faces": faces,
            },
            "position_gps": {
                "lat": centre_lat,
                "lon": centre_lon,
                "alt_m": centre_alt,
            },
            "bounds_gps": {
                "sw": {"lat": sw_lat, "lon": sw_lon},
                "ne": {"lat": ne_lat, "lon": ne_lon},
            },
            "resolution_m": res,
            "provenance": {
                "source_type": "usgs_ned",
                "source_id": "terrain_builder",
                "timestamp": now_iso,
            },
            "properties": {
                "elevation_source": "usgs_ned",
                "texture_source": texture_source,
                "slope_avg_deg": slope_avg,
            },
        }

        # ------------------------------------------------------------------
        # 5. Persist entity
        # ------------------------------------------------------------------
        self._store.upsert_entity(patch)

        # ------------------------------------------------------------------
        # 6. Log BuildRecord
        # ------------------------------------------------------------------
        build_record: dict[str, Any] = {
            "domain": "terrain",
            "timestamp": now_iso,
            "source_inputs": [
                {
                    "type": "elevation_grid",
                    "id": "usgs_ned",
                    "path": "",
                }
            ],
            "entities_written": 1,
            "entities_updated": 0,
            "errors": [],
        }

        self._store.log_build(build_record)

        return [patch]
