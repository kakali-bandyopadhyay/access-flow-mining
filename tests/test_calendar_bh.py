from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from flowmining.calendar_bh import add_bh, bh_between


LONDON = "access_risk_controls"
NEW_YORK = "application_owners"


def dt(value: str, zone: str) -> datetime:
    return datetime.fromisoformat(value).replace(tzinfo=ZoneInfo(zone))


def test_weekends_are_excluded():
    assert bh_between(
        dt("2026-05-01T09:00:00", "Europe/London"),
        dt("2026-05-04T09:00:00", "Europe/London"),
        LONDON,
    ) == pytest.approx(8.5)


def test_friday_1700_to_monday_0900_obeys_preregistered_london_hours():
    # The preregistered 09:00-17:30 day leaves only 30 minutes on Friday.
    assert bh_between(
        dt("2026-05-01T17:00:00", "Europe/London"),
        dt("2026-05-04T09:00:00", "Europe/London"),
        LONDON,
    ) == pytest.approx(0.5)


def test_friday_start_to_monday_open_is_eight_and_a_half_hours():
    assert bh_between(
        dt("2026-05-01T09:00:00", "Europe/London"),
        dt("2026-05-04T09:00:00", "Europe/London"),
        LONDON,
    ) == pytest.approx(8.5)


@pytest.mark.parametrize(
    ("friday", "monday", "team", "expected"),
    [
        ("2026-03-06T09:00:00", "2026-03-09T09:00:00", NEW_YORK, 8.0),
        ("2026-03-27T09:00:00", "2026-03-30T09:00:00", LONDON, 8.5),
        ("2026-10-23T09:00:00", "2026-10-26T09:00:00", LONDON, 8.5),
        ("2026-10-30T09:00:00", "2026-11-02T09:00:00", NEW_YORK, 8.0),
    ],
)
def test_spring_and_autumn_dst_transitions(friday, monday, team, expected):
    zone = "Europe/London" if team == LONDON else "America/New_York"
    assert bh_between(dt(friday, zone), dt(monday, zone), team) == pytest.approx(expected)


@pytest.mark.parametrize(
    ("timestamp", "team", "hours"),
    [
        ("2026-03-06T10:15:00", NEW_YORK, 7.25),
        ("2026-03-27T10:15:00", LONDON, 8.0),
        ("2026-10-23T10:15:00", LONDON, 8.0),
        ("2026-10-30T10:15:00", NEW_YORK, 7.25),
        ("2026-06-06T10:15:00", LONDON, 5.5),
    ],
)
def test_add_and_between_round_trip(timestamp, team, hours):
    zone = "Europe/London" if team == LONDON else "America/New_York"
    start = dt(timestamp, zone)
    end = add_bh(start, hours, team)
    assert bh_between(start, end, team) == pytest.approx(hours, abs=1 / 60)


def test_add_from_weekend_starts_at_next_open():
    result = add_bh(dt("2026-05-02T12:00:00", "Europe/London"), 1, LONDON)
    assert result == dt("2026-05-04T10:00:00", "Europe/London")
