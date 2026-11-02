"""Build the five registered synthetic data figures at 150 dpi."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "analysis" / "results"
FIGURES = ROOT / "figures"
CELLS = ("A1", "A2", "B1", "B2")
COLORS = {"approver_share": "#4472C4", "handoff_share": "#ED7D31", "doer_share": "#70AD47"}


def _scenario(cell: str) -> dict:
    with (RESULTS / f"scenario_{cell}.json").open(encoding="utf-8") as handle:
        return json.load(handle)


def _footer(fig) -> None:
    fig.text(0.5, 0.012, "Synthetic data", ha="center", va="bottom", fontsize=9, color="#555555")


def figure_owner_shares() -> Path:
    scenarios = [_scenario(cell) for cell in CELLS]
    fig, ax = plt.subplots(figsize=(9, 5.5), constrained_layout=False)
    bottom = np.zeros(len(CELLS))
    for key, label in (("approver_share", "Approver"), ("handoff_share", "Handoff"), ("doer_share", "Doer")):
        values = np.array([scenario[key] for scenario in scenarios])
        ax.bar(CELLS, values, bottom=bottom, color=COLORS[key], label=label, width=0.64)
        bottom += values
    for index, scenario in enumerate(scenarios):
        ax.text(index, 1.025, f"Margin {scenario['margin']:.2f}x", ha="center", va="bottom", fontsize=9)
    ax.set_ylim(0, 1.13)
    ax.set_ylabel("Share of cycle business hours")
    ax.set_title("Delay owner shares by synthetic cell")
    ax.legend(ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.12), frameon=False)
    ax.grid(axis="y", alpha=0.22)
    _footer(fig)
    fig.subplots_adjust(bottom=0.20, top=0.85)
    path = FIGURES / "owner_shares.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def figure_top_three() -> Path:
    scenarios = [_scenario(cell) for cell in CELLS]
    fig, axes = plt.subplots(2, 2, figsize=(12, 8), sharex=False)
    for ax, scenario in zip(axes.flat, scenarios):
        pairs = scenario["top_three_diagnostics"]
        labels = [f"{pair['activity']}\n{pair['component']}" for pair in reversed(pairs)]
        values = [pair["hours"] for pair in reversed(pairs)]
        ax.barh(labels, values, color="#4472C4")
        ax.set_title(scenario["scenario"])
        ax.set_xlabel("Summed business hours")
        ax.grid(axis="x", alpha=0.22)
    fig.suptitle("Top three delay components by cell", y=0.98)
    _footer(fig)
    fig.tight_layout(rect=(0, 0.035, 1, 0.95))
    path = FIGURES / "top3_pairs.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def figure_cycle_distribution() -> Path:
    samples = {}
    scenario_results = {cell: _scenario(cell) for cell in CELLS}
    all_values = []
    for cell in CELLS:
        path = ROOT / "data" / f"event_log_{cell}.csv"
        events = pd.read_csv(path, usecols=["case_id", "lifecycle", "timestamp"])
        events["timestamp_utc"] = pd.to_datetime(events["timestamp"], utc=True)
        first = events.loc[events["lifecycle"] == "schedule"].groupby("case_id")["timestamp_utc"].min()
        last = events.loc[events["lifecycle"] == "complete"].groupby("case_id")["timestamp_utc"].max()
        days = (last - first).dt.total_seconds() / 86400.0
        samples[cell] = days.to_numpy()
        all_values.extend(days.to_numpy().tolist())

    with (ROOT / "data" / "params.json").open(encoding="utf-8") as handle:
        sla_targets = sorted(set(json.load(handle)["table_3"]["sla_calendar_days"].values()))

    colors = {"A1": "#4472C4", "A2": "#5B9BD5", "B1": "#ED7D31", "B2": "#F4B183"}
    fig, ax = plt.subplots(figsize=(10, 6))
    for cell in CELLS:
        values = np.sort(samples[cell])
        visible = values[values <= 40]
        x = np.concatenate(([0.0], visible))
        y = np.concatenate(([0.0], 100.0 * np.arange(1, len(visible) + 1) / len(values)))
        ax.step(x, y, where="post", color=colors[cell], linewidth=2, label=cell)

        result = scenario_results[cell]
        offsets = {
            ("A1", "median"): (-54, -24), ("A2", "median"): (-54, 12),
            ("B1", "median"): (10, -24), ("B2", "median"): (10, 12),
            ("A1", "p95"): (-60, -28), ("A2", "p95"): (-60, -46),
            ("B1", "p95"): (10, 12), ("B2", "p95"): (10, -28),
        }
        for label, field, percentile in (("median", "median_days", 50), ("p95", "p95_days", 95)):
            value = float(result[field])
            ax.scatter([value], [percentile], color=colors[cell], edgecolor="white", linewidth=0.8, s=48, zorder=4)
            if value <= 40:
                ax.annotate(
                    f"{cell} {label} {value:.1f}d",
                    (value, percentile),
                    xytext=offsets[(cell, label)],
                    textcoords="offset points",
                    fontsize=7,
                    color=colors[cell],
                    bbox={"boxstyle": "round,pad=0.15", "facecolor": "white", "edgecolor": colors[cell], "alpha": 0.8},
                )

    for index, target in enumerate(sla_targets):
        ax.axvline(target, color="#777777", linestyle="--", linewidth=1.1, label=f"SLA {target:g} days")
    ax.set_xlim(0, 40)
    ax.set_ylim(0, 100)
    ax.set_xlabel("Calendar days")
    ax.set_ylabel("Cases completed (%)")
    ax.set_title("Empirical cycle-time distribution by cell")
    ax.legend(loc="upper left", frameon=True, fontsize=8, ncol=1)
    ax.grid(axis="y", alpha=0.22)
    above_limit = sum(value > 40 for value in all_values)
    max_days = max(all_values)
    fig.text(0.5, 0.055, f"{above_limit} cases above 40 days not shown (max {max_days:.1f} days)", ha="center", fontsize=9)
    _footer(fig)
    fig.subplots_adjust(left=0.12, right=0.96, bottom=0.18, top=0.90)
    path = FIGURES / "cycle_time_distribution.png"
    with path.open("wb") as output:
        fig.savefig(output, format="png", dpi=150)
    plt.close(fig)
    return path


def figure_rework_pareto() -> Path:
    selected = [_scenario("A2"), _scenario("B2")]
    fig, axes = plt.subplots(1, 2, figsize=(10, 5), sharey=True)
    for ax, scenario in zip(axes, selected):
        points = scenario["return_point_pareto"]
        labels = [f"Step {row['return_point']}" for row in points]
        counts = [row["loop_count"] for row in points]
        cumulative = [row["cumulative_share"] * 100 for row in points]
        positions = np.arange(len(points))
        ax.bar(positions, counts, color="#ED7D31", label="Loop count")
        ax.set_xticks(positions, labels)
        ax.set_title(scenario["scenario"])
        ax.set_xlabel("Return point")
        ax.grid(axis="y", alpha=0.2)
        line_ax = ax.twinx()
        line_ax.plot(positions, cumulative, color="#4472C4", marker="o", linewidth=2, label="Cumulative share")
        line_ax.set_ylim(0, 110)
        line_ax.set_ylabel("Cumulative loops (%)")
    axes[0].set_ylabel("Return-loop observations")
    fig.suptitle("Rework Pareto by return point")
    _footer(fig)
    fig.tight_layout(rect=(0, 0.04, 1, 0.93))
    path = FIGURES / "rework_pareto_A2_B2.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def figure_cumulative_value() -> Path:
    with (RESULTS / "value_model.json").open(encoding="utf-8") as handle:
        value_model = json.load(handle)
    ramp = value_model["ramp"]
    months = np.asarray(ramp["cumulative_months"])
    cumulative = np.asarray(ramp["cumulative_net_value_usd"])
    payback = float(ramp["payback_months"])

    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.plot(months, cumulative, color="#4472C4", linewidth=2.5)
    ax.axhline(0, color="#444444", linewidth=1)
    payback_value = 0.0
    ax.scatter([payback], [payback_value], color="#C00000", zorder=3, label=f"Payback: {payback:.2f} months")
    ax.axvline(payback, color="#C00000", linestyle="--", alpha=0.6)
    ax.set_xlabel("Month")
    ax.set_ylabel("Cumulative net value (USD)")
    ax.set_title("Cumulative net value along the adoption ramp")
    ax.legend(frameon=False)
    ax.grid(alpha=0.2)
    _footer(fig)
    fig.subplots_adjust(bottom=0.12, top=0.9)
    path = FIGURES / "cumulative_net_value.png"
    with path.open("wb") as output:
        fig.savefig(output, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def main() -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    paths = [
        figure_owner_shares(),
        figure_top_three(),
        figure_cycle_distribution(),
        figure_rework_pareto(),
        figure_cumulative_value(),
    ]
    for path in paths:
        print(path.relative_to(ROOT).as_posix())


if __name__ == "__main__":
    main()
