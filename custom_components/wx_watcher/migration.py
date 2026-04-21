"""Config entry migration for WX Watcher."""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_INTERVAL, CONF_TIMEOUT, CONFIG_VERSION, DEFAULT_TIMEOUT, MAX_TIMEOUT

_LOGGER = logging.getLogger(__name__)


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate old config entry data to current version."""
    version = config_entry.version
    data = {**config_entry.data}

    if version == 1:
        _LOGGER.debug("Migrating config entry from version 1")
        version = 2

    if version == 2:
        _LOGGER.debug("Migrating config entry from version 2")
        version = 3

    if version == 3:
        _LOGGER.debug("Migrating config entry from version 3")
        version = 4

    if version == 4:
        _LOGGER.debug("Migrating config entry from version 4 to 5")
        interval = data.get(CONF_INTERVAL, 1)
        data[CONF_INTERVAL] = interval * 60

        timeout = data.get(CONF_TIMEOUT, 120)
        if timeout > MAX_TIMEOUT:
            data[CONF_TIMEOUT] = MAX_TIMEOUT
        elif timeout == 120:
            data[CONF_TIMEOUT] = DEFAULT_TIMEOUT

        version = 5

    if version != CONFIG_VERSION:
        _LOGGER.error("Cannot migrate config entry from unknown version %s", version)
        return False

    hass.config_entries.async_update_entry(config_entry, data=data, version=version)
    _LOGGER.info("Migration to version %s complete", version)
    return True
