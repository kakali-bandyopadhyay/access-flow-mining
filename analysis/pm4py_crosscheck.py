"""PM4Py cross-check (exploratory, added after pre-registration). Synthetic data."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import pm4py
from pm4py.objects.bpmn.exporter import exporter as bpmn_exporter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from flowmining.components import ACTIVITY_STEPS


def load(cell: str) -> pd.DataFrame:
    df = pd.read_csv(ROOT / "data" / f"event_log_{cell}.csv")
    df = df[df["lifecycle"] == "complete"].copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    return pm4py.format_dataframe(
        df, case_id="case_id", activity_key="activity", timestamp_key="timestamp"
    )


def designed_model():
    """Discover a Petri net from the intended single-case path, in step order."""
    activities = sorted(ACTIVITY_STEPS, key=ACTIVITY_STEPS.get)
    ref_log = pd.DataFrame(
        {
            "case_id": ["reference"] * len(activities),
            "activity": activities,
            "timestamp": pd.date_range("2026-01-01T00:00:00Z", periods=len(activities), freq="min"),
        }
    )
    ref_log = pm4py.format_dataframe(
        ref_log, case_id="case_id", activity_key="activity", timestamp_key="timestamp"
    )
    return pm4py.discover_petri_net_inductive(ref_log)


def log_fit_metrics(fitness: dict[str, float]) -> dict[str, float]:
    """Keep the global fitness and fitting-trace share from PM4Py's result."""
    return {
        "log_fitness": float(fitness["log_fitness"]),
        "fitting_traces_share": float(fitness["percentage_of_fitting_traces"]) / 100.0,
    }


results = {
    "synthetic": True,
    "exploratory": True,
    "added_after_preregistration": True,
    "discovered_model_fitness_note": (
        "Discovered fitness is near 1.0 because noise_threshold=0.0 retains observed variants "
        "when the model is induced from the same log."
    ),
    "pm4py_version": pm4py.__version__,
    "cells": {},
}
ref_net, ref_im, ref_fm = designed_model()
a2_log = None
for cell in ("A1", "A2", "B1", "B2"):
    log = load(cell)
    if cell == "A2":
        a2_log = log
    fit_ref = pm4py.fitness_alignments(log, ref_net, ref_im, ref_fm)
    print(cell, fit_ref.keys())
    # With noise_threshold=0.0, the discovered model retains observed variants,
    # explaining its near-1.0 fitness against the same log used to discover it.
    net, im, fm = pm4py.discover_petri_net_inductive(log, noise_threshold=0.0)
    fit_discovered = pm4py.fitness_alignments(log, net, im, fm)
    precision = pm4py.precision_alignments(log, net, im, fm)
    scenario = json.loads((ROOT / "analysis" / "results" / f"scenario_{cell}.json").read_text(encoding="utf-8"))
    results["cells"][cell] = {
        "designed_model": log_fit_metrics(fit_ref),
        "discovered_model": {
            **log_fit_metrics(fit_discovered),
            "precision": float(precision),
        },
        "pandas_exact_path_conformance_rate": float(scenario["conformance_rate_exact_path"]),
    }

bpmn_path = ROOT / "lean" / "as_is_discovered_A2.bpmn"
bpmn_path.parent.mkdir(parents=True, exist_ok=True)
assert a2_log is not None
bpmn = pm4py.discover_bpmn_inductive(a2_log)
bpmn_exporter.apply(bpmn, str(bpmn_path))
(ROOT / "analysis" / "results" / "pm4py_crosscheck.json").write_text(
    json.dumps(results, indent=2) + "\n", encoding="utf-8"
)
