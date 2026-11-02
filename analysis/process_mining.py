"""Run the registered synthetic process mining and acceptance checks."""

from __future__ import annotations

import copy
import json
import math
import tempfile
from pathlib import Path
from statistics import NormalDist
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
import sys

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
sys.path.insert(0, str(ROOT / "data"))

from flowmining.classify import INTENDED, classify_components
from flowmining.components import components_from_events
from flowmining.metrics import compute_metrics
from generate_log import generate_scenario


CELLS = ("A1", "A2", "B1", "B2")
EXPECTED_SHARES = {
    "A1": {"approver_share": 0.773, "handoff_share": 0.195, "doer_share": 0.033},
    "A2": {"approver_share": 0.751, "handoff_share": 0.213, "doer_share": 0.036},
    "B1": {"approver_share": 0.105, "handoff_share": 0.862, "doer_share": 0.032},
    "B2": {"approver_share": 0.099, "handoff_share": 0.868, "doer_share": 0.033},
}
OWNER_SHARE_BAND = 0.03
VALUE_SAVED_HOURS = 683.2
VALUE_SAVED_USD = 15030.40
BUILD_COST_USD = 8000.0
RUN_COST_USD = 125.0


def _load_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype={"case_id": str})


def _sigma(dpmo: float) -> float:
    return NormalDist().inv_cdf(1.0 - dpmo / 1_000_000.0) + 1.5


def _quality_metrics(cases: pd.DataFrame) -> dict[str, Any]:
    breach = cases["outcome"].eq("sla_breach")
    reworked = cases["information_loop_count"].astype(int).gt(0)
    defect = breach | reworked
    breach_rate = float(breach.mean())
    defect_rate = float(defect.mean())
    dpmo = defect_rate * 1_000_000.0
    after_defect_rate = None
    sigma_after = None
    after_dpmo = None
    if cases["rework_intensity"].iloc[0] == "high":
        after_defect_rate = 1.0 - (1.0 - breach_rate) * (1.0 - 0.096)
        after_dpmo = after_defect_rate * 1_000_000.0
        sigma_after = _sigma(after_dpmo)
    return {
        "loop_rate": float(reworked.mean()),
        "breach_rate": breach_rate,
        "defect_rate": defect_rate,
        "dpmo": dpmo,
        "sigma_before": _sigma(dpmo),
        "after_defect_rate": after_defect_rate,
        "after_dpmo": after_dpmo,
        "sigma_after": sigma_after,
    }


def _scenario_payload(cell: str, components: pd.DataFrame, cases: pd.DataFrame, metrics: dict[str, Any]) -> dict[str, Any]:
    ownership = classify_components(components)
    cycle_row = metrics["cycle_time"].query("scenario == @cell and case_type == 'ALL'").iloc[0]
    quality = _quality_metrics(cases)
    rework_row = metrics["rework"]["summary"].query("scenario == @cell").iloc[0]
    return {
        "synthetic": True,
        "scenario": cell,
        "case_count": int(len(cases)),
        "intended_classification": INTENDED[cell],
        "classified": ownership["classified"],
        "margin": ownership["margin"],
        "approver_share": ownership["approver_share"],
        "handoff_share": ownership["handoff_share"],
        "doer_share": ownership["doer_share"],
        "wait_share": ownership["wait_share"],
        "cycle_bh_mean": float(cycle_row["cycle_bh_mean"]),
        "cycle_bh_median": float(cycle_row["cycle_bh_median"]),
        "cycle_bh_p90": float(cycle_row["cycle_bh_p90"]),
        "cycle_bh_p95": float(cycle_row["cycle_bh_p95"]),
        "mean_days": float(cycle_row["calendar_days_mean"]),
        "median_days": float(cycle_row["calendar_days_median"]),
        "p90_days": float(cycle_row["calendar_days_p90"]),
        "p95_days": float(cycle_row["calendar_days_p95"]),
        "loop_rate": quality["loop_rate"],
        "mean_loops_per_case": float(rework_row["mean_loops_per_case"]),
        "breach_rate": quality["breach_rate"],
        "defect_rate": quality["defect_rate"],
        "dpmo": quality["dpmo"],
        "sigma_before": quality["sigma_before"],
        "after_defect_rate": quality["after_defect_rate"],
        "after_dpmo": quality["after_dpmo"],
        "sigma_after": quality["sigma_after"],
        "top_three_diagnostics": ownership["top_three_diagnostics"],
        "return_point_pareto": metrics["rework"]["return_point_pareto"].query("scenario == @cell").to_dict(orient="records"),
        "top5_variant_coverage": float(metrics["variants"]["top5_coverage"].query("scenario == @cell")["top5_coverage"].iloc[0]),
        "conformance_rate_exact_path": float(metrics["conformance"]["summary"].query("scenario == @cell")["conformance_rate"].iloc[0]),
    }


def _value_checks() -> tuple[dict[str, float], list[dict[str, Any]]]:
    monthly_savings = VALUE_SAVED_USD / 12.0
    ramp = [0.60] * 4 + [0.80] * 4 + [0.95] * 28
    net_cash = [monthly_savings * coverage - RUN_COST_USD for coverage in ramp]
    cumulative = 0.0
    payback = math.nan
    for month, cash in enumerate(net_cash, start=1):
        if cumulative + cash >= BUILD_COST_USD:
            payback = month - 1 + (BUILD_COST_USD - cumulative) / cash
            break
        cumulative += cash
    monthly_rate = 1.12 ** (1.0 / 12.0) - 1.0
    npv = sum(cash / ((1.0 + monthly_rate) ** month) for month, cash in enumerate(net_cash, start=1)) - BUILD_COST_USD
    sensitivity = []
    for adoption in (0.60, 0.80, 0.95):
        net = monthly_savings * adoption - RUN_COST_USD
        sensitivity.append({"adoption": adoption, "hours": VALUE_SAVED_HOURS * adoption, "gross_usd": monthly_savings * 12.0 * adoption, "steady_state_payback_months": BUILD_COST_USD / net})
    return {"payback_months": payback, "npv_usd": npv}, sensitivity


def acceptance_checks(scenarios: dict[str, dict[str, Any]], touch: pd.DataFrame) -> list[dict[str, Any]]:
    """Evaluate every §1.4 acceptance band without changing any parameters."""
    checks: list[dict[str, Any]] = []

    def add(name: str, value: float, low: float, high: float) -> None:
        passed = math.isfinite(value) and low <= value <= high
        checks.append({"name": name, "value": value, "band": [low, high], "status": "PASS" if passed else "MISS"})

    for cell in CELLS:
        scenario = scenarios[cell]
        add(f"{cell} median calendar days", scenario["median_days"], 5.5, 6.5)
        add(f"{cell} p95 calendar days", scenario["p95_days"], 16.0, 20.0)
        for share in ("approver_share", "handoff_share", "doer_share"):
            target = EXPECTED_SHARES[cell][share]
            add(f"{cell} {share}", scenario[share], target - OWNER_SHARE_BAND, target + OWNER_SHARE_BAND)
        add(f"{cell} owner margin", scenario["margin"], 1.5, math.inf)

    touch = touch.set_index("scenario")
    for cell in CELLS:
        add(f"{cell} intake touch mean minutes", float(touch.loc[cell, "intake_touch_mean_min"]), 11.4, 12.6)
    for cell in ("A2", "B2"):
        add(f"{cell} resubmission touch mean minutes", float(touch.loc[cell, "resubmission_touch_mean_min"]), 20.9, 23.1)
        add(f"{cell} sigma before", scenarios[cell]["sigma_before"], 1.63, 1.93)

    value, _ = _value_checks()
    add("Payback months", value["payback_months"], 9.84, 9.88)
    add("NPV USD", value["npv_usd"], 21777.0, 22077.0)
    return checks


def _confusion_matrix(scenarios: dict[str, dict[str, Any]]) -> dict[str, dict[str, int]]:
    labels = ("APPROVER-BOUND", "HANDOFF-BOUND", "DOER-BOUND", "INDETERMINATE")
    matrix = {expected: {predicted: 0 for predicted in labels} for expected in labels}
    for scenario in scenarios.values():
        matrix[scenario["intended_classification"]][scenario["classified"]] += 1
    return matrix


def _remove_holds(components: pd.DataFrame, cases: pd.DataFrame) -> pd.DataFrame:
    adjusted = components.copy()
    hold_values = cases.set_index("case_id")["hold_hours"].astype(float).to_dict()
    held = cases.set_index("case_id")["hold_applied"].astype(str).str.lower().eq("true").to_dict()
    first_app_owner = (adjusted["step"] == 5) & (adjusted["execution_number"] == 0)
    for index in adjusted.index[first_app_owner]:
        case_id = adjusted.at[index, "case_id"]
        if held.get(case_id, False):
            if case_id.startswith(("A1-", "A2-")):
                component = "queue_bh"
            else:
                component = "handoff_bh"
            adjusted.at[index, component] = max(0.0, float(adjusted.at[index, component]) - hold_values[case_id])
    adjusted["cycle_bh"] = adjusted[["handoff_bh", "queue_bh", "touch_bh"]].sum(axis=1, skipna=True)
    return adjusted


def _jitter_parameters(base: dict[str, Any], rng: np.random.Generator) -> dict[str, Any]:
    """Apply independent +/-10% jitter to numeric model parameters.

    Exact loop-count allocations, sample size, dates, seeds, and structural
    step numbers stay fixed because they define the experiment rather than a
    sampled duration parameter. Probability vectors are renormalized after
    their elements are jittered.
    """
    params = copy.deepcopy(base)

    def factor() -> float:
        return float(rng.uniform(0.9, 1.1))

    for profile in params["activity_profiles"].values():
        for row in profile:
            for key in ("queue_mean_bh", "touch_mean_bh", "handoff_mean_bh"):
                row[key] *= factor()
    for key in params["distribution_sigma"]:
        params["distribution_sigma"][key] *= factor()

    table3 = params["table_3"]
    table3["arrival_in_hours_fraction"] = min(1.0, max(0.0, table3["arrival_in_hours_fraction"] * factor()))
    for probability_map in (table3["case_type_probabilities"],):
        values = {key: value * factor() for key, value in probability_map.items()}
        total = sum(values.values())
        probability_map.update({key: value / total for key, value in values.items()})
    for mapping in (table3["queue_handoff_multiplier"], table3["touch_multiplier"]):
        for key in mapping:
            mapping[key] *= factor()
    for key in table3["sla_calendar_days"]:
        table3["sla_calendar_days"][key] *= factor()
    for key in table3["provisioning_failure_probability"]:
        table3["provisioning_failure_probability"][key] = min(1.0, table3["provisioning_failure_probability"][key] * factor())
    for key in ("return_handoff_mean_bh", "replay_approval_queue_fraction", "resubmission_touch_total_mean_minutes", "intake_touch_mean_bh", "resubmission_touch_sigma", "intake_touch_sigma"):
        table3[key] *= factor()
    for key in table3["resubmission_touch_mean_bh"]:
        table3["resubmission_touch_mean_bh"][key] *= factor()
    hold = table3["hold"]
    for key in ("case_fraction", "mean_bh", "sigma"):
        hold[key] = min(1.0, hold[key] * factor()) if key == "case_fraction" else hold[key] * factor()

    for probabilities in (table3["regions"],):
        values = {key: region["probability"] * factor() for key, region in probabilities.items()}
        total = sum(values.values())
        for key, region in probabilities.items():
            region["probability"] = values[key] / total
    for intensity in ("low", "high"):
        points = table3["rework_case_shares"][intensity]["return_point_probabilities"]
        values = {key: value * factor() for key, value in points.items()}
        total = sum(values.values())
        points.update({key: value / total for key, value in values.items()})
    return params


def _load_cell(cell: str, data_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    components = components_from_events(data_dir / f"event_log_{cell}.csv")
    cases = _load_csv(data_dir / f"cases_{cell}.csv")
    return components, cases


def _run_robustness(
    components_by_cell: dict[str, pd.DataFrame],
    cases_by_cell: dict[str, pd.DataFrame],
    base_params: dict[str, Any],
    out_dir: Path,
) -> dict[str, Any]:
    hold_rows = []
    for cell in CELLS:
        adjusted = _remove_holds(components_by_cell[cell], cases_by_cell[cell])
        classified = classify_components(adjusted)
        hold_rows.append({
            "scenario": cell, "intended": INTENDED[cell], "classified": classified["classified"],
            "margin": classified["margin"], "wait_share": classified["wait_share"],
        })

    jitter_rows = []
    rng = np.random.default_rng(7831)
    with tempfile.TemporaryDirectory(prefix="access_flow_jitter_") as temp_root:
        temp_path = Path(temp_root)
        for repetition in range(1, 6):
            jittered = _jitter_parameters(base_params, rng)
            for cell in CELLS:
                output_dir = temp_path / f"rep_{repetition}_{cell}"
                event_path, _ = generate_scenario(cell, output_dir, params_override=jittered)
                comp = components_from_events(event_path)
                result = classify_components(comp)
                jitter_rows.append({
                    "repetition": repetition, "scenario": cell,
                    "intended": INTENDED[cell], "classified": result["classified"],
                    "margin": result["margin"], "wait_share": result["wait_share"],
                })

    hold_pass = all(row["classified"] == row["intended"] and row["margin"] >= 1.5 for row in hold_rows)
    jitter_pass_count = sum(row["classified"] == row["intended"] and row["margin"] >= 1.5 for row in jitter_rows)
    return {
        "synthetic": True,
        "hold_removed": {"pass": hold_pass, "results": hold_rows},
        "jitter": {
            "repetitions": 5,
            "scenarios": 4,
            "correct_with_margin": jitter_pass_count,
            "total": len(jitter_rows),
            "pass": jitter_pass_count == len(jitter_rows),
            "margin_min": min(row["margin"] for row in jitter_rows),
            "margin_max": max(row["margin"] for row in jitter_rows),
            "results": jitter_rows,
        },
    }


def run_analysis(data_dir: Path | str | None = None, output_dir: Path | str | None = None) -> dict[str, Any]:
    data_path = Path(data_dir) if data_dir is not None else ROOT / "data"
    results_path = Path(output_dir) if output_dir is not None else ROOT / "analysis" / "results"
    results_path.mkdir(parents=True, exist_ok=True)
    with (data_path / "params.json").open(encoding="utf-8") as handle:
        params = json.load(handle)

    components_by_cell: dict[str, pd.DataFrame] = {}
    cases_by_cell: dict[str, pd.DataFrame] = {}
    all_components = []
    all_cases = []
    for cell in CELLS:
        components, cases = _load_cell(cell, data_path)
        components_by_cell[cell] = components
        cases_by_cell[cell] = cases
        all_components.append(components)
        all_cases.append(cases)
    merged_components = pd.concat(all_components, ignore_index=True)
    merged_cases = pd.concat(all_cases, ignore_index=True)
    metrics = compute_metrics(merged_components, merged_cases)

    scenarios = {
        cell: _scenario_payload(cell, components_by_cell[cell], cases_by_cell[cell], metrics)
        for cell in CELLS
    }
    for cell, payload in scenarios.items():
        with (results_path / f"scenario_{cell}.json").open("w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=True, allow_nan=False)
            handle.write("\n")

    verdict = {
        "synthetic": True,
        "intended_by_cell": INTENDED,
        "confusion_matrix": _confusion_matrix(scenarios),
        "all_four_correct": all(scenarios[cell]["classified"] == INTENDED[cell] for cell in CELLS),
        "all_margins_at_least_1_5": all(scenarios[cell]["margin"] >= 1.5 for cell in CELLS),
        "no_indeterminate": all(scenarios[cell]["classified"] != "INDETERMINATE" for cell in CELLS),
        "wait_share_contradiction": any(
            scenarios[cell]["classified"] == "HANDOFF-BOUND" and scenarios[cell]["wait_share"] <= 0.60
            for cell in CELLS
        ),
    }
    verdict["pass"] = verdict["all_four_correct"] and verdict["all_margins_at_least_1_5"] and verdict["no_indeterminate"] and not verdict["wait_share_contradiction"]
    with (results_path / "verdict.json").open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(verdict, handle, indent=2, ensure_ascii=True, allow_nan=False)
        handle.write("\n")

    touch = metrics["touch_means"]
    checks = acceptance_checks(scenarios, touch)
    for check in checks:
        print(f"{check['name']} = {check['value']:.6f} [{check['band'][0]:.6f}, {check['band'][1]:.6f}] {check['status']}")
    misses = [check for check in checks if check["status"] == "MISS"]
    if misses:
        print("Acceptance band MISS recorded; continuing only with the requested robustness checks. Parameters were not changed.")
    verdict["acceptance_bands_pass"] = not misses
    verdict["acceptance_band_misses"] = [check["name"] for check in misses]
    with (results_path / "verdict.json").open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(verdict, handle, indent=2, ensure_ascii=True, allow_nan=False)
        handle.write("\n")

    robustness = _run_robustness(components_by_cell, cases_by_cell, params, results_path)
    with (results_path / "robustness.json").open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(robustness, handle, indent=2, ensure_ascii=True, allow_nan=False)
        handle.write("\n")
    print(f"Hold-removed robustness = {'PASS' if robustness['hold_removed']['pass'] else 'MISS'}")
    print(f"Jitter robustness = {robustness['jitter']['correct_with_margin']}/{robustness['jitter']['total']} {'PASS' if robustness['jitter']['pass'] else 'MISS'}")
    return {"scenarios": scenarios, "verdict": verdict, "acceptance_checks": checks, "robustness": robustness}


if __name__ == "__main__":
    run_analysis()
