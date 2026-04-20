"""WX Watcher sensors."""

# Derived in part from nws_alerts by finity69x2
# (https://github.com/finity69x2/nws_alerts).
# Sensor class structure, SENSOR_TYPES pattern, and setup pattern originate
# from the upstream sensor module. See NOTICE for details.
# As upstream-derived code is rewritten or removed, this comment should
# be updated or removed accordingly.

import logging
from typing import Final

from homeassistant.components.sensor import SensorDeviceClass, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ATTRIBUTION, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, CONF_LOCATIONS, COORDINATOR, DOMAIN

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

        self._attr_icon = sensor_description.icon
        self._attr_name = f"{entry.data.get(CONF_NAME, DOMAIN)} {sensor_description.name}"
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

        locations = self._config.data.get(CONF_LOCATIONS, [])
        if locations:
            attrs["locations"] = [
                {
                    "name": loc.get("name", ""),
                    "type": loc.get("type", ""),
                    "mode": loc.get("mode", ""),
                }
                for loc in locations
            ]

        attrs[ATTR_ATTRIBUTION] = ATTRIBUTION
        return attrs

    @property
    def device_info(self) -> DeviceInfo:
        """Return device registry information."""
        return DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, self._config.entry_id)},
            manufacturer="NWS",
            name=self._config.data.get(CONF_NAME, "WX Watcher"),
        )
