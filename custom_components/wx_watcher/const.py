"""Constants for WX Watcher."""

# Derived in part from nws_alerts by finity69x2
# (https://github.com/finity69x2/nws_alerts), which is derived from
# nws_custom_component by eracknaphobia
# (https://github.com/eracknaphobia/nws_custom_component).
# Neither upstream project includes a license. See NOTICE for details.
# As upstream-derived code is rewritten or removed, this comment should
# be updated or removed accordingly.

from homeassistant.const import Platform

# API
API_ENDPOINT = "https://api.weather.gov"
USER_AGENT = "wx_watcher homeassistant {}"

# Config
CONF_TIMEOUT = "timeout"
CONF_INTERVAL = "interval"

# Location config
CONF_LOCATIONS = "locations"
CONF_LOCATION_NAME = "name"
CONF_LOCATION_TYPE = "type"
CONF_LOCATION_MODE = "mode"
CONF_LOCATION_GPS = "gps"
CONF_LOCATION_ZONE = "zone"
CONF_LOCATION_TRACKER = "tracker"

# Location types
LOCATION_TYPE_STATIC = "static"
LOCATION_TYPE_TRACKED = "tracked"

# Location modes
LOCATION_MODE_ZONE = "zone"
LOCATION_MODE_POINT = "point"

# Defaults
DEFAULT_ICON = "mdi:alert"
DEFAULT_NAME = "WX Watcher"
DEFAULT_INTERVAL = 1
DEFAULT_TIMEOUT = 120

# Event attributes
EVENT_ATTR_CONFIG_ENTRY_ID = "config_entry_id"
EVENT_ATTR_SOURCES = "sources"

# Misc
VERSION = "7.0.1"
ISSUE_URL = "https://github.com/nalabelle/wx_watcher"
DOMAIN = "wx_watcher"
PLATFORM = "sensor"
ATTRIBUTION = "Data provided by Weather.gov"
COORDINATOR = "coordinator"
PLATFORMS = [Platform.SENSOR]
CONFIG_VERSION = 3

EVENT_ALERT_CREATED = f"{DOMAIN}_alert_created"
EVENT_ALERT_UPDATED = f"{DOMAIN}_alert_updated"
EVENT_ALERT_CLEARED = f"{DOMAIN}_alert_cleared"
EVENT_ALERT_STALE_DATA = f"{DOMAIN}_alert_stale_data"
