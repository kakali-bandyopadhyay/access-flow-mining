"""Pre-registered synthetic value model for intake validation automation."""

from __future__ import annotations

from typing import Any


ANNUAL_CASES = 4000
INTAKE_MINUTES_PER_CASE = 12.0
REWORK_REDUCTION = 0.12
RESUBMISSION_MINUTES_PER_REWORK_CASE = 22.0
BASELINE_COVERAGE = 0.70
HOURLY_VALUE_USD = 22.0
RUN_COST_MONTHLY_USD = 125.0
BUILD_COST_USD = 8000.0
ANNUAL_DISCOUNT_RATE = 0.12
RAMP = [(month, 0.60 if month <= 4 else 0.80 if month <= 8 else 0.95) for month in range(1, 37)]


def calculate_value_model() -> dict[str, Any]:
    """Return value, stepped cash flow, payback, NPV, and steady-state sensitivity."""
    direct_hours = ANNUAL_CASES * INTAKE_MINUTES_PER_CASE / 60.0 * BASELINE_COVERAGE
    rework_hours = ANNUAL_CASES * REWORK_REDUCTION * RESUBMISSION_MINUTES_PER_REWORK_CASE / 60.0 * BASELINE_COVERAGE
    total_hours = direct_hours + rework_hours
    annual_gross_usd = total_hours * HOURLY_VALUE_USD
    monthly_rate = (1.0 + ANNUAL_DISCOUNT_RATE) ** (1.0 / 12.0) - 1.0

    cash_rows = []
    cumulative = -BUILD_COST_USD
    cumulative_values = [cumulative]
    payback_months = None
    for month, adoption in RAMP:
        gross = annual_gross_usd / 12.0 * adoption
        net = gross - RUN_COST_MONTHLY_USD
        start_cumulative = cumulative
        cumulative += net
        cash_rows.append({
            "month": month,
            "adoption": adoption,
            "gross_savings_usd": gross,
            "run_cost_usd": RUN_COST_MONTHLY_USD,
            "net_cash_flow_usd": net,
            "cumulative_net_value_usd": cumulative,
        })
        cumulative_values.append(cumulative)
        if payback_months is None and cumulative >= 0:
            payback_months = (month - 1) + (-start_cumulative / net)

    npv = sum(row["net_cash_flow_usd"] / (1.0 + monthly_rate) ** row["month"] for row in cash_rows) - BUILD_COST_USD
    sensitivity = []
    for adoption in (0.60, 0.80, 0.95):
        annual_hours = total_hours * adoption
        gross_annual = annual_hours * HOURLY_VALUE_USD
        annual_run = RUN_COST_MONTHLY_USD * 12.0
        steady_net_monthly = gross_annual / 12.0 - RUN_COST_MONTHLY_USD
        sensitivity.append({
            "adoption": adoption,
            "hours_per_year": annual_hours,
            "gross_value_usd_per_year": gross_annual,
            "run_cost_usd_per_year": annual_run,
            "net_value_usd_per_year": gross_annual - annual_run,
            "steady_state_payback_months": BUILD_COST_USD / steady_net_monthly,
        })

    return {
        "synthetic": True,
        "currency": "USD",
        "annual_cases": ANNUAL_CASES,
        "hourly_value_usd": HOURLY_VALUE_USD,
        "baseline_coverage": BASELINE_COVERAGE,
        "annual_savings": {
            "direct_handling": {"hours_per_year": direct_hours, "value_usd_per_year": direct_hours * HOURLY_VALUE_USD},
            "rework_avoided": {"hours_per_year": rework_hours, "value_usd_per_year": rework_hours * HOURLY_VALUE_USD},
            "total": {"hours_per_year": total_hours, "value_usd_per_year": annual_gross_usd},
        },
        "ramp": {
            "build_cost_usd": BUILD_COST_USD,
            "run_cost_usd_per_month": RUN_COST_MONTHLY_USD,
            "annual_discount_rate": ANNUAL_DISCOUNT_RATE,
            "monthly_discount_rate": monthly_rate,
            "payback_months": payback_months,
            "npv_36_months_usd": npv,
            "cash_flows": cash_rows,
            "cumulative_months": list(range(37)),
            "cumulative_net_value_usd": cumulative_values,
        },
        "sensitivity": sensitivity,
    }
