"""Test WX Watcher event firing with multi-location support."""

import json
import pathlib

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.wx_watcher.const import (
    DOMAIN,
    EVENT_ALERT_CLEARED,
    EVENT_ALERT_CREATED,
    EVENT_ALERT_STALE_DATA,
    EVENT_ALERT_UPDATED,
)
from tests.conftest import ZONE_URL
from tests.const import CONFIG_DATA, CONFIG_DATA_POINT_ONLY

pytestmark = pytest.mark.asyncio

HEAT_ALERT_ID = "7681487b-41c6-0308-1a00-3cade72982c1"
AQA_ALERT_ID = "cbc5f830-921d-10c7-b447-e9bc1b744965"

EXPECTED_ALERT_FIELDS = {
    "Event",
    "ID",
    "URL",
    "Headline",
    "Type",
    "NWSCode",
    "Status",
    "Severity",
    "Certainty",
    "Sent",
    "Onset",
    "Expires",
    "Ends",
    "AreasAffected",
    "Description",
    "Instruction",
    "Urgency",
    "Response",
    "SenderName",
    "Effective",
    "FormattedHeadline",
    "VTEC",
    "VTECAction",
    "Significance",
    "References",
    "config_entry_id",
    "sources",
}


async def _setup_entry(hass, mock_aioclient, config_data, entry_title="WX Watcher"):
    """Set up a mock config entry and return it."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title=entry_title,
        data=config_data,
        version=4,
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


class TestFirstPoll:
    """Tests for the first poll fetching alerts."""

    async def test_zone_mode_first_poll_fires_created_events(self, hass, mock_aioclient):
        """First poll in zone mode should fire created events for all alerts."""
        mock_aioclient.get(ZONE_URL, status=200, body=load_fixture("api.json"))
        mock_aioclient.get(ZONE_URL, status=200, body=load_fixture("api.json"))

        events = []

        def listener(event):
            events.append(event)

        hass.bus.async_listen(EVENT_ALERT_CREATED, listener)
        hass.bus.async_listen(EVENT_ALERT_UPDATED, listener)
        hass.bus.async_listen(EVENT_ALERT_CLEARED, listener)

        entry = await _setup_entry(hass, mock_aioclient, CONFIG_DATA)

        created = [e for e in events if e.event_type == EVENT_ALERT_CREATED]
        assert len(created) == 2
        assert {e.data["ID"] for e in created} == {HEAT_ALERT_ID, AQA_ALERT_ID}

        for e in created:
            assert "sources" in e.data
            assert isinstance(e.data["sources"], list)
            assert e.data["config_entry_id"] == entry.entry_id

    async def test_event_data_contains_all_fields(self, hass, mock_aioclient):
        """Event data should contain all expected fields."""
        mock_aioclient.get(ZONE_URL, status=200, body=load_fixture("api.json"))
        mock_aioclient.get(ZONE_URL, status=200, body=load_fixture("api.json"))

        events = []

        def listener(event):
            events.append(event)

        hass.bus.async_listen(EVENT_ALERT_CREATED, listener)

        await _setup_entry(hass, mock_aioclient, CONFIG_DATA)

        assert len(events) == 2
        for event in events:
            assert EXPECTED_ALERT_FIELDS.issubset(set(event.data.keys()))

    async def test_zone_fan_out_sources(self, hass, mock_aioclient):
        """Zone alerts should map to locations via geocode.UGC fan-out."""
        mock_aioclient.get(ZONE_URL, status=200, body=load_fixture("api.json"))
        mock_aioclient.get(ZONE_URL, status=200, body=load_fixture("api.json"))

        events = []

        def listener(event):
            events.append(event)

        hass.bus.async_listen(EVENT_ALERT_CREATED, listener)

        await _setup_entry(hass, mock_aioclient, CONFIG_DATA)

        heat_event = [e for e in events if e.data["ID"] == HEAT_ALERT_ID][0]
        sources = heat_event.data["sources"]
        ha_zones = {s["ha_zone"] for s in sources if "ha_zone" in s}
        assert "zone.home" in ha_zones


class TestSecondPollNoChanges:
    """Tests for second poll with no changes."""

    async def test_second_poll_no_events(self, hass, mock_aioclient):
        """Second poll with identical data should fire no events."""
        for _ in range(3):
            mock_aioclient.get(ZONE_URL, status=200, body=load_fixture("api.json"))

        events = []

        def listener(event):
            events.append(event)

        hass.bus.async_listen(EVENT_ALERT_CREATED, listener)
        hass.bus.async_listen(EVENT_ALERT_UPDATED, listener)
        hass.bus.async_listen(EVENT_ALERT_CLEARED, listener)

        entry = await _setup_entry(hass, mock_aioclient, CONFIG_DATA)

        events.clear()

        coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
        await coordinator.async_refresh()
        await hass.async_block_till_done()

        created = [e for e in events if e.event_type == EVENT_ALERT_CREATED]
        updated = [e for e in events if e.event_type == EVENT_ALERT_UPDATED]
        cleared = [e for e in events if e.event_type == EVENT_ALERT_CLEARED]

        assert len(created) == 0
        assert len(updated) == 0
        assert len(cleared) == 0


class TestAlertUpdated:
    """Tests for alert updates."""

    async def test_alert_updated_fires_event(self, hass, mock_aioclient):
        """Changed alert data should fire updated event."""
        api_data = json.loads(load_fixture("api.json"))
        api_data["features"][0]["properties"]["severity"] = "Extreme"

        for _ in range(2):
            mock_aioclient.get(ZONE_URL, status=200, body=load_fixture("api.json"))
        mock_aioclient.get(ZONE_URL, status=200, body=json.dumps(api_data))

        events = []

        def listener(event):
            events.append(event)

        hass.bus.async_listen(EVENT_ALERT_CREATED, listener)
        hass.bus.async_listen(EVENT_ALERT_UPDATED, listener)
        hass.bus.async_listen(EVENT_ALERT_CLEARED, listener)

        entry = await _setup_entry(hass, mock_aioclient, CONFIG_DATA)

        events.clear()

        coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
        await coordinator.async_refresh()
        await hass.async_block_till_done()

        created = [e for e in events if e.event_type == EVENT_ALERT_CREATED]
        updated = [e for e in events if e.event_type == EVENT_ALERT_UPDATED]
        cleared = [e for e in events if e.event_type == EVENT_ALERT_CLEARED]

        assert len(created) == 0
        assert len(updated) == 1
        assert len(cleared) == 0
        assert updated[0].data["ID"] == HEAT_ALERT_ID
        assert updated[0].data["Severity"] == "Extreme"


class TestAlertCleared:
    """Tests for alert clearance."""

    async def test_alert_cleared_fires_event(self, hass, mock_aioclient):
        """Removed alert should fire cleared event."""
        for _ in range(2):
            mock_aioclient.get(ZONE_URL, status=200, body=load_fixture("api.json"))
        mock_aioclient.get(ZONE_URL, status=200, body=load_fixture("api_one_alert.json"))

        events = []

        def listener(event):
            events.append(event)

        hass.bus.async_listen(EVENT_ALERT_CREATED, listener)
        hass.bus.async_listen(EVENT_ALERT_UPDATED, listener)
        hass.bus.async_listen(EVENT_ALERT_CLEARED, listener)

        entry = await _setup_entry(hass, mock_aioclient, CONFIG_DATA)
        events.clear()

        coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
        await coordinator.async_refresh()
        await hass.async_block_till_done()

        created = [e for e in events if e.event_type == EVENT_ALERT_CREATED]
        cleared = [e for e in events if e.event_type == EVENT_ALERT_CLEARED]

        assert len(created) == 0
        assert len(cleared) == 1
        assert cleared[0].data["ID"] == AQA_ALERT_ID


class TestApiFailure:
    """Tests for API failure handling."""

    async def test_api_failure_fires_stale_data(self, hass, mock_aioclient):
        """API failure should fire stale_data event, not alert events."""
        for _ in range(2):
            mock_aioclient.get(ZONE_URL, status=200, body=load_fixture("api.json"))
        mock_aioclient.get(ZONE_URL, status=503)

        events = []

        def listener(event):
            events.append(event)

        hass.bus.async_listen(EVENT_ALERT_CREATED, listener)
        hass.bus.async_listen(EVENT_ALERT_UPDATED, listener)
        hass.bus.async_listen(EVENT_ALERT_CLEARED, listener)
        hass.bus.async_listen(EVENT_ALERT_STALE_DATA, listener)

        entry = await _setup_entry(hass, mock_aioclient, CONFIG_DATA)
        assert len([e for e in events if e.event_type == EVENT_ALERT_CREATED]) == 2

        events.clear()

        coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
        await coordinator.async_refresh()
        await hass.async_block_till_done()

        stale_events = [e for e in events if e.event_type == EVENT_ALERT_STALE_DATA]
        alert_events = [
            e
            for e in events
            if e.event_type in (EVENT_ALERT_CREATED, EVENT_ALERT_UPDATED, EVENT_ALERT_CLEARED)
        ]

        assert len(stale_events) == 1
        assert len(alert_events) == 0
        assert stale_events[0].data["last_successful"] is not None


class TestPointMode:
    """Tests for point mode queries."""

    async def test_point_mode_first_poll(self, hass, mock_aioclient):
        """Point mode should query by GPS coordinates."""
        point_url = "https://api.weather.gov/alerts/active?point=33.25,-112.3"
        mock_aioclient.get(point_url, status=200, body=load_fixture("api.json"))
        mock_aioclient.get(point_url, status=200, body=load_fixture("api.json"))

        events = []

        def listener(event):
            events.append(event)

        hass.bus.async_listen(EVENT_ALERT_CREATED, listener)

        await _setup_entry(hass, mock_aioclient, CONFIG_DATA_POINT_ONLY)

        created = [e for e in events if e.event_type == EVENT_ALERT_CREATED]
        assert len(created) == 2
        for e in created:
            sources = e.data["sources"]
            assert any(s.get("ha_zone") == "zone.home" and s["mode"] == "point" for s in sources)


def load_fixture(filename):
    """Load a test fixture."""
    return pathlib.Path(__file__).parent.joinpath("fixtures", filename).read_text(encoding="utf8")
