# garmin-workout-builder

A [Claude skill](https://www.anthropic.com/news/skills) that turns a photo, screenshot or text description of a running workout into a browser console script. Paste the script into your logged-in Garmin Connect session and the workout is created in your account, ready to sync to your Garmin watch.

> **Unofficial.** This project is not affiliated with or endorsed by Garmin. It uses Garmin Connect's private, undocumented web API, which can change or break at any time. Use it only with your own account.

## What it does

You give Claude a training plan, for example a photo of a coach's handwritten session like "3 km GA1 / 3 km GA2 / 1 km SWL" or "4 x 800 m at 5k pace, 90 s rest". Claude then:

1. Extracts the blocks, distances/times, repetitions and rests.
2. Makes sure every block has a concrete pace target. If the plan only says "threshold" or "marathon pace", Claude asks you for reference paces, or offers clearly labelled estimates.
3. Writes a small JSON spec and runs `scripts/build_garmin_js.py`, which produces a ready-to-paste JavaScript file.
4. Gives you short instructions for running it in the browser.

Claude cannot reach Garmin from its sandbox, so it never claims a workout exists until you have run the script yourself.

## Features

- Warm-up, interval, recovery, rest and cool-down steps
- Repeat blocks (`4 x (800 m + 90 s recovery)`)
- Pace targets as a range (`5:20-5:40`) or a single value with a tolerance (`5:30` becomes ±5 s)
- Distance, time and lap-button step ends
- Heart-rate targets by zone or bpm range
- Optional scheduling on your Garmin Connect calendar
- No passwords or tokens needed: the script reuses your existing browser session and only talks to `connect.garmin.com`

German training terms such as GA1/GA2 (base endurance 1/2) and SWL (threshold run) are understood.

## Installation

The skill is the folder containing `SKILL.md`.

- **Claude Code:** copy or clone this folder into your skills directory, for example `~/.claude/skills/garmin-workout-builder/`.
- **Claude.ai / Claude app:** zip the folder and upload it through your skills settings (requires a plan with skills and code execution enabled).

See Anthropic's skills documentation for the current details.

## Usage

Start a chat and share a workout, for example:

> Here's my session for Tuesday [photo]. My 5k pace is 4:10 and my easy pace is 5:30. Please put it in Garmin Connect.

Claude will confirm the paces, generate `garmin_upload.js`, and walk you through the next steps:

1. Log in at `connect.garmin.com/app/workouts`.
2. Open DevTools (F12) and go to the Console tab. The first time, type `allow pasting` and press Enter. In Firefox this shows a SyntaxError you can ignore.
3. Paste the contents of `garmin_upload.js` and press Enter. The console prints `Workout created, ID: ...`.
4. Open Garmin Connect under "Workouts" to check it, then use "Send to Device". Alternatively set `schedule_date` in the spec to put it on your calendar.

Only paste code you understand. The generated script is plain, readable JavaScript.

## Using the generator without Claude

`scripts/build_garmin_js.py` is a standalone Python 3 script with no dependencies.

```bash
python3 scripts/build_garmin_js.py spec.json -o garmin_upload.js
python3 scripts/build_garmin_js.py spec.json --print-json   # print only the Garmin workout JSON
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

The full field reference and the Garmin ID mapping are in [`references/spec-format.md`](references/spec-format.md). Invalid specs make the generator exit with code 2 and a readable error message.

## What has been tested

| Feature | Status |
|---|---|
| Simple steps with a distance end, with or without a pace target | Confirmed working |
| `repeat` groups | Confirmed working |
| Time and lap-button step ends | Unconfirmed |
| Heart-rate targets | Confirmed working |
| Scheduling via `workout-service/schedule/{id}` | Confirmed working |

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
