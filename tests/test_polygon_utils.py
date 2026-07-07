"""Tests for polygon_utils.py — point-in-polygon utility with unit tests.

All coordinates are synthetic test fixtures chosen solely to exercise
inside/outside/boundary behavior. They do not correspond to any real location.
"""

from custom_components.wx_watcher.polygon_utils import point_in_multi_polygon, point_in_polygon

# Synthetic test location: chosen to be inside some mock polygons and
# outside others, so the inside/outside/boundary logic is exercised.
# Not a real address or GPS coordinate.
TEST_LAT = 42.70
TEST_LON = -82.50

# --- point_in_polygon tests ---


class TestPointInPolygon:
    """Tests for the ray-casting point_in_polygon function."""

    # Simple square: lat 42.50–43.00, lon -83.00 to -82.40
    SQUARE_CLOSED = [
        [-83.00, 42.50],
        [-82.40, 42.50],
        [-82.40, 43.00],
        [-83.00, 43.00],
        [-83.00, 42.50],
    ]

    SQUARE_OPEN = [
        [-83.00, 42.50],
        [-82.40, 42.50],
        [-82.40, 43.00],
        [-83.00, 43.00],
    ]

    def test_point_inside_closed_polygon(self):
        """Point inside a closed polygon → True."""
        assert point_in_polygon(TEST_LAT, TEST_LON, self.SQUARE_CLOSED) is True

    def test_point_inside_open_polygon(self):
        """Point inside an open (unclosed) polygon → True."""
        assert point_in_polygon(TEST_LAT, TEST_LON, self.SQUARE_OPEN) is True

    def test_point_outside_closed_polygon(self):
        """Point outside a closed polygon → False."""
        assert point_in_polygon(42.10, -82.50, self.SQUARE_CLOSED) is False

    def test_point_outside_open_polygon(self):
        """Point outside an open (unclosed) polygon → False."""
        assert point_in_polygon(42.10, -82.50, self.SQUARE_OPEN) is False

    def test_point_on_vertex(self):
        """Point exactly on a vertex → True (boundary-inclusive)."""
        assert point_in_polygon(42.50, -83.00, self.SQUARE_CLOSED) is True

    def test_point_on_edge(self):
        """Point exactly on a horizontal edge → True (boundary-inclusive)."""
        assert point_in_polygon(42.50, -82.70, self.SQUARE_CLOSED) is True

    def test_point_on_vertical_edge(self):
        """Point exactly on a vertical edge → True (boundary-inclusive)."""
        assert point_in_polygon(42.70, -83.00, self.SQUARE_CLOSED) is True

    def test_point_just_inside(self):
        """Point just inside the boundary → True."""
        assert point_in_polygon(42.501, -82.50, self.SQUARE_CLOSED) is True

    def test_point_just_outside(self):
        """Point just outside the boundary → False."""
        assert point_in_polygon(42.499, -82.50, self.SQUARE_CLOSED) is False

    def test_degenerate_polygon_two_points(self):
        """Polygon with fewer than 3 points → False."""
        assert point_in_polygon(42.70, -82.50, [[-83.0, 42.50], [-82.0, 42.50]]) is False

    def test_degenerate_polygon_one_point(self):
        """Polygon with only 1 point → False."""
        assert point_in_polygon(42.70, -82.50, [[-83.0, 42.50]]) is False

    def test_degenerate_polygon_empty(self):
        """Empty polygon → False."""
        assert point_in_polygon(42.70, -82.50, []) is False

    def test_triangle_inside(self):
        """Point inside a triangle → True."""
        triangle = [[-83.0, 42.0], [-82.0, 42.0], [-82.5, 43.0], [-83.0, 42.0]]
        assert point_in_polygon(42.50, -82.50, triangle) is True

    def test_triangle_outside(self):
        """Point outside a triangle → False."""
        triangle = [[-83.0, 42.0], [-82.0, 42.0], [-82.5, 43.0], [-83.0, 42.0]]
        assert point_in_polygon(43.50, -82.50, triangle) is False


# --- point_in_multi_polygon tests ---


class TestPointInMultiPolygon:
    """Tests for the point_in_multi_polygon function."""

    # GeoJSON Polygon: square covering lat 42.50–43.00, lon -83.00 to -82.40
    POLYGON_COVERING = {
        "type": "Polygon",
        "coordinates": [
            [
                [-83.00, 42.50],
                [-82.40, 42.50],
                [-82.40, 43.00],
                [-83.00, 43.00],
                [-83.00, 42.50],
            ]
        ],
    }

    # GeoJSON Polygon: square NOT covering test point (lat 42.87–43.10)
    POLYGON_NOT_COVERING = {
        "type": "Polygon",
        "coordinates": [
            [
                [-82.90, 42.87],
                [-82.55, 42.87],
                [-82.55, 43.10],
                [-82.90, 43.10],
                [-82.90, 42.87],
            ]
        ],
    }

    # MultiPolygon: second polygon covers test point
    MULTIPOLYGON_ONE_COVERING = {
        "type": "MultiPolygon",
        "coordinates": [
            [[[-82.90, 42.87], [-82.55, 42.87], [-82.55, 43.10], [-82.90, 43.10], [-82.90, 42.87]]],
            [[[-83.00, 42.50], [-82.40, 42.50], [-82.40, 43.00], [-83.00, 43.00], [-83.00, 42.50]]],
        ],
    }

    # MultiPolygon: neither polygon covers test point
    MULTIPOLYGON_NONE_COVERING = {
        "type": "MultiPolygon",
        "coordinates": [
            [[[-82.90, 42.87], [-82.55, 42.87], [-82.55, 43.10], [-82.90, 43.10], [-82.90, 42.87]]],
            [[[-83.50, 43.50], [-83.20, 43.50], [-83.20, 44.00], [-83.50, 44.00], [-83.50, 43.50]]],
        ],
    }

    # Polygon with hole: outer ring covers test point, hole also covers test point
    POLYGON_WITH_HOLE_OUTSIDE = {
        "type": "Polygon",
        "coordinates": [
            [[-83.0, 42.0], [-82.0, 42.0], [-82.0, 43.5], [-83.0, 43.5], [-83.0, 42.0]],
            [[-82.9, 42.6], [-82.1, 42.6], [-82.1, 43.0], [-82.9, 43.0], [-82.9, 42.6]],
        ],
    }

    def test_point_inside_single_polygon(self):
        """Point inside a single polygon → True."""
        assert point_in_multi_polygon(TEST_LAT, TEST_LON, self.POLYGON_COVERING) is True

    def test_point_outside_single_polygon(self):
        """Point outside a single polygon → False."""
        assert point_in_multi_polygon(TEST_LAT, TEST_LON, self.POLYGON_NOT_COVERING) is False

    def test_point_inside_one_ring_of_multipolygon(self):
        """Point inside one ring of a MultiPolygon → True."""
        assert point_in_multi_polygon(TEST_LAT, TEST_LON, self.MULTIPOLYGON_ONE_COVERING) is True

    def test_point_outside_all_rings_of_multipolygon(self):
        """Point outside all rings of a MultiPolygon → False."""
        assert point_in_multi_polygon(TEST_LAT, TEST_LON, self.MULTIPOLYGON_NONE_COVERING) is False

    def test_none_geometry_returns_none(self):
        """None geometry → None."""
        assert point_in_multi_polygon(TEST_LAT, TEST_LON, None) is None

    def test_empty_dict_returns_none(self):
        """Empty dict geometry → None."""
        assert point_in_multi_polygon(TEST_LAT, TEST_LON, {}) is None

    def test_missing_type_returns_none(self):
        """Geometry dict with no 'type' → None."""
        assert point_in_multi_polygon(TEST_LAT, TEST_LON, {"coordinates": []}) is None

    def test_missing_coordinates_returns_none(self):
        """Geometry dict with no 'coordinates' → None."""
        assert point_in_multi_polygon(TEST_LAT, TEST_LON, {"type": "Polygon"}) is None

    def test_empty_coordinates_returns_none(self):
        """Polygon with empty coordinates → None."""
        assert (
            point_in_multi_polygon(TEST_LAT, TEST_LON, {"type": "Polygon", "coordinates": []})
            is None
        )

    def test_multipolygon_empty_coordinates_returns_none(self):
        """MultiPolygon with empty coordinates → None."""
        assert (
            point_in_multi_polygon(TEST_LAT, TEST_LON, {"type": "MultiPolygon", "coordinates": []})
            is None
        )

    def test_multipolygon_null_coordinates_returns_none(self):
        """MultiPolygon with null coordinates → None."""
        assert (
            point_in_multi_polygon(
                TEST_LAT, TEST_LON, {"type": "MultiPolygon", "coordinates": None}
            )
            is None
        )

    def test_non_dict_geometry_returns_none(self):
        """Non-dict geometry (string) → None."""
        assert point_in_multi_polygon(TEST_LAT, TEST_LON, "Polygon") is None  # type: ignore[arg-type]

    def test_unknown_geometry_type_returns_none(self):
        """Unknown geometry type → None."""
        assert (
            point_in_multi_polygon(
                TEST_LAT, TEST_LON, {"type": "LineString", "coordinates": [[1, 2]]}
            )
            is None
        )

    def test_polygon_with_hole_point_in_hole(self):
        """Point inside outer ring but also inside hole → False."""
        # Test point (42.80, -82.50) is inside the hole ring
        assert point_in_multi_polygon(42.80, -82.50, self.POLYGON_WITH_HOLE_OUTSIDE) is False

    def test_polygon_with_hole_point_outside_hole(self):
        """Point inside outer ring but outside hole → True."""
        # Test point (42.40, -82.50) is inside outer but outside hole
        assert point_in_multi_polygon(42.40, -82.50, self.POLYGON_WITH_HOLE_OUTSIDE) is True

    def test_multipolygon_with_empty_polygon_skip(self):
        """MultiPolygon with empty polygon entry — skip it, check the next."""
        geom = {
            "type": "MultiPolygon",
            "coordinates": [
                [],  # malformed — skip
                [[[-83.0, 42.50], [-82.4, 42.50], [-82.4, 43.00], [-83.0, 43.00], [-83.0, 42.50]]],
            ],
        }
        assert point_in_multi_polygon(TEST_LAT, TEST_LON, geom) is True

    def test_multipolygon_with_hole(self):
        """MultiPolygon with a polygon that has a hole — point in hole → False for that polygon, True for another."""
        geom = {
            "type": "MultiPolygon",
            "coordinates": [
                # First polygon: outer covers test point, hole also covers it
                [
                    [[-83.0, 42.0], [-82.0, 42.0], [-82.0, 43.5], [-83.0, 43.5], [-83.0, 42.0]],
                    [[-82.9, 42.6], [-82.1, 42.6], [-82.1, 43.0], [-82.9, 43.0], [-82.9, 42.6]],
                ],
                # Second polygon: covers test point with no hole
                [
                    [
                        [-83.0, 42.50],
                        [-82.4, 42.50],
                        [-82.4, 43.00],
                        [-83.0, 43.00],
                        [-83.0, 42.50],
                    ],
                ],
            ],
        }
        # Point at (42.80, -82.50): inside first polygon's hole, but inside second polygon
        assert point_in_multi_polygon(42.80, -82.50, geom) is True

    def test_edge_point_boundary_inclusive(self):
        """Point on polygon edge vertex → True (boundary-inclusive)."""
        geom = {
            "type": "Polygon",
            "coordinates": [
                [
                    [-83.00, 42.50],
                    [-82.40, 42.50],
                    [-82.40, 43.00],
                    [-83.00, 43.00],
                    [-83.00, 42.50],
                ]
            ],
        }
        # Point at (-83.00, 42.50) — lower-left corner
        assert point_in_multi_polygon(42.50, -83.00, geom) is True

    def test_very_small_polygon_covering_point(self):
        """Tiny polygon that just covers the test point → True."""
        ring = [
            [TEST_LON - 0.001, TEST_LAT - 0.001],
            [TEST_LON + 0.001, TEST_LAT - 0.001],
            [TEST_LON + 0.001, TEST_LAT + 0.001],
            [TEST_LON - 0.001, TEST_LAT + 0.001],
            [TEST_LON - 0.001, TEST_LAT - 0.001],
        ]
        geom = {"type": "Polygon", "coordinates": [ring]}
        assert point_in_multi_polygon(TEST_LAT, TEST_LON, geom) is True

    def test_very_small_polygon_not_covering_point(self):
        """Tiny polygon just offset from the test point → False."""
        ring = [
            [TEST_LON - 0.001, TEST_LAT - 0.001],
            [TEST_LON + 0.001, TEST_LAT - 0.001],
            [TEST_LON + 0.001, TEST_LAT + 0.001],
            [TEST_LON - 0.001, TEST_LAT + 0.001],
            [TEST_LON - 0.001, TEST_LAT - 0.001],
        ]
        geom = {"type": "Polygon", "coordinates": [ring]}
        assert point_in_multi_polygon(TEST_LAT, TEST_LON + 0.002, geom) is False
