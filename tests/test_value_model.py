import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from flowmining.value_model import calculate_value_model


@pytest.fixture(scope="module")
def result():
    return calculate_value_model()


def test_annual_hours_and_usd_are_separate_and_reconcile(result):
    annual = result["annual_savings"]
    assert annual["total"]["hours_per_year"] == pytest.approx(683.2)
    assert annual["total"]["value_usd_per_year"] == pytest.approx(15030.4)
    assert annual["direct_handling"]["hours_per_year"] == pytest.approx(560.0)
    assert annual["rework_avoided"]["hours_per_year"] == pytest.approx(123.2)
    assert annual["direct_handling"]["value_usd_per_year"] == pytest.approx(12320.0)
    assert annual["rework_avoided"]["value_usd_per_year"] == pytest.approx(2710.4)


def test_payback_and_npv_are_within_registered_bands(result):
    ramp = result["ramp"]
    assert ramp["payback_months"] == pytest.approx(9.86, abs=0.02)
    assert ramp["npv_36_months_usd"] == pytest.approx(21927.0, abs=150.0)
    assert ramp["cumulative_net_value_usd"][0] == -8000.0
    assert len(ramp["cumulative_net_value_usd"]) == 37


def test_steady_state_sensitivity_matches_registered_months(result):
    rows = result["sensitivity"]
    assert [row["adoption"] for row in rows] == [0.60, 0.80, 0.95]
    assert [row["steady_state_payback_months"] for row in rows] == pytest.approx([12.77, 9.12, 7.51], abs=0.01)
    assert all("hours_per_year" in row and "gross_value_usd_per_year" in row for row in rows)
