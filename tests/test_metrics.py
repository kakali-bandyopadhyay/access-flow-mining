import csv
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from flowmining.components import components_from_events
from flowmining.metrics import (
    case_cycle_times,
    compute_metrics,
    conformance_results,
    touch_means,
)


def _fixed_events():
    rows = []
    specs = [
        ("Submit request", "requester_india", "Asia/Kolkata", "2026-05-04T09:00:00+05:30", "2026-05-04T09:30:00+05:30", "2026-05-04T10:00:00+05:30"),
        ("Validate request", "access_service_desk", "Asia/Kolkata", "2026-05-04T11:00:00+05:30", "2026-05-04T12:00:00+05:30", "2026-05-04T12:15:00+05:30"),
        ("Line manager approval", "line_management_india", "Asia/Kolkata", "2026-05-04T13:15:00+05:30", "2026-05-04T13:45:00+05:30", "2026-05-04T14:45:00+05:30"),
    ]
    for activity, team, zone, schedule, start, complete in specs:
        for lifecycle, timestamp in (("schedule", schedule), ("start", start), ("complete", complete)):
            rows.append({
                "case_id": "T-C0001", "activity": activity, "lifecycle": lifecycle,
                "timestamp": timestamp, "resource": "SYN-IN-01", "team": team, "timezone": zone,
            })
    return pd.DataFrame(rows)


def test_components_match_hand_computed_fixed_case():
    result = components_from_events(_fixed_events()).sort_values("step").reset_index(drop=True)
    assert pd.isna(result["handoff_bh"].iloc[0])  # no handoff for opening step
    assert result.loc[0, ["queue_bh", "touch_bh"]].tolist() == pytest.approx([0.50, 0.50])
    assert result.loc[1, ["handoff_bh", "queue_bh", "touch_bh"]].tolist() == pytest.approx([1.00, 1.00, 0.25])
    assert result.loc[2, ["handoff_bh", "queue_bh", "touch_bh"]].tolist() == pytest.approx([1.00, 0.50, 1.00])
    assert result["cycle_bh"].sum() == pytest.approx(5.75)
    case_cycle = case_cycle_times(result).iloc[0]
    assert case_cycle["cycle_bh"] == pytest.approx(5.75)
    assert case_cycle["calendar_days"] == pytest.approx(5.75 / 24.0)


def test_reentry_at_step_one_keeps_return_handoff():
    rows = _fixed_events().to_dict("records")
    for lifecycle, timestamp in (
        ("schedule", "2026-05-04T16:00:00+05:30"),
        ("start", "2026-05-04T16:10:00+05:30"),
        ("complete", "2026-05-04T16:20:00+05:30"),
    ):
        rows.append({
            "case_id": "T-C0001", "activity": "Submit request", "lifecycle": lifecycle,
            "timestamp": timestamp, "resource": "SYN-IN-01", "team": "requester_india", "timezone": "Asia/Kolkata",
        })
    result = components_from_events(pd.DataFrame(rows))
    returned = result[(result["step"] == 1) & (result["execution_number"] == 1)].iloc[0]
    assert returned["handoff_bh"] == pytest.approx(1.25)
    assert returned["is_replay"]


def test_conformance_requires_the_exact_eight_activity_trace():
    from flowmining.metrics import conformance_results

    rows = []
    for case_id, trace in (("X-C0001", list(range(1, 9))), ("X-C0002", [1, 2, 1, 2, 3, 4, 5, 6, 7, 8]), ("X-C0003", [1, 2, 3, 4, 5, 6, 7, 6, 7, 8])):
        for index, step in enumerate(trace):
            rows.append({
                "case_id": case_id, "scenario": "X", "step": step,
                "schedule": pd.Timestamp("2026-05-04T09:00:00Z") + pd.Timedelta(minutes=index),
                "execution_number": trace[:index].count(step),
            })
    result = conformance_results(pd.DataFrame(rows)).set_index("case_id")
    assert result.loc["X-C0001", "conformant"]
    assert not result.loc["X-C0002", "conformant"]
    assert not result.loc["X-C0003", "conformant"]


@pytest.fixture(scope="module")
def mined():
    component_frames = []
    case_frames = []
    for scenario in ("A1", "A2", "B1", "B2"):
        component_frames.append(components_from_events(ROOT / "data" / f"event_log_{scenario}.csv"))
        with (ROOT / "data" / f"cases_{scenario}.csv").open(encoding="utf-8", newline="") as handle:
            case_frames.append(pd.DataFrame(list(csv.DictReader(handle))))
    return pd.concat(component_frames, ignore_index=True), pd.concat(case_frames, ignore_index=True)


def test_metrics_cover_cycle_time_rework_variants_and_conformance(mined):
    components, cases = mined
    metrics = compute_metrics(components, cases)
    cycle = metrics["cycle_time"]
    assert set(cycle["scenario"]) == {"A1", "A2", "B1", "B2"}
    assert set(cycle["case_type"]) == {"ALL", "standard", "privileged", "emergency"}
    assert (cycle["case_count"] > 0).all()
    assert (cycle["cycle_bh_p95"] >= cycle["cycle_bh_median"]).all()
    conformance = metrics["conformance"]["summary"].set_index("scenario")
    for scenario, case_group in cases.groupby("scenario"):
        loop_rate = (case_group["information_loop_count"].astype(int) > 0).mean()
        provision_rate = (case_group["provisioning_failure_count"].astype(int) > 0).mean()
        observed = conformance.loc[scenario, "conformance_rate"]
        assert 1.0 - loop_rate - provision_rate <= observed <= 1.0 - max(loop_rate, provision_rate)
    exact_paths = conformance_results(components)
    assert exact_paths.loc[exact_paths["conformant"], "trace"].map(lambda trace: trace == list(range(1, 9))).all()
    assert (metrics["variants"]["top5_coverage"]["top5_coverage"] > 0).all()
    assert (metrics["variants"]["top5_coverage"]["top5_coverage"] <= 1).all()
    rates = metrics["rework"]["summary"].set_index("scenario")["rework_rate"]
    assert rates.to_dict() == pytest.approx({"A1": 0.04, "A2": 0.18, "B1": 0.04, "B2": 0.18})
    assert set(metrics["rework"]["return_point_pareto"]["return_point"]) <= {2, 3, 5}


def test_touch_means_are_reported_against_registered_bands(mined):
    components, _ = mined
    means = touch_means(components).set_index("scenario")
    assert (means["intake_touch_mean_min"].between(11.4, 12.6)).all()
    assert means.loc["A2", "resubmission_touch_mean_min"] == pytest.approx(22.0, abs=1.1)
    assert means.loc["B2", "resubmission_touch_mean_min"] == pytest.approx(22.0, abs=1.1)

