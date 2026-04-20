"""VTEC specification code tables.

Reference tables derived from pyIEM (akrherz/pyIEM, src/pyiem/nws/vtec.py),
which itself references NWS Instruction 10-1703
(https://www.weather.gov/media/directives/010_pdfs/pd01017003curr.pdf).
"""

import re

VTEC_RE = (
    r"(/([A-Z])\.([A-Z]+)\.([A-Z]+)\.([A-Z]+)\.([A-Z])\."
    r"([0-9]+)\.([0-9TZ]+)-([0-9TZ]+)/)"
)

VTEC_CLASS: dict[str, str] = {
    "O": "Operational",
    "T": "Test",
    "E": "Experimental",
    "X": "Experimental VTEC",
}

VTEC_STATUS_CODES: frozenset[str] = frozenset(VTEC_CLASS)

VTEC_ACTION_NAMES: dict[str, str] = {
    "NEW": "issues",
    "CON": "continues",
    "EXA": "expands area to include",
    "EXT": "extends time of",
    "EXB": "extends time and expands area to include",
    "UPG": "issues upgrade to",
    "CAN": "cancels",
    "EXP": "expires",
    "ROU": "routine",
    "COR": "corrects",
}

VTEC_ACTION_CODES: frozenset[str] = frozenset(VTEC_ACTION_NAMES)

VTEC_SIGNIFICANCE_NAMES: dict[str, str] = {
    "W": "Warning",
    "A": "Watch",
    "Y": "Advisory",
    "S": "Statement",
    "O": "Outlook",
    "N": "Synopsis",
    "F": "Forecast",
}

VTEC_SIGNIFICANCE_CODES: frozenset[str] = frozenset(VTEC_SIGNIFICANCE_NAMES)

VTEC_PHENOMENA_NAMES: dict[str, str] = {
    "AF": "Ashfall",
    "AS": "Air Stagnation",
    "BH": "Beach Hazard",
    "BS": "Blowing Snow",
    "BW": "Brisk Wind",
    "BZ": "Blizzard",
    "CF": "Coastal Flood",
    "CW": "Cold Weather",
    "DF": "Debris Flow",
    "DS": "Dust Storm",
    "DU": "Blowing Dust",
    "EC": "Extreme Cold",
    "EH": "Excessive Heat",
    "EW": "Extreme Wind",
    "FA": "Flood",
    "FF": "Flash Flood",
    "FG": "Dense Fog",
    "FL": "Flood",
    "FR": "Frost",
    "FW": "Red Flag",
    "FZ": "Freeze",
    "UP": "Freezing Spray",
    "GL": "Gale",
    "HF": "Hurricane Force Wind",
    "HI": "Inland Hurricane",
    "HS": "Heavy Snow",
    "HT": "Heat",
    "HU": "Hurricane",
    "HW": "High Wind",
    "HY": "Hydrologic",
    "HZ": "Hard Freeze",
    "IP": "Sleet",
    "IS": "Ice Storm",
    "LB": "Lake Effect Snow and Blowing Snow",
    "LE": "Lake Effect Snow",
    "LO": "Low Water",
    "LS": "Lakeshore Flood",
    "LW": "Lake Wind",
    "MA": "Marine",
    "MF": "Marine Dense Fog",
    "MH": "Marine Ashfall",
    "MS": "Marine Dense Smoke",
    "RB": "Small Craft for Rough",
    "RP": "Rip Currents",
    "SB": "Snow and Blowing",
    "SC": "Small Craft",
    "SE": "Hazardous Seas",
    "SI": "Small Craft for Winds",
    "SM": "Dense Smoke",
    "SN": "Snow",
    "SQ": "Snow Squall",
    "SR": "Storm",
    "SS": "Storm Surge",
    "SU": "High Surf",
    "SV": "Severe Thunderstorm",
    "SW": "Small Craft for Hazardous Seas",
    "TI": "Inland Tropical Storm",
    "TO": "Tornado",
    "TR": "Tropical Storm",
    "TS": "Tsunami",
    "TY": "Typhoon",
    "WC": "Wind Chill",
    "WI": "Wind",
    "WS": "Winter Storm",
    "WW": "Winter Weather",
    "XH": "Extreme Heat",
    "ZF": "Freezing Fog",
    "ZR": "Freezing Rain",
}

VTEC_PHENOMENA_CODES: frozenset[str] = frozenset(VTEC_PHENOMENA_NAMES)

VTEC_TIMESTAMP_UNDEFINED = "00000000T0000Z"
VTEC_TIMESTAMP_FORMAT = "%y%m%dT%H%MZ"
VTEC_OFFICE_RE = re.compile(r"^[A-Z]{4}$")
VTEC_PHENOMENA_RE = re.compile(r"^[A-Z]{2}$")
