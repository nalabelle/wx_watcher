"""Ray-casting point-in-polygon algorithm for NWS alert geometries."""

from __future__ import annotations

import math
from typing import Any

_EPSILON = 1e-9
_EPSILON_SQ = _EPSILON * _EPSILON


def point_in_polygon(
    lat: float, lon: float, geometry: dict[str, Any] | None
) -> bool | None:
    """Return True if (lat, lon) is inside the GeoJSON geometry, False if outside.

    - ``geometry`` may be None / absent / empty — returns None in that case.
    - Uses ray-casting with boundary-inclusive semantics
      (point-on-edge counts as "inside").
    - ``lat`` and ``lon`` are in degrees; coordinates inside ``geometry`` are
      assumed to follow the GeoJSON convention (GeoJSON = [lon, lat],
      but NWS API polygons are actually encoded [lat, lon] per the spec).
      We treat them as passed-in order so callers from NWS can supply
      ``geometry["coordinates"]`` directly without swapping.
    """
    if not geometry:
        return None

    geom_type = geometry.get("type")
    coordinates = geometry.get("coordinates")

    if geom_type == "Polygon" and coordinates:
        rings = coordinates if isinstance(coordinates[0][0], list) else [coordinates]
        return _polygon_contains(lat, lon, rings)

    if geom_type == "MultiPolygon" and coordinates:
        for polygon in coordinates:
            rings = polygon if isinstance(polygon[0][0], list) else [polygon]
            if _polygon_contains(lat, lon, rings):
                return True
        return False

    return None


def _polygon_contains(lat: float, lon: float, rings: list) -> bool:
    """Check whether a point is inside a polygon defined by one or more rings.

    The first ring is the outer boundary; subsequent rings are holes.
    The point must be inside the outer ring and outside every hole ring.
    Each ring must be closed (first point == last point).
    Coordinates are expected as [[lat, lon], ...] (NWS convention).

    Returns True if inside, False if outside.
    Boundary-inclusive: points exactly on an edge or vertex are considered
    inside.
    """
    outer_ring = rings[0]
    n = len(outer_ring)
    if n >= 3:
        # Boundary-inclusive pre-check: test every edge of the outer ring
        for i in range(n - 1):
            if _point_on_segment(
                lat, lon,
                outer_ring[i][0], outer_ring[i][1],
                outer_ring[i + 1][0], outer_ring[i + 1][1],
            ):
                return True

    outer_ok = _ray_casting(lat, lon, outer_ring)
    if not outer_ok:
        return False
    for hole in rings[1:]:
        if _ray_casting(lat, lon, hole):
            return False
    return True


def _ray_casting(lat: float, lon: float, ring: list) -> bool:
    """Ray-casting algorithm: True if (lat, lon) is inside the closed ring.

    Casts a semi-infinite horizontal ray to the right and counts edge
    intersections. Odd count = inside, even count = outside.
    Closed rings only (first point == last point).
    Coordinates: [[lat, lon], ...] per NWS convention.
    """
    n = len(ring)
    if n < 3:
        return False

    inside = False
    i = 0
    j = n - 1

    while i < n:
        yi = ring[i][0]  # latitude
        yj = ring[j][0]  # latitude

        # Skip horizontal edges
        if yi != yj:
            xi = ring[i][1]  # longitude
            xj = ring[j][1]  # longitude

            # Check if the horizontal ray from (lon, INF) to (lon, lat) crosses
            # this edge.  lat is between yi and yj (excluding top vertex).
            cross_below = (yi > lat) != (yj > lat)
            if cross_below:
                # Intersection x-coordinate
                x_intersect = xi + (xj - xi) * (lat - yi) / (yj - yi)
                if lon < x_intersect:
                    inside = not inside

        j = i
        i += 1

    return inside


def _point_on_segment(
    px: float, py: float,
    x1: float, y1: float,
    x2: float, y2: float,
) -> bool:
    """Return True if point (px, py) lies exactly on segment (x1,y1)-(x2,y2).

    Uses squared distance to avoid sqrt.  Coordinates in the same unit
    system (degrees in our use case); epsilon accounts for floating-point
    imprecision.
    """
    # Parametric check: 0 <= t <= 1
    dx = x2 - x1
    dy = y2 - y1
    if dx == 0 and dy == 0:
        return (px - x1) * (px - x1) + (py - y1) * (py - y1) <= _EPSILON_SQ
    t_num = (px - x1) * dx + (py - y1) * dy
    t_den = dx * dx + dy * dy
    if t_den == 0:
        return (px - x1) * (px - x1) + (py - y1) * (py - y1) <= _EPSILON_SQ
    t = t_num / t_den
    if t < 0 or t > 1:
        return False
    proj_x = x1 + t * dx
    proj_y = y1 + t * dy
    dist_sq = (px - proj_x) * (px - proj_x) + (py - proj_y) * (py - proj_y)
    return dist_sq <= _EPSILON_SQ
