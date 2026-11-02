import csv
import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "data"))

from flowmining.calendar_bh import add_bh, bh_between
from generate_log import _lognormal_hours, generate_scenario


@pytest.fixture(scope="module")
def params():
    with (ROOT / "data" / "params.json").open(encoding="utf-8") as handle:
        return json.load(handle)


@pytest.mark.parametrize("scenario", ["A1", "A2", "B1", "B2"])
def test_seeded_generation_is_byte_identical(tmp_path, scenario):
    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"
    first_paths = generate_scenario(scenario, first_dir)
    second_paths = generate_scenario(scenario, second_dir)
    assert [path.read_bytes() for path in first_paths] == [path.read_bytes() for path in second_paths]


@pytest.mark.parametrize(
    ("zone", "team", "start", "mean", "sigma"),
    [
        ("Asia/Kolkata", "access_service_desk", "2026-04-01T09:17:00", 0.75, 0.55),
        ("Europe/London", "access_risk_controls", "2026-03-27T09:17:00", 4.71, 0.55),
        ("America/New_York", "application_owners", "2026-10-30T09:17:00", 0.86, 0.60),
    ],
)
def test_drawn_component_round_trip_within_one_minute(zone, team, start, mean, sigma):
    import numpy as np

    rng = np.random.default_rng(777)
    timestamp = datetime.fromisoformat(start).replace(tzinfo=ZoneInfo(zone))
    for _ in range(40):
        hours = _lognormal_hours(rng, mean, sigma)
        end = add_bh(timestamp, hours, team)
        assert bh_between(timestamp, end, team) == pytest.approx(hours, abs=1 / 60)


@pytest.mark.parametrize("scenario,expected_rate", [("A1", 0.04), ("B1", 0.04), ("A2", 0.18), ("B2", 0.18)])
def test_information_loop_rates_are_allocated_exactly(scenario, expected_rate, params):
    case_path = ROOT / "data" / f"cases_{scenario}.csv"
    if not case_path.exists():
        generate_scenario(scenario)
    with case_path.open(encoding="utf-8", newline="") as handle:
        cases = list(csv.DictReader(handle))
    observed = sum(int(row["information_loop_count"]) > 0 for row in cases) / len(cases)
    once = sum(int(row["information_loop_count"]) == 1 for row in cases) / len(cases)
    twice = sum(int(row["information_loop_count"]) == 2 for row in cases) / len(cases)
    assert observed == expected_rate
    expected_once, expected_twice = (0.035, 0.005) if expected_rate == 0.04 else (0.15, 0.03)
    assert once == expected_once
    assert twice == expected_twice
    assert len(cases) == params["table_3"]["cases_per_scenario"]


def test_touch_means_are_identical_across_all_cells(params):
    profiles = params["activity_profiles"]
    a_touch = [row["touch_mean_bh"] for row in profiles["A"]]
    b_touch = [row["touch_mean_bh"] for row in profiles["B"]]
    assert a_touch == b_touch
    assert [row["touch_mean_bh"] for row in profiles["A"]] == [0.05, 0.20, 0.10, 0.25, 0.15, 0.70, 0.10, 0.05]

