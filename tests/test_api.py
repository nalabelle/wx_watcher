"""Test NWS API client functions."""

from custom_components.wx_watcher.api import generate_id, parse_alert


def test_generate_id():
    """Test alert ID generation is stable and deterministic."""
    url = "https://api.weather.gov/alerts/urn:oid:2.49.0.1.840.0.505a7220d91b00eb1d75a3fb4f339f825496a522.004.1"
    id1 = generate_id(url)
    id2 = generate_id(url)
    assert id1 == id2
    assert isinstance(id1, str)
    assert len(id1) == 36  # UUID format


def test_parse_alert():
    """Test parsing a raw NWS alert feature."""
    raw = {
        "id": "https://api.weather.gov/alerts/urn:oid:test",
        "type": "Feature",
        "geometry": None,
        "properties": {
            "@id": "https://api.weather.gov/alerts/urn:oid:test",
            "@type": "wx:Alert",
            "id": "urn:oid:test",
            "areaDesc": "Test Area",
            "geocode": {
                "SAME": ["004013"],
                "UGC": ["AZZ540", "AZC013"],
            },
            "affectedZones": [],
            "references": [],
            "sent": "2024-07-18T12:47:00-07:00",
            "effective": "2024-07-18T12:47:00-07:00",
            "onset": "2024-07-19T10:00:00-07:00",
            "expires": "2024-07-19T03:00:00-07:00",
            "ends": "2024-07-20T20:00:00-07:00",
            "status": "Actual",
            "messageType": "Alert",
            "severity": "Severe",
            "certainty": "Likely",
            "urgency": "Expected",
            "event": "Test Warning",
            "eventCode": {"NationalWeatherService": ["TW"]},
            "sender": "w-nws.webmaster@noaa.gov",
            "senderName": "NWS Test",
            "headline": "Test Warning issued",
            "description": "Test description",
            "instruction": "Test instruction",
            "response": "Execute",
            "parameters": {
                "NWSheadline": ["TEST WARNING"],
                "VTEC": ["/O.NEW.KTST.TW.Y.0001.240719T1700Z-240721T0300Z/"],
            },
        },
    }

    result = parse_alert(raw)
    assert result is not None
    assert result["Event"] == "Test Warning"
    assert result["ID"] == generate_id("https://api.weather.gov/alerts/urn:oid:test")
    assert result["Severity"] == "Severe"
    assert result["_ugc"] == ["AZZ540", "AZC013"]
    assert result["VTECAction"] == "NEW"


def test_parse_alert_missing_properties():
    """Test parsing an alert with missing properties returns None."""
    raw = {"type": "Feature"}
    result = parse_alert(raw)
    assert result is None


def test_parse_alert_missing_id():
    """Test parsing an alert with missing id returns None."""
    raw = {
        "type": "Feature",
        "properties": {"event": "Test"},
    }
    result = parse_alert(raw)
    assert result is None
