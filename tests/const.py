"""Constants for tests."""

from custom_components.wx_watcher.const import (
    CONF_LOCATION_GPS,
    CONF_LOCATION_HA_ZONE,
    CONF_LOCATION_MODE,
    CONF_LOCATION_TRACKER,
    CONF_LOCATION_TYPE,
    CONF_LOCATION_ZONE,
    LOCATION_MODE_POINT,
    LOCATION_MODE_ZONE,
    LOCATION_TYPE_STATIC,
    LOCATION_TYPE_TRACKED,
)

CONFIG_DATA = {
    "name": "WX Watcher",
    "interval": 60,
    "timeout": 60,
    "locations": [
        {
            CONF_LOCATION_TYPE: LOCATION_TYPE_STATIC,
            CONF_LOCATION_MODE: LOCATION_MODE_ZONE,
            CONF_LOCATION_GPS: "33.25,-112.30",
            CONF_LOCATION_ZONE: "AZZ540,AZC013",
            CONF_LOCATION_HA_ZONE: "zone.home",
        },
    ],
}

CONFIG_DATA_TWO_LOCATIONS = {
    "name": "WX Watcher",
    "interval": 60,
    "timeout": 60,
    "locations": [
        {
            CONF_LOCATION_TYPE: LOCATION_TYPE_STATIC,
            CONF_LOCATION_MODE: LOCATION_MODE_ZONE,
            CONF_LOCATION_GPS: "33.25,-112.30",
            CONF_LOCATION_ZONE: "AZZ540,AZC013",
            CONF_LOCATION_HA_ZONE: "zone.home",
        },
        {
            CONF_LOCATION_TYPE: LOCATION_TYPE_STATIC,
            CONF_LOCATION_MODE: LOCATION_MODE_POINT,
            CONF_LOCATION_GPS: "33.45,-112.06",
            CONF_LOCATION_ZONE: "",
            CONF_LOCATION_HA_ZONE: "zone.work",
        },
    ],
}

CONFIG_DATA_POINT_ONLY = {
    "name": "WX Watcher",
    "interval": 60,
    "timeout": 60,
    "locations": [
        {
            CONF_LOCATION_TYPE: LOCATION_TYPE_STATIC,
            CONF_LOCATION_MODE: LOCATION_MODE_POINT,
            CONF_LOCATION_GPS: "33.25,-112.30",
            CONF_LOCATION_ZONE: "",
            CONF_LOCATION_HA_ZONE: "zone.home",
        },
    ],
}

CONFIG_DATA_TRACKER_IN_STATIC_ZONE = {
    "name": "WX Watcher",
    "interval": 60,
    "timeout": 60,
    "locations": [
        {
            CONF_LOCATION_TYPE: LOCATION_TYPE_STATIC,
            CONF_LOCATION_MODE: LOCATION_MODE_ZONE,
            CONF_LOCATION_GPS: "33.25,-112.30",
            CONF_LOCATION_ZONE: "AZZ540,AZC013",
            CONF_LOCATION_HA_ZONE: "zone.home",
        },
        {
            CONF_LOCATION_TYPE: LOCATION_TYPE_TRACKED,
            CONF_LOCATION_MODE: LOCATION_MODE_POINT,
            CONF_LOCATION_GPS: "",
            CONF_LOCATION_ZONE: "",
            CONF_LOCATION_TRACKER: "device_tracker.phone",
        },
    ],
}
