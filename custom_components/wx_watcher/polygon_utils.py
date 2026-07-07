"""Point-in-polygon utilities for NWS alert geometry filtering.

GeoJSON uses [lon, lat] coordinate ordering throughout.
All coordinates in NWS alerts follow this convention.

Provides:
- point_in_polygon: ray-casting test against a single polygon ring
- point_in_multi_polygon: test against a GeoJSON Polygon or MultiPolygon geometry
"""

from __future__ import annotations


def point_in_polygon(lat: float, lon: float, polygon: list[list[float]]) -> bool:
    """Test whether a point is inside a single polygon using the ray-casting algorithm.

    Boundary-inclusive: points on edges or vertices are considered inside.

    Args:
        lat: Latitude of the test point (degrees).
        lon: Longitude of the test point (degrees).
        polygon: A list of [lon, lat] coordinate pairs forming the polygon ring.
                 May be closed (first == last point) or open.

    Returns:
        True if the point is inside or on the boundary, False otherwise.

    """
    n = len(polygon)
    if n < 3:
        return False

    # Close the ring if not already closed
    if polygon[0] != polygon[-1]:
        polygon = [*polygon, polygon[0]]

    inside = False
    j = len(polygon) - 1  # index of the previous vertex

    for i in range(len(polygon)):
        xi, yi = polygon[i]  # (lon, lat)
        xj, yj = polygon[j]  # (lon, lat)

        # Ray-casting: count crossings of a ray from (lon, lat) going right
        if ((yi > lat) != (yj > lat)) and (lon < (xj - xi) * (lat - yi) / (yj - yi) + xi):
            inside = not inside

        j = i

    return inside


def point_in_multi_polygon(lat: float, lon: float, geometry: dict | None) -> bool | None:
    """Test whether a point falls inside a GeoJSON Polygon or MultiPolygon geometry.

    NWS geometry uses GeoJSON format:
    - Polygon: {"type": "Polygon", "coordinates": [[[lon, lat], ...]]}
    - MultiPolygon: {"type": "MultiPolygon", "coordinates": [[[[lon, lat], ...]], ...]}

    Args:
        lat: Latitude of the test point (degrees).
        lon: Longitude of the test point (degrees).
        geometry: GeoJSON geometry dict with "type" and "coordinates" keys.
                  May be None, empty, or have missing/invalid fields.

    Returns:
        True  — point is inside at least one polygon (boundary counts as inside).
        False — point is outside all polygons.
        None  — geometry is absent, empty, or not a Polygon/MultiPolygon type.

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

    if not coordinates:
        return None

    if geom_type == "Polygon":
        if not isinstance(coordinates, list) or len(coordinates) == 0:
            return None

        # First ring is outer boundary; remaining rings are holes
        outer_ring = coordinates[0]
        if not isinstance(outer_ring, list) or len(outer_ring) == 0:
            return None

        if not point_in_polygon(lat, lon, outer_ring):
            return False

        # Inside outer ring but check holes
        for hole in coordinates[1:]:
            if isinstance(hole, list) and point_in_polygon(lat, lon, hole):
                return False

        return True

    if geom_type == "MultiPolygon":
        if not isinstance(coordinates, list):
            return None

        for polygon_coords in coordinates:
            if not isinstance(polygon_coords, list) or len(polygon_coords) == 0:
                continue  # skip malformed entries

            outer_ring = polygon_coords[0]
            if not isinstance(outer_ring, list) or len(outer_ring) == 0:
                continue

            if not point_in_polygon(lat, lon, outer_ring):
                continue

            # Inside outer ring but check holes
            in_hole = False
            for hole in polygon_coords[1:]:
                if isinstance(hole, list) and point_in_polygon(lat, lon, hole):
                    in_hole = True
                    break

            if not in_hole:
                return True

        # If we got here, point wasn't inside any polygon
        # But we need to distinguish "we had valid polygons and the point was outside"
        # from "all entries were malformed"
        had_valid_polygon = False
        for polygon_coords in coordinates:
            if (
                isinstance(polygon_coords, list)
                and len(polygon_coords) > 0
                and isinstance(polygon_coords[0], list)
                and len(polygon_coords[0]) >= 3
            ):
                had_valid_polygon = True
                break

        return False if had_valid_polygon else None

    # Unknown geometry type
    return None
