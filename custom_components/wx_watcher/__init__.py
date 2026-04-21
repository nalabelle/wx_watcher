"""WX Watcher — weather alert integration for Home Assistant."""

# Derived in part from nws_alerts by finity69x2
# (https://github.com/finity69x2/nws_alerts).
# Setup/unload pattern and user agent construction originate from the
# upstream module. See NOTICE for details.
# As upstream-derived code is rewritten or removed, this comment should
# be updated or removed accordingly.

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.instance_id import async_get as async_get_instance_id

from .const import COORDINATOR, DOMAIN, ISSUE_URL, PLATFORMS, USER_AGENT, VERSION
from .coordinator import AlertsDataUpdateCoordinator
from .migration import async_migrate_entry as async_migrate_entry

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Load the saved entities."""
    _LOGGER.info(
        "Version %s is starting, if you have any issues please report them here: %s",
        VERSION,
        ISSUE_URL,
    )
    hass.data.setdefault(DOMAIN, {})

    instance_id = await async_get_instance_id(hass)
    user_agent = USER_AGENT.format(instance_id)
    _LOGGER.debug("WX Watcher User-Agent: %s", user_agent)

    coordinator = AlertsDataUpdateCoordinator(
        hass,
        config_entry,
        session=async_get_clientsession(hass),
        user_agent=user_agent,
    )

    hass.data[DOMAIN][config_entry.entry_id] = {
        COORDINATOR: coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    await coordinator.async_refresh()

    return True


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    """Handle removal of an entry."""
    _LOGGER.debug("Attempting to unload entities from the %s integration", DOMAIN)

    unload_ok = await hass.config_entries.async_unload_platforms(config_entry, PLATFORMS)

    if unload_ok:
        _LOGGER.debug("Successfully removed entities from the %s integration", DOMAIN)

    return unload_ok
