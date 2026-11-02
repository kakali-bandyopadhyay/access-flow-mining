"""Extract lifecycle components from synthetic event logs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from .calendar_bh import bh_between


ACTIVITY_STEPS = {
    "Submit request": 1,
    "Validate request": 2,
    "Line manager approval": 3,
    "SoD / access-risk check": 4,
    "Entitlement owner approval": 5,
    "Provision access": 6,
    "Confirm access works": 7,
    "Close request": 8,
}
REQUIRED_EVENT_COLUMNS = {"case_id", "activity", "lifecycle", "timestamp", "team", "timezone"}
EXECUTION_KEYS = ["case_id", "activity", "execution_number"]


def _read_events(events: pd.DataFrame | str | Path) -> pd.DataFrame:
    frame = pd.read_csv(events, dtype={"case_id": str}) if isinstance(events, (str, Path)) else events.copy()
    missing = REQUIRED_EVENT_COLUMNS - set(frame.columns)
    if missing:
        raise ValueError(f"event log is missing required columns: {sorted(missing)}")
    unknown = set(frame["activity"].dropna().unique()) - set(ACTIVITY_STEPS)
    if unknown:
        raise ValueError(f"event log contains unknown activities: {sorted(unknown)}")
    if not set(frame["lifecycle"].dropna().unique()) <= {"schedule", "start", "complete"}:
        raise ValueError("lifecycle must be schedule, start, or complete")
    frame = frame.reset_index(drop=True)
    frame["_row_order"] = range(len(frame))
    frame["timestamp_utc"] = pd.to_datetime(frame["timestamp"], utc=True, errors="raise")
    return frame.sort_values(["case_id", "timestamp_utc", "_row_order"], kind="stable")


def components_from_events(events: pd.DataFrame | str | Path) -> pd.DataFrame:
    """Return one row per activity execution with handoff, queue, touch and cycle.

    The first execution of step 1 has no handoff (NaN). Later step-1
    executions retain the return handoff as the interval from the prior
    completion to that re-entry's schedule.
    """
    frame = _read_events(events)
    frame["execution_number"] = frame.groupby(
        ["case_id", "activity", "lifecycle"], sort=False
    ).cumcount()

    index_keys = EXECUTION_KEYS
    timestamps = frame.pivot(index=index_keys, columns="lifecycle", values="timestamp_utc")
    for lifecycle in ("schedule", "start", "complete"):
        if lifecycle not in timestamps.columns:
            raise ValueError(f"event log has no {lifecycle} events")
    if timestamps[["schedule", "start", "complete"]].isna().any().any():
        raise ValueError("each activity execution must have schedule, start, and complete events")

    schedule_meta = frame[frame["lifecycle"] == "schedule"][
        index_keys + ["team", "timezone"]
    ]
    if schedule_meta.duplicated(index_keys).any():
        raise ValueError("activity execution has multiple schedule rows")
    extracted = timestamps.reset_index().merge(schedule_meta, on=index_keys, validate="one_to_one")
    extracted["step"] = extracted["activity"].map(ACTIVITY_STEPS).astype(int)
    extracted = extracted.sort_values(["case_id", "schedule"], kind="stable").reset_index(drop=True)
    extracted["previous_complete"] = extracted.groupby("case_id", sort=False)["complete"].shift(1)

    handoffs: list[float] = []
    queues: list[float] = []
    touches: list[float] = []
    for row in extracted.itertuples(index=False):
        team = row.team
        if pd.isna(row.previous_complete):
            handoffs.append(float("nan"))
        else:
            handoffs.append(bh_between(row.previous_complete.to_pydatetime(), row.schedule.to_pydatetime(), team))
        queues.append(bh_between(row.schedule.to_pydatetime(), row.start.to_pydatetime(), team))
        touches.append(bh_between(row.start.to_pydatetime(), row.complete.to_pydatetime(), team))

    extracted["handoff_bh"] = handoffs
    extracted["queue_bh"] = queues
    extracted["touch_bh"] = touches
    extracted["cycle_bh"] = extracted[["handoff_bh", "queue_bh", "touch_bh"]].sum(axis=1, skipna=True)
    extracted["is_replay"] = extracted["execution_number"] > 0
    extracted["scenario"] = extracted["case_id"].str.split("-", n=1).str[0]
    return extracted[
        ["case_id", "scenario", "step", "activity", "execution_number", "is_replay",
         "team", "timezone", "previous_complete", "schedule", "start", "complete",
         "handoff_bh", "queue_bh", "touch_bh", "cycle_bh"]
    ]


def case_cycle_times(components: pd.DataFrame) -> pd.DataFrame:
    """Aggregate execution components into one business/calendar cycle per case."""
    records: list[dict[str, Any]] = []
    for case_id, group in components.groupby("case_id", sort=True):
        ordered = group.sort_values("schedule", kind="stable")
        first_schedule = ordered.iloc[0]["schedule"]
        last_complete = ordered["complete"].max()
        records.append({
            "case_id": case_id,
            "scenario": ordered.iloc[0]["scenario"],
            "cycle_bh": float(ordered[["handoff_bh", "queue_bh", "touch_bh"]].sum(axis=1, skipna=True).sum()),
            "calendar_days": (last_complete - first_schedule).total_seconds() / 86400.0,
            "first_schedule": first_schedule,
            "last_complete": last_complete,
        })
    return pd.DataFrame.from_records(records)
