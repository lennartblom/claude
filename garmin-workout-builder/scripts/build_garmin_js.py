#!/usr/bin/env python3
"""Generates a browser console script from a simple workout spec (JSON) that
creates the workout in Garmin Connect (unofficial web API, logged-in session).

Usage:
    python3 build_garmin_js.py spec.json -o garmin_upload.js
    python3 build_garmin_js.py spec.json --print-json     # Garmin workout JSON only

Spec format: see SKILL.md and references/spec-format.md.
Running workouts only (sportType running). No credentials, no network access.
"""
import argparse
import json
import re
import sys

STEP_TYPES = {  # key -> (stepTypeId, stepTypeKey)
    "warmup": (1, "warmup"),
    "cooldown": (2, "cooldown"),
    "interval": (3, "interval"),
    "recovery": (4, "recovery"),
    "rest": (5, "rest"),
}
DEFAULT_PACE_TOLERANCE_S = 5


class SpecError(ValueError):
    pass


def parse_mmss(text, what):
    m = re.fullmatch(r"\s*(\d+):([0-5]\d)\s*", str(text))
    if not m:
        raise SpecError(f"{what}: '{text}' is not a valid m:ss time format")
    return int(m.group(1)) * 60 + int(m.group(2))


def parse_duration(text):
    """'10:00' -> 600 s; 90 -> 90 s; '1:30:00' -> 5400 s."""
    if isinstance(text, (int, float)):
        return float(text)
    parts = str(text).split(":")
    if len(parts) == 2:
        return float(int(parts[0]) * 60 + int(parts[1]))
    if len(parts) == 3:
        return float(int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2]))
    raise SpecError(f"duration: '{text}' is not in m:ss or h:mm:ss format")


def pace_target(spec_pace, tol):
    """'5:20-5:40' (min/km) or '5:30' (+-tol seconds) -> Garmin pace.zone in m/s."""
    s = str(spec_pace).replace("/km", "").strip()
    if "-" in s:
        a, b = s.split("-", 1)
        lo, hi = sorted((parse_mmss(a, "pace"), parse_mmss(b, "pace")))
    else:
        c = parse_mmss(s, "pace")
        lo, hi = c - tol, c + tol
    if lo < 120 or hi > 1200:
        raise SpecError(f"pace '{spec_pace}' looks implausible (expected 2:00-20:00 min/km)")
    return {
        "targetType": {"workoutTargetTypeId": 6, "workoutTargetTypeKey": "pace.zone"},
        "targetValueOne": round(1000 / hi, 4),  # slower limit (smaller m/s)
        "targetValueTwo": round(1000 / lo, 4),  # faster limit
    }


def hr_target(step):
    tt = {"workoutTargetTypeId": 4, "workoutTargetTypeKey": "heart.rate.zone"}
    if "hr_zone" in step:
        z = int(step["hr_zone"])
        if not 1 <= z <= 5:
            raise SpecError("hr_zone must be 1-5")
        return {"targetType": tt, "zoneNumber": z}
    lo, hi = sorted(int(x) for x in str(step["hr"]).split("-"))
    return {"targetType": tt, "targetValueOne": lo, "targetValueTwo": hi}


def end_condition(step):
    if step.get("lap_button"):
        return {"conditionTypeId": 1, "conditionTypeKey": "lap.button"}, None
    if "distance_km" in step:
        return {"conditionTypeId": 3, "conditionTypeKey": "distance"}, float(step["distance_km"]) * 1000
    if "distance_m" in step:
        return {"conditionTypeId": 3, "conditionTypeKey": "distance"}, float(step["distance_m"])
    if "duration" in step:
        return {"conditionTypeId": 2, "conditionTypeKey": "time"}, parse_duration(step["duration"])
    raise SpecError(f"Step without an end (distance_km/distance_m/duration/lap_button): {step}")


class Builder:
    def __init__(self, tol):
        self.order = 0
        self.tol = tol

    def next_order(self):
        self.order += 1
        return self.order

    def executable(self, step, child=False):
        kind = step.get("type")
        if kind not in STEP_TYPES:
            raise SpecError(f"Unknown step type '{kind}' (allowed: {', '.join(STEP_TYPES)}, repeat)")
        type_id, type_key = STEP_TYPES[kind]
        cond, value = end_condition(step)
        out = {
            "type": "ExecutableStepDTO",
            "stepOrder": self.next_order(),
            "stepType": {"stepTypeId": type_id, "stepTypeKey": type_key},
            "endCondition": cond,
        }
        if child:
            out["childStepId"] = 1
        if value is not None:
            out["endConditionValue"] = value
        if "pace" in step:
            out.update(pace_target(step["pace"], step.get("pace_tolerance_s", self.tol)))
        elif "hr_zone" in step or "hr" in step:
            out.update(hr_target(step))
        else:
            out["targetType"] = {"workoutTargetTypeId": 1, "workoutTargetTypeKey": "no.target"}
        return out

    def build(self, step, child=False):
        if step.get("type") != "repeat":
            return self.executable(step, child)
        count = int(step["count"])
        if count < 2:
            raise SpecError("repeat.count must be >= 2 (for 1, write the steps out directly)")
        group = {
            "type": "RepeatGroupDTO",
            "stepOrder": self.next_order(),
            "stepType": {"stepTypeId": 6, "stepTypeKey": "repeat"},
            "numberOfIterations": count,
            "endCondition": {"conditionTypeId": 7, "conditionTypeKey": "iterations"},
            "endConditionValue": float(count),
            "smartRepeat": False,
        }
        if child:
            group["childStepId"] = 1
        group["workoutSteps"] = [self.build(s, child=True) for s in step["steps"]]
        return group


def build_workout(spec):
    if not spec.get("steps"):
        raise SpecError("Spec needs 'steps'")
    sport = {"sportTypeId": 1, "sportTypeKey": "running"}
    b = Builder(spec.get("pace_tolerance_s", DEFAULT_PACE_TOLERANCE_S))
    steps = [b.build(s) for s in spec["steps"]]
    return {
        "workoutName": spec.get("name", "Workout"),
        "sportType": sport,
        "workoutSegments": [{"segmentOrder": 1, "sportType": sport, "workoutSteps": steps}],
    }


JS_TEMPLATE = """// Paste into the DevTools console in your logged-in browser at https://connect.garmin.com/app/workouts.
// Firefox/Chrome require you to type `allow pasting` first the first time you paste (Enter, ignore the error message).
// Unofficial, private web API: may change at any time. Use only for your own account.
// The script talks exclusively to connect.garmin.com and uses your existing session.

(async () => {
  const SCHEDULE_DATE = __DATE__; // e.g. "2026-11-02" or null = only create in "Workouts"
  const EXISTING_WORKOUT_ID = null; // only for testing scheduling: enter the ID of an already created workout, then nothing new is created

  const csrf = document.querySelector('meta[name="csrf-token"]')?.content;
  if (!csrf) { console.error("No CSRF token found. Are you logged in at connect.garmin.com?"); return; }

  const workout = __WORKOUT__;

  const call = async (path, body) => {
    const r = await fetch("/gc-api/" + path, {
      method: "POST",
      credentials: "include",
      headers: { "content-type": "application/json", "connect-csrf-token": csrf, "accept": "application/json" },
      body: JSON.stringify(body),
    });
    const text = await r.text();
    console.log(`POST ${path} -> HTTP ${r.status}`, text.slice(0, 300));
    if (!r.ok) throw new Error(`${r.status} ${path}: ${text.slice(0, 500)}`);
    try { return text ? JSON.parse(text) : {}; } catch { return { raw: text }; }
  };

  let workoutId = EXISTING_WORKOUT_ID;
  if (!workoutId) {
    try {
      const created = await call("workout-service/workout", workout);
      workoutId = created.workoutId;
      console.log("Workout created, ID:", workoutId);
    } catch (e) {
      console.error("Creating the workout failed:", e);
      return;
    }
  }

  if (SCHEDULE_DATE) {
    if (!workoutId) { console.warn("No workoutId in the response, scheduling skipped."); return; }
    try {
      await call(`workout-service/schedule/${workoutId}`, { date: SCHEDULE_DATE });
      console.log("Scheduled for", SCHEDULE_DATE, "(check the calendar in Garmin Connect)");
    } catch (e) {
      console.error(`Workout ${workoutId} was created, but scheduling failed:`, e);
    }
  }
})();
"""


def render_js(workout, date):
    body = json.dumps(workout, indent=2, ensure_ascii=False).replace("\n", "\n  ")
    date_js = json.dumps(date) if date else "null"
    return JS_TEMPLATE.replace("__WORKOUT__", body).replace("__DATE__", date_js)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec")
    ap.add_argument("-o", "--output", default="garmin_upload.js")
    ap.add_argument("--print-json", action="store_true", help="print only the Garmin workout JSON")
    args = ap.parse_args()
    try:
        spec = json.load(open(args.spec, encoding="utf-8"))
        workout = build_workout(spec)
    except (SpecError, KeyError, ValueError, json.JSONDecodeError) as e:
        print(f"Error in spec: {e}", file=sys.stderr)
        return 2
    if args.print_json:
        print(json.dumps(workout, indent=2, ensure_ascii=False))
        return 0
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(render_js(workout, spec.get("schedule_date")))
    print(f"Written: {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())