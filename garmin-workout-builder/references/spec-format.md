# Spec format and Garmin mapping

## Spec (input for `scripts/build_garmin_js.py`)

```json
{
  "name": "GA1 3km / GA2 3km / SWL 1km",
  "schedule_date": "2026-11-02",
  "pace_tolerance_s": 5,
  "steps": [
    {"type": "warmup", "distance_km": 2},
    {"type": "interval", "distance_km": 3, "pace": "5:20-5:40"},
    {"type": "repeat", "count": 4, "steps": [
      {"type": "interval", "distance_m": 800, "pace": "3:42-3:48"},
      {"type": "recovery", "duration": "1:30"}
    ]},
    {"type": "cooldown", "distance_km": 2}
  ]
}
```

Fields per step:

| Field | Meaning |
|---|---|
| `type` | `warmup`, `interval`, `recovery`, `rest`, `cooldown`, `repeat` |
| End (exactly one) | `distance_km`, `distance_m`, `duration` (`m:ss` or `h:mm:ss`), `lap_button: true` |
| Target (optional, at most one) | `pace` (`"5:20-5:40"` min/km or `"5:30"` = ±`pace_tolerance_s`), `hr_zone` (1-5), `hr` (`"140-150"` bpm) |
| `repeat` | `count` (>= 2) and `steps` (list of steps, no nesting needed) |

Top level: `name`, `schedule_date` (optional, written into the script as a constant), `pace_tolerance_s` (default 5).

## Garmin IDs (as used in the generator)

| What | ID | Key |
|---|---|---|
| Sport running | 1 | running |
| Step warmup / cooldown / interval / recovery / rest / repeat | 1 / 2 / 3 / 4 / 5 / 6 | same name |
| End lap.button / time / distance / iterations | 1 / 2 / 3 / 7 | same name |
| Target no.target / heart.rate.zone / pace.zone | 1 / 4 / 6 | same name |

- Pace limits are m/s (`1000 / seconds per km`). `targetValueOne` is the slower limit, `targetValueTwo` the faster one. The values belong on the step, not inside `targetType` (Garmin silently discards nested values).
- A Garmin HR zone is set with `zoneNumber`, a custom bpm range with `targetValueOne/Two` and without `zoneNumber`.
- The numeric ID is what counts, not the key: if they don't match, Garmin stores by the ID.

## Confirmed and unconfirmed

- Confirmed (tested successfully by the author): simple steps with a distance end, with a pace target and with no target (warm-up, interval, cool-down).
- Not confirmed: `repeat` groups, time/lap-button ends, HR targets and scheduling via `workout-service/schedule/{id}`. They follow the structure that community libraries for the private Garmin API use. On first use, have the result checked in Garmin Connect.