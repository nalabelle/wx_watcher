"""WX Watcher sensors."""

# Derived in part from nws_alerts by finity69x2
# (https://github.com/finity69x2/nws_alerts).
# Sensor class structure, SENSOR_TYPES pattern, and setup pattern originate
# from the upstream sensor module. The extra_state_attributes property was
# rewritten in v8 for entity-based locations. See NOTICE for details.
# As upstream-derived code is rewritten or removed, this comment should
# be updated or removed accordingly.

import logging
from typing import Final

from homeassistant.components.sensor import SensorDeviceClass, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ATTRIBUTION
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, CONF_LOCATIONS, COORDINATOR, DEFAULT_NAME, DOMAIN
from .coordinator import AlertsDataUpdateCoordinator

SENSOR_TYPES: Final[dict[str, SensorEntityDescription]] = {
    "state": SensorEntityDescription(key="state", name="Alerts", icon="mdi:alert"),
    "last_updated": SensorEntityDescription(
        name="Last Updated",
        key="last_updated",
        icon="mdi:update",
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
}

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    """Sensor platform setup."""
    sensors = [WXWatcherSensor(hass, entry, sensor) for sensor in SENSOR_TYPES.values()]
    async_add_entities(sensors, True)


class WXWatcherSensor(CoordinatorEntity):
    """Representation of a Sensor."""

    coordinator: AlertsDataUpdateCoordinator

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        sensor_description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(hass.data[DOMAIN][entry.entry_id][COORDINATOR])
        self._config = entry
        self._key = sensor_description.key
        self._hass = hass

        self._attr_icon = sensor_description.icon
        self._attr_name = f"{DEFAULT_NAME} {sensor_description.name}"
        self._attr_device_class = sensor_description.device_class
        self._attr_unique_id = f"{self._attr_name}_{entry.entry_id}"

    @property
    def state(self) -> int | None:
        """Return the state of the sensor."""
        if self.coordinator.data is None:
            return None
        if self._key in self.coordinator.data:
            return self.coordinator.data[self._key]
        return None

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        attrs = {}
        if self.coordinator.data is None:
            return attrs
        if "alerts" in self.coordinator.data and self._key == "state":
            attrs["Alerts"] = self.coordinator.data["alerts"]
            if self.coordinator.nws_updated:
                attrs["nws_updated"] = self.coordinator.nws_updated

        locations = self._config.data.get(CONF_LOCATIONS, [])
        if locations:
            attrs["locations"] = []
            for loc in locations:
                entity_id = loc.get("ha_zone") or loc.get("tracker", "")
                state = self._hass.states.get(entity_id)
                attrs["locations"].append(
                    {
                        "entity": entity_id,
                        "name": state.name if state else entity_id,
                        "type": loc.get("type", ""),
                        "mode": loc.get("mode", ""),
                        "zone": loc.get("zone", ""),
                        "gps": loc.get("gps", ""),
                    }
                )

        attrs[ATTR_ATTRIBUTION] = ATTRIBUTION
        return attrs

    @property
    def device_info(self) -> DeviceInfo:
        """Return device registry information."""
        return DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, self._config.entry_id)},
            manufacturer="NWS",
            name=DEFAULT_NAME,
        )
