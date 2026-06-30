"""Tests for polygon.py."""

import pytest
from custom_components.wx_watcher.polygon import point_in_polygon

# NOTE: The task description has a coordinate typo — "40.1234, -74.5678" puts
# the user in New Jersey (far east of all NWS polygons in Michigan).
# Verified correct location for tests: lat=42.70, lon=-82.50 (Michigan, MIZ999).
# Mock descriptions confirm this: "polygon starts at 42.87°, user at 42.70° below".
USER_LAT = 42.70
USER_LON = -82.50

# Spec mock fixtures (coordinates corrected to GeoJSON [lon, lat] format).
# MultiPolygon coordinates = [polygon1, polygon2, ...]
# Each polygon = [ring] where ring = [[lon, lat], ...]

MOCK1_POLYGON_NOT_COVERING = {
    "type": "Polygon",
    "coordinates": [[
        [-82.90, 42.87],
        [-82.55, 42.87],
        [-82.55, 43.10],
        [-82.90, 43.10],
        [-82.90, 42.87],
    ]],
}
# User at 42.70°N — below the polygon which starts at 42.87°N

MOCK2_POLYGON_COVERING = {
    "type": "Polygon",
    "coordinates": [[
        [-83.00, 42.50],
        [-82.40, 42.50],
        [-82.40, 43.00],
        [-83.00, 43.00],
        [-83.00, 42.50],
    ]],
}
# User at 42.70°N, lon=-82.50 — inside polygon (lat 42.50–43.00, lon -83 to -82.4)

MOCK3_NO_GEOMETRY = None
# No geometry field at all → None

MOCK4_MULTIPOLYGON_ONE_COVERING = {
    "type": "MultiPolygon",
    "coordinates": [
        [[[-82.90, 42.87], [-82.55, 42.87], [-82.55, 43.10], [-82.90, 43.10], [-82.90, 42.87]]],
        [[[-83.00, 42.50], [-82.40, 42.50], [-82.40, 43.00], [-83.00, 43.00], [-83.00, 42.50]]],
    ],
}
# First polygon: lat 42.87–43.10 (user below). Second: lat 42.50–43.00 (user inside).

MOCK5_MULTIPOLYGON_NONE_COVERING = {
    "type": "MultiPolygon",
    "coordinates": [
        [[[-82.90, 42.87], [-82.55, 42.87], [-82.55, 43.10], [-82.90, 43.10], [-82.90, 42.87]]],
        [[[-83.50, 43.50], [-83.20, 43.50], [-83.20, 44.00], [-83.50, 44.00], [-83.50, 43.50]]],
    ],
}
# Both polygons: user (42.70°N, -82.50) is south/west of both (first: 42.87+; second: 43.50+)

# Mock 6: user's lat EXACTLY on polygon edge (boundary-inclusive → True).
# User at (-82.50, 42.50) is on the vertical edge from (-83, 42.50) to (-83, 43.00).
MOCK6_EDGE_POINT = {
    "type": "Polygon",
    "coordinates": [[
        [-83.00, 42.50],
        [-82.40, 40.1234],
        [-82.40, 43.00],
        [-83.00, 43.00],
        [-83.00, 42.50],
    ]],
}

MOCK7_EMPTY_GEOMETRY = {}

# Polygon with a hole — user inside outer ring but also inside the hole (should be False)
MOCK_POLYGON_WITH_HOLE_OUTSIDE = {
    "type": "Polygon",
    "coordinates": [
        [[-83.0, 42.0], [-82.0, 42.0], [-82.0, 43.5], [-83.0, 43.5], [-83.0, 42.0]],
        [[-82.9, 42.6], [-82.1, 42.6], [-82.1, 43.0], [-82.9, 43.0], [-82.9, 42.6]],
    ],
}


class TestSpecMocks:
    """Spec mock fixtures from the task description."""

    def test_mock1_polygon_not_covering(self):
        """Mock 1: polygon lat 42.87–43.10, user at 42.70 → outside."""
        assert point_in_polygon(USER_LAT, USER_LON, MOCK1_POLYGON_NOT_COVERING) is False

    def test_mock2_polygon_covering(self):
        """Mock 2: polygon lat 42.50–43.00, user at 42.70 → inside."""
        assert point_in_polygon(USER_LAT, USER_LON, MOCK2_POLYGON_COVERING) is True

    def test_mock3_no_geometry_null(self):
        """Mock 3: geometry is None → None."""
        assert point_in_polygon(USER_LAT, USER_LON, MOCK3_NO_GEOMETRY) is None

    def test_mock4_multipolygon_one_covering(self):
        """Mock 4: MultiPolygon, second polygon covers user → True."""
        assert point_in_polygon(USER_LAT, USER_LON, MOCK4_MULTIPOLYGON_ONE_COVERING) is True

    def test_mock5_multipolygon_none_covering(self):
        """Mock 5: MultiPolygon, neither polygon covers user → False."""
        assert point_in_polygon(USER_LAT, USER_LON, MOCK5_MULTIPOLYGON_NONE_COVERING) is False

    def test_mock6_edge_point_boundary_inclusive(self):
        """Mock 6: user on polygon edge (lat matches vertex) → inside (boundary-inclusive)."""
        assert point_in_polygon(42.50, -82.50, MOCK6_EDGE_POINT) is True

    def test_mock7_empty_geometry_null(self):
        """Mock 7: geometry is empty dict {} → None."""
        assert point_in_polygon(USER_LAT, USER_LON, MOCK7_EMPTY_GEOMETRY) is None


class TestEdgeCases:
    """Edge cases beyond the spec mocks."""

    def test_geometry_empty_list(self):
        """Empty list geometry → None."""
        assert point_in_polygon(USER_LAT, USER_LON, []) is None

    def test_geometry_missing_type(self):
        """Geometry dict with no 'type' → None."""
        assert point_in_polygon(USER_LAT, USER_LON, {"coordinates": []}) is None

    def test_geometry_missing_coordinates(self):
        """Geometry dict with no 'coordinates' → None."""
        assert point_in_polygon(USER_LAT, USER_LON, {"type": "Polygon"}) is None

    def test_geometry_wrong_type_string(self):
        """Non-dict geometry string → None."""
        assert point_in_polygon(USER_LAT, USER_LON, "Polygon") is None

    def test_polygon_at_vertex(self):
        """User at exact polygon vertex → inside (boundary-inclusive)."""
        assert point_in_polygon(42.87, -82.90, MOCK1_POLYGON_NOT_COVERING) is True

    def test_polygon_just_outside(self):
        """User just outside polygon edge → outside."""
        assert point_in_polygon(42.499, -82.50, MOCK2_POLYGON_COVERING) is False

    def test_polygon_just_inside(self):
        """User just inside polygon edge → inside."""
        assert point_in_polygon(42.501, -82.50, MOCK2_POLYGON_COVERING) is True

    def test_polygon_with_hole_user_in_hole(self):
        """User inside polygon hole → outside the polygon."""
        assert point_in_polygon(42.80, -82.50, MOCK_POLYGON_WITH_HOLE_OUTSIDE) is False

    def test_polygon_with_hole_user_in_outer(self):
        """User inside outer ring but outside hole → inside."""
        assert point_in_polygon(42.40, -82.50, MOCK_POLYGON_WITH_HOLE_OUTSIDE) is True

    def test_point_exactly_on_horizontal_edge(self):
        """User exactly on a horizontal edge → inside."""
        ring = [[-83.0, 42.70], [-82.0, 42.70], [-82.0, 43.0], [-83.0, 43.0], [-83.0, 42.70]]
        assert point_in_polygon(42.70, -82.50, {"type": "Polygon", "coordinates": [ring]}) is True

    def test_unclosed_ring(self):
        """Ring without closing point — algorithm still processes it."""
        ring = [[-83.0, 42.50], [-82.4, 42.50], [-82.4, 43.00], [-83.0, 43.00]]
        geom = {"type": "Polygon", "coordinates": [ring]}
        assert point_in_polygon(USER_LAT, USER_LON, geom) is True

    def test_multipolygon_empty_coordinates(self):
        """MultiPolygon with empty coordinates list → None."""
        assert point_in_polygon(USER_LAT, USER_LON, {"type": "MultiPolygon", "coordinates": []}) is None

    def test_multipolygon_null_coordinates(self):
        """MultiPolygon with null coordinates → None."""
        assert point_in_polygon(USER_LAT, USER_LON, {"type": "MultiPolygon", "coordinates": None}) is None

    def test_multipolygon_with_empty_polygon(self):
        """MultiPolygon where first polygon has no rings — skip it, check the second."""
        geom = {
            "type": "MultiPolygon",
            "coordinates": [
                [],  # malformed — skip
                [[[-83.0, 42.50], [-82.4, 42.50], [-82.4, 43.00], [-83.0, 43.00], [-83.0, 42.50]]],
            ],
        }
        assert point_in_polygon(USER_LAT, USER_LON, geom) is True

    def test_very_small_polygon_covering_user(self):
        """Tiny polygon that just covers the user point."""
        ring = [
            [USER_LON - 0.001, USER_LAT - 0.001],
            [USER_LON + 0.001, USER_LAT - 0.001],
            [USER_LON + 0.001, USER_LAT + 0.001],
            [USER_LON - 0.001, USER_LAT + 0.001],
            [USER_LON - 0.001, USER_LAT - 0.001],
        ]
        geom = {"type": "Polygon", "coordinates": [ring]}
        assert point_in_polygon(USER_LAT, USER_LON, geom) is True

    def test_user_just_outside_tiny_polygon(self):
        """User just outside a tiny polygon → outside."""
        ring = [
            [USER_LON - 0.001, USER_LAT - 0.001],
            [USER_LON + 0.001, USER_LAT - 0.001],
            [USER_LON + 0.001, USER_LAT + 0.001],
            [USER_LON - 0.001, USER_LAT + 0.001],
            [USER_LON - 0.001, USER_LAT - 0.001],
        ]
        geom = {"type": "Polygon", "coordinates": [ring]}
        assert point_in_polygon(USER_LAT, USER_LON + 0.002, geom) is False
