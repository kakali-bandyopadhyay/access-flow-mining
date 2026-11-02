import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from flowmining.classify import classify_components, classify_shares


@pytest.mark.parametrize(
    ("shares", "expected"),
    [
        ((0.60, 0.30, 0.10), "APPROVER-BOUND"),
        ((0.20, 0.60, 0.20), "HANDOFF-BOUND"),
        ((0.10, 0.20, 0.70), "DOER-BOUND"),
        ((0.40, 0.35, 0.25), "INDETERMINATE"),
    ],
)
def test_classifier_covers_each_class(shares, expected):
    assert classify_shares(*shares)["classified"] == expected


def test_classifier_accepts_margin_exactly_at_one_and_a_half():
    result = classify_shares(0.60, 0.40, 0.0)
    assert result["margin"] == pytest.approx(1.5)
    assert result["classified"] == "APPROVER-BOUND"


def test_handoff_share_includes_handoffs_at_approval_steps():
    components = pd.DataFrame([
        {"step": 2, "activity": "Validate request", "handoff_bh": 30.0, "queue_bh": 10.0, "touch_bh": 5.0},
        {"step": 3, "activity": "Line manager approval", "handoff_bh": 100.0, "queue_bh": 10.0, "touch_bh": 5.0},
    ])
    result = classify_components(components)
    assert result["handoff_hours"] == pytest.approx(140.0)
    assert result["handoff_share"] == pytest.approx(140 / 160)

