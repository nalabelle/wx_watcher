"""WX Watcher number entities."""

from datetime import timedelta

from homeassistant.components.number import RestoreNumber
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_INTERVAL,
    CONF_TIMEOUT,
    COORDINATOR,
    DEFAULT_INTERVAL,
    DEFAULT_NAME,
    DEFAULT_TIMEOUT,
    DOMAIN,
    INTERVAL_STEP,
    MAX_INTERVAL,
    MAX_TIMEOUT,
    MIN_INTERVAL,
    MIN_TIMEOUT,
    TIMEOUT_STEP,
)
from .coordinator import AlertsDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the WX Watcher number platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id][COORDINATOR]
    async_add_entities(
        [
            WXWatcherIntervalNumber(coordinator, entry),
            WXWatcherTimeoutNumber(coordinator, entry),
        ],
        True,
    )


class WXWatcherIntervalNumber(CoordinatorEntity, RestoreNumber):
    """Number entity for update interval control."""

    _attr_has_entity_name = True
    _attr_name = "Update Interval"
    _attr_native_min_value = MIN_INTERVAL
    _attr_native_max_value = MAX_INTERVAL
    _attr_native_step = INTERVAL_STEP
    _attr_native_unit_of_measurement = "s"
    _attr_icon = "mdi:timer-outline"
    _attr_entity_category = EntityCategory.CONFIG
    coordinator: AlertsDataUpdateCoordinator

    def __init__(self, coordinator: AlertsDataUpdateCoordinator, entry: ConfigEntry) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator)
        self._config_entry = entry
        self._attr_native_value = float(entry.data.get(CONF_INTERVAL, DEFAULT_INTERVAL))
        self._attr_unique_id = f"{entry.entry_id}_update_interval"
        self._attr_device_info = DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, entry.entry_id)},
            manufacturer="NWS",
            name=DEFAULT_NAME,
        )

    @property
    def native_value(self) -> float | None:
        """Return current interval value."""
        return self._attr_native_value

    async def async_added_to_hass(self) -> None:
        """Restore last value on startup."""
        await super().async_added_to_hass()
        if (
            last := await self.async_get_last_number_data()
        ) is not None and last.native_value is not None:
            self._attr_native_value = last.native_value
            self.coordinator.update_interval = timedelta(seconds=int(last.native_value))
        else:
            self.coordinator.update_interval = timedelta(
                seconds=int(self._attr_native_value or DEFAULT_INTERVAL)
            )

    async def async_set_native_value(self, value: float) -> None:
        """Change the update interval."""
        int_value = int(value)
        int_value = max(MIN_INTERVAL, min(MAX_INTERVAL, int_value))
        self._attr_native_value = float(int_value)
        self.coordinator.update_interval = timedelta(seconds=int_value)
        await self.coordinator.async_request_refresh()
        self.async_write_ha_state()


class WXWatcherTimeoutNumber(CoordinatorEntity, RestoreNumber):
    """Number entity for update timeout control."""

    _attr_has_entity_name = True
    _attr_name = "Update Timeout"
    _attr_native_min_value = MIN_TIMEOUT
    _attr_native_max_value = MAX_TIMEOUT
    _attr_native_step = TIMEOUT_STEP
    _attr_native_unit_of_measurement = "s"
    _attr_icon = "mdi:timer-off-outline"
    _attr_entity_category = EntityCategory.CONFIG
    coordinator: AlertsDataUpdateCoordinator

    def __init__(self, coordinator: AlertsDataUpdateCoordinator, entry: ConfigEntry) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator)
        self._config_entry = entry
        self._attr_native_value = float(entry.data.get(CONF_TIMEOUT, DEFAULT_TIMEOUT))
        self._attr_unique_id = f"{entry.entry_id}_update_timeout"
        self._attr_device_info = DeviceInfo(
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, entry.entry_id)},
            manufacturer="NWS",
            name=DEFAULT_NAME,
        )

    @property
    def native_value(self) -> float | None:
        """Return current timeout value."""
        return self._attr_native_value

    async def async_added_to_hass(self) -> None:
        """Restore last value on startup."""
        await super().async_added_to_hass()
        if (
            last := await self.async_get_last_number_data()
        ) is not None and last.native_value is not None:
            self._attr_native_value = last.native_value
            self.coordinator.timeout = int(last.native_value)
        else:
            self.coordinator.timeout = int(self._attr_native_value or DEFAULT_TIMEOUT)

    async def async_set_native_value(self, value: float) -> None:
        """Change the update timeout."""
        int_value = int(value)
        int_value = max(MIN_TIMEOUT, min(MAX_TIMEOUT, int_value))
        self._attr_native_value = float(int_value)
        self.coordinator.timeout = int_value
        await self.coordinator.async_request_refresh()
        self.async_write_ha_state()
