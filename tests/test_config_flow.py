"""Test for config flow."""

from unittest.mock import patch

import pytest

from custom_components.wx_watcher.const import DOMAIN
from homeassistant import config_entries, setup
from homeassistant.data_entry_flow import FlowResultType

pytestmark = pytest.mark.asyncio


async def test_form_zone(hass):
    """Test we get the form and can create a zone entry."""
    await setup.async_setup_component(hass, "persistent_notification", {})
    with patch("custom_components.wx_watcher.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        assert result["type"] == FlowResultType.FORM

    user_data = {
        "name": "Testing Alerts",
        "interval": 1,
        "timeout": 120,
    }
    with (
        patch("custom_components.wx_watcher.async_setup_entry", return_value=True),
        patch(
            "custom_components.wx_watcher.config_flow.resolve_zones",
            return_value=["AZZ540", "AZC013"],
        ),
    ):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], user_data)
        await hass.async_block_till_done()

    with (
        patch("custom_components.wx_watcher.async_setup_entry", return_value=True),
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"action": "done"}
        )
        assert result2["type"] == "create_entry"
        assert result2["title"] == "Testing Alerts"
        await hass.async_block_till_done()
