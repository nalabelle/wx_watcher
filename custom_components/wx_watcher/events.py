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


def _dedup_key(alert: dict) -> str:
    """Return the dedup key for an alert.

    Uses the VTEC product code when available for stable identification
    across URI changes. Falls back to the alert ID for alerts without
    VTEC (e.g., Air Quality Alerts).
    """
    # Alerts without VTEC (e.g., Air Quality Alerts) fall back to ID-based
    # matching. This is safe because: (1) NWS does not revise non-VTEC
    # alerts as aggressively as severe weather warnings, so the spam
    # problem is less severe, and (2) an alert's VTEC status is fixed
    # from creation — an alert never transitions from no-VTEC to having
    # VTEC or vice versa.
    return alert.get("_VTECKey") or alert["ID"]


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

    Alerts are compared by VTEC dedup key when available, falling back
    to ID-based matching for non-VTEC alerts. This ensures revisions
    (same VTEC, new URI) produce UPDATED instead of CLEARED+CREATED.
    """
    new_alerts = new_data.get("alerts", [])
    new_alerts_by_key = {_dedup_key(alert): alert for alert in new_alerts}

    created_event_data = []
    updated_event_data = []
    cleared_event_data = []

    for alert in new_alerts:
        key = _dedup_key(alert)
        if alert.get("VTECAction") in ("CAN", "EXP"):
            cleared_event_data.append(previous_merged.get(key, alert))
        elif key not in previous_merged:
            created_event_data.append(alert)
        elif alert != previous_merged[key]:
            updated_event_data.append(alert)

    for key, prev_alert in previous_merged.items():
        if key not in new_alerts_by_key:
            cleared_event_data.append(prev_alert)

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
