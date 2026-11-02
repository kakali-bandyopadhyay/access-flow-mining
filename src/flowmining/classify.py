"""Pre-registered owner-share classifier and diagnostics."""

from __future__ import annotations

import math
from typing import Any

import pandas as pd


APPROVAL_STEPS = {3, 5}
INTENDED = {"A1": "APPROVER-BOUND", "A2": "APPROVER-BOUND", "B1": "HANDOFF-BOUND", "B2": "HANDOFF-BOUND"}
SHARE_NAMES = ("approver_share", "handoff_share", "doer_share")


def classify_shares(approver_share: float, handoff_share: float, doer_share: float) -> dict[str, Any]:
    """Classify normalized synthetic shares with the fixed 1.5x margin rule."""
    values = {
        "APPROVER-BOUND": float(approver_share),
        "HANDOFF-BOUND": float(handoff_share),
        "DOER-BOUND": float(doer_share),
    }
    if any(not math.isfinite(value) or value < 0 for value in values.values()):
        raise ValueError("shares must be finite and nonnegative")
    if not math.isclose(sum(values.values()), 1.0, rel_tol=0.0, abs_tol=1e-6):
        raise ValueError("owner shares must sum to one")
    ranked = sorted(values.items(), key=lambda item: (-item[1], item[0]))
    largest, next_largest = ranked[0], ranked[1]
    margin = math.inf if next_largest[1] == 0 else largest[1] / next_largest[1]
    clears_margin = margin >= 1.5 or math.isclose(margin, 1.5, rel_tol=0.0, abs_tol=1e-12)
    classification = largest[0] if clears_margin else "INDETERMINATE"
    return {
        "classified": classification,
        "margin": margin,
        "largest_share": largest[1],
        "next_share": next_largest[1],
        "ranked_shares": [{"class": name, "share": share} for name, share in ranked],
    }


def classify_components(components: pd.DataFrame) -> dict[str, Any]:
    """Compute scenario shares, wait share, classification, and top-three pairs."""
    if components.empty:
        raise ValueError("components cannot be empty")
    approval = components["step"].isin(APPROVAL_STEPS)
    handoffs = components["handoff_bh"].fillna(0.0)
    queues = components["queue_bh"].fillna(0.0)
    touches = components["touch_bh"].fillna(0.0)
    approver_hours = float((queues[approval] + touches[approval]).sum())
    handoff_hours = float(handoffs.sum() + queues[~approval].sum())
    doer_hours = float(touches[~approval].sum())
    cycle_bh = approver_hours + handoff_hours + doer_hours
    if cycle_bh <= 0:
        raise ValueError("cycle_bh must be positive")
    approver_share = approver_hours / cycle_bh
    handoff_share = handoff_hours / cycle_bh
    doer_share = doer_hours / cycle_bh
    classification = classify_shares(approver_share, handoff_share, doer_share)

    waits = float((handoffs + queues).sum())
    pair_rows = []
    for field, component_name in (("handoff_bh", "handoff"), ("queue_bh", "queue"), ("touch_bh", "touch")):
        grouped = components.groupby(["step", "activity"], as_index=False)[field].sum()
        for row in grouped.itertuples(index=False):
            hours = float(getattr(row, field))
            pair_rows.append({
                "step": int(row.step), "activity": row.activity,
                "component": component_name, "hours": hours,
                "share": hours / cycle_bh,
            })
    pair_rows.sort(key=lambda row: (-row["hours"], row["step"], row["component"]))
    return {
        "cycle_bh": cycle_bh,
        "approver_hours": approver_hours,
        "handoff_hours": handoff_hours,
        "doer_hours": doer_hours,
        "approver_share": approver_share,
        "handoff_share": handoff_share,
        "doer_share": doer_share,
        "wait_share": waits / cycle_bh,
        "classified": classification["classified"],
        "margin": classification["margin"],
        "ranked_shares": classification["ranked_shares"],
        "top_three_diagnostics": pair_rows[:3],
    }
