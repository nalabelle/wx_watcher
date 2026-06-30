"""Tests for polygon.py — ray-casting point-in-polygon algorithm."""

import pytest

from custom_components.wx_watcher.polygon import point_in_polygon

# Shared user location for all tests (from the mock spec):
#   lat=42.70, lon=-74.5678
#   (The task description says "40.1234, -74.5678" but mock descriptions
#   consistently reference 42.70° N as the test latitude — e.g. mock1
#   says user at 42.70° is outside the polygon starting at 42.87°,
#   and mock2 says user at 42.70° is inside the polygon 42.50–43.00°.)
USER_LAT = 42.70
USER_LON = -74.5678

# --- Mock fixtures (GeoJSON coordinates in NWS [lat, lon] order) ---

MOCK_NONE = None

MOCK_EMPTY = {}

MOCK_NOT_POLYGON = {"type": "Point", "coordinates": [[USER_LAT, USER_LON]]}

# mock1: Polygon lat 42.87–43.10° N, lon -82.90 to -82.55° W.
# User at 42.70° N is south of the polygon → False.
MOCK1 = {
    "type": "Polygon",
    "coordinates": [
        [
            [42.87, -82.90],
            [42.87, -82.55],
            [43.10, -82.55],
            [43.10, -82.90],
            [42.87, -82.90],  # closed
        ]
    ],
}

# mock2: Polygon lat 42.50–43.00° N → user at 42.70° N is inside → True.
MOCK2 = {
    "type": "Polygon",
    "coordinates": [
        [
            [42.50, -75.00],
            [42.50, -74.00],
            [43.00, -74.00],
            [43.00, -75.00],
            [42.50, -75.00],  # closed
        ]
    ],
}

# mock3: Polygon lat 41.00–42.00° N, lon -70.00 to -69.00° W.
# Both ranges are far outside user → False.
MOCK3 = {
    "type": "Polygon",
    "coordinates": [
        [
            [41.00, -70.00],
            [41.00, -69.00],
            [42.00, -69.00],
            [42.00, -70.00],
            [41.00, -70.00],  # closed
        ]
    ],
}

# mock4: MultiPolygon.
#   Ring 1: lat 42.50–43.00° N, lon -75.00 to -74.00° W  → COVERS user at 42.70°
#   Ring 2: lat 39.00–40.00° N, lon -82.00 to -81.00° W → outside
# One polygon covers user → True.
MOCK4 = {
    "type": "MultiPolygon",
    "coordinates": [
        [
            [
                [42.50, -75.00],
                [42.50, -74.00],
                [43.00, -74.00],
                [43.00, -75.00],
                [42.50, -75.00],
            ]
        ],
        [
            [
                [39.00, -82.00],
                [39.00, -81.00],
                [40.00, -81.00],
                [40.00, -82.00],
                [39.00, -82.00],
            ]
        ],
    ],
}

# mock5: MultiPolygon.
#   Ring 1: lat 43.50–44.50° N → outside user at 42.70°
#   Ring 2: lat 39.00–40.50° N → outside user at 42.70°
# Neither covers user → False.
MOCK5 = {
    "type": "MultiPolygon",
    "coordinates": [
        [
            [
                [43.50, -75.00],
                [43.50, -74.00],
                [44.50, -74.00],
                [44.50, -75.00],
                [43.50, -75.00],
            ]
        ],
        [
            [
                [39.00, -75.00],
                [39.00, -74.00],
                [40.50, -74.00],
                [40.50, -75.00],
                [39.00, -75.00],
            ]
        ],
    ],
}

# mock6: Polygon that tests boundary inclusivity.
# Polygon lat range 42.00–42.70° N, exactly on the top edge at 42.70°.
# USER_LAT=42.70 → point is on top edge → True (boundary-inclusive).
MOCK6 = {
    "type": "Polygon",
    "coordinates": [
        [
            [42.00, -75.00],
            [42.00, -74.00],
            [42.70, -74.00],
            [42.70, -75.00],
            [42.00, -75.00],  # closed
        ]
    ],
}


@pytest.mark.parametrize(
    ("geometry", "expected"),
    [
        (MOCK_NONE, None),
        (MOCK_EMPTY, None),
        (MOCK_NOT_POLYGON, None),
        (MOCK1, False),
        (MOCK2, True),
        (MOCK3, False),
        (MOCK4, True),
        (MOCK5, False),
        (MOCK6, True),
    ],
)
def test_point_in_polygon(geometry, expected):
    """Verify point_in_polygon returns the expected result for each mock."""
    result = point_in_polygon(USER_LAT, USER_LON, geometry)
    assert result == expected, f"Expected {expected}, got {result}"


def test_none_returns_none():
    """None geometry returns None."""
    assert point_in_polygon(USER_LAT, USER_LON, None) is None


def test_empty_dict_returns_none():
    """Empty dict geometry returns None."""
    assert point_in_polygon(USER_LAT, USER_LON, {}) is None


def test_missing_type_returns_none():
    """Geometry dict without 'type' key returns None."""
    assert point_in_polygon(USER_LAT, USER_LON, {"coordinates": []}) is None


def test_missing_coordinates_returns_none():
    """Geometry dict without 'coordinates' key returns None."""
    assert point_in_polygon(USER_LAT, USER_LON, {"type": "Polygon"}) is None


def test_point_exactly_at_centroid():
    """A point at the centroid of a polygon is inside."""
    # Polygon: 0.0 to 10.0 lat, 0.0 to 10.0 lon (rectangle)
    geom = {
        "type": "Polygon",
        "coordinates": [
            [
                [0.0, 0.0],
                [0.0, 10.0],
                [10.0, 10.0],
                [10.0, 0.0],
                [0.0, 0.0],
            ]
        ],
    }
    assert point_in_polygon(5.0, 5.0, geom) is True


def test_point_clearly_outside():
    """A point far from the polygon is correctly reported as outside."""
    geom = {
        "type": "Polygon",
        "coordinates": [
            [
                [0.0, 0.0],
                [0.0, 10.0],
                [10.0, 10.0],
                [10.0, 0.0],
                [0.0, 0.0],
            ]
        ],
    }
    assert point_in_polygon(50.0, 50.0, geom) is False


def test_polygon_with_hole_excludes_point():
    """A point inside the outer ring but inside a hole is reported as outside."""
    # Outer ring: 0–100 lat, 0–100 lon
    # Hole: 20–80 lat, 20–80 lon
    # Point at (50, 50) is inside outer but inside hole → outside
    geom = {
        "type": "Polygon",
        "coordinates": [
            [[0.0, 0.0], [0.0, 100.0], [100.0, 100.0], [100.0, 0.0], [0.0, 0.0]],
            [[20.0, 20.0], [20.0, 80.0], [80.0, 80.0], [80.0, 20.0], [20.0, 20.0]],
        ],
    }
    assert point_in_polygon(50.0, 50.0, geom) is False


def test_polygon_with_hole_point_outside_both():
    """A point outside both outer ring and hole is outside."""
    geom = {
        "type": "Polygon",
        "coordinates": [
            [[0.0, 0.0], [0.0, 100.0], [100.0, 100.0], [100.0, 0.0], [0.0, 0.0]],
            [[20.0, 20.0], [20.0, 80.0], [80.0, 80.0], [80.0, 20.0], [20.0, 20.0]],
        ],
    }
    assert point_in_polygon(150.0, 150.0, geom) is False


def test_polygon_with_hole_point_in_outer_not_hole():
    """A point inside outer ring but outside the hole is inside."""
    geom = {
        "type": "Polygon",
        "coordinates": [
            [[0.0, 0.0], [0.0, 100.0], [100.0, 100.0], [100.0, 0.0], [0.0, 0.0]],
            [[20.0, 20.0], [20.0, 80.0], [80.0, 80.0], [80.0, 20.0], [20.0, 20.0]],
        ],
    }
    # (10, 10) is inside outer ring, outside hole
    assert point_in_polygon(10.0, 10.0, geom) is True


def test_multipolygon_first_polygon_covers():
    """MultiPolygon: True when first polygon covers the point."""
    geom = {
        "type": "MultiPolygon",
        "coordinates": [
            [[[0.0, 0.0], [0.0, 10.0], [10.0, 10.0], [10.0, 0.0], [0.0, 0.0]]],
            [[[100.0, 100.0], [100.0, 110.0], [110.0, 110.0], [110.0, 100.0], [100.0, 100.0]]],
        ],
    }
    assert point_in_polygon(5.0, 5.0, geom) is True


def test_multipolygon_second_polygon_covers():
    """MultiPolygon: True when only second polygon covers the point."""
    geom = {
        "type": "MultiPolygon",
        "coordinates": [
            [[[100.0, 100.0], [100.0, 110.0], [110.0, 110.0], [110.0, 100.0], [100.0, 100.0]]],
            [[[0.0, 0.0], [0.0, 10.0], [10.0, 10.0], [10.0, 0.0], [0.0, 0.0]]],
        ],
    }
    assert point_in_polygon(5.0, 5.0, geom) is True


def test_boundary_exact_vertex():
    """Boundary-inclusive: point exactly on a vertex is inside."""
    # Polygon where USER_LAT, USER_LON falls exactly on a corner
    geom = {
        "type": "Polygon",
        "coordinates": [
            [
                [42.00, -75.00],
                [42.00, -74.00],
                [43.00, -74.00],
                [43.00, -75.00],
                [42.00, -75.00],
            ]
        ],
    }
    # Point at (43.00, -75.00) — top-left corner of polygon
    assert point_in_polygon(43.00, -75.00, geom) is True


def test_boundary_on_edge():
    """Boundary-inclusive: point on an edge (not vertex) is inside."""
    geom = {
        "type": "Polygon",
        "coordinates": [
            [
                [42.00, -75.00],
                [42.00, -74.00],
                [43.00, -74.00],
                [43.00, -75.00],
                [42.00, -75.00],
            ]
        ],
    }
    # Point on the bottom edge at lat=42.00, mid-lon
    assert point_in_polygon(42.00, -74.50, geom) is True


def test_near_boundary_not_inside():
    """Point just barely outside the polygon is correctly reported as outside."""
    geom = {
        "type": "Polygon",
        "coordinates": [
            [
                [42.00, -75.00],
                [42.00, -74.00],
                [43.00, -74.00],
                [43.00, -75.00],
                [42.00, -75.00],
            ]
        ],
    }
    # Just outside bottom edge
    assert point_in_polygon(41.999999, -74.50, geom) is False
