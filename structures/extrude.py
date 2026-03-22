"""
Wall and room extrusion logic for converting 2D floor plans into 3D geometry.

All dimensions are in meters.
"""
from __future__ import annotations

from typing import Any


def extrude_wall(
    start_point: tuple[float, float],
    end_point: tuple[float, float],
    height_m: float,
    thickness_m: float = 0.15,
) -> dict[str, Any]:
    """
    Extrude a wall from 2D floor plan coordinates to 3D geometry.

    Parameters
    ----------
    start_point : tuple[float, float]
        (x, y) coordinates of wall start in meters
    end_point : tuple[float, float]
        (x, y) coordinates of wall end in meters
    height_m : float
        Wall height in meters
    thickness_m : float, optional
        Wall thickness in meters (default: 0.15m = 6 inches)

    Returns
    -------
    dict
        Wall geometry as vertices and faces suitable for StructureEntity
    """
    x1, y1 = start_point
    x2, y2 = end_point

    # Calculate wall direction vector
    dx = x2 - x1
    dy = y2 - y1
    length = (dx**2 + dy**2) ** 0.5

    if length == 0:
        raise ValueError("Wall start and end points cannot be identical")

    # Perpendicular vector for thickness (normalized)
    nx = -dy / length * thickness_m / 2
    ny = dx / length * thickness_m / 2

    # Define 8 vertices for the wall box (4 bottom, 4 top)
    vertices = [
        # Bottom face
        [x1 - nx, y1 - ny, 0.0],
        [x1 + nx, y1 + ny, 0.0],
        [x2 + nx, y2 + ny, 0.0],
        [x2 - nx, y2 - ny, 0.0],
        # Top face
        [x1 - nx, y1 - ny, height_m],
        [x1 + nx, y1 + ny, height_m],
        [x2 + nx, y2 + ny, height_m],
        [x2 - nx, y2 - ny, height_m],
    ]

    # Define faces (triangulated)
    faces = [
        # Bottom face (2 triangles)
        [0, 1, 2],
        [0, 2, 3],
        # Top face (2 triangles)
        [4, 6, 5],
        [4, 7, 6],
        # Side faces (2 triangles each)
        [0, 4, 5],
        [0, 5, 1],  # Front
        [1, 5, 6],
        [1, 6, 2],  # Right
        [2, 6, 7],
        [2, 7, 3],  # Back
        [3, 7, 4],
        [3, 4, 0],  # Left
    ]

    return {"vertices": vertices, "faces": faces}


def extrude_room(
    boundary_points: list[tuple[float, float]],
    floor_height_m: float,
    ceiling_height_m: float,
) -> dict[str, Any]:
    """
    Extrude a room from 2D floor plan boundary to 3D geometry.

    Parameters
    ----------
    boundary_points : list[tuple[float, float]]
        Ordered list of (x, y) coordinates defining the room boundary in meters
    floor_height_m : float
        Height of the floor in meters
    ceiling_height_m : float
        Height of the ceiling in meters

    Returns
    -------
    dict
        Room geometry as vertices and faces suitable for StructureEntity
    """
    if len(boundary_points) < 3:
        raise ValueError("Room boundary must have at least 3 points")

    n = len(boundary_points)
    vertices = []
    faces = []

    # Create vertices for floor and ceiling
    for x, y in boundary_points:
        vertices.append([x, y, floor_height_m])  # Floor vertices

    for x, y in boundary_points:
        vertices.append([x, y, ceiling_height_m])  # Ceiling vertices

    # Floor faces (fan triangulation from first vertex)
    for i in range(1, n - 1):
        faces.append([0, i, i + 1])

    # Ceiling faces (fan triangulation from first vertex, reversed winding)
    for i in range(1, n - 1):
        faces.append([n, n + i + 1, n + i])

    # Wall faces connecting floor to ceiling
    for i in range(n):
        next_i = (i + 1) % n
        # Two triangles per wall segment
        faces.append([i, i + n, next_i])
        faces.append([next_i, i + n, next_i + n])

    return {"vertices": vertices, "faces": faces}


def calculate_room_dimensions(boundary_points: list[tuple[float, float]]) -> dict[str, float]:
    """
    Calculate bounding box dimensions for a room.

    Parameters
    ----------
    boundary_points : list[tuple[float, float]]
        Ordered list of (x, y) coordinates defining the room boundary in meters

    Returns
    -------
    dict
        Dictionary with width_m, depth_m keys
    """
    if not boundary_points:
        return {"width_m": 0.0, "depth_m": 0.0}

    x_coords = [p[0] for p in boundary_points]
    y_coords = [p[1] for p in boundary_points]

    width_m = max(x_coords) - min(x_coords)
    depth_m = max(y_coords) - min(y_coords)

    return {"width_m": width_m, "depth_m": depth_m}


def calculate_wall_dimensions(
    start_point: tuple[float, float],
    end_point: tuple[float, float],
    height_m: float,
    thickness_m: float = 0.15,
) -> dict[str, float]:
    """
    Calculate dimensions for a wall.

    Parameters
    ----------
    start_point : tuple[float, float]
        (x, y) coordinates of wall start in meters
    end_point : tuple[float, float]
        (x, y) coordinates of wall end in meters
    height_m : float
        Wall height in meters
    thickness_m : float, optional
        Wall thickness in meters (default: 0.15m)

    Returns
    -------
    dict
        Dictionary with width_m (length), height_m, depth_m (thickness) keys
    """
    x1, y1 = start_point
    x2, y2 = end_point
    length = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5

    return {"width_m": length, "height_m": height_m, "depth_m": thickness_m}
