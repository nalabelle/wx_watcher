# WX Watcher

A Home Assistant custom integration for monitoring weather alerts from the US National Weather Service.

**Derived in part from [nws_alerts](https://github.com/finity69x2/nws_alerts) by finity69x2 and [nws_custom_component](https://github.com/eracknaphobia/nws_custom_component) by eracknaphobia. See [NOTICE](NOTICE) for details.**

## Features

- **Multi-location monitoring** — configure multiple static locations (home, work, school) and tracked devices (phone, car) in a single config entry
- **Zone and point modes** — each location uses zone queries (broader coverage) or point queries (precise, polygon-based) based on your preference
- **Automatic zone resolution** — GPS coordinates or Home Assistant zones are automatically resolved to NWS forecast, county, and fire weather zones
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
3. **Add Static Location** — Choose from:
   - **Home Assistant zone** — pick a zone from your HA config (auto-resolves GPS and NWS zones)
   - **Manual GPS** — enter latitude,longitude coordinates
   - **Manual zone IDs** — enter NWS zone/county codes directly
4. **Add Tracked Device** — Select a device tracker entity and choose zone or point mode

### Location Types

| Type        | Description                                          |
| ----------- | ---------------------------------------------------- |
| **Static**  | Always-monitored fixed location (home, work, school) |
| **Tracked** | Follows a device_tracker entity (phone, car)         |

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

| Field                                           | Description                                                                                    |
| ----------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| `Event`                                         | Alert type (e.g., "Excessive Heat Warning")                                                    |
| `ID`                                            | Stable UUID for the alert                                                                      |
| `URL`                                           | NWS alert URL                                                                                  |
| `Headline`                                      | NWS headline text                                                                              |
| `Type`                                          | Alert type (Alert, Update, Cancel, etc.)                                                       |
| `NWSCode`                                       | NWS event code                                                                                 |
| `Status`                                        | Alert status                                                                                   |
| `Severity`                                      | Severity level                                                                                 |
| `Certainty`                                     | Certainty level                                                                                |
| `Urgency`                                       | Urgency level                                                                                  |
| `Response`                                      | Recommended response                                                                           |
| `AreasAffected`                                 | Area description                                                                               |
| `Description`                                   | Full alert description                                                                         |
| `Instruction`                                   | Recommended actions                                                                            |
| `Sent`, `Onset`, `Expires`, `Ends`, `Effective` | Timestamps                                                                                     |
| `VTEC`, `VTECAction`                            | VTEC codes                                                                                     |
| `References`                                    | Referenced previous alerts                                                                     |
| `SenderName`                                    | Issuing NWS office                                                                             |
| `config_entry_id`                               | Config entry that fired the event                                                              |
| `sources`                                       | List of `{"location": "...", "mode": "..."}` dicts showing which locations observed this alert |

### Automation Example

No dedup condition is needed — the integration already deduplicates:

```yaml
automation:
  - alias: WX Watcher → Notifications
    trigger:
      - trigger: event
        event_type: wx_watcher_alert_created
    action:
      - action: notify.mobile_phone
        data:
          title: "{{ trigger.event.data.Event }}"
          message: "{{ trigger.event.data.Headline }}"
          data:
            url: "{{ trigger.event.data.URL }}"
```

## Sensors

| Entity                           | State                            | Attributes                                                                           |
| -------------------------------- | -------------------------------- | ------------------------------------------------------------------------------------ |
| `sensor.wx_watcher_alerts`       | Number of active alerts          | `Alerts` (full list with sources), `locations` (configured locations), `attribution` |
| `sensor.wx_watcher_last_updated` | Last successful update timestamp | `attribution`                                                                        |

## Breaking Changes from nws_alerts v6

WX Watcher is a complete redesign. If you were using the `nws_alerts` integration:

- **You must delete your old config entries and reconfigure** — the data model is incompatible
- The domain changed from `nws_alerts to `wx_watcher` — all entity IDs change
- Event names changed from `nws_alerts_alert_*` to `wx_watcher_alert_*`
- Event data no longer includes `config_name`; it now includes `sources`
- The old per-entry dedup automation condition (`config_name != 'NWS Alerts Phone'`) is no longer needed

## Attribution

This integration is derived from [nws_alerts](https://github.com/finity69x2/nws_alerts) by finity69x2, which is derived from [nws_custom_component](https://github.com/eracknaphobia/nws_custom_component) by eracknaphobia. Neither upstream project includes a license. See [NOTICE](NOTICE) for the full provenance inventory.
