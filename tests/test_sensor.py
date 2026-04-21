"""Test WX Watcher Sensors."""

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.wx_watcher.const import DOMAIN
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.helpers import entity_registry as er
from tests.const import CONFIG_DATA

pytestmark = pytest.mark.asyncio


async def test_sensor(hass, mock_api):
    """Test sensors."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="WX Watcher",
        data=CONFIG_DATA,
        version=5,
    )

    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert DOMAIN in hass.config.components

    entity_ids = hass.states.async_entity_ids(SENSOR_DOMAIN)
    alerts_entity_id = next(eid for eid in entity_ids if eid.endswith("_alerts"))
    state = hass.states.get(alerts_entity_id)
    assert state
    assert state.state == "2"
    assert "Alerts" in state.attributes
    assert "locations" in state.attributes

    loc_info = state.attributes["locations"]
    assert len(loc_info) == 1
    assert loc_info[0]["entity"] == "zone.home"
    assert loc_info[0]["name"] == "Home"
    assert loc_info[0]["type"] == "static"
    assert loc_info[0]["mode"] == "zone"
    assert loc_info[0]["zone"] == "AZZ540,AZC013"
    assert loc_info[0]["gps"] == "33.25,-112.30"

    entity_registry = er.async_get(hass)
    assert entity_registry.async_get(alerts_entity_id)
