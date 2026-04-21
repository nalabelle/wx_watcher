"""Constants for WX Watcher."""

# Derived in part from nws_alerts by finity69x2
# (https://github.com/finity69x2/nws_alerts), which is derived from
# nws_custom_component by eracknaphobia
# (https://github.com/eracknaphobia/nws_custom_component).
# Neither upstream project includes a license. See NOTICE for details.
# As upstream-derived code is rewritten or removed, this comment should
# be updated or removed accordingly.

from homeassistant.const import Platform

API_ENDPOINT = "https://api.weather.gov"
USER_AGENT = "wx_watcher homeassistant {}"

CONF_TIMEOUT = "timeout"
CONF_INTERVAL = "interval"

CONF_LOCATIONS = "locations"
CONF_LOCATION_TYPE = "type"
CONF_LOCATION_MODE = "mode"
CONF_LOCATION_GPS = "gps"
CONF_LOCATION_ZONE = "zone"
CONF_LOCATION_TRACKER = "tracker"
CONF_LOCATION_HA_ZONE = "ha_zone"

LOCATION_TYPE_STATIC = "static"
LOCATION_TYPE_TRACKED = "tracked"

LOCATION_MODE_ZONE = "zone"
LOCATION_MODE_POINT = "point"

DEFAULT_ICON = "mdi:alert"
DEFAULT_NAME = "WX Watcher"
DEFAULT_INTERVAL = 60
DEFAULT_TIMEOUT = 60

MIN_INTERVAL = 15
MAX_INTERVAL = 300
INTERVAL_STEP = 15

MIN_TIMEOUT = 5
MAX_TIMEOUT = 120
TIMEOUT_STEP = 5

EVENT_ATTR_CONFIG_ENTRY_ID = "config_entry_id"
EVENT_ATTR_SOURCES = "sources"

VERSION = "8.1.1"
ISSUE_URL = "https://github.com/nalabelle/wx_watcher"
DOMAIN = "wx_watcher"
PLATFORM = "sensor"
ATTRIBUTION = "Data provided by Weather.gov"
COORDINATOR = "coordinator"
PLATFORMS = [Platform.SENSOR, Platform.NUMBER]
CONFIG_VERSION = 5

EVENT_ALERT_CREATED = f"{DOMAIN}_alert_created"
EVENT_ALERT_UPDATED = f"{DOMAIN}_alert_updated"
EVENT_ALERT_CLEARED = f"{DOMAIN}_alert_cleared"
EVENT_ALERT_STALE_DATA = f"{DOMAIN}_alert_stale_data"
