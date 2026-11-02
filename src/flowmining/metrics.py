"""Case-level process, rework, variant, and touch metrics."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .components import case_cycle_times


def _read_cases(cases: pd.DataFrame | str | Path | None, components: pd.DataFrame) -> pd.DataFrame:
    if cases is None:
        case_ids = components["case_id"].drop_duplicates()
        return pd.DataFrame({"case_id": case_ids, "scenario": case_ids.str.split("-", n=1).str[0]})
    frame = pd.read_csv(cases, dtype={"case_id": str}) if isinstance(cases, (str, Path)) else cases.copy()
    if "case_id" not in frame:
        raise ValueError("case table must contain case_id")
    if "scenario" not in frame:
        frame["scenario"] = frame["case_id"].str.split("-", n=1).str[0]
    return frame


def cycle_time_summary(components: pd.DataFrame, cases: pd.DataFrame | str | Path | None = None) -> pd.DataFrame:
    """Summarize business-hour and calendar-day cycle time by cell and case type."""
    cycle = case_cycle_times(components)
    metadata = _read_cases(cases, components)
    if "case_type" not in metadata:
        metadata["case_type"] = "unknown"
    cycle = cycle.merge(metadata[["case_id", "scenario", "case_type"]], on="case_id", suffixes=("", "_case"), validate="one_to_one")
    cycle["scenario"] = cycle["scenario_case"].fillna(cycle["scenario"]) if "scenario_case" in cycle else cycle["scenario"]
    cycle = cycle.drop(columns=[c for c in ("scenario_case",) if c in cycle])
    cycle["case_type"] = cycle["case_type"].fillna("unknown")
    all_rows = cycle.copy()
    all_rows["case_type"] = "ALL"
    grouped = pd.concat([cycle, all_rows], ignore_index=True)

    records: list[dict[str, Any]] = []
    for (scenario, case_type), group in grouped.groupby(["scenario", "case_type"], sort=True):
        record: dict[str, Any] = {"scenario": scenario, "case_type": case_type, "case_count": int(len(group))}
        for field in ("cycle_bh", "calendar_days"):
            values = group[field].to_numpy(dtype=float)
            record[f"{field}_mean"] = float(np.mean(values))
            record[f"{field}_median"] = float(np.median(values))
            record[f"{field}_p90"] = float(np.quantile(values, 0.90))
            record[f"{field}_p95"] = float(np.quantile(values, 0.95))
        records.append(record)
    return pd.DataFrame.from_records(records)


def _case_traces(components: pd.DataFrame) -> dict[str, list[int]]:
    traces: dict[str, list[int]] = {}
    for case_id, group in components.groupby("case_id", sort=True):
        ordered = group.sort_values(["schedule", "execution_number"], kind="stable")
        traces[case_id] = ordered["step"].astype(int).tolist()
    return traces


def conformance_results(components: pd.DataFrame) -> pd.DataFrame:
    """Mark only the exact 1,2,3,4,5,6,7,8 path conformant.

    Any activity repetition, information return, or provisioning retry is
    non-conforming for this strict designed-path measure.
    """
    traces = _case_traces(components)
    rows = []
    for case_id, trace in traces.items():
        conforms = trace == [1, 2, 3, 4, 5, 6, 7, 8]
        rows.append({"case_id": case_id, "scenario": case_id.split("-", 1)[0], "conformant": bool(conforms), "trace": trace})
    return pd.DataFrame(rows)


def variant_metrics(components: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Return observed trace variants, sorted counts, shares, and top-five coverage."""
    traces = _case_traces(components)
    case_scenario = components[["case_id", "scenario"]].drop_duplicates().set_index("case_id")["scenario"].to_dict()
    counts: dict[tuple[str, str], int] = {}
    for case_id, trace in traces.items():
        variant = ">".join(map(str, trace))
        key = (case_scenario[case_id], variant)
        counts[key] = counts.get(key, 0) + 1

    variant_rows = []
    coverage_rows = []
    for scenario in sorted(set(case_scenario.values())):
        values = [(variant, count) for (cell, variant), count in counts.items() if cell == scenario]
        total = sum(count for _, count in values)
        values.sort(key=lambda item: (-item[1], item[0]))
        cumulative = 0
        for rank, (variant, count) in enumerate(values, start=1):
            cumulative += count
            variant_rows.append({
                "scenario": scenario, "rank": rank, "variant": variant,
                "case_count": count, "share": count / total,
                "cumulative_share": cumulative / total,
            })
        top5 = sum(count for _, count in values[:5])
        coverage_rows.append({"scenario": scenario, "case_count": total, "unique_variants": len(values), "top5_coverage": top5 / total})
    return {"variants": pd.DataFrame(variant_rows), "top5_coverage": pd.DataFrame(coverage_rows)}


def rework_metrics(components: pd.DataFrame, cases: pd.DataFrame | str | Path | None = None) -> dict[str, pd.DataFrame]:
    """Summarize information-return loops and their return-point Pareto."""
    metadata = _read_cases(cases, components)
    traces = _case_traces(components)
    loop_counts: dict[str, int] = {}
    return_observations: list[tuple[str, int]] = []
    for case_id, trace in traces.items():
        loop_counts[case_id] = trace.count(1) - 1
        for previous, current in zip(trace, trace[1:]):
            if current == 1:
                return_observations.append((case_id, previous))

    case_frame = metadata[["case_id", "scenario"]].drop_duplicates().copy()
    case_frame["information_loop_count"] = case_frame["case_id"].map(loop_counts).fillna(0).astype(int)
    case_frame["has_rework"] = case_frame["information_loop_count"] > 0
    summary_rows = []
    for scenario, group in case_frame.groupby("scenario", sort=True):
        summary_rows.append({
            "scenario": scenario,
            "case_count": int(len(group)),
            "rework_rate": float(group["has_rework"].mean()),
            "mean_loops_per_case": float(group["information_loop_count"].mean()),
        })
    loop_distribution = (
        case_frame.groupby(["scenario", "information_loop_count"], as_index=False)
        .size().rename(columns={"size": "case_count"})
    )

    point_counts: dict[tuple[str, int], int] = {}
    for case_id, point in return_observations:
        scenario = case_id.split("-", 1)[0]
        point_counts[(scenario, point)] = point_counts.get((scenario, point), 0) + 1
    pareto_rows = []
    for scenario in sorted(case_frame["scenario"].unique()):
        values = sorted(
            ((point, count) for (cell, point), count in point_counts.items() if cell == scenario),
            key=lambda item: (-item[1], item[0]),
        )
        total = sum(count for _, count in values)
        cumulative = 0
        for rank, (point, count) in enumerate(values, start=1):
            cumulative += count
            pareto_rows.append({
                "scenario": scenario, "rank": rank, "return_point": point,
                "loop_count": count, "share": count / total if total else 0.0,
                "cumulative_share": cumulative / total if total else 0.0,
            })
    return {
        "summary": pd.DataFrame(summary_rows),
        "loops_per_case": loop_distribution,
        "return_point_pareto": pd.DataFrame(pareto_rows),
    }


def touch_means(components: pd.DataFrame) -> pd.DataFrame:
    """Return first-pass intake touch and mean replay touch per info loop, in minutes."""
    rows = []
    for scenario, group in components.groupby("scenario", sort=True):
        step2 = group[(group["step"] == 2) & (group["execution_number"] == 0)]
        replays = group[(group["step"].isin([1, 2])) & (group["execution_number"] > 0)]
        per_case_loops = group[group["step"] == 1].groupby("case_id").size().sub(1).clip(lower=0)
        total_loops = int(per_case_loops.sum())
        resub_touch_minutes = float(replays["touch_bh"].sum() * 60.0)
        rows.append({
            "scenario": scenario,
            "intake_touch_mean_min": float(step2["touch_bh"].mean() * 60.0),
            "resubmission_touch_mean_min": resub_touch_minutes / total_loops if total_loops else float("nan"),
            "information_loop_count": total_loops,
        })
    return pd.DataFrame(rows)


def compute_metrics(components: pd.DataFrame, cases: pd.DataFrame | str | Path | None = None) -> dict[str, Any]:
    """Convenience bundle for deliverable 3's requested metrics."""
    conformance = conformance_results(components)
    conformance_summary = conformance.groupby("scenario", as_index=False).agg(
        case_count=("case_id", "count"), conformant_cases=("conformant", "sum")
    )
    conformance_summary["conformance_rate"] = conformance_summary["conformant_cases"] / conformance_summary["case_count"]
    return {
        "cycle_time": cycle_time_summary(components, cases),
        "rework": rework_metrics(components, cases),
        "variants": variant_metrics(components),
        "conformance": {"cases": conformance, "summary": conformance_summary},
        "touch_means": touch_means(components),
    }
