"""
terrain/elevation.py — Elevation grid parsing and triangulation.

In HOMEMODEL_MODE=stub, parse_geotiff() returns a small fixture grid
without any file I/O or network calls.  In real mode it would open a
USGS NED GeoTIFF via rasterio (not installed in stub mode).
"""
from __future__ import annotations

import math
import os
from dataclasses import dataclass, field
from typing import List

# ---------------------------------------------------------------------------
# Data structure
# ---------------------------------------------------------------------------

@dataclass
class ElevationGrid:
    """Holds a 2-D elevation grid aligned to WGS84 GPS coordinates.

    Attributes
    ----------
    origin_lat, origin_lon, origin_alt_m:
        Scene origin (south-west corner of the grid).
    resolution_m:
        Ground sample distance in metres per cell.
    rows, cols:
        Grid dimensions.
    data:
        ``rows × cols`` 2-D list of elevation values in metres.
    """
    origin_lat: float
    origin_lon: float
    origin_alt_m: float
    resolution_m: float
    rows: int
    cols: int
    data: List[List[float]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Stub / fixture constants  (also exported for use by builder.py)
# ---------------------------------------------------------------------------

#: Scene origin — single source of truth for the whole terrain package.
SCENE_LAT   =  42.98743
SCENE_LON   = -70.98709
SCENE_ALT_M =  26.8

_STUB_ORIGIN_LAT   = SCENE_LAT
_STUB_ORIGIN_LON   = SCENE_LON
_STUB_ORIGIN_ALT_M = SCENE_ALT_M
_STUB_RESOLUTION_M =  1.0

# A 3×3 grid that gives a range of elevations representative of the site.
_STUB_DATA: List[List[float]] = [
    [26.5, 26.6, 26.8],
    [26.7, 26.9, 27.1],
    [27.0, 27.3, 27.6],
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_geotiff(path: str) -> ElevationGrid:
    """Parse a USGS NED GeoTIFF at *path* and return an ElevationGrid.

    In **stub mode** (``HOMEMODEL_MODE=stub``) the *path* argument is
    ignored and the built-in fixture grid is returned immediately.
    """
    if os.getenv("HOMEMODEL_MODE") == "stub":
        rows = len(_STUB_DATA)
        cols = len(_STUB_DATA[0]) if rows else 0
        return ElevationGrid(
            origin_lat=_STUB_ORIGIN_LAT,
            origin_lon=_STUB_ORIGIN_LON,
            origin_alt_m=_STUB_ORIGIN_ALT_M,
            resolution_m=_STUB_RESOLUTION_M,
            rows=rows,
            cols=cols,
            data=[row[:] for row in _STUB_DATA],
        )

    # --- Real mode: requires rasterio ---
    try:
        import rasterio  # type: ignore
    except ImportError as exc:
        raise ImportError(
            "rasterio is required for real GeoTIFF parsing; "
            "install it with 'pip install rasterio'"
        ) from exc

    with rasterio.open(path) as src:
        band = src.read(1)
        transform = src.transform
        rows, cols = band.shape
        # top-left corner in geographic coordinates
        origin_lon, origin_lat = transform * (0, rows)  # SW corner
        data = band.tolist()

    return ElevationGrid(
        origin_lat=float(origin_lat),
        origin_lon=float(origin_lon),
        origin_alt_m=float(data[-1][0]),
        resolution_m=float(abs(transform.a)),
        rows=rows,
        cols=cols,
        data=data,
    )


def triangulate(grid: ElevationGrid) -> tuple[list, list]:
    """Convert an ElevationGrid into a triangulated mesh.

    Vertices are expressed in a local Cartesian frame where:
    - x increases eastward  (metres from origin)
    - y increases northward (metres from origin)
    - z is elevation above the scene origin (metres)

    Returns
    -------
    vertices : list of [x, y, z]
    faces    : list of [i, j, k] index triplets (counter-clockwise)
    """
    r = grid.resolution_m
    vertices: list[list[float]] = []
    # Build a 2-D index array: idx[row][col] → vertex index
    idx: list[list[int]] = []

    for row in range(grid.rows):
        idx_row: list[int] = []
        for col in range(grid.cols):
            vi = len(vertices)
            x = col * r
            y = row * r
            z = float(grid.data[row][col])
            vertices.append([x, y, z])
            idx_row.append(vi)
        idx.append(idx_row)

    faces: list[list[int]] = []
    for row in range(grid.rows - 1):
        for col in range(grid.cols - 1):
            tl = idx[row][col]
            tr = idx[row][col + 1]
            bl = idx[row + 1][col]
            br = idx[row + 1][col + 1]
            # Two triangles per quad (counter-clockwise winding)
            faces.append([tl, bl, tr])
            faces.append([tr, bl, br])

    return vertices, faces


# ---------------------------------------------------------------------------
# Slope helper (shared with builder)
# ---------------------------------------------------------------------------

def _cross_product(a: list[float], b: list[float]) -> list[float]:
    return [
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    ]


def _vec_sub(p: list[float], q: list[float]) -> list[float]:
    return [p[i] - q[i] for i in range(3)]


def compute_slope_avg_deg(vertices: list, faces: list) -> float:
    """Return average slope angle (degrees) across all triangular faces."""
    if not faces:
        return 0.0

    total_deg = 0.0
    for face in faces:
        v0 = vertices[face[0]]
        v1 = vertices[face[1]]
        v2 = vertices[face[2]]
        ab = _vec_sub(v1, v0)
        ac = _vec_sub(v2, v0)
        normal = _cross_product(ab, ac)
        mag = math.sqrt(sum(c * c for c in normal))
        if mag < 1e-12:
            continue
        # angle between normal and vertical (0,0,1)
        cos_angle = normal[2] / mag
        cos_angle = max(-1.0, min(1.0, cos_angle))
        slope_rad = math.acos(cos_angle)
        total_deg += math.degrees(slope_rad)

    return round(total_deg / len(faces), 4)
