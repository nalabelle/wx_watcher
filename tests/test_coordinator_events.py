"""Test NWS Alerts event firing."""

import json

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.nws_alerts.const import DOMAIN
from custom_components.nws_alerts.events import (
    EVENT_ALERT_CLEARED,
    EVENT_ALERT_CREATED,
    EVENT_ALERT_STALE_DATA,
    EVENT_ALERT_UPDATED,
)
from tests.conftest import ZONE_URL, load_fixture

pytestmark = pytest.mark.asyncio

HEAT_ALERT_ID = "7681487b-41c6-0308-1a00-3cade72982c1"
AQA_ALERT_ID = "cbc5f830-921d-10c7-b447-e9bc1b744965"

EXPECTED_FIELD_COUNT = 26


async def _setup_entry(hass, mock_aioclient):
    """Set up a mock config entry and return it."""
    # Register 2 copies for the 2 setup fetches
    mock_aioclient.get(ZONE_URL, status=200, body=load_fixture("api.json"))
    mock_aioclient.get(ZONE_URL, status=200, body=load_fixture("api.json"))
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="NWS Alerts",
        data={"name": "NWS Alerts", "zone_id": "AZZ540,AZC013"},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


class TestFirstPoll:
    """Tests for the first poll fetching alerts."""

    async def test_first_poll_fires_created_events(self, hass, mock_aioclient):
        """First poll should fire created events for all alerts."""
        # Register 2 copies for setup, plus we don't need more
        mock_aioclient.get(ZONE_URL, status=200, body=load_fixture("api.json"))
        mock_aioclient.get(ZONE_URL, status=200, body=load_fixture("api.json"))

        events = []

        def listener(event):
            events.append(event)

        hass.bus.async_listen(EVENT_ALERT_CREATED, listener)
        hass.bus.async_listen(EVENT_ALERT_UPDATED, listener)
        hass.bus.async_listen(EVENT_ALERT_CLEARED, listener)
        hass.bus.async_listen(EVENT_ALERT_STALE_DATA, listener)

        entry = MockConfigEntry(
            domain=DOMAIN,
            title="NWS Alerts",
            data={"name": "NWS Alerts", "zone_id": "AZZ540,AZC013"},
        )
        entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        created = [e for e in events if e.event_type == EVENT_ALERT_CREATED]
        updated = [e for e in events if e.event_type == EVENT_ALERT_UPDATED]
        cleared = [e for e in events if e.event_type == EVENT_ALERT_CLEARED]
        stale = [e for e in events if e.event_type == EVENT_ALERT_STALE_DATA]

        assert len(created) == 2
        assert len(updated) == 0
        assert len(cleared) == 0
        assert len(stale) == 0
        assert {e.data["ID"] for e in created} == {HEAT_ALERT_ID, AQA_ALERT_ID}


class TestSecondPollNoChanges:
    """Tests for second poll with no changes."""

    async def test_second_poll_no_events(self, hass, mock_aioclient):
        """Second poll with identical data should fire no events."""
        # 2 for setup + 1 for explicit refresh
        mock_aioclient.get(ZONE_URL, status=200, body=load_fixture("api.json"))
        mock_aioclient.get(ZONE_URL, status=200, body=load_fixture("api.json"))
        mock_aioclient.get(ZONE_URL, status=200, body=load_fixture("api.json"))

        events = []

        def listener(event):
            events.append(event)

        hass.bus.async_listen(EVENT_ALERT_CREATED, listener)
        hass.bus.async_listen(EVENT_ALERT_UPDATED, listener)
        hass.bus.async_listen(EVENT_ALERT_CLEARED, listener)

        entry = MockConfigEntry(
            domain=DOMAIN,
            title="NWS Alerts",
            data={"name": "NWS Alerts", "zone_id": "AZZ540,AZC013"},
        )
        entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

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

        # 2 for setup + 1 for explicit refresh (with modified data)
        mock_aioclient.get(ZONE_URL, status=200, body=load_fixture("api.json"))
        mock_aioclient.get(ZONE_URL, status=200, body=load_fixture("api.json"))
        mock_aioclient.get(ZONE_URL, status=200, body=json.dumps(api_data))

        events = []

        def listener(event):
            events.append(event)

        hass.bus.async_listen(EVENT_ALERT_CREATED, listener)
        hass.bus.async_listen(EVENT_ALERT_UPDATED, listener)
        hass.bus.async_listen(EVENT_ALERT_CLEARED, listener)

        entry = MockConfigEntry(
            domain=DOMAIN,
            title="NWS Alerts",
            data={"name": "NWS Alerts", "zone_id": "AZZ540,AZC013"},
        )
        entry.add_to_hass(hass)

        # First poll - original data (2 fetches during setup)
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        events.clear()

        # Second poll - updated data
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
        # 2 for setup (2 alerts) + 1 for explicit refresh (1 alert)
        mock_aioclient.get(ZONE_URL, status=200, body=load_fixture("api.json"))
        mock_aioclient.get(ZONE_URL, status=200, body=load_fixture("api.json"))
        mock_aioclient.get(ZONE_URL, status=200, body=load_fixture("api_one_alert.json"))

        events = []

        def listener(event):
            events.append(event)

        hass.bus.async_listen(EVENT_ALERT_CREATED, listener)
        hass.bus.async_listen(EVENT_ALERT_UPDATED, listener)
        hass.bus.async_listen(EVENT_ALERT_CLEARED, listener)

        entry = MockConfigEntry(
            domain=DOMAIN,
            title="NWS Alerts",
            data={"name": "NWS Alerts", "zone_id": "AZZ540,AZC013"},
        )
        entry.add_to_hass(hass)

        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        events.clear()

        coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
        await coordinator.async_refresh()
        await hass.async_block_till_done()

        created = [e for e in events if e.event_type == EVENT_ALERT_CREATED]
        updated = [e for e in events if e.event_type == EVENT_ALERT_UPDATED]
        cleared = [e for e in events if e.event_type == EVENT_ALERT_CLEARED]

        assert len(created) == 0
        assert len(updated) == 0
        assert len(cleared) == 1
        assert cleared[0].data["ID"] == AQA_ALERT_ID
        assert cleared[0].data["Event"] == "Air Quality Alert"


class TestCreatedAfterCleared:
    """Tests for alert re-created after being cleared."""

    async def test_alert_created_after_clear(self, hass, mock_aioclient):
        """Alert that disappears then reappears should fire created event."""
        # 2 for setup (2 alerts) + 1 for refresh (1 alert) + 1 for refresh (2 alerts)
        mock_aioclient.get(ZONE_URL, status=200, body=load_fixture("api.json"))
        mock_aioclient.get(ZONE_URL, status=200, body=load_fixture("api.json"))
        mock_aioclient.get(ZONE_URL, status=200, body=load_fixture("api_one_alert.json"))
        mock_aioclient.get(ZONE_URL, status=200, body=load_fixture("api.json"))

        events = []

        def listener(event):
            events.append(event)

        hass.bus.async_listen(EVENT_ALERT_CREATED, listener)
        hass.bus.async_listen(EVENT_ALERT_UPDATED, listener)
        hass.bus.async_listen(EVENT_ALERT_CLEARED, listener)

        entry = MockConfigEntry(
            domain=DOMAIN,
            title="NWS Alerts",
            data={"name": "NWS Alerts", "zone_id": "AZZ540,AZC013"},
        )
        entry.add_to_hass(hass)

        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        events.clear()

        # Second poll: one alert removed
        coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
        await coordinator.async_refresh()
        await hass.async_block_till_done()

        cleared = [e for e in events if e.event_type == EVENT_ALERT_CLEARED]
        assert len(cleared) == 1
        assert cleared[0].data["ID"] == AQA_ALERT_ID

        events.clear()

        # Third poll: both alerts back
        await coordinator.async_refresh()
        await hass.async_block_till_done()

        created = [e for e in events if e.event_type == EVENT_ALERT_CREATED]
        assert len(created) == 1
        assert created[0].data["ID"] == AQA_ALERT_ID


class TestApiFailure:
    """Tests for API failure handling."""

    async def test_api_failure_fires_stale_data(self, hass, mock_aioclient):
        """API failure should fire stale_data event, not alert events."""
        # 2 for setup (success) + 1 for explicit refresh (503)
        mock_aioclient.get(ZONE_URL, status=200, body=load_fixture("api.json"))
        mock_aioclient.get(ZONE_URL, status=200, body=load_fixture("api.json"))
        mock_aioclient.get(ZONE_URL, status=503)

        events = []

        def listener(event):
            events.append(event)

        hass.bus.async_listen(EVENT_ALERT_CREATED, listener)
        hass.bus.async_listen(EVENT_ALERT_UPDATED, listener)
        hass.bus.async_listen(EVENT_ALERT_CLEARED, listener)
        hass.bus.async_listen(EVENT_ALERT_STALE_DATA, listener)

        entry = MockConfigEntry(
            domain=DOMAIN,
            title="NWS Alerts",
            data={"name": "NWS Alerts", "zone_id": "AZZ540,AZC013"},
        )
        entry.add_to_hass(hass)

        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        assert len([e for e in events if e.event_type == EVENT_ALERT_CREATED]) == 2

        events.clear()

        # Explicit refresh fails
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

    async def test_api_failure_preserves_previous_alerts(self, hass, mock_aioclient):
        """API failure should not clear previous_alerts."""
        # 2 for setup (success) + 1 for explicit refresh (503)
        mock_aioclient.get(ZONE_URL, status=200, body=load_fixture("api.json"))
        mock_aioclient.get(ZONE_URL, status=200, body=load_fixture("api.json"))
        mock_aioclient.get(ZONE_URL, status=503)

        entry = MockConfigEntry(
            domain=DOMAIN,
            title="NWS Alerts",
            data={"name": "NWS Alerts", "zone_id": "AZZ540,AZC013"},
        )
        entry.add_to_hass(hass)
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
        assert len(coordinator.previous_alerts) == 2

        await coordinator.async_refresh()
        await hass.async_block_till_done()

        # previous_alerts should still have both alerts after failure
        assert len(coordinator.previous_alerts) == 2

    async def test_api_failure_then_recovery(self, hass, mock_aioclient):
        """After API failure, recovery should fire correct events."""
        # 2 for setup (success) + 1 for refresh (503) + 1 for refresh (1 alert)
        mock_aioclient.get(ZONE_URL, status=200, body=load_fixture("api.json"))
        mock_aioclient.get(ZONE_URL, status=200, body=load_fixture("api.json"))
        mock_aioclient.get(ZONE_URL, status=503)
        mock_aioclient.get(ZONE_URL, status=200, body=load_fixture("api_one_alert.json"))

        events = []

        def listener(event):
            events.append(event)

        hass.bus.async_listen(EVENT_ALERT_CREATED, listener)
        hass.bus.async_listen(EVENT_ALERT_UPDATED, listener)
        hass.bus.async_listen(EVENT_ALERT_CLEARED, listener)
        hass.bus.async_listen(EVENT_ALERT_STALE_DATA, listener)

        entry = MockConfigEntry(
            domain=DOMAIN,
            title="NWS Alerts",
            data={"name": "NWS Alerts", "zone_id": "AZZ540,AZC013"},
        )
        entry.add_to_hass(hass)

        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        events.clear()

        coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

        # Poll fails
        await coordinator.async_refresh()
        await hass.async_block_till_done()

        stale_events = [e for e in events if e.event_type == EVENT_ALERT_STALE_DATA]
        assert len(stale_events) == 1

        events.clear()

        # Poll recovers with one alert (two were present before)
        await coordinator.async_refresh()
        await hass.async_block_till_done()

        created = [e for e in events if e.event_type == EVENT_ALERT_CREATED]
        cleared = [e for e in events if e.event_type == EVENT_ALERT_CLEARED]
        stale_events = [e for e in events if e.event_type == EVENT_ALERT_STALE_DATA]

        assert len(created) == 0
        assert len(cleared) == 1
        assert cleared[0].data["ID"] == AQA_ALERT_ID
        assert len(stale_events) == 0


class TestEventData:
    """Tests for event data contents."""

    async def test_event_data_contains_all_fields(self, hass, mock_aioclient):
        """Event data should contain all 21 alert fields."""
        mock_aioclient.get(ZONE_URL, status=200, body=load_fixture("api.json"))
        mock_aioclient.get(ZONE_URL, status=200, body=load_fixture("api.json"))

        events = []

        def listener(event):
            events.append(event)

        hass.bus.async_listen(EVENT_ALERT_CREATED, listener)

        entry = MockConfigEntry(
            domain=DOMAIN,
            title="NWS Alerts",
            data={"name": "NWS Alerts", "zone_id": "AZZ540,AZC013"},
        )
        entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        assert len(events) == 2
        for event in events:
            assert len(event.data) == EXPECTED_FIELD_COUNT
            assert "Event" in event.data
            assert "ID" in event.data
            assert "URL" in event.data
            assert "Headline" in event.data
            assert "Type" in event.data
            assert "NWSCode" in event.data
            assert "Status" in event.data
            assert "Severity" in event.data
            assert "Certainty" in event.data
            assert "Sent" in event.data
            assert "Onset" in event.data
            assert "Expires" in event.data
            assert "Ends" in event.data
            assert "AreasAffected" in event.data
            assert "Description" in event.data
            assert "Instruction" in event.data
            assert "Urgency" in event.data
            assert "Response" in event.data
            assert "SenderName" in event.data
            assert "Effective" in event.data
            assert "FormattedHeadline" in event.data
            assert "VTEC" in event.data
            assert "VTECAction" in event.data
            assert "References" in event.data
            assert "config_entry_id" in event.data
            assert "config_name" in event.data
