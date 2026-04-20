"""Tests for the VTEC parsing and mapping package."""

import logging

import pytest

from custom_components.wx_watcher.vtec import (
    VTECParseError,
    action_name,
    describe_action,
    describe_significance,
    parse_vtec,
    phenomena_name,
    significance_name,
)
from custom_components.wx_watcher.vtec.codes import (
    VTEC_ACTION_CODES,
    VTEC_PHENOMENA_CODES,
    VTEC_SIGNIFICANCE_CODES,
)

FIXTURE_VTEC = "/O.CON.KPSR.EH.W.0006.240719T1700Z-240721T0300Z/"
TEST_DATA_VTEC = "/O.NEW.KTST.TW.Y.0001.240719T1700Z-240721T0300Z/"


def _build_vtec(
    status="O",
    action="NEW",
    office="KPSR",
    phenomena="EH",
    significance="W",
    etn="0001",
    begints="240719T1700Z",
    endts="240721T0300Z",
):
    return f"/{status}.{action}.{office}.{phenomena}.{significance}.{etn}.{begints}-{endts}/"


class TestParseValid:
    """Tests for parsing valid VTEC strings."""

    def test_parse_fixture_vtec(self):
        """Full parse of api.json fixture VTEC string."""
        tokens = parse_vtec(FIXTURE_VTEC)
        assert tokens.status == "O"
        assert tokens.action == "CON"
        assert tokens.office == "KPSR"
        assert tokens.phenomena == "EH"
        assert tokens.significance == "W"
        assert tokens.etn == 6
        assert tokens.begints == "240719T1700Z"
        assert tokens.endts == "240721T0300Z"

    def test_parse_test_data_vtec(self):
        """Parse test_api.py VTEC string with significance Y."""
        tokens = parse_vtec(TEST_DATA_VTEC)
        assert tokens.significance == "Y"
        assert tokens.action == "NEW"
        assert tokens.office == "KTST"
        assert tokens.phenomena == "TW"
        assert tokens.etn == 1

    def test_parse_all_significance_codes(self):
        """Every known significance code should parse successfully."""
        for sig in VTEC_SIGNIFICANCE_CODES:
            vtec = _build_vtec(significance=sig)
            tokens = parse_vtec(vtec)
            assert tokens.significance == sig

    def test_parse_all_action_codes(self):
        """Every known action code should parse successfully."""
        for action in VTEC_ACTION_CODES:
            vtec = _build_vtec(action=action)
            tokens = parse_vtec(vtec)
            assert tokens.action == action

    def test_parse_all_known_phenomena(self):
        """Every known phenomena code should parse successfully."""
        for phen in VTEC_PHENOMENA_CODES:
            vtec = _build_vtec(phenomena=phen)
            tokens = parse_vtec(vtec)
            assert tokens.phenomena == phen

    def test_parse_undefined_begin_timestamp(self):
        """Undefined begin timestamp sentinel should be accepted."""
        vtec = _build_vtec(begints="00000000T0000Z")
        tokens = parse_vtec(vtec)
        assert tokens.begints == "00000000T0000Z"

    def test_parse_undefined_end_timestamp(self):
        """Undefined end timestamp sentinel should be accepted."""
        vtec = _build_vtec(endts="00000000T0000Z")
        tokens = parse_vtec(vtec)
        assert tokens.endts == "00000000T0000Z"

    def test_parse_both_undefined_timestamps(self):
        """Both timestamps as undefined sentinels should be accepted."""
        vtec = _build_vtec(begints="00000000T0000Z", endts="00000000T0000Z")
        tokens = parse_vtec(vtec)
        assert tokens.begints == "00000000T0000Z"
        assert tokens.endts == "00000000T0000Z"


class TestParseInvalid:
    """Tests for VTECParseError on invalid VTEC strings."""

    def test_parse_no_regex_match(self):
        """Garbage string should raise VTECParseError."""
        with pytest.raises(VTECParseError, match="does not match expected format"):
            parse_vtec("not-a-vtec-string")

    def test_parse_empty_string(self):
        """Empty string should raise VTECParseError."""
        with pytest.raises(VTECParseError, match="does not match expected format"):
            parse_vtec("")

    def test_parse_bad_status(self):
        """Invalid status letter should raise VTECParseError."""
        vtec = _build_vtec(status="Z")
        with pytest.raises(VTECParseError, match="Invalid VTEC status"):
            parse_vtec(vtec)

    def test_parse_bad_action(self):
        """Unknown action code should raise VTECParseError."""
        vtec = _build_vtec(action="XXX")
        with pytest.raises(VTECParseError, match="Invalid VTEC action"):
            parse_vtec(vtec)

    def test_parse_bad_office_short(self):
        """Too-short office should raise VTECParseError."""
        vtec = _build_vtec(office="KP")
        with pytest.raises(VTECParseError, match="Invalid VTEC office"):
            parse_vtec(vtec)

    def test_parse_bad_office_lowercase(self):
        """Lowercase office should fail regex match."""
        vtec = _build_vtec(office="kpsr")
        with pytest.raises(VTECParseError, match="does not match expected format"):
            parse_vtec(vtec)

    def test_parse_bad_significance(self):
        """Unknown significance code should raise VTECParseError."""
        vtec = _build_vtec(significance="Z")
        with pytest.raises(VTECParseError, match="Invalid VTEC significance"):
            parse_vtec(vtec)

    def test_parse_invalid_begin_timestamp_format(self):
        """Non-numeric begin timestamp should fail regex match."""
        vtec = _build_vtec(begints="garbage")
        with pytest.raises(VTECParseError, match="does not match expected format"):
            parse_vtec(vtec)

    def test_parse_invalid_end_timestamp_format(self):
        """Non-numeric end timestamp should fail regex match."""
        vtec = _build_vtec(endts="not-a-time")
        with pytest.raises(VTECParseError, match="does not match expected format"):
            parse_vtec(vtec)

    def test_parse_pre1971_timestamp(self):
        """Pre-1971 timestamp should raise VTECParseError."""
        vtec = _build_vtec(begints="691231T0000Z")
        with pytest.raises(VTECParseError, match="year 1969"):
            parse_vtec(vtec)

    def test_parse_bad_phenomena_format(self):
        """3-character phenomena should raise VTECParseError."""
        vtec = _build_vtec(phenomena="ABC")
        with pytest.raises(VTECParseError, match="Invalid VTEC phenomena"):
            parse_vtec(vtec)

    def test_parse_bad_phenomena_lowercase(self):
        """Lowercase phenomena should fail regex match."""
        vtec = _build_vtec(phenomena="eh")
        with pytest.raises(VTECParseError, match="does not match expected format"):
            parse_vtec(vtec)

    def test_parse_invalid_begin_timestamp_bad_month(self):
        """Timestamp with invalid month should raise VTECParseError."""
        vtec = _build_vtec(begints="241319T1700Z")
        with pytest.raises(VTECParseError, match="begin timestamp"):
            parse_vtec(vtec)

    def test_parse_invalid_end_timestamp_bad_month(self):
        """Timestamp with invalid month should raise VTECParseError."""
        vtec = _build_vtec(endts="241319T1700Z")
        with pytest.raises(VTECParseError, match="end timestamp"):
            parse_vtec(vtec)


class TestParseUnknownPhenomena:
    """Tests for unknown phenomena code handling."""

    def test_parse_unknown_phenomena_warns(self, caplog):
        """Unknown 2-letter phenomena should parse with a warning."""
        vtec = _build_vtec(phenomena="ZZ")
        with caplog.at_level(logging.WARNING, logger="custom_components.wx_watcher.vtec.parser"):
            tokens = parse_vtec(vtec)
        assert tokens.phenomena == "ZZ"
        assert "Unknown VTEC phenomena code 'ZZ'" in caplog.text


class TestMapper:
    """Tests for VTEC code mapper functions."""

    def test_significance_name_known(self):
        """Known significance codes should return human-readable names."""
        assert significance_name("W") == "Warning"
        assert significance_name("A") == "Watch"
        assert significance_name("Y") == "Advisory"

    def test_significance_name_unknown(self):
        """Unknown significance code should return the raw code."""
        assert significance_name("Z") == "Z"

    def test_action_name_known(self):
        """Known action codes should return human-readable verbs."""
        assert action_name("NEW") == "issues"
        assert action_name("CON") == "continues"
        assert action_name("CAN") == "cancels"

    def test_action_name_unknown(self):
        """Unknown action code should return the raw code."""
        assert action_name("XXX") == "XXX"

    def test_phenomena_name_known(self):
        """Known phenomena codes should return human-readable names."""
        assert phenomena_name("EH") == "Excessive Heat"
        assert phenomena_name("TO") == "Tornado"
        assert phenomena_name("FF") == "Flash Flood"

    def test_phenomena_name_unknown(self):
        """Unknown phenomena code should return the raw code."""
        assert phenomena_name("ZZ") == "ZZ"

    def test_describe_significance(self):
        """describe_significance should combine phenomena and significance names."""
        tokens = parse_vtec(FIXTURE_VTEC)
        assert describe_significance(tokens) == "Excessive Heat Warning"

    def test_describe_significance_fw_watch(self):
        """FW+A special case should return Fire Weather Watch."""
        tokens = parse_vtec(_build_vtec(phenomena="FW", significance="A"))
        assert describe_significance(tokens) == "Fire Weather Watch"

    def test_describe_action(self):
        """describe_action should combine action verb with significance description."""
        tokens = parse_vtec(FIXTURE_VTEC)
        assert describe_action(tokens) == "continues Excessive Heat Warning"

    def test_describe_action_new(self):
        """describe_action with NEW should use 'issues' verb."""
        tokens = parse_vtec(_build_vtec(action="NEW"))
        assert describe_action(tokens) == "issues Excessive Heat Warning"
