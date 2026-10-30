# garmin-workout-builder

A Claude skill that turns a photo, screenshot or text description of a running workout into a browser console script for Garmin Connect. For what it does, how to install it and how to use it, see the [skill README](garmin-workout-builder/README.md).

> **Unofficial.** This project is not affiliated with or endorsed by Garmin. It uses Garmin Connect's private, undocumented web API, which can change or break at any time. Use it only with your own account.

## Using the generator without Claude

`garmin-workout-builder/scripts/build_garmin_js.py` is a standalone Python 3 script with no dependencies.

```bash
python3 garmin-workout-builder/scripts/build_garmin_js.py spec.json -o garmin_upload.js
python3 garmin-workout-builder/scripts/build_garmin_js.py spec.json --print-json   # print only the Garmin workout JSON
```

Example `spec.json`:

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

The full field reference and the Garmin ID mapping are in [`garmin-workout-builder/references/spec-format.md`](garmin-workout-builder/references/spec-format.md). Invalid specs make the generator exit with code 2 and a readable error message.

## What has been tested

| Feature | Status |
|---|---|
| Simple steps with a distance end, with or without a pace target | Confirmed working |
| `repeat` groups | Unconfirmed |
| Time and lap-button step ends | Unconfirmed |
| Heart-rate targets | Unconfirmed |
| Scheduling via `workout-service/schedule/{id}` | Unconfirmed |

The unconfirmed parts follow the structure used by community libraries for the private Garmin API. If one of them fails for you, the console shows the HTTP status and response for every call. Opening an issue with that output (it contains no cookies or tokens) helps a lot. As a fallback for repeat blocks, write the steps out individually.

## Troubleshooting

- **No CSRF token found:** you are not logged in, or you are on the wrong page. Reload on `connect.garmin.com`.
- **401 / 403:** your session expired (log in again) or Garmin rejected the request.
- **400 error:** most likely one of the unconfirmed features above. Try creating the workout without it.
- **Workout is created but not scheduled:** set `EXISTING_WORKOUT_ID` at the top of the script to the ID from the first run, so only the scheduling call is retried.
- **Pace target missing on the watch:** first check that it appears in the workout in Garmin Connect, then check sync and device compatibility.

## Limitations

- Running workouts only. Cycling, swimming and strength would need extra sport IDs and target types in the generator.
- Depends on an unofficial API that Garmin may change without notice.

## Repository layout

```
.
├── README.md                       # this file
├── LICENSE
└── garmin-workout-builder/         # the skill (copy this folder to install it)
    ├── SKILL.md                    # skill instructions for Claude
    ├── README.md                   # what it does, installation, usage
    ├── references/
    │   └── spec-format.md          # spec fields and Garmin ID mapping
    └── scripts/
        └── build_garmin_js.py      # spec -> console script generator
```

## Contributing

Issues and pull requests are welcome, especially confirmations (or fixes) for the unconfirmed features, and support for more sports.

## License

Add a license of your choice here (for example MIT) before publishing.

Garmin and Garmin Connect are trademarks of Garmin Ltd. or its subsidiaries.