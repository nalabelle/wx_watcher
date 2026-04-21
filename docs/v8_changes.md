# WX Watcher v8 Changes

## Entity-Based Locations

Locations are now defined by Home Assistant entities instead of free-text names:

- **Static locations** are HA zone entities (e.g., `zone.home`, `zone.work`)
- **Tracked locations** are device tracker entities (e.g., `device_tracker.phone`)

The free-text `name` field has been removed. Friendly names are derived from
entity state at display time.

## Event Source Data

Event `sources` now use entity IDs:

- Static: `{"ha_zone": "zone.home", "mode": "zone"}`
- Tracked: `{"tracker": "device_tracker.phone", "mode": "point"}`

The `location` key has been removed.

## Tracker Skip Optimization

When a tracked device's state indicates it is inside a static location's HA zone
(e.g., device_tracker state is `"zone.home"` when `zone.home` is a static location),
the coordinator skips the tracked device's NWS API query entirely. The static
location's zone query is a superset — it already covers the area.

This means:

- When phone is at home: only the home zone query runs. Events carry
  `ha_zone: zone.home` in sources, never both `ha_zone` and `tracker`.
- When phone is away: both queries run. Home events carry `ha_zone`,
  phone events carry `tracker`. These are different alerts (different IDs)
  for different geographic areas.

> **Bug fix:** The initial implementation compared tracker state against
> stripped zone slugs (`"home"`) instead of full entity IDs (`"zone.home"`),
> so the skip check never matched. This has been corrected — the coordinator
> now stores full entity IDs in the static-zone set, matching the format
> that device_tracker entities report.

## Config Flow Changes

- Removed manual GPS and manual NWS zone ID source options
- All static locations start from an HA zone entity
- NWS zone IDs are auto-resolved but editable via the form
- Zone IDs are deduplicated on save
- Added edit and remove location flows
- Device trackers use entity selector instead of raw dropdown
- Location names are no longer configurable (derived from entity friendly name)

## Blueprint

See `blueprints/automation/wx_watcher_ticker.yaml` — routes alert notifications
per-user based on static locations and tracked devices. Supports multiple zones
and multiple devices per automation instance.

## VTEC Significance Field

Alert events now include a `Significance` field extracted from the NWS VTEC string.
This is the VTEC significance code — `W` for Warning, `A` for Watch, `Y` for
Advisory, etc. — and is more reliable than text-matching the `Event` field.

The blueprint now routes alerts by `Significance` code instead of substring
matching on `Event`. Non-VTEC alerts (e.g., Air Quality Alert) have an empty
`Significance` and fall to the default advisory category.

A new `vtec/` subpackage provides strict VTEC parsing with full spec validation.
Any deviation from the expected format raises `VTECParseError` with detailed
diagnostics — no silent fallback on safety-critical alert data.

## GPS Input Guard

The coordinator now guards against empty or malformed GPS coordinates for
tracked devices and point-mode locations. Previously, `_parse_gps()` could
crash the entire update cycle on bad input. It now logs a warning and skips
the affected location.
