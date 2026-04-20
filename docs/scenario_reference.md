# WX Watcher Scenario Reference

## Background

This document describes the behavior of the WX Watcher integration across all
combinations of location mode and device state. It is intended as a reference
for planning and future implementation work.

## How the WX Watcher API works

The NWS API provides two mutually exclusive methods for querying active alerts:

**Zone query** (`?zone={zone_id}`) — Returns every alert whose `affectedZones`
list includes the given zone code. NWS issues alerts with both a polygon (the
actual threat boundary) and a list of zone codes that may be affected. The zone
query matches against the zone code list, not the polygon. If a severe
thunderstorm warning polygon covers the northern half of a county but the user
is in the southern half, the zone query still returns it because the zone code
is listed.

**Point query** (`?point={lat},{lon}`) — Returns only alerts whose polygon
geometry contains the given coordinates. If the storm polygon does not cover
the user's exact GPS point, the alert does not appear, even if the user's zone
code is listed in the alert's affected zones.

An alert can appear in a zone query but not a point query for the same location
(e.g., storm polygon covers the other side of the county). The reverse is rarer
but possible (alert has polygon covering a point but incomplete or inaccurate
zone coding).

NWS recommends zone queries for most users because they provide earlier
awareness of threats developing in the region. Point queries can miss
approaching storms whose polygon has not yet reached the exact coordinate.

## How Home Assistant zones relate to NWS zones

Home Assistant zones are circles defined by a center point (latitude,
longitude) and a radius in meters. When a GPS-based device tracker reports
coordinates, HA checks which zone circles contain the device. The device
tracker's state reflects the zone it is in: `"home"` for `zone.home`, the
zone's friendly name for other zones, or `"not_home"` if not in any zone.

The NWS API provides an endpoint (`api.weather.gov/points/{lat},{lon}`) that
maps any GPS coordinate to NWS zone IDs. Given a latitude and longitude, it
returns the forecast zone, county zone, and fire weather zone for that point.
This means any HA zone (or device tracker position) can be resolved to the NWS
zones it falls within.

## Locations and modes

The integration has two types of monitored locations:

**Static location** — A fixed place that is always monitored, regardless of
device tracker positions. Configured as an HA zone, a custom GPS coordinate, or
manually entered NWS zone IDs. Each static location has a query mode:

- **Zone mode** — Queries alerts by NWS zone IDs. Returns all alerts listed for
  those zones, including those whose polygons only partially cover the zone.
- **Point mode** — Queries alerts by GPS coordinates. Returns only alerts whose
  polygon geometry covers the exact point.

**Tracked location** — A location that follows a device tracker. Each tracked
location also has a query mode (zone or point). When the phone is away from
home, the tracked location fetches alerts for the phone's current position
using its configured mode. When the phone is at home, both the home location
and the tracked location may produce alerts for the same area — the scenarios
below describe what happens in each case.

## Scenario setup

The following eight scenarios use this example configuration:

- **Home location:** 34.25, -118.55 (NW Los Angeles County foothills), NWS zone
  LAC037
- **Tracked device:** Phone with device_tracker entity, reporting GPS
  coordinates
- **Phone at home:** Device tracker state is `"home"`, GPS near 34.25, -118.55
- **Phone away:** Device tracker state is `"not_home"`, GPS at 33.75, -117.90
  (Orange County), NWS zone ORC059

**Alerts active during each scenario:**

| #   | Alert                  | Zones listed | Polygon covers                      |
| --- | ---------------------- | ------------ | ----------------------------------- |
| A   | Dense Fog Advisory     | LAC037       | LA basin, NOT NW foothills          |
| B   | Red Flag Warning       | LAC037       | LA mountains/foothills including NW |
| C   | Coastal Flood Warning  | ORC059       | OC coastline only                   |
| D   | Severe T-Storm Warning | ORC059       | Central OC including phone GPS      |

## Scenario 1: Phone at home, home=zone, device=zone

Both queries target the same NWS zone (LAC037).

| Alert      | Home (?zone=LAC037) | Device (?zone=LAC037) | API Results | Desired | Notes                                                                                   |
| ---------- | ------------------- | --------------------- | ----------- | ------- | --------------------------------------------------------------------------------------- |
| A Fog      | Found               | Found                 | 2           | 1       | Same alert ID. Device is at home in the same zone — this is one weather event, not two. |
| B Red Flag | Found               | Found                 | 2           | 1       | Same.                                                                                   |
| C Flood    | —                   | —                     | 0           | 0       |                                                                                         |
| D T-Storm  | —                   | —                     | 0           | 0       |                                                                                         |

## Scenario 2: Phone at home, home=zone, device=point

Home queries by zone, device queries by point at the phone's GPS coordinates
near the home location.

| Alert      | Home (?zone=LAC037) | Device (?point=34.25,-118.55) | API Results | Desired | Notes                                                                                                    |
| ---------- | ------------------- | ----------------------------- | ----------- | ------- | -------------------------------------------------------------------------------------------------------- |
| A Fog      | Found               | Not found                     | 1           | 1       | Fog polygon doesn't reach NW foothills, so the point query misses it. The zone query is the only source. |
| B Red Flag | Found               | Found                         | 2           | 1       | Same alert ID. Device is at home at the same location — this is one weather event, not two.              |
| C Flood    | —                   | —                             | 0           | 0       |                                                                                                          |
| D T-Storm  | —                   | —                             | 0           | 0       |                                                                                                          |

## Scenario 3: Phone at home, home=point, device=zone

Home queries by point, device queries by zone (LAC037) since the phone is at
home.

| Alert      | Home (?point=34.25,-118.55) | Device (?zone=LAC037) | API Results | Desired | Notes                                                                                                                 |
| ---------- | --------------------------- | --------------------- | ----------- | ------- | --------------------------------------------------------------------------------------------------------------------- |
| A Fog      | Not found                   | Found                 | 1           | 1       | The device is in zone mode because the user chose zone mode for it. The fog advisory appears from the device's query. |
| B Red Flag | Found                       | Found                 | 2           | 1       | Same alert ID. Device is at home.                                                                                     |
| C Flood    | —                           | —                     | 0           | 0       |                                                                                                                       |
| D T-Storm  | —                           | —                     | 0           | 0       |                                                                                                                       |

## Scenario 4: Phone at home, home=point, device=point

Both queries use point mode at the same coordinates.

| Alert      | Home (?point=34.25,-118.55) | Device (?point=34.25,-118.55) | API Results | Desired | Notes                                               |
| ---------- | --------------------------- | ----------------------------- | ----------- | ------- | --------------------------------------------------- |
| A Fog      | Not found                   | Not found                     | 0           | 0       | Fog polygon doesn't reach NW foothills.             |
| B Red Flag | Found                       | Found                         | 2           | 1       | Same alert ID, same coordinates. One weather event. |
| C Flood    | —                           | —                             | 0           | 0       |                                                     |
| D T-Storm  | —                           | —                             | 0           | 0       |                                                     |

## Scenario 5: Phone away, home=zone, device=zone

Home queries LAC037. Device queries ORC059. Non-overlapping zones.

| Alert      | Home (?zone=LAC037) | Device (?zone=ORC059) | API Results | Desired | Notes                               |
| ---------- | ------------------- | --------------------- | ----------- | ------- | ----------------------------------- |
| A Fog      | Found               | —                     | 1           | 1       | Different zone, different location. |
| B Red Flag | Found               | —                     | 1           | 1       |                                     |
| C Flood    | —                   | Found                 | 1           | 1       |                                     |
| D T-Storm  | —                   | Found                 | 1           | 1       |                                     |

## Scenario 6: Phone away, home=zone, device=point

Home queries LAC037. Device queries by point at phone's GPS in OC.

| Alert      | Home (?zone=LAC037) | Device (?point=33.75,-117.90) | API Results | Desired | Notes                                                                                                             |
| ---------- | ------------------- | ----------------------------- | ----------- | ------- | ----------------------------------------------------------------------------------------------------------------- |
| A Fog      | Found               | —                             | 1           | 1       | Fog is in LA basin, far from OC.                                                                                  |
| B Red Flag | Found               | —                             | 1           | 1       | LA mountains, far from OC.                                                                                        |
| C Flood    | —                   | Not found                     | 0           | 0       | Flood polygon is on the coastline, phone GPS is inland. Point mode at the device means this alert doesn't appear. |
| D T-Storm  | —                   | Found                         | 1           | 1       | Polygon covers phone GPS.                                                                                         |

## Scenario 7: Phone away, home=point, device=point

Home queries by point. Device queries by point at phone's GPS in OC.

| Alert      | Home (?point=34.25,-118.55) | Device (?point=33.75,-117.90) | API Results | Desired | Notes                                         |
| ---------- | --------------------------- | ----------------------------- | ----------- | ------- | --------------------------------------------- |
| A Fog      | Not found                   | —                             | 0           | 0       | Fog is in the basin, doesn't reach foothills. |
| B Red Flag | Found                       | —                             | 1           | 1       |                                               |
| C Flood    | —                           | Not found                     | 0           | 0       | Coastal polygon doesn't reach inland phone.   |
| D T-Storm  | —                           | Found                         | 1           | 1       |                                               |

## Scenario 8: Phone away, home=point, device=zone

Home queries by point. Device queries ORC059 by zone.

| Alert      | Home (?point=34.25,-118.55) | Device (?zone=ORC059) | API Results | Desired | Notes                                                             |
| ---------- | --------------------------- | --------------------- | ----------- | ------- | ----------------------------------------------------------------- |
| A Fog      | Not found                   | —                     | 0           | 0       | Fog doesn't reach foothills. Different county on the device side. |
| B Red Flag | Found                       | —                     | 1           | 1       |                                                                   |
| C Flood    | —                           | Found                 | 1           | 1       |                                                                   |
| D T-Storm  | —                           | Found                 | 1           | 1       |                                                                   |

## Key observations

**At-home duplicates:** In Scenarios 1–4, when both the home and device queries
find the same alert (same alert ID), the API returns 2 results. The desired
count is always 1. These are the same weather event seen by two queries covering
the same area — only one event should reach the user.

**No mode conflicts at home:** In Scenario 3, the device's zone query finds
alert A (fog), but the home's point query does not. Both modes are
independently valid — the user chose zone mode for the device and point mode
for home, so alerts from either source are shown. There is no conflict; the
only dedup rule is that the same alert ID from multiple sources produces one
event.

**Away scenarios have no conflicts:** In Scenarios 5–8, the phone is in a
different area querying different zones or coordinates. No alert can appear in
both queries, so every API result maps to exactly one desired event.

**Point mode misses:** Alerts C and A are missed by point queries in several
scenarios because their polygons don't cover the queried coordinates. This is
the expected behavior for point mode — the user chose precision over coverage.

## Mismatches: API Results vs. Desired Count

Cases where the API returns more results than desired. All are the same
pattern: the phone is at home, both queries find the same alert by ID, and the
duplicate must be resolved to a single event.

| Scenario | Alert      | Home finds? | Device finds? | API Results | Desired | Notes                           |
| -------- | ---------- | ----------- | ------------- | ----------- | ------- | ------------------------------- |
| 1        | A Fog      | Yes         | Yes           | 2           | 1       | Same alert ID, same zone        |
| 1        | B Red Flag | Yes         | Yes           | 2           | 1       | Same alert ID, same zone        |
| 2        | B Red Flag | Yes         | Yes           | 2           | 1       | Same alert ID, same location    |
| 3        | B Red Flag | Yes         | Yes           | 2           | 1       | Same alert ID, same location    |
| 4        | B Red Flag | Yes         | Yes           | 2           | 1       | Same alert ID, same coordinates |

No mismatches exist in the away scenarios (5–8) because non-overlapping
zones/coordinates cannot produce the same alert from both queries.

## V7 Integration-Level Deduplication

As of v7.0.0, the integration resolves all 5 mismatches at the coordinator level:

- All zone-mode locations' zone IDs are combined into a single `?zone=` query.
- The API response's `geocode.UGC` field is used to determine which locations
  observe each alert (fan-out).
- All point-mode locations are queried individually via `?point=`.
- Results are merged by NWS alert ID: same alert found by multiple locations
  produces one event with a `sources` list indicating which locations observed it.
- No automation-level dedup is required. The integration fires exactly one event
  per unique alert, matching the "Desired" column in every scenario.
