"""Point-in-polygon for NWS alert geometry filtering.

GeoJSON uses [lon, lat] coordinate ordering throughout.
All coordinates in NWS alerts follow this convention.
"""

from __future__ import annotations

import math
from typing import Any

_EPSILON = 1e-9


def _squared_distance_to_segment(
    px: float, py: float,
    ax: float, ay: float,
    bx: float, by: float,
) -> float:
    """Return squared distance from point P to segment AB."""
    abx, aby = bx - ax, by - ay
    length_sq = abx * abx + aby * aby
    if length_sq == 0.0:
        return (px - ax) * (px - ax) + (py - ay) * (py - ay)

    t = max(0.0, min(1.0, ((px - ax) * abx + (py - ay) * aby) / length_sq))
    proj_x = ax + t * abx
    proj_y = ay + t * aby
    return (px - proj_x) * (px - proj_x) + (py - proj_y) * (py - proj_y)


def _point_in_ring(lat: float, lon: float, ring: list[list[float]]) -> bool:
    """Ray-casting point-in-ring, boundary-inclusive.

    Returns True if (lat, lon) is inside the ring (inclusive of edges
    and vertices), False otherwise. Ring is a list of [lon, lat] points.
    The ring is assumed to be closed (first == last point), but the
    function handles it gracefully if not.
    """
    # Boundary pre-check: point on any edge or vertex → inside
    for i in range(len(ring) - 1):
        ax, ay = ring[i]
        bx, by = ring[i + 1]
        if _squared_distance_to_segment(lon, lat, ax, ay, bx, by) <= _EPSILON:
            return True

    # Ray-casting: count intersections of ray (lon, lat) → (+∞, lat)
    crossings = 0
    for i in range(len(ring) - 1):
        ax, ay = ring[i]
        bx, by = ring[i + 1]

        # Exclude horizontal edges
        if ay == by:
            continue

        # Does the horizontal ray cross this edge?
        if (ay <= lat < by) or (by <= lat < ay):
            x_intersect = ax + (bx - ax) * (lat - ay) / (by - ay)
            if x_intersect > lon:
                crossings += 1

    return crossings % 2 == 1


def _point_in_polygon(lat: float, lon: float, coordinates: Any) -> bool:
    """Test a point against a single GeoJSON Polygon.

    coordinates: the Polygon ``coordinates`` field (list of rings).
    First ring is outer boundary; remaining rings are holes.
    Returns True if inside outer boundary and outside all holes.
    """
    if not coordinates or not isinstance(coordinates, list) or len(coordinates) == 0:
        return False

    outer_ring = coordinates[0]
    if not _point_in_ring(lat, lon, outer_ring):
        return False

    # Outside a hole → inside polygon; inside a hole → outside
    for hole in coordinates[1:]:
        if _point_in_ring(lat, lon, hole):
            return False

    return True


def point_in_polygon(lat: float, lon: float, geometry: dict | None) -> bool | None:
    """Return True/False/None for whether a point falls inside alert geometry.

    Args:
        lat:  User latitude (degrees).
        lon:  User longitude (degrees).
        geometry: GeoJSON geometry dict with ``type`` and ``coordinates``.
                  May be None, empty dict, or missing fields.

    Returns:
        True   — point is inside the polygon (boundary counts as inside).
        False  — point is outside the polygon.
        None   — geometry is absent/empty/invalid; no filtering possible.
    """
    if geometry is None:
        return None

    if not isinstance(geometry, dict):
        return None

    if not geometry:
        return None

    geom_type = geometry.get("type")
    coordinates = geometry.get("coordinates")

    if geom_type is None or coordinates is None:
        return None

    if geom_type == "Polygon":
        return _point_in_polygon(lat, lon, coordinates)

    if geom_type == "MultiPolygon":
        if not coordinates or not isinstance(coordinates, list):
            return None
        for polygon in coordinates:
            if _point_in_polygon(lat, lon, polygon):
                return True
        return False

    # Unknown geometry type — treat as missing
    return None
