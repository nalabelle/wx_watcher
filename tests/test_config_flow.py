"""Test for config flow."""

from unittest.mock import patch

import pytest

from custom_components.wx_watcher.const import DOMAIN
from homeassistant import config_entries, setup
from homeassistant.data_entry_flow import FlowResultType

pytestmark = pytest.mark.asyncio


async def test_form_static_zone(hass):
    """Test we can create a static zone entry with auto-resolved zone IDs."""
    await setup.async_setup_component(hass, "persistent_notification", {})
    with patch("custom_components.wx_watcher.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        await hass.async_block_till_done()
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "locations"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"action": "add_static"}
        )
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "add_static"

        with patch(
            "custom_components.wx_watcher.config_flow.resolve_zones",
            return_value=["AZZ540", "AZC013"],
        ):
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {"ha_zone": "zone.home", "mode": "zone", "zone": ""},
            )
            assert result["type"] == FlowResultType.FORM
            assert result["step_id"] == "locations"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"action": "done"}
        )
        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["title"] == "WX Watcher"
        assert len(result["data"]["locations"]) == 1
        assert result["data"]["locations"][0]["ha_zone"] == "zone.home"
        assert result["data"]["locations"][0]["zone"] == "AZC013,AZZ540"
        assert result["data"]["locations"][0]["mode"] == "zone"
        await hass.async_block_till_done()


async def test_form_static_zone_with_manual_edit(hass):
    """Test zone IDs can be manually provided on first submit."""
    await setup.async_setup_component(hass, "persistent_notification", {})
    with patch("custom_components.wx_watcher.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        await hass.async_block_till_done()
        assert result["step_id"] == "locations"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"action": "add_static"}
        )

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"ha_zone": "zone.home", "mode": "zone", "zone": "AZZ540"},
        )
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "locations"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"action": "done"}
        )
        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["data"]["locations"][0]["zone"] == "AZZ540"
        await hass.async_block_till_done()


async def test_form_static_point_mode(hass):
    """Test point mode skips zone resolution."""
    await setup.async_setup_component(hass, "persistent_notification", {})
    with patch("custom_components.wx_watcher.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        await hass.async_block_till_done()
        assert result["step_id"] == "locations"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"action": "add_static"}
        )

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"ha_zone": "zone.home", "mode": "point", "zone": ""},
        )
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "locations"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"action": "done"}
        )
        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["data"]["locations"][0]["mode"] == "point"
        assert result["data"]["locations"][0]["zone"] == ""
        await hass.async_block_till_done()
