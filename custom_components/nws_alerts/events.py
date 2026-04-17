"""Event handling for NWS Alerts."""

from datetime import UTC, datetime
import logging

from homeassistant.core import HomeAssistant

from .const import (
    EVENT_ALERT_CLEARED,
    EVENT_ALERT_CREATED,
    EVENT_ALERT_STALE_DATA,
    EVENT_ALERT_UPDATED,
)

_LOGGER = logging.getLogger(__name__)


async def async_fire_alert_events(
    hass: HomeAssistant,
    coordinator: object,
    new_data: dict,
) -> None:
    """Compare new alert data against previous state and fire appropriate events.

    Fires nws_alerts_alert_created for new alerts,
    nws_alerts_alert_updated for changed alerts,
    and nws_alerts_alert_cleared for removed alerts.
    Updates coordinator._previous_alerts and _last_successful_update afterward.
    """
    new_alerts = new_data.get("alerts", [])
    new_alerts_by_id = {alert["ID"]: alert for alert in new_alerts}
    previous_alerts = coordinator._previous_alerts

    created_event_data = []
    updated_event_data = []
    cleared_event_data = []

    for alert_id, alert in new_alerts_by_id.items():
        if alert_id not in previous_alerts:
            created_event_data.append(alert)
        elif alert != previous_alerts[alert_id]:
            updated_event_data.append(alert)

    for alert_id in previous_alerts:
        if alert_id not in new_alerts_by_id:
            cleared_event_data.append(previous_alerts[alert_id])

    for alert in created_event_data:
        _LOGGER.debug("Firing %s for %s", EVENT_ALERT_CREATED, alert["ID"])
        hass.bus.async_fire(EVENT_ALERT_CREATED, alert)

    for alert in updated_event_data:
        _LOGGER.debug("Firing %s for %s", EVENT_ALERT_UPDATED, alert["ID"])
        hass.bus.async_fire(EVENT_ALERT_UPDATED, alert)

    for alert in cleared_event_data:
        _LOGGER.debug("Firing %s for %s", EVENT_ALERT_CLEARED, alert["ID"])
        hass.bus.async_fire(EVENT_ALERT_CLEARED, alert)

    coordinator._previous_alerts = new_alerts_by_id
    coordinator._last_successful_update = datetime.now(tz=UTC).isoformat()


async def async_fire_stale_data_event(
    hass: HomeAssistant,
    last_successful_update: str | None,
) -> None:
    """Fire nws_alerts_alert_stale_data event when an API fetch fails.

    Includes the timestamp of the last successful update so automations
    can determine how stale the data is.
    """
    _LOGGER.warning(
        "NWS Alerts API fetch failed. Last successful update: %s",
        last_successful_update,
    )
    hass.bus.async_fire(
        EVENT_ALERT_STALE_DATA,
        {"last_successful": last_successful_update},
    )
