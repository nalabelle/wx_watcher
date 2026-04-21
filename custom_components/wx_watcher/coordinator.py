"""Coordinator for WX Watcher."""

# Derived in part from nws_alerts by finity69x2
# (https://github.com/finity69x2/nws_alerts).
# DataUpdateCoordinator structure, _async_update_data pattern with
# async_timeout + UpdateFailed originate from the upstream coordinator.
# See NOTICE for details.
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
    CONF_LOCATION_HA_ZONE,
    CONF_LOCATION_MODE,
    CONF_LOCATION_TRACKER,
    CONF_LOCATION_TYPE,
    CONF_LOCATION_ZONE,
    CONF_LOCATIONS,
    CONF_TIMEOUT,
    DEFAULT_INTERVAL,
    DEFAULT_NAME,
    DEFAULT_TIMEOUT,
    LOCATION_MODE_POINT,
    LOCATION_MODE_ZONE,
    LOCATION_TYPE_STATIC,
    LOCATION_TYPE_TRACKED,
    MAX_TIMEOUT,
    MIN_TIMEOUT,
)
from .events import async_fire_alert_events, async_fire_stale_data_event

_LOGGER = logging.getLogger(__name__)


def _parse_timestamp(ts: str) -> datetime | None:
    """Parse ISO 8601 timestamp, return None if invalid."""
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts)
    except ValueError:
        _LOGGER.warning("Invalid timestamp from NWS API: %s", ts)
        return None


def _parse_gps_str(gps_str: str) -> tuple[float, float]:
    """Parse a ``lat,lon`` string into a float tuple."""
    parts = gps_str.replace(" ", "").split(",")
    return float(parts[0]), float(parts[1])


def _safe_parse_gps(loc: dict[str, Any]) -> tuple[float, float] | None:
    """Parse GPS coordinates from a location dict, with validation and error handling.

    Returns (lat, lon) on success, or None with a logged warning on failure.
    """
    gps = loc.get(CONF_LOCATION_GPS, "")
    if not gps:
        _LOGGER.warning("No GPS coordinates for %s, skipping", _entity_id(loc))
        return None
    try:
        return _parse_gps_str(gps)
    except (ValueError, IndexError) as err:
        _LOGGER.warning("Invalid GPS format for %s: %s", _entity_id(loc), err)
        return None


def _entity_id(loc: dict[str, Any]) -> str:
    """Return the primary entity ID for a location dict."""
    return loc.get(CONF_LOCATION_HA_ZONE) or loc.get(CONF_LOCATION_TRACKER, "")


def _build_source(loc: dict[str, Any]) -> dict[str, str]:
    """Build a source descriptor from a location configuration."""
    source: dict[str, str] = {"mode": loc[CONF_LOCATION_MODE]}
    if loc.get(CONF_LOCATION_HA_ZONE):
        source["ha_zone"] = loc[CONF_LOCATION_HA_ZONE]
    if loc.get(CONF_LOCATION_TRACKER):
        source["tracker"] = loc[CONF_LOCATION_TRACKER]
    return source


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
        self._interval = timedelta(seconds=config.data.get(CONF_INTERVAL, DEFAULT_INTERVAL))
        self._timeout = config.data.get(CONF_TIMEOUT, DEFAULT_TIMEOUT)
        self._config = config
        self._session = session
        self._user_agent = user_agent
        self._entry_id = config.entry_id
        self._locations: list[dict[str, Any]] = config.data.get(CONF_LOCATIONS, [])
        self._previous_merged: dict[str, dict] = {}
        self._previous_per_location: dict[str, set[str]] = {}
        self._last_successful_update: str | None = None
        self._nws_updated: str | None = None
        self._tracker_gps_warned: dict[str, datetime] = {}

        _LOGGER.debug("Data will be updated every %s", self._interval)

        super().__init__(
            hass,
            _LOGGER,
            config_entry=config,
            name=DEFAULT_NAME,
            update_interval=self._interval,
        )

    @property
    def entry_id(self) -> str:
        """Return the config entry ID."""
        return self._entry_id

    @property
    def timeout(self) -> int:
        """Return the current timeout in seconds."""
        return self._timeout

    @timeout.setter
    def timeout(self, value: int) -> None:
        """Set the timeout in seconds."""
        self._timeout = max(MIN_TIMEOUT, min(MAX_TIMEOUT, value))

    @property
    def nws_updated(self) -> str | None:
        """Return the NWS API 'updated' timestamp from last fetch."""
        return self._nws_updated

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
        """Fetch alerts for all configured locations."""
        static_zone_entity_ids = {
            loc[CONF_LOCATION_HA_ZONE]
            for loc in self._locations
            if loc[CONF_LOCATION_TYPE] == LOCATION_TYPE_STATIC and loc.get(CONF_LOCATION_HA_ZONE)
        }

        location_zones, point_tasks = await self._build_fetch_tasks(static_zone_entity_ids)

        all_zone_ids: set[str] = set()
        for loc_zones in location_zones.values():
            all_zone_ids.update(loc_zones)

        zone_alerts_raw: list[dict[str, Any]] = []
        nws_updated: str | None = None
        if all_zone_ids:
            zone_alerts_raw, zone_updated = await fetch_zone_alerts(
                self._session, self._user_agent, sorted(all_zone_ids)
            )
            if zone_updated:
                nws_updated = zone_updated

        point_results, point_updated = await self._fetch_point_alerts(point_tasks)
        point_dt = _parse_timestamp(point_updated)
        zone_dt = _parse_timestamp(nws_updated or "")
        if point_dt and (zone_dt is None or point_dt > zone_dt):
            nws_updated = point_updated

        self._nws_updated = nws_updated

        merged = self._merge_zone_alerts(zone_alerts_raw, location_zones)
        self._merge_point_alerts(point_results, merged)

        alerts = sorted(merged.values(), key=lambda x: x["ID"])
        return {
            "state": len(alerts),
            "alerts": alerts,
            "last_updated": datetime.now(tz=UTC).isoformat(),
        }

    async def _build_fetch_tasks(
        self, static_zone_entity_ids: set[str]
    ) -> tuple[dict[str, set[str]], list[tuple[dict, tuple[float, float]]]]:
        """Build zone-lookup and point-fetch tasks from configured locations."""
        location_zones: dict[str, set[str]] = {}
        point_tasks: list[tuple[dict, tuple[float, float]]] = []

        for loc in self._locations:
            loc_type = loc[CONF_LOCATION_TYPE]
            loc_mode = loc[CONF_LOCATION_MODE]

            if loc_type == LOCATION_TYPE_TRACKED:
                tracker_entity = loc[CONF_LOCATION_TRACKER]
                tracker_state = self.hass.states.get(tracker_entity)
                if tracker_state and tracker_state.state in static_zone_entity_ids:
                    _LOGGER.debug(
                        "Tracker %s is inside static zone %s, skipping",
                        tracker_entity,
                        tracker_state.state,
                    )
                    continue

                gps = await self._get_tracker_gps(tracker_entity)
                if gps is None:
                    _LOGGER.debug(
                        "Tracker %s unavailable, skipping",
                        tracker_entity,
                    )
                    continue
                loc[CONF_LOCATION_GPS] = gps

            if loc_mode == LOCATION_MODE_ZONE:
                zone_str = loc.get(CONF_LOCATION_ZONE, "")
                if loc_type == LOCATION_TYPE_TRACKED or not zone_str:
                    coords = _safe_parse_gps(loc)
                    if coords is None:
                        continue
                    lat, lon = coords
                    zones = await resolve_zones(self._session, self._user_agent, lat, lon)
                    if zones is None:
                        _LOGGER.warning(
                            "Could not resolve zones for location %s, skipping",
                            self._display_name(_entity_id(loc)),
                        )
                        continue
                    zone_str = ",".join(zones)
                    loc[CONF_LOCATION_ZONE] = zone_str

                loc_zones = {z.strip() for z in zone_str.split(",") if z.strip()}
                location_zones[_entity_id(loc)] = loc_zones

            elif loc_mode == LOCATION_MODE_POINT:
                coords = _safe_parse_gps(loc)
                if coords is None:
                    continue
                lat, lon = coords
                point_tasks.append((loc, (lat, lon)))

        return location_zones, point_tasks

    async def _fetch_point_alerts(
        self, point_tasks: list[tuple[dict, tuple[float, float]]]
    ) -> tuple[dict[str, list[dict[str, Any]]], str]:
        """Fetch point alerts for all point-mode locations concurrently.

        Returns (results dict, latest updated timestamp).
        """
        if not point_tasks:
            return {}, ""

        coros = [
            fetch_point_alerts(self._session, self._user_agent, coords[0], coords[1])
            for _, coords in point_tasks
        ]
        raw_results = await asyncio.gather(*coros, return_exceptions=True)
        results: dict[str, list[dict[str, Any]]] = {}
        latest_updated = ""
        latest_dt: datetime | None = None
        for i, result in enumerate(raw_results):
            loc = point_tasks[i][0]
            eid = _entity_id(loc)
            if isinstance(result, Exception):
                _LOGGER.warning(
                    "Failed to fetch point alerts for %s: %s",
                    self._display_name(eid),
                    result,
                )
            else:
                features, updated = cast(tuple[list[dict[str, Any]], str], result)
                results[eid] = features
                updated_dt = _parse_timestamp(updated)
                if updated_dt and (latest_dt is None or updated_dt > latest_dt):
                    latest_updated = updated
                    latest_dt = updated_dt
        return results, latest_updated

    def _merge_zone_alerts(
        self,
        zone_alerts_raw: list[dict[str, Any]],
        location_zones: dict[str, set[str]],
    ) -> dict[str, dict[str, Any]]:
        """Merge raw zone alerts and assign source locations."""
        merged: dict[str, dict[str, Any]] = {}
        for raw_alert in zone_alerts_raw:
            parsed = parse_alert(raw_alert)
            if parsed is None:
                continue
            alert_id = parsed["ID"]
            ugc: set[str] = set(parsed.pop("_ugc", []))
            sources = []
            for entity_id, loc_zones in location_zones.items():
                if ugc & loc_zones:
                    loc = next(loc for loc in self._locations if _entity_id(loc) == entity_id)
                    sources.append(_build_source(loc))

            if alert_id in merged:
                merged[alert_id]["sources"].extend(sources)
            else:
                parsed["sources"] = sources
                merged[alert_id] = parsed
        return merged

    def _merge_point_alerts(
        self,
        point_results: dict[str, list[dict[str, Any]]],
        merged: dict[str, dict[str, Any]],
    ) -> None:
        """Merge point-alert results into *merged* in place."""
        for entity_id, raw_alerts in point_results.items():
            loc = next(loc for loc in self._locations if _entity_id(loc) == entity_id)
            for raw_alert in raw_alerts:
                parsed = parse_alert(raw_alert)
                if parsed is None:
                    continue
                alert_id = parsed["ID"]
                parsed.pop("_ugc", None)
                source = _build_source(loc)
                if alert_id in merged:
                    merged[alert_id]["sources"].append(source)
                else:
                    parsed["sources"] = [source]
                    merged[alert_id] = parsed

    async def _get_tracker_gps(self, tracker_entity_id: str) -> str | None:
        """Return ``lat,lon`` string for a tracker entity, or None."""
        entity = self.hass.states.get(tracker_entity_id)
        if entity is None:
            _LOGGER.warning("Tracker entity %s not found", tracker_entity_id)
            return None
        attrs = entity.attributes
        if "latitude" in attrs and "longitude" in attrs:
            self._tracker_gps_warned.pop(tracker_entity_id, None)
            return f"{attrs['latitude']},{attrs['longitude']}"
        now = datetime.now(tz=UTC)
        last_warned = self._tracker_gps_warned.get(tracker_entity_id)
        if last_warned is None or (now - last_warned) > timedelta(hours=24):
            _LOGGER.warning("Tracker %s missing latitude/longitude attributes", tracker_entity_id)
            self._tracker_gps_warned[tracker_entity_id] = now
        else:
            _LOGGER.debug("Tracker %s missing latitude/longitude attributes", tracker_entity_id)
        return None

    def _display_name(self, entity_id: str) -> str:
        """Return the friendly name for an entity ID."""
        state = self.hass.states.get(entity_id)
        return state.name if state else entity_id
