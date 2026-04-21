"""Adds config flow for WX Watcher."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry, ConfigFlowResult
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
    CONF_LOCATION_HA_ZONE,
    CONF_LOCATION_MODE,
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

MODE_OPTIONS = [
    SelectOptionDict(value=LOCATION_MODE_ZONE, label="Zone mode (broader coverage)"),
    SelectOptionDict(value=LOCATION_MODE_POINT, label="Point mode (precise location)"),
]


def _hub_actions(done_label: str) -> list[SelectOptionDict]:
    """Return action options for the locations menu."""
    return [
        SelectOptionDict(value="add_static", label="Add a static location"),
        SelectOptionDict(value="add_tracked", label="Add a tracked device"),
        SelectOptionDict(value="edit_location", label="Edit a location"),
        SelectOptionDict(value="remove_location", label="Remove a location"),
        SelectOptionDict(value="done", label=done_label),
    ]


def _location_display(hass: HomeAssistant, loc: dict[str, Any]) -> str:
    """Return a human-readable label for a location."""
    entity_id = loc.get(CONF_LOCATION_HA_ZONE) or loc.get(CONF_LOCATION_TRACKER, "")
    state = hass.states.get(entity_id)
    name = state.name if state else entity_id
    display = f"{name} ({loc[CONF_LOCATION_TYPE]}, {loc[CONF_LOCATION_MODE]}"
    zone = loc.get(CONF_LOCATION_ZONE, "")
    if zone:
        display += f", {zone}"
    return display + ")"


def _location_list_str(hass: HomeAssistant, locations: list[dict[str, Any]]) -> str:
    """Return a comma-separated summary of all locations."""
    if not locations:
        return "None"
    return ", ".join(_location_display(hass, loc) for loc in locations)


def _location_select_options(
    hass: HomeAssistant, locations: list[dict[str, Any]]
) -> list[SelectOptionDict]:
    """Return select options for the location picker."""
    options = []
    for i, loc in enumerate(locations):
        entity_id = loc.get(CONF_LOCATION_HA_ZONE) or loc.get(CONF_LOCATION_TRACKER, "")
        state = hass.states.get(entity_id)
        name = state.name if state else entity_id
        loc_type = "static" if loc[CONF_LOCATION_TYPE] == LOCATION_TYPE_STATIC else "tracked"
        label = f"{name} ({loc_type}, {loc[CONF_LOCATION_MODE]}"
        zone = loc.get(CONF_LOCATION_ZONE, "")
        if zone:
            label += f", {zone}"
        label += ")"
        options.append(SelectOptionDict(value=str(i), label=label))
    return options


def _dedupe_zone_str(zone_str: str) -> str:
    """Deduplicate and sort comma-separated zone IDs."""
    zones = sorted({z.strip() for z in zone_str.split(",") if z.strip()})
    return ",".join(zones)


def _static_schema(
    ha_zone_default: str | None = None,
    mode_default: str = LOCATION_MODE_ZONE,
    zone_default: str = "",
) -> vol.Schema:
    """Return a voluptuous schema for the static-location form."""
    return vol.Schema(
        {
            vol.Required(CONF_LOCATION_HA_ZONE, default=ha_zone_default): EntitySelector(
                EntitySelectorConfig(domain="zone")
            ),
            vol.Required(CONF_LOCATION_MODE, default=mode_default): SelectSelector(
                SelectSelectorConfig(options=MODE_OPTIONS)
            ),
            vol.Optional(CONF_LOCATION_ZONE, default=zone_default): str,
        }
    )


def _tracked_schema(
    tracker_default: str | None = None,
    mode_default: str = LOCATION_MODE_ZONE,
) -> vol.Schema:
    """Return a voluptuous schema for the tracked-device form."""
    return vol.Schema(
        {
            vol.Required(CONF_LOCATION_TRACKER, default=tracker_default): EntitySelector(
                EntitySelectorConfig(domain="device_tracker")
            ),
            vol.Required(CONF_LOCATION_MODE, default=mode_default): SelectSelector(
                SelectSelectorConfig(options=MODE_OPTIONS)
            ),
        }
    )


async def _validate_static(
    hass: HomeAssistant, user_input: dict[str, Any]
) -> tuple[dict[str, Any] | None, dict[str, str], dict[str, Any]]:
    """Validate a static location submission.

    Returns (location_dict | None, errors, form_data).
    """
    errors: dict[str, str] = {}
    ha_zone = user_input.get(CONF_LOCATION_HA_ZONE, "")
    mode = user_input[CONF_LOCATION_MODE]
    zone_str = user_input.get(CONF_LOCATION_ZONE, "")
    gps = ""

    if not ha_zone:
        errors["base"] = "no_zone_selected"

    if not errors:
        state = hass.states.get(ha_zone)
        if not state:
            errors["base"] = "no_zone_selected"
        elif "latitude" not in state.attributes or "longitude" not in state.attributes:
            errors["base"] = "zone_no_gps"
        else:
            gps = f"{state.attributes['latitude']},{state.attributes['longitude']}"

    if not errors and mode == LOCATION_MODE_ZONE and not zone_str:
        instance_id = await async_get_instance_id(hass)
        user_agent = USER_AGENT.format(instance_id)
        session = async_get_clientsession(hass)
        lat_str, lon_str = gps.split(",")
        zones = await resolve_zones(session, user_agent, float(lat_str), float(lon_str))
        if zones:
            zone_str = ",".join(zones)
        else:
            errors["base"] = "zone_resolve_failed"

    if not errors:
        location = {
            CONF_LOCATION_TYPE: LOCATION_TYPE_STATIC,
            CONF_LOCATION_MODE: mode,
            CONF_LOCATION_GPS: gps,
            CONF_LOCATION_ZONE: _dedupe_zone_str(zone_str),
            CONF_LOCATION_HA_ZONE: ha_zone,
        }
        return location, errors, {}

    return (
        None,
        errors,
        {
            CONF_LOCATION_HA_ZONE: ha_zone,
            CONF_LOCATION_MODE: mode,
            CONF_LOCATION_ZONE: zone_str,
        },
    )


def _validate_tracked(
    hass: HomeAssistant, user_input: dict[str, Any]
) -> tuple[dict[str, Any] | None, dict[str, str]]:
    """Validate a tracked-device submission.

    Returns (location_dict | None, errors).
    """
    errors: dict[str, str] = {}
    tracker = user_input.get(CONF_LOCATION_TRACKER, "")
    mode = user_input[CONF_LOCATION_MODE]

    state = hass.states.get(tracker)
    if not state:
        errors["base"] = "tracker_not_found"

    if not errors:
        location = {
            CONF_LOCATION_TYPE: LOCATION_TYPE_TRACKED,
            CONF_LOCATION_MODE: mode,
            CONF_LOCATION_GPS: "",
            CONF_LOCATION_ZONE: "",
            CONF_LOCATION_TRACKER: tracker,
        }
        return location, errors

    return None, errors


class WXWatcherFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for WX Watcher."""

    VERSION = CONFIG_VERSION

    def __init__(self) -> None:
        """Initialize the config flow handler."""
        self._data: dict[str, Any] = {}
        self._locations: list[dict[str, Any]] = []
        self._errors: dict[str, str] = {}
        self._edit_index: int = -1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle the initial user step."""
        self._data["name"] = DEFAULT_NAME
        self._data[CONF_INTERVAL] = DEFAULT_INTERVAL
        self._data[CONF_TIMEOUT] = DEFAULT_TIMEOUT
        return await self.async_step_locations()

    async def async_step_locations(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the locations menu step."""
        if user_input is not None:
            action = user_input.get("action")
            if action == "add_static":
                return await self.async_step_add_static()
            if action == "add_tracked":
                return await self.async_step_add_tracked()
            if action == "edit_location":
                return await self.async_step_edit_location()
            if action == "remove_location":
                return await self.async_step_remove_location()
            if action == "done":
                return self._create_entry()

        return self.async_show_form(
            step_id="locations",
            data_schema=vol.Schema(
                {
                    vol.Required("action"): SelectSelector(
                        SelectSelectorConfig(options=_hub_actions("Done — finish setup"))
                    ),
                }
            ),
            description_placeholders={
                "location_list": _location_list_str(self.hass, self._locations),
            },
        )

    async def async_step_add_static(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle adding a static location."""
        if user_input is not None:
            location, errors, form_data = await _validate_static(self.hass, user_input)
            if location:
                self._locations.append(location)
                return await self.async_step_locations()
            return self.async_show_form(
                step_id="add_static",
                data_schema=_static_schema(
                    ha_zone_default=form_data.get(CONF_LOCATION_HA_ZONE),
                    mode_default=form_data.get(CONF_LOCATION_MODE, LOCATION_MODE_ZONE),
                    zone_default=form_data.get(CONF_LOCATION_ZONE, ""),
                ),
                errors=errors,
            )

        return self.async_show_form(
            step_id="add_static",
            data_schema=_static_schema(),
        )

    async def async_step_add_tracked(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle adding a tracked device."""
        if user_input is not None:
            location, errors = _validate_tracked(self.hass, user_input)
            if location:
                self._locations.append(location)
                return await self.async_step_locations()
            return self.async_show_form(
                step_id="add_tracked",
                data_schema=_tracked_schema(),
                errors=errors,
            )

        return self.async_show_form(
            step_id="add_tracked",
            data_schema=_tracked_schema(),
        )

    async def async_step_edit_location(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle selecting a location to edit."""
        if not self._locations:
            return await self.async_step_locations()

        if user_input is not None and "location_index" in user_input:
            idx = int(user_input["location_index"])
            if idx < 0 or idx >= len(self._locations):
                return await self.async_step_locations()
            self._edit_index = idx
            loc = self._locations[idx]
            if loc[CONF_LOCATION_TYPE] == LOCATION_TYPE_STATIC:
                return self.async_show_form(
                    step_id="edit_static",
                    data_schema=_static_schema(
                        ha_zone_default=loc.get(CONF_LOCATION_HA_ZONE),
                        mode_default=loc[CONF_LOCATION_MODE],
                        zone_default=loc.get(CONF_LOCATION_ZONE, ""),
                    ),
                )
            return self.async_show_form(
                step_id="edit_tracked",
                data_schema=_tracked_schema(
                    tracker_default=loc.get(CONF_LOCATION_TRACKER),
                    mode_default=loc[CONF_LOCATION_MODE],
                ),
            )

        return self.async_show_form(
            step_id="edit_location",
            data_schema=vol.Schema(
                {
                    vol.Required("location_index"): SelectSelector(
                        SelectSelectorConfig(
                            options=_location_select_options(self.hass, self._locations)
                        )
                    ),
                }
            ),
        )

    async def async_step_edit_static(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle editing a static location."""
        idx = self._edit_index
        if idx < 0 or idx >= len(self._locations):
            return await self.async_step_locations()

        if user_input is not None:
            location, errors, form_data = await _validate_static(self.hass, user_input)
            if location:
                self._locations[idx] = location
                return await self.async_step_locations()
            return self.async_show_form(
                step_id="edit_static",
                data_schema=_static_schema(
                    ha_zone_default=form_data.get(CONF_LOCATION_HA_ZONE),
                    mode_default=form_data.get(CONF_LOCATION_MODE, LOCATION_MODE_ZONE),
                    zone_default=form_data.get(CONF_LOCATION_ZONE, ""),
                ),
                errors=errors,
            )

        return await self.async_step_locations()

    async def async_step_edit_tracked(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle editing a tracked device."""
        idx = self._edit_index
        if idx < 0 or idx >= len(self._locations):
            return await self.async_step_locations()

        if user_input is not None:
            location, errors = _validate_tracked(self.hass, user_input)
            if location:
                self._locations[idx] = location
                return await self.async_step_locations()
            return self.async_show_form(
                step_id="edit_tracked",
                data_schema=_tracked_schema(
                    tracker_default=self._locations[idx].get(CONF_LOCATION_TRACKER),
                    mode_default=self._locations[idx][CONF_LOCATION_MODE],
                ),
                errors=errors,
            )

        return await self.async_step_locations()

    async def async_step_remove_location(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle removing a location."""
        if not self._locations:
            return await self.async_step_locations()

        if user_input is not None and "location_index" in user_input:
            idx = int(user_input["location_index"])
            if 0 <= idx < len(self._locations):
                self._locations.pop(idx)
            return await self.async_step_locations()

        return self.async_show_form(
            step_id="remove_location",
            data_schema=vol.Schema(
                {
                    vol.Required("location_index"): SelectSelector(
                        SelectSelectorConfig(
                            options=_location_select_options(self.hass, self._locations)
                        )
                    ),
                }
            ),
        )

    def _create_entry(self) -> ConfigFlowResult:
        """Create the config entry from collected data."""
        self._data[CONF_LOCATIONS] = self._locations
        return self.async_create_entry(title=DEFAULT_NAME, data=self._data)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> WXWatcherOptionsFlow:
        """Return the options flow handler."""
        return WXWatcherOptionsFlow(config_entry)


class WXWatcherOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for WX Watcher."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize the options flow handler."""
        self._config = config_entry
        self._data = dict(config_entry.data)
        self._locations: list[dict[str, Any]] = list(config_entry.data.get(CONF_LOCATIONS, []))
        self._errors: dict[str, str] = {}
        self._edit_index: int = -1

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle the options flow main menu."""
        if user_input is not None:
            action = user_input.get("action")
            if action == "add_static":
                return await self.async_step_add_static()
            if action == "add_tracked":
                return await self.async_step_add_tracked()
            if action == "edit_location":
                return await self.async_step_edit_location()
            if action == "remove_location":
                return await self.async_step_remove_location()
            if action == "done":
                self._data[CONF_LOCATIONS] = self._locations
                return self.async_create_entry(title="", data=self._data)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required("action"): SelectSelector(
                        SelectSelectorConfig(options=_hub_actions("Done — save changes"))
                    ),
                }
            ),
            description_placeholders={
                "location_list": _location_list_str(self.hass, self._locations),
            },
        )

    async def async_step_add_static(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle adding a static location."""
        if user_input is not None:
            location, errors, form_data = await _validate_static(self.hass, user_input)
            if location:
                self._locations.append(location)
                return await self.async_step_init()
            return self.async_show_form(
                step_id="add_static",
                data_schema=_static_schema(
                    ha_zone_default=form_data.get(CONF_LOCATION_HA_ZONE),
                    mode_default=form_data.get(CONF_LOCATION_MODE, LOCATION_MODE_ZONE),
                    zone_default=form_data.get(CONF_LOCATION_ZONE, ""),
                ),
                errors=errors,
            )

        return self.async_show_form(
            step_id="add_static",
            data_schema=_static_schema(),
        )

    async def async_step_add_tracked(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle adding a tracked device."""
        if user_input is not None:
            location, errors = _validate_tracked(self.hass, user_input)
            if location:
                self._locations.append(location)
                return await self.async_step_init()
            return self.async_show_form(
                step_id="add_tracked",
                data_schema=_tracked_schema(),
                errors=errors,
            )

        return self.async_show_form(
            step_id="add_tracked",
            data_schema=_tracked_schema(),
        )

    async def async_step_edit_location(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle selecting a location to edit."""
        if not self._locations:
            return await self.async_step_init()

        if user_input is not None and "location_index" in user_input:
            idx = int(user_input["location_index"])
            if idx < 0 or idx >= len(self._locations):
                return await self.async_step_init()
            self._edit_index = idx
            loc = self._locations[idx]
            if loc[CONF_LOCATION_TYPE] == LOCATION_TYPE_STATIC:
                return self.async_show_form(
                    step_id="edit_static",
                    data_schema=_static_schema(
                        ha_zone_default=loc.get(CONF_LOCATION_HA_ZONE),
                        mode_default=loc[CONF_LOCATION_MODE],
                        zone_default=loc.get(CONF_LOCATION_ZONE, ""),
                    ),
                )
            return self.async_show_form(
                step_id="edit_tracked",
                data_schema=_tracked_schema(
                    tracker_default=loc.get(CONF_LOCATION_TRACKER),
                    mode_default=loc[CONF_LOCATION_MODE],
                ),
            )

        return self.async_show_form(
            step_id="edit_location",
            data_schema=vol.Schema(
                {
                    vol.Required("location_index"): SelectSelector(
                        SelectSelectorConfig(
                            options=_location_select_options(self.hass, self._locations)
                        )
                    ),
                }
            ),
        )

    async def async_step_edit_static(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle editing a static location."""
        idx = self._edit_index
        if idx < 0 or idx >= len(self._locations):
            return await self.async_step_init()

        if user_input is not None:
            location, errors, form_data = await _validate_static(self.hass, user_input)
            if location:
                self._locations[idx] = location
                return await self.async_step_init()
            return self.async_show_form(
                step_id="edit_static",
                data_schema=_static_schema(
                    ha_zone_default=form_data.get(CONF_LOCATION_HA_ZONE),
                    mode_default=form_data.get(CONF_LOCATION_MODE, LOCATION_MODE_ZONE),
                    zone_default=form_data.get(CONF_LOCATION_ZONE, ""),
                ),
                errors=errors,
            )

        return await self.async_step_init()

    async def async_step_edit_tracked(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle editing a tracked device."""
        idx = self._edit_index
        if idx < 0 or idx >= len(self._locations):
            return await self.async_step_init()

        if user_input is not None:
            location, errors = _validate_tracked(self.hass, user_input)
            if location:
                self._locations[idx] = location
                return await self.async_step_init()
            return self.async_show_form(
                step_id="edit_tracked",
                data_schema=_tracked_schema(
                    tracker_default=self._locations[idx].get(CONF_LOCATION_TRACKER),
                    mode_default=self._locations[idx][CONF_LOCATION_MODE],
                ),
                errors=errors,
            )

        return await self.async_step_init()

    async def async_step_remove_location(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle removing a location."""
        if not self._locations:
            return await self.async_step_init()

        if user_input is not None and "location_index" in user_input:
            idx = int(user_input["location_index"])
            if 0 <= idx < len(self._locations):
                self._locations.pop(idx)
            return await self.async_step_init()

        return self.async_show_form(
            step_id="remove_location",
            data_schema=vol.Schema(
                {
                    vol.Required("location_index"): SelectSelector(
                        SelectSelectorConfig(
                            options=_location_select_options(self.hass, self._locations)
                        )
                    ),
                }
            ),
        )
