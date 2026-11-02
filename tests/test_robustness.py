import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_hold_removed_run_preserves_all_four_classifications():
    path = ROOT / "analysis" / "results" / "robustness.json"
    with path.open(encoding="utf-8") as handle:
        robustness = json.load(handle)
    assert robustness["synthetic"] is True
    hold = robustness["hold_removed"]
    assert hold["pass"] is True
    assert len(hold["results"]) == 4
    assert all(row["classified"] == row["intended"] for row in hold["results"])
    assert all(row["margin"] >= 1.5 for row in hold["results"])


def test_jitter_run_classifies_all_twenty_cell_repetitions():
    path = ROOT / "analysis" / "results" / "robustness.json"
    with path.open(encoding="utf-8") as handle:
        jitter = json.load(handle)["jitter"]
    assert jitter["repetitions"] == 5
    assert jitter["scenarios"] == 4
    assert jitter["total"] == 20
    assert jitter["correct_with_margin"] == 20
    assert jitter["pass"] is True
    assert all(row["classified"] == row["intended"] and row["margin"] >= 1.5 for row in jitter["results"])
