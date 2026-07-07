"""Integration tests for zone_point hybrid mode — polygon filtering in the alert pipeline.

Test location: lat=42.70, lon=-82.70, zone=MIZ999

The fixture contains 7 NWS alert features covering different geometry cases:
  Mock 1: Polygon NOT covering user (lat 42.87-43.10) → polygon_covers_location=False
  Mock 2: Polygon COVERING user (lat 42.50-43.00, user at 42.70 inside) → True
  Mock 3: null geometry → None
  Mock 4: MultiPolygon, one polygon covering user → True
  Mock 5: MultiPolygon, NO polygon covering user → False
  Mock 6: Polygon with user on edge → True (boundary-inclusive)
  Mock 7: Empty geometry object {} → None
"""

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.wx_watcher.const import (
    CONF_LOCATION_GPS,
    CONF_LOCATION_HA_ZONE,
    CONF_LOCATION_MODE,
    CONF_LOCATION_TYPE,
    CONF_LOCATION_ZONE,
    DOMAIN,
    EVENT_ALERT_CREATED,
    LOCATION_MODE_ZONE_POINT,
    LOCATION_TYPE_STATIC,
)
from homeassistant.core import CoreState
from tests.conftest import ZONE_URL, load_fixture
from tests.const import CONFIG_DATA, CONFIG_DATA_POINT_ONLY

pytestmark = pytest.mark.asyncio

# Test location: inside Mock 2 polygon, outside Mock 1 polygon
TEST_LAT = 42.70
TEST_LON = -82.70
TEST_GPS = f"{TEST_LAT},{TEST_LON}"
TEST_ZONE = "MIZ999"
TEST_ZONE_URL = f"https://api.weather.gov/alerts/active?zone={TEST_ZONE}"


def _make_zone_point_config(gps: str = TEST_GPS, zone: str = TEST_ZONE) -> dict:
    """Create a zone_point config with the given GPS and zone."""
    return {
        "name": "WX Watcher",
        "interval": 60,
        "timeout": 60,
        "locations": [
            {
                CONF_LOCATION_TYPE: LOCATION_TYPE_STATIC,
                CONF_LOCATION_MODE: LOCATION_MODE_ZONE_POINT,
                CONF_LOCATION_GPS: gps,
                CONF_LOCATION_ZONE: zone,
                CONF_LOCATION_HA_ZONE: "zone.home",
            },
        ],
    }


async def _setup_entry(hass, mock_aioclient, config_data, zone_url=TEST_ZONE_URL):
    """Set up a mock config entry and return it."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="WX Watcher",
        data=config_data,
        version=4,
    )
    entry.add_to_hass(hass)
    hass.set_state(CoreState.running)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


class TestZonePointPolygonFilter:
    """Tests for zone_point mode polygon filtering in the alert pipeline."""

    async def test_polygon_not_covering_user_returns_false(self, hass, mock_aioclient):
        """Alert with polygon NOT covering user location → polygon_covers_location=False.

        Mock 1: polygon lat 42.87-43.10, lon -82.90 to -82.55
        User at lat=42.70 → outside (below the southern boundary).
        """
        config = _make_zone_point_config()
        for _ in range(2):
            mock_aioclient.get(
                TEST_ZONE_URL,
                status=200,
                body=load_fixture("api_zone_point.json"),
            )

        events = []

        def listener(event):
            events.append(event)

        hass.bus.async_listen(EVENT_ALERT_CREATED, listener)
        entry = await _setup_entry(hass, mock_aioclient, config)

        alerts = hass.data[DOMAIN][entry.entry_id]["coordinator"].data["alerts"]
        # Mock 1: Northern Pinewood County, polygon NOT covering user
        northern_storms = [
            a
            for a in alerts
            if a.get("AreasAffected") == "Northern Pinewood County"
            and a.get("polygon_covers_location") is False
        ]
        assert len(northern_storms) >= 1, (
            "At least one Northern Pinewood alert should have polygon_covers_location=False"
        )

    async def test_polygon_covering_user_returns_true(self, hass, mock_aioclient):
        """Alert with polygon COVERING user location → polygon_covers_location=True.

        Mock 2: polygon lat 42.50-43.00, lon -83.00 to -82.40
        User at lat=42.70 → inside the polygon.
        """
        config = _make_zone_point_config()
        for _ in range(2):
            mock_aioclient.get(
                TEST_ZONE_URL,
                status=200,
                body=load_fixture("api_zone_point.json"),
            )

        events = []

        def listener(event):
            events.append(event)

        hass.bus.async_listen(EVENT_ALERT_CREATED, listener)
        entry = await _setup_entry(hass, mock_aioclient, config)

        alerts = hass.data[DOMAIN][entry.entry_id]["coordinator"].data["alerts"]
        # Mock 2: "Pinewood County" Severe Thunderstorm Warning with covering polygon
        covering = [
            a
            for a in alerts
            if a.get("AreasAffected") == "Pinewood County"
            and a.get("Event") == "Severe Thunderstorm Warning"
            and a.get("polygon_covers_location") is True
        ]
        assert len(covering) >= 1, (
            "At least one Pinewood County alert should have polygon_covers_location=True"
        )
        # Also verify in event data
        covering_events = [
            e
            for e in events
            if e.data.get("AreasAffected") == "Pinewood County"
            and e.data.get("polygon_covers_location") is True
        ]
        assert len(covering_events) >= 1

    async def test_no_polygon_geometry_returns_none(self, hass, mock_aioclient):
        """Alert WITHOUT polygon geometry → polygon_covers_location=None.

        Mock 3: geometry=null (Extreme Heat Watch)
        """
        config = _make_zone_point_config()
        for _ in range(2):
            mock_aioclient.get(
                TEST_ZONE_URL,
                status=200,
                body=load_fixture("api_zone_point.json"),
            )

        entry = await _setup_entry(hass, mock_aioclient, config)

        alerts = hass.data[DOMAIN][entry.entry_id]["coordinator"].data["alerts"]
        heat_watch = [a for a in alerts if a.get("Event") == "Extreme Heat Watch"]
        assert len(heat_watch) == 1
        assert heat_watch[0]["polygon_covers_location"] is None

    async def test_multipolygon_covering_user_returns_true(self, hass, mock_aioclient):
        """Alert with MultiPolygon where one polygon covers user → polygon_covers_location=True.

        Mock 4: MultiPolygon with second polygon covering user location.
        """
        config = _make_zone_point_config()
        for _ in range(2):
            mock_aioclient.get(
                TEST_ZONE_URL,
                status=200,
                body=load_fixture("api_zone_point.json"),
            )

        entry = await _setup_entry(hass, mock_aioclient, config)

        alerts = hass.data[DOMAIN][entry.entry_id]["coordinator"].data["alerts"]
        multi_cover = [
            a
            for a in alerts
            if "multi-polygon" in a.get("FormattedHeadline", "").lower()
            and a.get("polygon_covers_location") is True
        ]
        assert len(multi_cover) == 1

    async def test_multipolygon_not_covering_user_returns_false(self, hass, mock_aioclient):
        """Alert with MultiPolygon where NO polygon covers user → polygon_covers_location=False.

        Mock 5: MultiPolygon, user outside both polygons.
        """
        config = _make_zone_point_config()
        for _ in range(2):
            mock_aioclient.get(
                TEST_ZONE_URL,
                status=200,
                body=load_fixture("api_zone_point.json"),
            )

        entry = await _setup_entry(hass, mock_aioclient, config)

        alerts = hass.data[DOMAIN][entry.entry_id]["coordinator"].data["alerts"]
        multi_no_cover = [a for a in alerts if "no cover" in a.get("FormattedHeadline", "").lower()]
        assert len(multi_no_cover) == 1
        assert multi_no_cover[0]["polygon_covers_location"] is False

    async def test_empty_geometry_returns_none(self, hass, mock_aioclient):
        """Alert with empty geometry object → polygon_covers_location=None.

        Mock 7: geometry={} (Flood Advisory)
        """
        config = _make_zone_point_config()
        for _ in range(2):
            mock_aioclient.get(
                TEST_ZONE_URL,
                status=200,
                body=load_fixture("api_zone_point.json"),
            )

        entry = await _setup_entry(hass, mock_aioclient, config)

        alerts = hass.data[DOMAIN][entry.entry_id]["coordinator"].data["alerts"]
        flood_advisory = [a for a in alerts if a.get("Event") == "Flood Advisory"]
        assert len(flood_advisory) == 1
        assert flood_advisory[0]["polygon_covers_location"] is None

    async def test_zone_mode_does_not_add_polygon_covers_location(self, hass, mock_aioclient):
        """Zone mode should NOT add polygon_covers_location to alerts (backward compatibility)."""
        mock_aioclient.get(
            ZONE_URL,
            status=200,
            body=load_fixture("api.json"),
        )
        mock_aioclient.get(
            ZONE_URL,
            status=200,
            body=load_fixture("api.json"),
        )

        entry = await _setup_entry(hass, mock_aioclient, CONFIG_DATA)

        alerts = hass.data[DOMAIN][entry.entry_id]["coordinator"].data["alerts"]
        for alert in alerts:
            assert "polygon_covers_location" not in alert, (
                f"Zone mode alerts should not have polygon_covers_location, "
                f"but alert {alert['ID']} does"
            )

    async def test_point_mode_does_not_add_polygon_covers_location(self, hass, mock_aioclient):
        """Point mode should NOT add polygon_covers_location to alerts (backward compatibility)."""
        point_url = "https://api.weather.gov/alerts/active?point=33.25,-112.3"
        mock_aioclient.get(point_url, status=200, body=load_fixture("api.json"))
        mock_aioclient.get(point_url, status=200, body=load_fixture("api.json"))

        entry = await _setup_entry(hass, mock_aioclient, CONFIG_DATA_POINT_ONLY)

        alerts = hass.data[DOMAIN][entry.entry_id]["coordinator"].data["alerts"]
        for alert in alerts:
            assert "polygon_covers_location" not in alert, (
                f"Point mode alerts should not have polygon_covers_location, "
                f"but alert {alert['ID']} does"
            )

    async def test_sensor_attributes_include_polygon_covers_location(self, hass, mock_aioclient):
        """Sensor attributes should include polygon_covers_location for zone_point mode alerts."""
        config = _make_zone_point_config()
        for _ in range(2):
            mock_aioclient.get(
                TEST_ZONE_URL,
                status=200,
                body=load_fixture("api_zone_point.json"),
            )

        entry = await _setup_entry(hass, mock_aioclient, config)

        alerts = hass.data[DOMAIN][entry.entry_id]["coordinator"].data["alerts"]
        # Each alert in zone_point mode should have polygon_covers_location
        for alert in alerts:
            assert "polygon_covers_location" in alert, (
                f"Alert {alert['ID']} missing polygon_covers_location in zone_point mode"
            )

        # Verify specific expected values
        heat_watch = [a for a in alerts if a.get("Event") == "Extreme Heat Watch"]
        assert heat_watch[0]["polygon_covers_location"] is None

        flood = [a for a in alerts if a.get("Event") == "Flood Advisory"]
        assert flood[0]["polygon_covers_location"] is None

    async def test_internal_fields_not_leaked_in_events(self, hass, mock_aioclient):
        """Internal fields (_ugc, _geometry, _VTECKey) should not appear in event data."""
        config = _make_zone_point_config()
        for _ in range(2):
            mock_aioclient.get(
                TEST_ZONE_URL,
                status=200,
                body=load_fixture("api_zone_point.json"),
            )

        events = []

        def listener(event):
            events.append(event)

        hass.bus.async_listen(EVENT_ALERT_CREATED, listener)
        await _setup_entry(hass, mock_aioclient, config)

        for event in events:
            for key in event.data:
                assert not key.startswith("_"), f"Internal field '{key}' leaked into event data"

    async def test_zone_point_no_point_api_call(self, hass, mock_aioclient):
        """Zone_point mode should NOT make point API calls — only zone calls."""
        config = _make_zone_point_config()

        # Only set up the zone URL mock, NOT any point URL
        for _ in range(2):
            mock_aioclient.get(
                TEST_ZONE_URL,
                status=200,
                body=load_fixture("api_zone_point.json"),
            )

        # This should succeed without making point API calls
        entry = await _setup_entry(hass, mock_aioclient, config)

        alerts = hass.data[DOMAIN][entry.entry_id]["coordinator"].data["alerts"]
        assert len(alerts) > 0, "Zone_point mode should fetch alerts by zone"
