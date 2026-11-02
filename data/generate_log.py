"""Generate the four deterministic synthetic event logs and case files."""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
from flowmining.calendar_bh import add_bh


ROOT = Path(__file__).resolve().parents[1]
PARAMS_PATH = Path(__file__).resolve().with_name("params.json")
CALENDAR_PATH = Path(__file__).resolve().with_name("calendar.json")
EVENT_FIELDS = ["case_id", "activity", "lifecycle", "timestamp", "resource", "team", "timezone"]
CASE_FIELDS = [
    "case_id", "scenario", "rework_intensity", "case_type", "region", "priority",
    "requesting_team", "channel", "sla_target_days", "outcome", "arrival_timestamp",
    "information_loop_count", "return_points", "provisioning_failure_count",
    "hold_applied", "hold_hours",
]
RESOURCE_CODES = {
    "requester_india": "RQ-IN-01",
    "requester_uk": "RQ-UK-01",
    "requester_us_east": "RQ-US-01",
    "access_service_desk": "SD-IN-07",
    "line_management_india": "LM-IN-03",
    "line_management_uk": "LM-UK-03",
    "line_management_us_east": "LM-US-03",
    "access_risk_controls": "RC-UK-02",
    "application_owners": "AO-US-04",
    "iam_engineering": "IAM-IN-05",
}


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


_PARAMS = _read_json(PARAMS_PATH)
_CALENDAR = _read_json(CALENDAR_PATH)
_CURRENT_PARAMS = _PARAMS


def _lognormal_hours(rng: np.random.Generator, mean: float, sigma: float) -> float:
    if mean == 0:
        return 0.0
    return float(rng.lognormal(mean=math.log(mean) - sigma * sigma / 2.0, sigma=sigma))


def _team_for_step(step: dict[str, Any], region: dict[str, Any]) -> str:
    if step["team"] == "requester_by_region":
        return region["requester_team"]
    if step["team"] == "line_management_by_region":
        return region["line_management_team"]
    return step["team"]


def _random_arrival(rng: np.random.Generator, region: dict[str, Any], table3: dict[str, Any]) -> datetime:
    window_start = date.fromisoformat(table3["log_window"]["start"])
    window_end = date.fromisoformat(table3["log_window"]["end"])
    day_count = (window_end - window_start).days + 1
    zone = ZoneInfo(region["timezone"])
    calendar_cfg = _CALENDAR["teams"][region["requester_team"]]
    start_hour, start_minute = map(int, calendar_cfg["start"].split(":"))
    end_hour, end_minute = map(int, calendar_cfg["end"].split(":"))
    start_of_day = start_hour * 60 + start_minute
    work_minutes = end_hour * 60 + end_minute - start_of_day
    in_hours = rng.random() < table3["arrival_in_hours_fraction"]
    while True:
        day = window_start + timedelta(days=int(rng.integers(0, day_count)))
        if in_hours:
            if day.weekday() >= 5:
                continue
            minute_of_day = start_of_day + int(rng.integers(0, work_minutes))
            hour, minute = divmod(minute_of_day, 60)
            clock_time = time(hour, minute)
            return datetime.combine(day, clock_time, tzinfo=zone)

        minute = int(rng.integers(0, 24 * 60))
        hour, minute = divmod(minute, 60)
        candidate = datetime.combine(day, time(hour, minute), tzinfo=zone)
        in_working_window = (
            day.weekday() < 5
            and hour * 60 + minute >= start_of_day
            and hour * 60 + minute < start_of_day + work_minutes
        )
        if not in_working_window:
            return candidate


def _allocate_loop_counts(rng: np.random.Generator, intensity: str, case_count: int, params: dict[str, Any]) -> list[int]:
    spec = params["table_3"]["rework_case_shares"][intensity]
    one_count = int(round(spec["once"] * case_count))
    two_count = int(round(spec["twice"] * case_count))
    counts = np.array([0] * (case_count - one_count - two_count) + [1] * one_count + [2] * two_count, dtype=int)
    rng.shuffle(counts)
    return counts.tolist()


def _draw_return_points(rng: np.random.Generator, loop_count: int, intensity: str, params: dict[str, Any]) -> list[int]:
    if loop_count == 0:
        return []
    spec = params["table_3"]["rework_case_shares"][intensity]["return_point_probabilities"]
    points = [int(point) for point in spec]
    probabilities = [spec[str(point)] for point in points]
    # Sorting makes the synthetic path executable in forward step order.
    return sorted(int(point) for point in rng.choice(points, size=loop_count, p=probabilities))


def _emit_activity(
    *, rng: np.random.Generator, events: list[dict[str, str]], case_id: str,
    step: dict[str, Any], profile: str, team: str, previous_complete: datetime | None,
    replay: bool, first_activity: bool, hold_hours: float, table3: dict[str, Any],
) -> datetime:
    team_cfg = _CALENDAR["teams"][team]
    timezone_name = team_cfg["timezone"]
    if first_activity:
        schedule = previous_complete
    else:
        handoff = _lognormal_hours(
            rng,
            step["handoff_mean_bh"] * params_type_multiplier(step, "handoff"),
            params_sigma("handoff"),
        )
        hold_component = table3["hold"]["attach_by_profile"][profile]
        if step["step"] == table3["hold"]["activity_step"] and hold_hours and hold_component == "handoff":
            handoff += hold_hours
        schedule = add_bh(previous_complete, handoff, team)
    assert schedule is not None

    queue_mean = step["queue_mean_bh"]
    if replay and step["approval"]:
        queue_mean *= table3["replay_approval_queue_fraction"]
    queue_mean *= params_type_multiplier(step, "queue")
    hold_component = table3["hold"]["attach_by_profile"][profile]
    if step["step"] == table3["hold"]["activity_step"] and hold_hours and hold_component == "queue":
        queue = _lognormal_hours(rng, queue_mean, params_sigma("queue")) + hold_hours
    else:
        queue = _lognormal_hours(rng, queue_mean, params_sigma("queue"))
    start = add_bh(schedule, queue, team)

    touch_mean = step["touch_mean_bh"]
    if replay and step["step"] in (1, 2):
        touch_mean = table3["resubmission_touch_mean_bh"][f"step_{step['step']}"]
        touch_sigma = table3["resubmission_touch_sigma"]
    else:
        touch_sigma = params_sigma("touch")
    touch_mean *= params_type_multiplier(step, "touch")
    touch = _lognormal_hours(rng, touch_mean, touch_sigma)
    complete = add_bh(start, touch, team)

    activity = step["activity"]
    resource = RESOURCE_CODES[team]
    for lifecycle, timestamp in (("schedule", schedule), ("start", start), ("complete", complete)):
        events.append({
            "case_id": case_id,
            "activity": activity,
            "lifecycle": lifecycle,
            "timestamp": timestamp.isoformat(timespec="seconds"),
            "resource": resource,
            "team": team,
            "timezone": timezone_name,
        })
    return complete


def params_sigma(component: str) -> float:
    return _CURRENT_PARAMS["distribution_sigma"][component]


def params_type_multiplier(step: dict[str, Any], component: str) -> float:
    # Set by the current case before activity generation.
    return _CURRENT_TYPE_MULTIPLIER[component]


_CURRENT_TYPE_MULTIPLIER = {"queue": 1.0, "handoff": 1.0, "touch": 1.0}


def _write_csv(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def generate_scenario(
    scenario: str,
    output_dir: Path | str | None = None,
    params_override: dict[str, Any] | None = None,
) -> tuple[Path, Path]:
    """Write one event log and case table. Repeated seeded runs are byte-identical."""
    global _CURRENT_PARAMS
    params = params_override if params_override is not None else _read_json(PARAMS_PATH)
    _CURRENT_PARAMS = params
    calendar = _read_json(CALENDAR_PATH)
    try:
        scenario_cfg = params["scenarios"][scenario]
    except KeyError as exc:
        raise ValueError(f"unknown scenario: {scenario}") from exc

    output = Path(output_dir) if output_dir is not None else ROOT / "data"
    output.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(scenario_cfg["seed"])
    table3 = params["table_3"]
    steps = params["activity_profiles"][scenario_cfg["profile"]]
    intensity = scenario_cfg["rework_intensity"]
    case_count = table3["cases_per_scenario"]
    loop_counts = _allocate_loop_counts(rng, intensity, case_count, params)

    region_names = list(table3["regions"])
    region_probabilities = [table3["regions"][name]["probability"] for name in region_names]
    case_types = list(table3["case_type_probabilities"])
    case_type_probabilities = list(table3["case_type_probabilities"].values())
    queue_handoff_multipliers = table3["queue_handoff_multiplier"]
    event_rows: list[dict[str, str]] = []
    case_rows: list[dict[str, Any]] = []

    for case_index in range(case_count):
        case_id = f"{scenario}-C{case_index + 1:04d}"
        region = table3["regions"][str(rng.choice(region_names, p=region_probabilities))]
        case_type = str(rng.choice(case_types, p=case_type_probabilities))
        _CURRENT_TYPE_MULTIPLIER["queue"] = queue_handoff_multipliers[case_type]
        _CURRENT_TYPE_MULTIPLIER["handoff"] = queue_handoff_multipliers[case_type]
        _CURRENT_TYPE_MULTIPLIER["touch"] = table3["touch_multiplier"][case_type]
        arrival = _random_arrival(rng, region, table3)
        loop_count = loop_counts[case_index]
        return_points = _draw_return_points(rng, loop_count, intensity, params)
        failure_probability = table3["provisioning_failure_probability"][intensity]
        provisioning_failures = int(rng.random() < failure_probability)
        hold_applied = rng.random() < table3["hold"]["case_fraction"]
        hold_hours = (
            _lognormal_hours(rng, table3["hold"]["mean_bh"], table3["hold"]["sigma"])
            if hold_applied else 0.0
        )

        previous_complete: datetime | None = arrival
        pointer = 1
        for return_point in return_points:
            while pointer <= return_point:
                step = steps[pointer - 1]
                team = _team_for_step(step, region)
                previous_complete = _emit_activity(
                    rng=rng, events=event_rows, case_id=case_id, step=step,
                    profile=scenario_cfg["profile"], team=team,
                    previous_complete=previous_complete, replay=False,
                    first_activity=(pointer == 1 and not event_rows_for_case(event_rows, case_id)),
                    hold_hours=hold_hours, table3=table3,
                )
                pointer += 1

            # Return handoff is measured on the step-1/requester's calendar.
            step1 = steps[0]
            return_team = _team_for_step(step1, region)
            return_handoff = _lognormal_hours(rng, table3["return_handoff_mean_bh"], params_sigma("handoff"))
            previous_complete = add_bh(previous_complete, return_handoff, return_team)
            pointer = 1
            while pointer <= return_point:
                step = steps[pointer - 1]
                team = _team_for_step(step, region)
                previous_complete = _emit_activity(
                    rng=rng, events=event_rows, case_id=case_id, step=step,
                    profile=scenario_cfg["profile"], team=team,
                    previous_complete=previous_complete, replay=True,
                    first_activity=False, hold_hours=0.0, table3=table3,
                )
                pointer += 1

        while pointer <= 8:
            step = steps[pointer - 1]
            team = _team_for_step(step, region)
            previous_complete = _emit_activity(
                rng=rng, events=event_rows, case_id=case_id, step=step,
                profile=scenario_cfg["profile"], team=team,
                previous_complete=previous_complete, replay=False,
                first_activity=(pointer == 1 and not event_rows_for_case(event_rows, case_id)),
                hold_hours=hold_hours, table3=table3,
            )
            if pointer == 7 and provisioning_failures:
                for retry_step in (steps[5], steps[6]):
                    retry_team = _team_for_step(retry_step, region)
                    previous_complete = _emit_activity(
                        rng=rng, events=event_rows, case_id=case_id, step=retry_step,
                        profile=scenario_cfg["profile"], team=retry_team,
                        previous_complete=previous_complete, replay=False,
                        first_activity=False, hold_hours=0.0, table3=table3,
                    )
            pointer += 1

        assert previous_complete is not None
        elapsed_days = (previous_complete.astimezone(timezone.utc) - arrival.astimezone(timezone.utc)).total_seconds() / 86400
        sla_target = table3["sla_calendar_days"][case_type]
        outcome = "sla_breach" if elapsed_days > sla_target else "completed_within_sla"
        case_rows.append({
            "case_id": case_id,
            "scenario": scenario,
            "rework_intensity": intensity,
            "case_type": case_type,
            "region": next(name for name, cfg in table3["regions"].items() if cfg == region),
            "priority": {"standard": "normal", "privileged": "high", "emergency": "urgent"}[case_type],
            "requesting_team": calendar["teams"][region["requester_team"]]["display_name"],
            "channel": table3["channels"][0],
            "sla_target_days": sla_target,
            "outcome": outcome,
            "arrival_timestamp": arrival.isoformat(timespec="seconds"),
            "information_loop_count": loop_count,
            "return_points": ";".join(str(point) for point in return_points),
            "provisioning_failure_count": provisioning_failures,
            "hold_applied": str(bool(hold_applied)).lower(),
            "hold_hours": f"{hold_hours:.9f}",
        })

    event_path = output / f"event_log_{scenario}.csv"
    case_path = output / f"cases_{scenario}.csv"
    _write_csv(event_path, EVENT_FIELDS, event_rows)
    _write_csv(case_path, CASE_FIELDS, case_rows)
    return event_path, case_path


def event_rows_for_case(rows: list[dict[str, str]], case_id: str) -> bool:
    return bool(rows and rows[-1]["case_id"] == case_id)


def generate_all(output_dir: Path | str | None = None) -> list[tuple[Path, Path]]:
    params = _read_json(PARAMS_PATH)
    return [generate_scenario(scenario, output_dir) for scenario in params["scenarios"]]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "data")
    parser.add_argument("--scenario", choices=("A1", "A2", "B1", "B2"))
    args = parser.parse_args()
    if args.scenario:
        generate_scenario(args.scenario, args.output_dir)
    else:
        generate_all(args.output_dir)


if __name__ == "__main__":
    main()
