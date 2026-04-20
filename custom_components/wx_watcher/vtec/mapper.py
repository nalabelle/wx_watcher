"""VTEC code mapper — inflates raw codes to human-readable strings.

All functions return the raw code string as a fallback for unknown inputs.
No exceptions are raised from this module — it is display logic, not
safety-critical.
"""

from custom_components.wx_watcher.vtec.codes import (
    VTEC_ACTION_NAMES,
    VTEC_PHENOMENA_NAMES,
    VTEC_SIGNIFICANCE_NAMES,
)
from custom_components.wx_watcher.vtec.parser import VTECTokens


def significance_name(code: str) -> str:
    """Return the human-readable name for a VTEC significance code."""
    return VTEC_SIGNIFICANCE_NAMES.get(code, code)


def action_name(code: str) -> str:
    """Return the human-readable verb for a VTEC action code."""
    return VTEC_ACTION_NAMES.get(code, code)


def phenomena_name(code: str) -> str:
    """Return the human-readable name for a VTEC phenomena code."""
    return VTEC_PHENOMENA_NAMES.get(code, code)


def describe_significance(tokens: VTECTokens) -> str:
    """Return '{phenomena_name} {significance_name}' for the token pair.

    Special case: phenomena FW + significance A → 'Fire Weather Watch'
    (matches pyIEM's get_ps_string convention).
    """
    if tokens.significance == "A" and tokens.phenomena == "FW":
        return "Fire Weather Watch"
    return f"{phenomena_name(tokens.phenomena)} {significance_name(tokens.significance)}"


def describe_action(tokens: VTECTokens) -> str:
    """Return '{action_name} {describe_significance}' for the token set."""
    return f"{action_name(tokens.action)} {describe_significance(tokens)}"
