"""Coordinator for WX Watcher."""

# Derived in part from nws_alerts by finity69x2
# (https://github.com/finity69x2/nws_alerts).
# DataUpdateCoordinator structure, _async_update_data pattern with
# async_timeout + UpdateFailed, _get_tracker_gps originate from the
# upstream coordinator. See NOTICE for details.
# As upstream-derived code is rewritten or removed, this comment should
# be updated or removed accordingly.

import asyncio
from asyncio import timeout as async_timeout
from datetime import UTC, datetime, timedelta
import logging
from typing import Any, cast

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import fetch_point_alerts, fetch_zone_alerts, parse_alert, resolve_zones
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
    LOCATION_MODE_POINT,
    LOCATION_MODE_ZONE,
    LOCATION_TYPE_TRACKED,
)
from .events import async_fire_alert_events, async_fire_stale_data_event

_LOGGER = logging.getLogger(__name__)


def _parse_gps(gps_str: str) -> tuple[float, float]:
    """Parse a 'lat,lon' string into (lat, lon) floats."""
    parts = gps_str.replace(" ", "").split(",")
    return float(parts[0]), float(parts[1])


class AlertsDataUpdateCoordinator(DataUpdateCoordinator):
    """Coordinator that manages multi-location NWS alert fetching."""

    def __init__(
        self,
        hass: HomeAssistant,
        config: ConfigEntry,
        *,
        session: aiohttp.ClientSession,
        user_agent: str,
    ) -> None:
        """Initialize the coordinator."""
        self._interval = timedelta(minutes=config.data.get(CONF_INTERVAL, 1))
        self._timeout = config.data.get(CONF_TIMEOUT, 120)
        self._config = config
        self._session = session
        self._user_agent = user_agent
        self._entry_id = config.entry_id
        self._locations: list[dict[str, Any]] = config.data.get(CONF_LOCATIONS, [])
        self._previous_merged: dict[str, dict] = {}
        self._previous_per_location: dict[str, set[str]] = {}
        self._last_successful_update: str | None = None

        _LOGGER.debug("Data will be updated every %s", self._interval)

        super().__init__(
            hass,
            _LOGGER,
            config_entry=config,
            name=config.data.get("name", "NWS Alerts"),
            update_interval=self._interval,
        )

    @property
    def entry_id(self) -> str:
        """Return the config entry ID."""
        return self._entry_id

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from all locations and merge."""
        async with async_timeout(self._timeout):
            try:
                data = await self._fetch_all_locations()
            except Exception as error:
                await async_fire_stale_data_event(self.hass, self._last_successful_update)
                raise UpdateFailed(error) from error

            await async_fire_alert_events(self.hass, self._entry_id, data, self._previous_merged)
            self._previous_merged = {alert["ID"]: alert for alert in data["alerts"]}
            self._last_successful_update = datetime.now(tz=UTC).isoformat()
            _LOGGER.debug("Data: %s", data)
            return data

    async def _fetch_all_locations(self) -> dict[str, Any]:
        """Fetch alerts from all locations, merge by ID, return deduplicated data."""
        zone_alerts_raw: list[dict[str, Any]] = []
        point_tasks: list[tuple[dict, Any]] = []
        location_zones: dict[str, set[str]] = {}

        for loc in self._locations:
            loc_name = loc[CONF_LOCATION_NAME]
            loc_mode = loc[CONF_LOCATION_MODE]
            loc_type = loc[CONF_LOCATION_TYPE]

            if loc_type == LOCATION_TYPE_TRACKED:
                gps = await self._get_tracker_gps(loc[CONF_LOCATION_TRACKER])
                if gps is None:
                    _LOGGER.debug(
                        "Tracker %s unavailable, skipping location %s",
                        loc.get(CONF_LOCATION_TRACKER),
                        loc_name,
                    )
                    continue
                loc[CONF_LOCATION_GPS] = gps

            if loc_mode == LOCATION_MODE_ZONE:
                zone_str = loc.get(CONF_LOCATION_ZONE, "")
                if loc_type == LOCATION_TYPE_TRACKED or not zone_str:
                    lat, lon = _parse_gps(loc[CONF_LOCATION_GPS])
                    zones = await resolve_zones(self._session, self._user_agent, lat, lon)
                    if zones is None:
                        _LOGGER.warning(
                            "Could not resolve zones for location %s, skipping", loc_name
                        )
                        continue
                    zone_str = ",".join(zones)
                    loc[CONF_LOCATION_ZONE] = zone_str

                loc_zones = {z.strip() for z in zone_str.split(",") if z.strip()}
                location_zones[loc_name] = loc_zones

            elif loc_mode == LOCATION_MODE_POINT:
                lat, lon = _parse_gps(loc[CONF_LOCATION_GPS])
                point_tasks.append((loc, (lat, lon)))

        all_zone_ids: set[str] = set()
        for loc_zones in location_zones.values():
            all_zone_ids.update(loc_zones)

        if all_zone_ids:
            zone_alerts_raw = await fetch_zone_alerts(
                self._session, self._user_agent, sorted(all_zone_ids)
            )

        point_results: dict[str, list[dict[str, Any]]] = {}
        if point_tasks:
            coros = [
                fetch_point_alerts(self._session, self._user_agent, coords[0], coords[1])
                for _, coords in point_tasks
            ]
            raw_results = await asyncio.gather(*coros, return_exceptions=True)
            for i, result in enumerate(raw_results):
                loc_name = point_tasks[i][0][CONF_LOCATION_NAME]
                if isinstance(result, Exception):
                    _LOGGER.warning("Failed to fetch point alerts for %s: %s", loc_name, result)
                else:
                    point_results[loc_name] = cast(list[dict[str, Any]], result)

        merged: dict[str, dict[str, Any]] = {}

        if all_zone_ids:
            for raw_alert in zone_alerts_raw:
                parsed = parse_alert(raw_alert)
                if parsed is None:
                    continue
                alert_id = parsed["ID"]
                ugc: set[str] = set(parsed.pop("_ugc", []))
                sources = []
                for loc_name, loc_zones in location_zones.items():
                    if ugc & loc_zones:
                        loc = next(
                            loc for loc in self._locations if loc[CONF_LOCATION_NAME] == loc_name
                        )
                        sources.append(
                            {
                                "location": loc_name,
                                "mode": loc[CONF_LOCATION_MODE],
                            }
                        )
                if not sources and location_zones:
                    matching = [ln for ln, lz in location_zones.items() if ugc & lz]
                    sources = [{"location": n, "mode": "zone"} for n in matching]

                if alert_id in merged:
                    merged[alert_id]["sources"].extend(sources)
                else:
                    parsed["sources"] = sources
                    merged[alert_id] = parsed

        for loc_name, raw_alerts in point_results.items():
            loc = next(loc for loc in self._locations if loc[CONF_LOCATION_NAME] == loc_name)
            for raw_alert in raw_alerts:
                parsed = parse_alert(raw_alert)
                if parsed is None:
                    continue
                alert_id = parsed["ID"]
                parsed.pop("_ugc", None)
                source = {"location": loc_name, "mode": loc[CONF_LOCATION_MODE]}
                if alert_id in merged:
                    merged[alert_id]["sources"].append(source)
                else:
                    parsed["sources"] = [source]
                    merged[alert_id] = parsed

        alerts = sorted(merged.values(), key=lambda x: x["ID"])
        return {
            "state": len(alerts),
            "alerts": alerts,
            "last_updated": datetime.now(tz=UTC).isoformat(),
        }

    async def _get_tracker_gps(self, tracker_entity_id: str) -> str | None:
        """Return 'lat,lon' string from a device tracker, or None if unavailable."""
        entity = self.hass.states.get(tracker_entity_id)
        if entity is None:
            _LOGGER.warning("Tracker entity %s not found", tracker_entity_id)
            return None
        attrs = entity.attributes
        if "latitude" in attrs and "longitude" in attrs:
            return f"{attrs['latitude']},{attrs['longitude']}"
        _LOGGER.warning("Tracker %s missing latitude/longitude attributes", tracker_entity_id)
        return None
