"""Business-hours arithmetic for the synthetic access-flow case study."""

from __future__ import annotations

import json
import math
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo


_CALENDAR_PATH = Path(__file__).resolve().parents[2] / "data" / "calendar.json"
with _CALENDAR_PATH.open("r", encoding="utf-8") as _calendar_file:
    _CALENDAR = json.load(_calendar_file)

_WORKDAYS = {0, 1, 2, 3, 4}


def _parse_datetime(value: datetime | str) -> datetime:
    if isinstance(value, str):
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    elif isinstance(value, datetime):
        parsed = value
    else:
        raise TypeError("timestamp must be an aware datetime or ISO 8601 string")
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must include a UTC offset")
    return parsed


def _resolve_team(team: str) -> tuple[ZoneInfo, time, time]:
    if not isinstance(team, str):
        raise TypeError("team must be a string")
    key = team.strip().lower().replace("_", " ")
    key = " ".join(key.split())
    team_key = _CALENDAR["aliases"].get(key, team.strip())
    try:
        settings = _CALENDAR["teams"][team_key]
    except KeyError as exc:
        raise ValueError(f"unknown calendar team: {team}") from exc
    return (
        ZoneInfo(settings["timezone"]),
        time.fromisoformat(settings["start"]),
        time.fromisoformat(settings["end"]),
    )


def _at_local(day: date, clock: time, zone: ZoneInfo) -> datetime:
    return datetime.combine(day, clock, tzinfo=zone)


def _next_workday(day: date) -> date:
    day += timedelta(days=1)
    while day.weekday() not in _WORKDAYS:
        day += timedelta(days=1)
    return day


def _utc(value: datetime) -> datetime:
    return value.astimezone(timezone.utc)


def bh_between(t0: datetime | str, t1: datetime | str, team: str) -> float:
    """Return working hours overlapping [t0, t1] on ``team``'s calendar.

    Timestamps must be timezone-aware. Weekends are excluded; public holidays
    are intentionally not modelled. ``team`` may be a calendar key or alias.
    Line Management is selected with the requester's region-specific calendar.
    """
    start, end = _parse_datetime(t0), _parse_datetime(t1)
    start_utc, end_utc = _utc(start), _utc(end)
    if end_utc < start_utc:
        raise ValueError("t1 must be at or after t0")
    if end_utc == start_utc:
        return 0.0

    zone, opens, closes = _resolve_team(team)
    local_start = start.astimezone(zone).date()
    local_end = end.astimezone(zone).date()
    total_seconds = 0.0
    day = local_start
    while day <= local_end:
        if day.weekday() in _WORKDAYS:
            opening_utc = _utc(_at_local(day, opens, zone))
            closing_utc = _utc(_at_local(day, closes, zone))
            overlap_start = max(start_utc, opening_utc)
            overlap_end = min(end_utc, closing_utc)
            if overlap_end > overlap_start:
                total_seconds += (overlap_end - overlap_start).total_seconds()
        day += timedelta(days=1)
    return total_seconds / 3600.0


def add_bh(t: datetime | str, hours: float, team: str) -> datetime:
    """Add nonnegative business hours and return a timestamp in team's zone."""
    start = _parse_datetime(t)
    if isinstance(hours, bool) or not isinstance(hours, (int, float)):
        raise TypeError("hours must be a finite nonnegative number")
    if not math.isfinite(hours) or hours < 0:
        raise ValueError("hours must be a finite nonnegative number")

    zone, opens, closes = _resolve_team(team)
    remaining = float(hours) * 3600.0
    current = start.astimezone(zone)
    if remaining == 0:
        return current

    while True:
        day = current.date()
        if day.weekday() not in _WORKDAYS:
            day = _next_workday(day)
            current = _at_local(day, opens, zone)
        else:
            opening = _at_local(day, opens, zone)
            closing = _at_local(day, closes, zone)
            current_utc = _utc(current)
            if current_utc < _utc(opening):
                current = opening
            elif current_utc >= _utc(closing):
                day = _next_workday(day)
                current = _at_local(day, opens, zone)

        close_utc = _utc(_at_local(current.date(), closes, zone))
        available_seconds = (close_utc - _utc(current)).total_seconds()
        if remaining <= available_seconds:
            return (_utc(current) + timedelta(seconds=remaining)).astimezone(zone)
        remaining -= available_seconds
        next_day = _next_workday(current.date())
        current = _at_local(next_day, opens, zone)
