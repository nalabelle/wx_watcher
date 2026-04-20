"""Adds config flow for WX Watcher."""

# Derived in part from nws_alerts by finity69x2
# (https://github.com/finity69x2/nws_alerts).
# ConfigFlow/OptionsFlow class pattern and tracker entity listing originate
# from the upstream config flow. See NOTICE for details.
# As upstream-derived code is rewritten or removed, this comment should
# be updated or removed accordingly.

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components.device_tracker.const import DOMAIN as TRACKER_DOMAIN
from homeassistant.config_entries import ConfigEntry, ConfigFlowResult
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.instance_id import async_get as async_get_instance_id
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
)

from .api import resolve_zones
from .const import (
    CONF_INTERVAL,
    CONF_LOCATION_GPS,
    CONF_LOCATION_MODE,
    CONF_LOCATION_NAME,
    CONF_LOCATION_TRACKER,
    CONF_LOCATION_TYPE,
    CONF_LOCATION_ZONE,
    CONF_LOCATIONS,
    CONF_TIMEOUT,
    CONFIG_VERSION,
    DEFAULT_INTERVAL,
    DEFAULT_NAME,
    DEFAULT_TIMEOUT,
    DOMAIN,
    LOCATION_MODE_POINT,
    LOCATION_MODE_ZONE,
    LOCATION_TYPE_STATIC,
    LOCATION_TYPE_TRACKED,
    USER_AGENT,
)

_LOGGER = logging.getLogger(__name__)


def _get_tracker_entities(hass: HomeAssistant) -> list[str]:
    """Get list of device tracker entity IDs."""
    data = ["(none)"]
    entities = hass.states.async_entity_ids(TRACKER_DOMAIN)
    data.extend(entities)
    return data


def _get_ha_zone_entities(hass: HomeAssistant) -> list[SelectOptionDict]:
    """Get list of HA zone entity IDs as select options."""
    options = [SelectOptionDict(value="(none)", label="None")]
    for entity_id in sorted(hass.states.async_entity_ids("zone")):
        state = hass.states.get(entity_id)
        label = entity_id
        if state:
            label = f"{state.name} ({entity_id})"
        options.append(SelectOptionDict(value=entity_id, label=label))
    return options


class WXWatcherFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for WX Watcher."""

    VERSION = CONFIG_VERSION

    def __init__(self) -> None:
        """Initialize."""
        self._data: dict[str, Any] = {}
        self._locations: list[dict[str, Any]] = []
        self._errors: dict[str, str] = {}

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle the initial step — entry name and settings."""
        if user_input is not None:
            self._data[CONF_NAME] = user_input[CONF_NAME]
            self._data[CONF_INTERVAL] = user_input.get(CONF_INTERVAL, DEFAULT_INTERVAL)
            self._data[CONF_TIMEOUT] = user_input.get(CONF_TIMEOUT, DEFAULT_TIMEOUT)
            return await self.async_step_locations()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
                    vol.Optional(CONF_INTERVAL, default=DEFAULT_INTERVAL): int,
                    vol.Optional(CONF_TIMEOUT, default=DEFAULT_TIMEOUT): int,
                }
            ),
            errors=self._errors,
        )

    async def async_step_locations(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Hub page showing current locations and add/done buttons."""
        if user_input is not None:
            action = user_input.get("action")
            if action == "add_static":
                return await self.async_step_add_static()
            if action == "add_tracked":
                return await self.async_step_add_tracked()
            if action == "done":
                return self._create_entry()

        location_list = (
            ", ".join(
                f"{loc[CONF_LOCATION_NAME]} ({loc[CONF_LOCATION_TYPE]}, {loc[CONF_LOCATION_MODE]})"
                for loc in self._locations
            )
            if self._locations
            else "None"
        )

        return self.async_show_form(
            step_id="locations",
            data_schema=vol.Schema(
                {
                    vol.Required("action"): SelectSelector(
                        SelectSelectorConfig(
                            options=[
                                SelectOptionDict(value="add_static", label="Add a static location"),
                                SelectOptionDict(value="add_tracked", label="Add a tracked device"),
                                SelectOptionDict(value="done", label="Done — finish setup"),
                            ],
                        )
                    ),
                }
            ),
            description_placeholders={"location_list": location_list},
        )

    async def async_step_add_static(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle adding a static location."""
        errors: dict[str, str] = {}

        if user_input is not None:
            name = user_input[CONF_LOCATION_NAME]
            mode = user_input[CONF_LOCATION_MODE]
            source = user_input.get("source", "manual_gps")
            zone_str = ""
            gps = ""

            if source == "ha_zone":
                ha_zone = user_input.get("ha_zone", "(none)")
                if ha_zone == "(none)":
                    errors["ha_zone"] = "no_zone_selected"
                else:
                    state = self.hass.states.get(ha_zone)
                    if state and "latitude" in state.attributes and "longitude" in state.attributes:
                        gps = f"{state.attributes['latitude']},{state.attributes['longitude']}"
                    else:
                        errors["ha_zone"] = "zone_no_gps"

            if source == "manual_gps":
                gps = user_input.get(CONF_LOCATION_GPS, "").replace(" ", "")

            if not errors:
                if mode == LOCATION_MODE_ZONE and gps:
                    instance_id = await async_get_instance_id(self.hass)
                    user_agent = USER_AGENT.format(instance_id)
                    session = async_get_clientsession(self.hass)
                    lat_str, lon_str = gps.split(",")
                    zones = await resolve_zones(session, user_agent, float(lat_str), float(lon_str))
                    if zones:
                        zone_str = ",".join(zones)
                    else:
                        errors["base"] = "zone_resolve_failed"

                if mode == LOCATION_MODE_ZONE and not gps and not zone_str:
                    if source == "manual_zone":
                        zone_str = user_input.get(CONF_LOCATION_ZONE, "").replace(" ", "")
                    if not zone_str:
                        errors["base"] = "no_zone_or_gps"

            if not errors:
                if source == "manual_zone":
                    zone_str = user_input.get(CONF_LOCATION_ZONE, "").replace(" ", "")

                location: dict[str, Any] = {
                    CONF_LOCATION_NAME: name,
                    CONF_LOCATION_TYPE: LOCATION_TYPE_STATIC,
                    CONF_LOCATION_MODE: mode,
                    CONF_LOCATION_GPS: gps,
                    CONF_LOCATION_ZONE: zone_str,
                }
                if source == "ha_zone":
                    location["ha_zone"] = user_input.get("ha_zone", "")
                self._locations.append(location)
                return await self.async_step_locations()

        source_options = [
            SelectOptionDict(value="ha_zone", label="Home Assistant zone"),
            SelectOptionDict(value="manual_gps", label="Manual GPS coordinates"),
            SelectOptionDict(value="manual_zone", label="Manual NWS zone IDs"),
        ]
        mode_options = [
            SelectOptionDict(value=LOCATION_MODE_ZONE, label="Zone mode (broader coverage)"),
            SelectOptionDict(value=LOCATION_MODE_POINT, label="Point mode (precise location)"),
        ]

        schema_dict: dict[vol.Marker, Any] = {
            vol.Required(CONF_LOCATION_NAME): str,
            vol.Required("source", default="ha_zone"): SelectSelector(
                SelectSelectorConfig(options=source_options)
            ),
            vol.Required(CONF_LOCATION_MODE, default=LOCATION_MODE_ZONE): SelectSelector(
                SelectSelectorConfig(options=mode_options)
            ),
        }
        schema_dict[vol.Optional(CONF_LOCATION_GPS, default="")] = str
        schema_dict[vol.Optional(CONF_LOCATION_ZONE, default="")] = str
        schema_dict[vol.Optional("ha_zone", default="(none)")] = EntitySelector(
            EntitySelectorConfig(domain="zone")
        )

        return self.async_show_form(
            step_id="add_static",
            data_schema=vol.Schema(schema_dict),
            errors=errors,
        )

    async def async_step_add_tracked(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle adding a tracked device location."""
        errors: dict[str, str] = {}

        if user_input is not None:
            name = user_input[CONF_LOCATION_NAME]
            tracker = user_input.get(CONF_LOCATION_TRACKER, "(none)")
            mode = user_input[CONF_LOCATION_MODE]

            if tracker == "(none)":
                errors["tracker"] = "no_tracker_selected"
            else:
                state = self.hass.states.get(tracker)
                if state is None:
                    errors["tracker"] = "tracker_not_found"

            if not errors:
                location: dict[str, Any] = {
                    CONF_LOCATION_NAME: name,
                    CONF_LOCATION_TYPE: LOCATION_TYPE_TRACKED,
                    CONF_LOCATION_MODE: mode,
                    CONF_LOCATION_GPS: "",
                    CONF_LOCATION_ZONE: "",
                    CONF_LOCATION_TRACKER: tracker,
                }
                self._locations.append(location)
                return await self.async_step_locations()

        tracker_entities = _get_tracker_entities(self.hass)
        mode_options = [
            SelectOptionDict(value=LOCATION_MODE_ZONE, label="Zone mode (broader coverage)"),
            SelectOptionDict(value=LOCATION_MODE_POINT, label="Point mode (precise location)"),
        ]

        schema = vol.Schema(
            {
                vol.Required(CONF_LOCATION_NAME): str,
                vol.Required(CONF_LOCATION_TRACKER, default="(none)"): vol.In(tracker_entities),
                vol.Required(CONF_LOCATION_MODE, default=LOCATION_MODE_ZONE): SelectSelector(
                    SelectSelectorConfig(options=mode_options)
                ),
            }
        )

        return self.async_show_form(
            step_id="add_tracked",
            data_schema=schema,
            errors=errors,
        )

    def _create_entry(self) -> ConfigFlowResult:
        """Create the config entry."""
        self._data[CONF_LOCATIONS] = self._locations
        return self.async_create_entry(title=self._data[CONF_NAME], data=self._data)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> WXWatcherOptionsFlow:
        """Display options flow."""
        return WXWatcherOptionsFlow(config_entry)


class WXWatcherOptionsFlow(config_entries.OptionsFlow):
    """Options flow for WX Watcher."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize."""
        self._config = config_entry
        self._data = dict(config_entry.data)
        self._locations: list[dict[str, Any]] = list(config_entry.data.get(CONF_LOCATIONS, []))
        self._errors: dict[str, str] = {}

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Manage options — locations hub."""
        if user_input is not None:
            action = user_input.get("action")
            if action == "add_static":
                return await self.async_step_add_static()
            if action == "add_tracked":
                return await self.async_step_add_tracked()
            if action == "done":
                self._data[CONF_LOCATIONS] = self._locations
                return self.async_create_entry(title="", data=self._data)

        location_list = (
            ", ".join(
                f"{loc[CONF_LOCATION_NAME]} ({loc[CONF_LOCATION_TYPE]}, {loc[CONF_LOCATION_MODE]})"
                for loc in self._locations
            )
            if self._locations
            else "None"
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required("action"): SelectSelector(
                        SelectSelectorConfig(
                            options=[
                                SelectOptionDict(value="add_static", label="Add a static location"),
                                SelectOptionDict(value="add_tracked", label="Add a tracked device"),
                                SelectOptionDict(value="done", label="Done — save changes"),
                            ],
                        )
                    ),
                }
            ),
            description_placeholders={"location_list": location_list},
        )

    async def async_step_add_static(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle adding a static location in options."""
        return await self._handle_add_static(user_input)

    async def async_step_add_tracked(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle adding a tracked device in options."""
        return await self._handle_add_tracked(user_input)

    async def _handle_add_static(self, user_input: dict[str, Any] | None) -> ConfigFlowResult:
        """Shared static location logic between setup and options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            name = user_input[CONF_LOCATION_NAME]
            mode = user_input[CONF_LOCATION_MODE]
            source = user_input.get("source", "manual_gps")
            zone_str = ""
            gps = ""

            if source == "ha_zone":
                ha_zone = user_input.get("ha_zone", "(none)")
                if ha_zone == "(none)":
                    errors["ha_zone"] = "no_zone_selected"
                else:
                    state = self.hass.states.get(ha_zone)
                    if state and "latitude" in state.attributes and "longitude" in state.attributes:
                        gps = f"{state.attributes['latitude']},{state.attributes['longitude']}"
                    else:
                        errors["ha_zone"] = "zone_no_gps"

            if source == "manual_gps":
                gps = user_input.get(CONF_LOCATION_GPS, "").replace(" ", "")

            if not errors:
                if mode == LOCATION_MODE_ZONE and gps:
                    instance_id = await async_get_instance_id(self.hass)
                    user_agent = USER_AGENT.format(instance_id)
                    session = async_get_clientsession(self.hass)
                    lat_str, lon_str = gps.split(",")
                    zones = await resolve_zones(session, user_agent, float(lat_str), float(lon_str))
                    if zones:
                        zone_str = ",".join(zones)
                    else:
                        errors["base"] = "zone_resolve_failed"

                if mode == LOCATION_MODE_ZONE and not gps and not zone_str:
                    if source == "manual_zone":
                        zone_str = user_input.get(CONF_LOCATION_ZONE, "").replace(" ", "")
                    if not zone_str:
                        errors["base"] = "no_zone_or_gps"

            if not errors:
                if source == "manual_zone":
                    zone_str = user_input.get(CONF_LOCATION_ZONE, "").replace(" ", "")

                location: dict[str, Any] = {
                    CONF_LOCATION_NAME: name,
                    CONF_LOCATION_TYPE: LOCATION_TYPE_STATIC,
                    CONF_LOCATION_MODE: mode,
                    CONF_LOCATION_GPS: gps,
                    CONF_LOCATION_ZONE: zone_str,
                }
                if source == "ha_zone":
                    location["ha_zone"] = user_input.get("ha_zone", "")
                self._locations.append(location)
                return await self.async_step_init()

        source_options = [
            SelectOptionDict(value="ha_zone", label="Home Assistant zone"),
            SelectOptionDict(value="manual_gps", label="Manual GPS coordinates"),
            SelectOptionDict(value="manual_zone", label="Manual NWS zone IDs"),
        ]
        mode_options = [
            SelectOptionDict(value=LOCATION_MODE_ZONE, label="Zone mode (broader coverage)"),
            SelectOptionDict(value=LOCATION_MODE_POINT, label="Point mode (precise location)"),
        ]

        schema_dict: dict[vol.Marker, Any] = {
            vol.Required(CONF_LOCATION_NAME): str,
            vol.Required("source", default="ha_zone"): SelectSelector(
                SelectSelectorConfig(options=source_options)
            ),
            vol.Required(CONF_LOCATION_MODE, default=LOCATION_MODE_ZONE): SelectSelector(
                SelectSelectorConfig(options=mode_options)
            ),
            vol.Optional(CONF_LOCATION_GPS, default=""): str,
            vol.Optional(CONF_LOCATION_ZONE, default=""): str,
            vol.Optional("ha_zone", default="(none)"): EntitySelector(
                EntitySelectorConfig(domain="zone")
            ),
        }

        return self.async_show_form(
            step_id="add_static",
            data_schema=vol.Schema(schema_dict),
            errors=errors,
        )

    async def _handle_add_tracked(self, user_input: dict[str, Any] | None) -> ConfigFlowResult:
        """Shared tracked location logic between setup and options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            name = user_input[CONF_LOCATION_NAME]
            tracker = user_input.get(CONF_LOCATION_TRACKER, "(none)")
            mode = user_input[CONF_LOCATION_MODE]

            if tracker == "(none)":
                errors["tracker"] = "no_tracker_selected"
            else:
                state = self.hass.states.get(tracker)
                if state is None:
                    errors["tracker"] = "tracker_not_found"

            if not errors:
                location: dict[str, Any] = {
                    CONF_LOCATION_NAME: name,
                    CONF_LOCATION_TYPE: LOCATION_TYPE_TRACKED,
                    CONF_LOCATION_MODE: mode,
                    CONF_LOCATION_GPS: "",
                    CONF_LOCATION_ZONE: "",
                    CONF_LOCATION_TRACKER: tracker,
                }
                self._locations.append(location)
                return await self.async_step_init()

        tracker_entities = _get_tracker_entities(self.hass)
        mode_options = [
            SelectOptionDict(value=LOCATION_MODE_ZONE, label="Zone mode (broader coverage)"),
            SelectOptionDict(value=LOCATION_MODE_POINT, label="Point mode (precise location)"),
        ]

        schema = vol.Schema(
            {
                vol.Required(CONF_LOCATION_NAME): str,
                vol.Required(CONF_LOCATION_TRACKER, default="(none)"): vol.In(tracker_entities),
                vol.Required(CONF_LOCATION_MODE, default=LOCATION_MODE_ZONE): SelectSelector(
                    SelectSelectorConfig(options=mode_options)
                ),
            }
        )

        return self.async_show_form(
            step_id="add_tracked",
            data_schema=schema,
            errors=errors,
        )
