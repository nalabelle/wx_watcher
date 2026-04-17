"""Consts for nws_alerts."""

from homeassistant.const import Platform

# API
API_ENDPOINT = "https://api.weather.gov"
USER_AGENT = "nws_alerts homeassistant {}"

# Config
CONF_TIMEOUT = "timeout"
CONF_INTERVAL = "interval"
CONF_ZONE_ID = "zone_id"
CONF_GPS_LOC = "gps_loc"
CONF_TRACKER = "tracker"

# Defaults
DEFAULT_ICON = "mdi:alert"
DEFAULT_NAME = "NWS Alerts"
DEFAULT_INTERVAL = 1
DEFAULT_TIMEOUT = 120

# Misc
ZONE_ID = ""
VERSION = "6.7.3"
ISSUE_URL = "https://github.com/finity69x2/nws_alert"
DOMAIN = "nws_alerts"
PLATFORM = "sensor"
ATTRIBUTION = "Data provided by Weather.gov"
COORDINATOR = "coordinator"
PLATFORMS = [Platform.SENSOR]
CONFIG_VERSION = 2  # Config flow version

FORK_VERSION = "events.2"

EVENT_ALERT_CREATED = f"{DOMAIN}_alert_created"
EVENT_ALERT_UPDATED = f"{DOMAIN}_alert_updated"
EVENT_ALERT_CLEARED = f"{DOMAIN}_alert_cleared"
EVENT_ALERT_STALE_DATA = f"{DOMAIN}_alert_stale_data"

# Translations URLS
LOOKUP_URL = "https://github.com/finity69x2/nws_alerts/blob/master/lookup_options.md"
ID_URL = "https://github.com/finity69x2/nws_alerts/blob/master/README.md#if-using-use-either-a-zone-or-county-code"
