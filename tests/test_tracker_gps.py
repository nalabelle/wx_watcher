"""Tests for tracker GPS startup grace period and missing-tracker warnings."""

from datetime import UTC, datetime, timedelta
import logging

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.wx_watcher.const import DOMAIN, TRACKER_STARTUP_GRACE_PERIOD
from homeassistant.core import CoreState
from tests.conftest import load_fixture
from tests.const import CONFIG_DATA_TRACKER_ONLY

pytestmark = pytest.mark.asyncio

TRACKER_ENTITY = "device_tracker.phone"
TRACKER_POINT_URL = "https://api.weather.gov/alerts/active?point=33.5,-112.0"


async def _setup_entry(hass, mock_aioclient, config_data):
    """Set up a mock config entry and return (entry, coordinator)."""
    hass.set_state(CoreState.running)
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="WX Watcher",
        data=config_data,
        version=4,
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    return entry, coordinator


async def test_tracker_not_found_within_grace_period_logs_debug(hass, mock_aioclient, caplog):
    """Tracker not found within grace period should log debug, not warning."""
    mock_aioclient.get(TRACKER_POINT_URL, status=200, body=load_fixture("api.json"))

    with caplog.at_level(logging.DEBUG):
        _, coordinator = await _setup_entry(hass, mock_aioclient, CONFIG_DATA_TRACKER_ONLY)

        coordinator._startup_time = datetime.now(tz=UTC)
        await coordinator._get_tracker_gps(TRACKER_ENTITY)

        assert any(
            "startup grace period" in r.message and r.levelno == logging.DEBUG
            for r in caplog.records
        )
        assert not any(
            "not found" in r.message and r.levelno == logging.WARNING for r in caplog.records
        )


async def test_tracker_not_found_after_grace_period_logs_warning(hass, mock_aioclient, caplog):
    """Tracker not found after grace period should log warning."""
    mock_aioclient.get(TRACKER_POINT_URL, status=200, body=load_fixture("api.json"))

    with caplog.at_level(logging.DEBUG):
        _, coordinator = await _setup_entry(hass, mock_aioclient, CONFIG_DATA_TRACKER_ONLY)

        coordinator._startup_time = (
            datetime.now(tz=UTC) - TRACKER_STARTUP_GRACE_PERIOD - timedelta(seconds=1)
        )
        await coordinator._get_tracker_gps(TRACKER_ENTITY)

        assert any(
            "not found after startup grace period" in r.message and r.levelno == logging.WARNING
            for r in caplog.records
        )


async def test_tracker_previously_seen_now_missing_logs_warning(hass, mock_aioclient, caplog):
    """Tracker that was previously available but now missing should always warn."""
    mock_aioclient.get(TRACKER_POINT_URL, status=200, body=load_fixture("api.json"))

    with caplog.at_level(logging.DEBUG):
        _, coordinator = await _setup_entry(hass, mock_aioclient, CONFIG_DATA_TRACKER_ONLY)

        coordinator._startup_time = datetime.now(tz=UTC)
        coordinator._trackers_seen.add(TRACKER_ENTITY)
        await coordinator._get_tracker_gps(TRACKER_ENTITY)

        assert any(
            "previously available but now missing" in r.message and r.levelno == logging.WARNING
            for r in caplog.records
        )


async def test_tracker_found_added_to_seen(hass, mock_aioclient):
    """Successful GPS lookup should add tracker to _trackers_seen."""
    mock_aioclient.get(TRACKER_POINT_URL, status=200, body=load_fixture("api.json"))

    _, coordinator = await _setup_entry(hass, mock_aioclient, CONFIG_DATA_TRACKER_ONLY)

    hass.states.async_set(
        TRACKER_ENTITY,
        "not_home",
        {"latitude": 33.50, "longitude": -112.00, "friendly_name": "Phone"},
    )

    result = await coordinator._get_tracker_gps(TRACKER_ENTITY)
    assert result == "33.5,-112.0"
    assert TRACKER_ENTITY in coordinator._trackers_seen


async def test_tracker_previously_seen_warns_every_time(hass, mock_aioclient, caplog):
    """Previously-seen tracker gone missing should warn on every call."""
    mock_aioclient.get(TRACKER_POINT_URL, status=200, body=load_fixture("api.json"))

    with caplog.at_level(logging.DEBUG):
        _, coordinator = await _setup_entry(hass, mock_aioclient, CONFIG_DATA_TRACKER_ONLY)

        coordinator._startup_time = datetime.now(tz=UTC)
        coordinator._trackers_seen.add(TRACKER_ENTITY)

        await coordinator._get_tracker_gps(TRACKER_ENTITY)
        await coordinator._get_tracker_gps(TRACKER_ENTITY)

        warnings = [
            r
            for r in caplog.records
            if "previously available but now missing" in r.message and r.levelno == logging.WARNING
        ]
        assert len(warnings) == 2
