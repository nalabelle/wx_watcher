# WX Watcher

A Home Assistant custom integration for monitoring weather alerts from the US National Weather Service.

**Derived in part from [nws_alerts](https://github.com/finity69x2/nws_alerts) by finity69x2 and [nws_custom_component](https://github.com/eracknaphobia/nws_custom_component) by eracknaphobia. See [NOTICE](NOTICE) for details.**

## Features

- **Entity-based locations** — static locations are HA zones, tracked locations are device trackers
- **Automatic zone resolution** — NWS zone IDs are auto-resolved from zone GPS coordinates and editable
- **Tracker skip optimization** — tracked devices inside a static location's HA zone are skipped (zone query is a superset)
- **Deduplicated alerts** — same alert observed from multiple locations fires one event, with a `sources` list showing which locations detected it
- **Combined zone queries** — all zone-mode locations are queried in a single API call, minimizing NWS API usage
- **Event-driven architecture** — fires `wx_watcher_alert_created`, `wx_watcher_alert_updated`, `wx_watcher_alert_cleared`, and `wx_watcher_alert_stale_data` events for precise automation triggers
- **Dashboard sensor** — `sensor.wx_watcher_alerts` shows current alert count with full details in attributes; `sensor.wx_watcher_last_updated` shows the last successful update time

## Installation

### HACS

1. Open HACS in Home Assistant
2. Search for "WX Watcher"
3. Click Download

### Manual

1. Copy the `custom_components/wx_watcher/` directory into your `custom_components/` folder
2. Restart Home Assistant

## Configuration

Go to **Settings → Devices & Services → Add Integration** and search for "WX Watcher".

### Setup Flow

1. **Name & Settings** — Enter a name (e.g., "WX Watcher"), update interval, and timeout
2. **Locations Hub** — Add static locations or tracked devices, or finish setup
3. **Add Static Location** — Select an HA zone. NWS zone IDs are automatically resolved. You can edit them after resolution.
4. **Add Tracked Device** — Select a device tracker entity and choose zone or point mode

### Location Types

| Type        | Description                                   |
| ----------- | --------------------------------------------- |
| **Static**  | Always-monitored HA zone (home, work, school) |
| **Tracked** | Follows a device_tracker entity (phone, car)  |

### Query Modes

| Mode      | Behavior                                                                                                                                                    |
| --------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Zone**  | Queries all alerts listed for the resolved NWS zones. Broader coverage — includes alerts that may not cover your exact point.                               |
| **Point** | Queries only alerts whose polygon covers your exact GPS coordinates. More precise — filters out zone-wide alerts that don't actually include your location. |

## Event Schema

Events are fired for each unique alert (deduplicated across locations):

| Event                         | When                          |
| ----------------------------- | ----------------------------- |
| `wx_watcher_alert_created`    | New alert appears             |
| `wx_watcher_alert_updated`    | Existing alert's data changes |
| `wx_watcher_alert_cleared`    | Alert is no longer active     |
| `wx_watcher_alert_stale_data` | NWS API fetch failed          |

### Event Data

Each event carries these fields:

| Field                                           | Description                                                                                                                                                     |
| ----------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `Event`                                         | Alert type (e.g., "Excessive Heat Warning")                                                                                                                     |
| `ID`                                            | Stable UUID for the alert                                                                                                                                       |
| `URL`                                           | NWS alert URL                                                                                                                                                   |
| `Headline`                                      | NWS headline text                                                                                                                                               |
| `Type`                                          | Alert type (Alert, Update, Cancel, etc.)                                                                                                                        |
| `NWSCode`                                       | NWS event code                                                                                                                                                  |
| `Status`                                        | Alert status                                                                                                                                                    |
| `Severity`                                      | Severity level                                                                                                                                                  |
| `Certainty`                                     | Certainty level                                                                                                                                                 |
| `Urgency`                                       | Urgency level                                                                                                                                                   |
| `Response`                                      | Recommended response                                                                                                                                            |
| `AreasAffected`                                 | Area description                                                                                                                                                |
| `Description`                                   | Full alert description                                                                                                                                          |
| `Instruction`                                   | Recommended actions                                                                                                                                             |
| `Sent`, `Onset`, `Expires`, `Ends`, `Effective` | Timestamps                                                                                                                                                      |
| `VTEC`, `VTECAction`                            | VTEC codes                                                                                                                                                      |
| `Significance`                                  | VTEC significance code (`W` = Warning, `A` = Watch, `Y` = Advisory, `S` = Statement, `O` = Outlook, `N` = Synopsis, `F` = Forecast). Empty for non-VTEC alerts. |
| `References`                                    | Referenced previous alerts                                                                                                                                      |
| `SenderName`                                    | Issuing NWS office                                                                                                                                              |
| `config_entry_id`                               | Config entry that fired the event                                                                                                                               |
| `sources`                                       | List of source dicts. Static: `{"ha_zone": "zone.home", "mode": "zone"}`. Tracked: `{"tracker": "device_tracker.phone", "mode": "point"}`.                      |

### Automation Example

No dedup condition is needed — the integration already deduplicates:

```yaml
automation:
  - alias: WX Watcher → Notifications
    trigger:
      - trigger: event
        event_type: wx_watcher_alert_created
    condition:
      - condition: template
        value_template: >-
          {{ 'zone.home' in
            (trigger.event.data.sources | map(attribute='ha_zone') | list) }}
    action:
      - action: notify.mobile_phone
        data:
          title: "{{ trigger.event.data.Event }}"
          message: "{{ trigger.event.data.Headline }}"
          data:
            url: "{{ trigger.event.data.URL }}"
```

## Blueprints

### WX Watcher → Ticker

An automation blueprint that routes WX Watcher alert notifications based on
static locations (HA zones) and tracked devices. Import multiple times for
different users or notification targets.

The integration automatically skips NWS queries for tracked devices that are
currently inside a configured static location's HA zone, since the zone query
is a superset. No duplicate queries or redundant notifications.

**Import:** Paste this URL in **Settings → Automations & scenes → Blueprints → Import Blueprint**:

```
https://github.com/nalabelle/wx_watcher/blob/main/blueprints/automation/wx_watcher_ticker.yaml
```

To update, re-import the blueprint from the same URL.

**Inputs:**

| Input             | Description                                                |
| ----------------- | ---------------------------------------------------------- |
| Static Locations  | One or more HA zones to monitor                            |
| Tracked Devices   | One or more device tracker entities to follow              |
| Warning Category  | Category for Warning alerts (default: `Weather Warning`)   |
| Watch Category    | Category for Watch alerts (default: `Weather Watch`)       |
| Advisory Category | Category for Advisory alerts (default: `Weather Advisory`) |

## Sensors

| Entity                           | State                            | Attributes                                                                           |
| -------------------------------- | -------------------------------- | ------------------------------------------------------------------------------------ |
| `sensor.wx_watcher_alerts`       | Number of active alerts          | `Alerts` (full list with sources), `locations` (configured locations), `attribution` |
| `sensor.wx_watcher_last_updated` | Last successful update timestamp | `attribution`                                                                        |

## Breaking Changes from v7

- **You must delete your old config entries and reconfigure** — the data model is incompatible
- Location names removed — locations are now defined by HA zone entities (static) or device tracker entities (tracked)
- Event source data uses `ha_zone` and `tracker` keys instead of `location`
- Manual GPS and manual NWS zone ID source options removed — all static locations start from an HA zone
- NWS zone IDs are auto-resolved but editable
- Tracked devices inside a static location's HA zone are automatically skipped (zone query is a superset)

## Attribution

This integration is derived from [nws_alerts](https://github.com/finity69x2/nws_alerts) by finity69x2, which is derived from [nws_custom_component](https://github.com/eracknaphobia/nws_custom_component) by eracknaphobia. Neither upstream project includes a license. See [NOTICE](NOTICE) for the full provenance inventory.
