"""VTEC parsing and mapping package.

Provides strict VTEC string parsing, specification code tables, and
human-readable code inflation. Designed to be splittable as a standalone
package — no Home Assistant dependencies.
"""

from custom_components.wx_watcher.vtec.codes import (
    VTEC_ACTION_CODES,
    VTEC_ACTION_NAMES,
    VTEC_CLASS,
    VTEC_PHENOMENA_CODES,
    VTEC_PHENOMENA_NAMES,
    VTEC_SIGNIFICANCE_CODES,
    VTEC_SIGNIFICANCE_NAMES,
    VTEC_STATUS_CODES,
)
from custom_components.wx_watcher.vtec.mapper import (
    action_name,
    describe_action,
    describe_significance,
    phenomena_name,
    significance_name,
)
from custom_components.wx_watcher.vtec.parser import VTECParseError, VTECTokens, parse_vtec

__all__ = [
    "VTEC_ACTION_CODES",
    "VTEC_ACTION_NAMES",
    "VTEC_CLASS",
    "VTEC_PHENOMENA_CODES",
    "VTEC_PHENOMENA_NAMES",
    "VTEC_SIGNIFICANCE_CODES",
    "VTEC_SIGNIFICANCE_NAMES",
    "VTEC_STATUS_CODES",
    "VTECParseError",
    "VTECTokens",
    "action_name",
    "describe_action",
    "describe_significance",
    "parse_vtec",
    "phenomena_name",
    "significance_name",
]
