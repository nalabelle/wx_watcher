"""Event handling for WX Watcher."""

import logging
from typing import Any

from homeassistant.core import HomeAssistant

from .const import (
    EVENT_ALERT_CLEARED,
    EVENT_ALERT_CREATED,
    EVENT_ALERT_FETCH_RESULT,
    EVENT_ALERT_UPDATED,
    EVENT_ATTR_CONFIG_ENTRY_ID,
)

_LOGGER = logging.getLogger(__name__)


async def async_fire_alert_events(
    hass: HomeAssistant,
    entry_id: str,
    new_data: dict,
    previous_merged: dict[str, dict],
) -> None:
    """Compare new merged alert data against previous state and fire appropriate events.

    Fires wx_watcher_alert_created for new alerts,
    wx_watcher_alert_updated for changed alerts,
    and wx_watcher_alert_cleared for removed alerts.
    """
    new_alerts = new_data.get("alerts", [])
    new_alerts_by_id = {alert["ID"]: alert for alert in new_alerts}

    created_event_data = []
    updated_event_data = []
    cleared_event_data = []

    for alert_id, alert in new_alerts_by_id.items():
        if alert_id not in previous_merged:
            created_event_data.append(alert)
        elif alert != previous_merged[alert_id]:
            updated_event_data.append(alert)

    cleared_event_data = [
        previous_merged[alert_id]
        for alert_id in previous_merged
        if alert_id not in new_alerts_by_id
    ]

    for alert in created_event_data:
        enriched = {
            **_strip_internal(alert),
            EVENT_ATTR_CONFIG_ENTRY_ID: entry_id,
        }
        _LOGGER.debug("Firing %s for %s", EVENT_ALERT_CREATED, alert["ID"])
        hass.bus.async_fire(EVENT_ALERT_CREATED, enriched)

    for alert in updated_event_data:
        enriched = {
            **_strip_internal(alert),
            EVENT_ATTR_CONFIG_ENTRY_ID: entry_id,
        }
        _LOGGER.debug("Firing %s for %s", EVENT_ALERT_UPDATED, alert["ID"])
        hass.bus.async_fire(EVENT_ALERT_UPDATED, enriched)

    for alert in cleared_event_data:
        enriched = {
            **_strip_internal(alert),
            EVENT_ATTR_CONFIG_ENTRY_ID: entry_id,
        }
        _LOGGER.debug("Firing %s for %s", EVENT_ALERT_CLEARED, alert["ID"])
        hass.bus.async_fire(EVENT_ALERT_CLEARED, enriched)


def _strip_internal(alert: dict) -> dict:
    """Remove internal-only fields before firing events."""
    return {k: v for k, v in alert.items() if not k.startswith("_")}


async def async_fire_fetch_result_event(
    hass: HomeAssistant,
    status: str,
    last_successful: str | None,
    http_status: int | None = None,
) -> None:
    """Fire wx_watcher_alert_fetch_result event with fetch status."""
    event_data: dict[str, Any] = {
        "status": status,
        "last_successful": last_successful,
    }
    if http_status is not None:
        event_data["http_status"] = http_status
    hass.bus.async_fire(EVENT_ALERT_FETCH_RESULT, event_data)
