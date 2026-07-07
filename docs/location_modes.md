# WX Watcher Location Modes

WX Watcher supports three location modes, each offering a different balance between coverage and precision.

## Zone Mode

**How it works:** Resolves your HA zone's GPS coordinates to NWS zone codes (forecast zone, county, fire weather zone), then fetches all active alerts for those zone codes.

**Best for:** Users who want every alert for their area, even distant ones.

| Pros | Cons |
| ---- | ---- |
| Broad coverage — never misses an alert for your zone | May include alerts far from your actual location |
| No GPS dependency beyond initial zone resolution | NWS attaches alerts to full zone codes, so "Northern County" warnings reach you even if you're in the southern part |

**Event data:** All standard alert fields. No `polygon_covers_location` attribute.

## Point Mode

**How it works:** Uses the NWS `/alerts/active?point={lat},{lon}` API, which returns only alerts whose polygon geometry covers your exact GPS coordinates.

**Best for:** Users who only want alerts that directly affect their location.

| Pros | Cons |
| ---- | ---- |
| Precise — only alerts whose polygon covers you | Misses alerts without polygon data (watches, advisories, broad regional alerts) |
| No false positives from distant storms | Some important alerts lack polygon geometry entirely |

**Event data:** All standard alert fields. No `polygon_covers_location` attribute.

## Zone + Point (Hybrid) Mode

**How it works:** Fetches all alerts for your NWS zone codes (like Zone mode), then applies point-in-polygon filtering against your GPS coordinates. Each alert gets a `polygon_covers_location` attribute indicating whether the alert's storm area actually covers you.

**Best for:** Users in large counties or zones who want broad coverage with the ability to filter out geographically distant storms.

| Pros | Cons |
| ---- | ---- |
| Full coverage — fetches all zone alerts | Slightly more complex automations |
| Precision — `polygon_covers_location` tells you if the storm is near you | Alerts without polygon data still come through (but flagged `null`) |
| No-polygon alerts (watches, advisories) are preserved with `null` | |

### `polygon_covers_location` Values

| Value | Meaning | Typical Use |
| ----- | ------- | ----------- |
| `true` | The alert's polygon geometry covers your location | The storm is near you — notify immediately |
| `false` | The alert's polygon exists but doesn't cover your location | The storm is somewhere else in your zone — you can skip or deprioritize |
| `null` | The alert has no polygon geometry (watches, advisories, broad alerts) | Passed through for your automation to handle — these are often important |

### Automation Examples

**Only notify for nearby storms (skip distant ones):**

```yaml
automation:
  - alias: WX Watcher → Nearby Storm Alert
    trigger:
      - trigger: event
        event_type: wx_watcher_alert_created
    condition:
      - condition: template
        value_template: >-
          {{ trigger.event.data.polygon_covers_location is true
             or trigger.event.data.polygon_covers_location is none }}
    action:
      - action: notify.mobile_phone
        data:
          title: "{{ trigger.event.data.Event }}"
          message: "{{ trigger.event.data.Headline }}"
```

**Different actions for nearby vs. distant storms:**

```yaml
automation:
  - alias: WX Watcher → Priority Alert
    trigger:
      - trigger: event
        event_type: wx_watcher_alert_created
    action:
      - choose:
          - conditions:
              - condition: template
                value_template: "{{ trigger.event.data.polygon_covers_location is true }}"
            sequence:
              - action: notify.mobile_phone
                data:
                  title: "⚠️ {{ trigger.event.data.Event }}"
                  message: "Storm near your location: {{ trigger.event.data.Headline }}"
          - conditions:
              - condition: template
                value_template: "{{ trigger.event.data.polygon_covers_location is false }}"
            sequence:
              - action: notify.mobile_phone
                data:
                  title: "{{ trigger.event.data.Event }}"
                  message: "Storm in your zone but not near you: {{ trigger.event.data.Headline }}"
        default:
          - action: notify.mobile_phone
            data:
              title: "{{ trigger.event.data.Event }}"
              message: "{{ trigger.event.data.Headline }}"
```

**Only notify for polygon-verified storms (strict, ignores no-polygon alerts):**

```yaml
automation:
  - alias: WX Watcher → Polygon-Verified Only
    trigger:
      - trigger: event
        event_type: wx_watcher_alert_created
    condition:
      - condition: template
        value_template: "{{ trigger.event.data.polygon_covers_location is true }}"
    action:
      - action: notify.mobile_phone
        data:
          title: "{{ trigger.event.data.Event }}"
          message: "{{ trigger.event.data.Headline }}"
```

## Comparison Table

| Feature | Zone | Point | Zone + Point |
| ------- | ---- | ----- | ------------ |
| Fetches by zone codes | ✅ | ❌ | ✅ |
| Fetches by point API | ❌ | ✅ | ❌ |
| Polygon filtering | ❌ | Implicit | ✅ |
| `polygon_covers_location` attribute | ❌ | ❌ | ✅ |
| Catches no-polygon alerts (watches, advisories) | ✅ | ❌ | ✅ (as `null`) |
| Risk of distant-storm false positives | High | None | Filterable |
| Risk of missing no-polygon alerts | None | High | None |