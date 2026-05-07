"""Tests for init."""

import logging

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.wx_watcher.const import DOMAIN
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.core import CoreState
from tests.const import CONFIG_DATA

pytestmark = pytest.mark.asyncio


async def test_setup_entry_cold_start(hass, mock_api, caplog):
    """Test setup during cold start registers started listener instead of immediate refresh."""
    hass.set_state(CoreState.not_running)

    with caplog.at_level(logging.DEBUG):
        entry = MockConfigEntry(
            domain=DOMAIN,
            title="WX Watcher",
            data=CONFIG_DATA,
            version=4,
        )

        entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        assert len(hass.states.async_entity_ids(SENSOR_DOMAIN)) == 1
        entries = hass.config_entries.async_entries(DOMAIN)
        assert len(entries) == 1

        hass.bus.async_fire("homeassistant_started")
        await hass.async_block_till_done()

        coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
        assert coordinator.data is not None


async def test_setup_entry_already_running(hass, mock_api, caplog):
    """Test setup when HA is already running — refresh fires immediately."""
    hass.set_state(CoreState.running)

    with caplog.at_level(logging.DEBUG):
        entry = MockConfigEntry(
            domain=DOMAIN,
            title="WX Watcher",
            data=CONFIG_DATA,
            version=4,
        )

        entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        assert len(hass.states.async_entity_ids(SENSOR_DOMAIN)) == 1
        entries = hass.config_entries.async_entries(DOMAIN)
        assert len(entries) == 1

        coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
        assert coordinator.data is not None


async def test_unload_entry(hass, mock_api):
    """Test unloading entities."""
    hass.set_state(CoreState.running)

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="WX Watcher",
        data=CONFIG_DATA,
        version=4,
    )

    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert len(hass.states.async_entity_ids(SENSOR_DOMAIN)) == 1
    entries = hass.config_entries.async_entries(DOMAIN)
    assert len(entries) == 1

    assert await hass.config_entries.async_unload(entries[0].entry_id)
    await hass.async_block_till_done()

    assert await hass.config_entries.async_remove(entries[0].entry_id)
    await hass.async_block_till_done()
    assert len(hass.states.async_entity_ids(SENSOR_DOMAIN)) == 0
