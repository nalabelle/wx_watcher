"""VTEC string parser with strict validation.

Parses a raw VTEC string into a VTECTokens NamedTuple, validating every
field against the NWS VTEC specification. Raises VTECParseError on any
deviation — this is safety-critical weather alert data and silent
misclassification is unacceptable.
"""

from datetime import UTC, datetime
import logging
import re
from typing import NamedTuple

from custom_components.wx_watcher.vtec.codes import (
    VTEC_ACTION_CODES,
    VTEC_OFFICE_RE,
    VTEC_PHENOMENA_CODES,
    VTEC_PHENOMENA_RE,
    VTEC_RE,
    VTEC_SIGNIFICANCE_CODES,
    VTEC_STATUS_CODES,
    VTEC_TIMESTAMP_FORMAT,
    VTEC_TIMESTAMP_UNDEFINED,
)

_LOGGER = logging.getLogger(__name__)


class VTECParseError(ValueError):
    """Raised when a VTEC string fails spec validation."""


class VTECTokens(NamedTuple):
    """Parsed and validated VTEC fields — all raw codes, no inflation."""

    status: str
    action: str
    office: str
    phenomena: str
    significance: str
    etn: int
    begints: str
    endts: str


def parse_vtec(vtec_string: str) -> VTECTokens:
    """Parse and strictly validate a VTEC string.

    Returns VTECTokens with all fields validated against the spec.
    Raises VTECParseError on any deviation from the expected format.
    """
    match = re.match(VTEC_RE, vtec_string)
    if not match:
        raise VTECParseError(f"VTEC string does not match expected format: {vtec_string!r}")

    status = match.group(2)
    action = match.group(3)
    office = match.group(4)
    phenomena = match.group(5)
    significance = match.group(6)
    etn_raw = match.group(7)
    begints = match.group(8)
    endts = match.group(9)

    _validate_status(vtec_string, status)
    _validate_action(vtec_string, action)
    _validate_office(vtec_string, office)
    _validate_phenomena(vtec_string, phenomena)
    _validate_significance(vtec_string, significance)
    etn = _validate_etn(vtec_string, etn_raw)
    _validate_timestamp(vtec_string, begints, "begin")
    _validate_timestamp(vtec_string, endts, "end")

    return VTECTokens(
        status=status,
        action=action,
        office=office,
        phenomena=phenomena,
        significance=significance,
        etn=etn,
        begints=begints,
        endts=endts,
    )


def _validate_status(vtec_string: str, status: str) -> None:
    if status not in VTEC_STATUS_CODES:
        raise VTECParseError(
            f"Invalid VTEC status {status!r} in {vtec_string!r}; "
            f"expected one of {sorted(VTEC_STATUS_CODES)}"
        )


def _validate_action(vtec_string: str, action: str) -> None:
    if action not in VTEC_ACTION_CODES:
        raise VTECParseError(
            f"Invalid VTEC action {action!r} in {vtec_string!r}; "
            f"expected one of {sorted(VTEC_ACTION_CODES)}"
        )


def _validate_office(vtec_string: str, office: str) -> None:
    if not VTEC_OFFICE_RE.match(office):
        raise VTECParseError(
            f"Invalid VTEC office {office!r} in {vtec_string!r}; "
            f"expected 4 uppercase letters (e.g. KPSR)"
        )


def _validate_phenomena(vtec_string: str, phenomena: str) -> None:
    if not VTEC_PHENOMENA_RE.match(phenomena):
        raise VTECParseError(
            f"Invalid VTEC phenomena {phenomena!r} in {vtec_string!r}; "
            f"expected 2 uppercase letters (e.g. EH)"
        )
    if phenomena not in VTEC_PHENOMENA_CODES:
        _LOGGER.warning(
            "Unknown VTEC phenomena code %r in %r — not in known codes list; "
            "parsing will proceed but this may indicate a new NWS phenomena code",
            phenomena,
            vtec_string,
        )


def _validate_significance(vtec_string: str, significance: str) -> None:
    if significance not in VTEC_SIGNIFICANCE_CODES:
        raise VTECParseError(
            f"Invalid VTEC significance {significance!r} in {vtec_string!r}; "
            f"expected one of {sorted(VTEC_SIGNIFICANCE_CODES)}"
        )


def _validate_etn(vtec_string: str, etn_raw: str) -> int:
    try:
        etn = int(etn_raw)
    except ValueError as err:
        raise VTECParseError(
            f"Invalid VTEC ETN {etn_raw!r} in {vtec_string!r}; expected non-negative integer"
        ) from err
    if etn < 0:
        raise VTECParseError(
            f"Negative VTEC ETN {etn} in {vtec_string!r}; expected non-negative integer"
        )
    return etn


def _validate_timestamp(vtec_string: str, ts: str, label: str) -> None:
    if ts == VTEC_TIMESTAMP_UNDEFINED:
        return
    try:
        dt = datetime.strptime(ts, VTEC_TIMESTAMP_FORMAT)
    except ValueError as err:
        raise VTECParseError(
            f"Invalid VTEC {label} timestamp {ts!r} in {vtec_string!r}; "
            f"expected format {VTEC_TIMESTAMP_FORMAT!r} or "
            f"sentinel {VTEC_TIMESTAMP_UNDEFINED!r}"
        ) from err
    dt = dt.replace(tzinfo=UTC)
    if dt.year < 1971:
        raise VTECParseError(
            f"VTEC {label} timestamp {ts!r} in {vtec_string!r} resolves to "
            f"year {dt.year}; years before 1971 are rejected "
            f"(known NWS data bug)"
        )
