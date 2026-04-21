"""NWS API client for WX Watcher."""

# Derived in part from nws_alerts by finity69x2
# (https://github.com/finity69x2/nws_alerts).
# generate_id() and alert field extraction originate from the upstream
# coordinator's async_get_alerts method. See NOTICE for details.
# As upstream-derived code is rewritten or removed, this comment should
# be updated or removed accordingly.

import hashlib
import logging
from typing import Any
import uuid

import aiohttp

from .const import API_ENDPOINT
from .vtec import VTECParseError, parse_vtec

_LOGGER = logging.getLogger(__name__)


class NWSApiError(Exception):
    """Exception raised when the NWS API returns a non-200 status."""


async def resolve_zones(
    session: aiohttp.ClientSession,
    user_agent: str,
    lat: float,
    lon: float,
) -> list[str] | None:
    """Resolve GPS coordinates to NWS zone IDs via the /points and /zones endpoints.

    Returns a deduplicated list of zone IDs (forecast, county, and fire weather),
    or None if the API call fails.
    """
    headers = {"User-Agent": user_agent, "Accept": "application/geo+json"}
    point_url = f"{API_ENDPOINT}/points/{lat},{lon}"

    async with session.get(point_url, headers=headers) as r:
        if r.status != 200:
            _LOGGER.warning("Failed to resolve zones for %s,%s: %s", lat, lon, r.status)
            return None
        data = await r.json()

    try:
        properties = data["properties"]
    except (KeyError, TypeError):
        _LOGGER.warning("Unexpected /points response for %s,%s", lat, lon)
        return None

    zone_ids: set[str] = set()

    for key in ("forecastZone", "county", "fireWeatherZone"):
        url = properties.get(key)
        if url and isinstance(url, str):
            zone_id = url.rsplit("/", 1)[-1]
            zone_ids.add(zone_id)

    if zone_ids:
        _LOGGER.debug("Resolved zones for %s,%s: %s", lat, lon, sorted(zone_ids))
        return sorted(zone_ids)

    _LOGGER.warning("No zone IDs found in /points response for %s,%s", lat, lon)
    return None


async def fetch_zone_alerts(
    session: aiohttp.ClientSession,
    user_agent: str,
    zone_ids: list[str],
) -> tuple[list[dict[str, Any]], str]:
    """Fetch active alerts for a combined set of zone IDs.

    The zone_ids list is joined with commas for a single ?zone= query.
    Returns a tuple of (raw alert features list, updated timestamp string).
    """
    if not zone_ids:
        return [], ""

    url = f"{API_ENDPOINT}/alerts/active?zone={','.join(zone_ids)}"
    return await _fetch_alerts(session, user_agent, url, f"zones {zone_ids}")


async def fetch_point_alerts(
    session: aiohttp.ClientSession,
    user_agent: str,
    lat: float,
    lon: float,
) -> tuple[list[dict[str, Any]], str]:
    """Fetch active alerts for a GPS point.

    Returns a tuple of (raw alert features list, updated timestamp string).
    """
    url = f"{API_ENDPOINT}/alerts/active?point={lat},{lon}"
    return await _fetch_alerts(session, user_agent, url, f"point {lat},{lon}")


async def _fetch_alerts(
    session: aiohttp.ClientSession,
    user_agent: str,
    url: str,
    desc: str,
) -> tuple[list[dict[str, Any]], str]:
    """Fetch and return raw alert features from an NWS API URL.

    Returns a tuple of (features list, updated timestamp string).
    """
    headers = {"User-Agent": user_agent, "Accept": "application/geo+json"}
    _LOGGER.debug("Fetching alerts for %s from %s", desc, url)

    async with session.get(url, headers=headers) as r:
        if r.status == 200:
            data = await r.json()
            features = data.get("features", [])
            updated = data.get("updated", "")
            _LOGGER.debug("Got %d alerts for %s", len(features), desc)
            return features, updated
        msg = f"Problem fetching alerts for {desc}: ({r.status}) {r.reason}"
        _LOGGER.warning(msg)
        raise NWSApiError(msg)


def parse_alert(raw_alert: dict[str, Any]) -> dict[str, Any] | None:
    """Parse a raw NWS alert feature into our internal alert dict.

    Returns None if required fields are missing.
    """
    try:
        props = raw_alert["properties"]
    except (KeyError, TypeError):
        _LOGGER.warning("Alert missing properties, skipping")
        return None

    try:
        alert_id = generate_id(raw_alert["id"])
    except (KeyError, TypeError):
        _LOGGER.warning("Alert missing id, skipping")
        return None

    try:
        event = props["event"]
    except KeyError:
        _LOGGER.warning("Alert missing event field, skipping")
        return None

    ugc: list[str] = []
    geocode = props.get("geocode", {})
    if isinstance(geocode, dict):
        ugc = geocode.get("UGC", [])

    parsed: dict[str, Any] = {
        "Event": event,
        "ID": alert_id,
        "URL": raw_alert.get("id", ""),
        "Headline": (
            props["parameters"]["NWSheadline"][0]
            if "NWSheadline" in props.get("parameters", {})
            else event
        ),
        "Type": props.get("messageType", ""),
        "NWSCode": props.get("eventCode", {}).get("NationalWeatherService", [""])[0],
        "Status": props.get("status", ""),
        "Severity": props.get("severity", "Unknown"),
        "Certainty": props.get("certainty", "Unknown"),
        "Sent": props.get("sent", ""),
        "Onset": props.get("onset", ""),
        "Expires": props.get("expires", ""),
        "Ends": props.get("ends", ""),
        "AreasAffected": props.get("areaDesc", ""),
        "Description": props.get("description", ""),
        "Instruction": props.get("instruction", ""),
        "Urgency": props.get("urgency", "Unknown"),
        "Response": props.get("response", "Monitor"),
        "SenderName": props.get("senderName", ""),
        "Effective": props.get("effective", ""),
        "FormattedHeadline": props.get("headline", ""),
        "VTEC": props.get("parameters", {}).get("VTEC", []),
        "VTECAction": None,
        "Significance": "",
        "References": props.get("references", []),
        "_ugc": ugc,
    }

    vtec_list = parsed["VTEC"]
    if vtec_list:
        try:
            tokens = parse_vtec(vtec_list[0])
        except VTECParseError:
            _LOGGER.warning(
                "Failed to parse VTEC for alert %s: %s",
                alert_id,
                vtec_list[0],
                exc_info=True,
            )
        else:
            parsed["VTECAction"] = tokens.action
            parsed["Significance"] = tokens.significance
    else:
        parsed["VTECAction"] = None

    return parsed


def generate_id(val: str) -> str:
    """Generate a stable UUID from an NWS alert URI."""
    hex_string = hashlib.md5(val.encode("UTF-8")).hexdigest()
    return str(uuid.UUID(hex=hex_string))
