---
name: "garmin-workout-builder"
description: Turns a photo, screenshot or description of a running workout (intervals, tempo runs, GA1/GA2/SWL i.e. base endurance 1/2 and threshold runs, repetitions with rests) into a browser console script that creates the workout directly in Garmin Connect (and optionally schedules it on the calendar) so it can sync to the Garmin watch. Always use this when the user wants a workout in Garmin Connect, on their Garmin watch or in the Garmin Workout Builder, wants a JS script for Garmin Connect, or wants to "send a training session to Garmin", even without Intervals.icu and even if they don't explicitly mention a script. Create a Garmin Connect workout from a photo/description via a console script that uses the user's logged-in session.
---
 
# Garmin workout via console script
 
The user shares a training session (photo, screenshot, text). You turn it into a workout spec, generate a JavaScript file with `scripts/build_garmin_js.py`, and the user pastes it into the DevTools console in their logged-in browser on connect.garmin.com. The script calls Garmin Connect's private web API using the existing session (cookie plus CSRF token). It needs no passwords or tokens, and you never ask for any.
 
You have no access to Garmin from the sandbox. So never claim a workout has been created: that only happens once the user runs the script.
 
## Process
 
1. **Capture the training session.** From the photo, take over all blocks, distances/times, repetitions, rests and target values. Briefly name anything ambiguous (for example whether a block rest applies in addition to the last repetition rest) and make an assumption. "rest 0" means: no rest step.
2. **Clarify target values.** This is the most important step. If the image only shows RPE, "marathon", "threshold" or "5k pace", every block still needs a concrete pace, otherwise the watch shows only distances and the workout looks empty.
   - Tell the user which paces you need and ask for them. If reference values are already given (for example GA1 and 5k pace), use them.
   - Derive missing values only if the user wants that or has given reference values. Then label them as an **estimate**, with the reasoning (rough rules of thumb: marathon about 5k pace +35 s/km, threshold about 5k pace +10 s/km) and an offer to correct them. Never silently invent a pace.
   - A single value like "5:30" becomes a range of ±`pace_tolerance_s` (default 5 s). For easy runs set a range (for example 5:20-5:40), for hard intervals keep it narrow.
   - Warm-up and cool-down need no target if the photo names none.
3. **Write the spec** following `references/spec-format.md` (JSON, steps with `type`, end condition and optional target). Represent repetitions as a `repeat` block with `count` and `steps` instead of writing them out.
4. **Generate the script:** `python3 scripts/build_garmin_js.py spec.json -o /mnt/user-data/outputs/garmin_upload.js`. The generator converts pace to m/s and sets step IDs, order and target values correctly. Do not build the JSON by hand. Fix generator errors (exit code 2) instead of working around them. Check the result with `node --check` if Node is available.
5. **Deliver** with `present_files`. Then briefly explain what is in it (table: block / distance / pace target / origin), which values are estimates or assumptions, and give the instructions below.
## Instructions for the user
 
1. Log in at `connect.garmin.com/app/workouts`.
2. Open DevTools (F12), Console tab. The first time, type `allow pasting` and press Enter. In Firefox this produces a SyntaxError that can be ignored, because the block is lifted anyway.
3. Paste the contents of `garmin_upload.js` and press Enter. The console shows `Workout created, ID: …`.
4. Check it in Garmin Connect under "Workouts" and send it to the watch with "Send to Device", or set `schedule_date` in the spec to put it on the calendar.
Mention in passing: this is a private, undocumented Garmin API for your own account, it may change, and you should only paste code you understand (the script only talks to connect.garmin.com).
 
## If something goes wrong
 
- The error message in the console contains the status code and response. Ask the user to copy it (session cookies and tokens are not included).
- No CSRF token: not logged in or wrong page, reload on connect.garmin.com.
- 401/403: session expired (log in again) or Garmin rejected the request.
- 400 involving `repeat`, time/lap-button ends, HR targets or scheduling: these parts are unconfirmed (see `references/spec-format.md`). Narrow it down by having the user create the workout without the affected part as a test, and adjust the structure using the error response. Fallback for repeated blocks: write the steps out.
- Scheduling fails or the calendar entry is missing: the console now shows the HTTP status and response for every call, and reports separately whether creating or scheduling failed. To test only the scheduling, set `EXISTING_WORKOUT_ID` in the script (the ID from the first output) so nothing is created twice. If it stays unclear, have the user do the scheduling once in the Garmin interface, find the call in the DevTools Network tab, and show only URL, method and request body (no headers, no cookies). The spec supports `schedule_date`; the call `POST workout-service/schedule/{id}` with `{"date": "YYYY-MM-DD"}` is unconfirmed.
- If a pace target doesn't arrive on the watch, first check in Garmin Connect whether it is in the workout, then check sync and device compatibility.
## Limits
 
- Running workouts only. For cycling, swimming or strength, the generator would need to be extended with sport IDs and target types.
- If the workout should land in Intervals.icu instead, the skill `intervals-workout` is responsible.
 
