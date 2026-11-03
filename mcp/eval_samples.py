"""Ten-sample evaluation of the triage gate. Synthetic data only.

    python mcp/eval_samples.py              # 3 repeats, real model from .env
    python mcp/eval_samples.py --repeats 1

Each repeat runs every sample through the same order as triage.run():
early_check -> check_registered -> gather_evidence -> recommend -> confirm
[-> second confirm] -> execute, with a fresh audit log.

The human is simulated and stated here so it can be challenged: the reviewer
confirms when the model recommends 'approve' and declines otherwise. Privileged
samples get two reviewers (EMP-9001 then EMP-9002) with the same decision.
RQ-004 is confirmed by the requester (the fixture's self-approval case).

Fixture keys (expected_*, gate_outcome) are read here, in the evaluation only,
and never reach the prompt: triage.build_prompt refuses them.

Output (git-ignored): mcp/runs/<UTC stamp>/repeat_<n>/audit_log.jsonl and
mcp/runs/<UTC stamp>/results.json. The summary printed at the end is the only
text meant for FINDINGS.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any, Callable

import triage
from server import get_request

HERE = Path(__file__).resolve().parent
SAMPLES = HERE / "sample_requests.json"
RUNS = HERE / "runs"
FIRST, SECOND = "EMP-9001", "EMP-9002"
MAX_TOTAL_COST_USD = 0.05  # stop the run if spend passes this

#: fixture gate_outcome text -> the outcome this script records
EXPECTED_GATE = {
    "permitted after confirmation": "granted",
    "not reached": "declined",
    "no action without human confirmation": "declined",
    "SelfApprovalBlocked": "blocked_self_approval",
    "blocked at triage": "blocked_at_triage",
}


def load_fixtures() -> list[dict[str, Any]]:
    data = json.loads(SAMPLES.read_text(encoding="utf-8"))
    return next(v for v in data.values() if isinstance(v, list)) if isinstance(data, dict) else data


def run_one(fixture: dict[str, Any], model_fn: Callable[[str], Any], log: Path) -> dict[str, Any]:
    request = get_request(fixture["id"])
    row: dict[str, Any] = {
        "request_id": fixture["id"],
        "expected_recommendation": fixture.get("expected_recommendation"),
        "expected_gate": EXPECTED_GATE.get(fixture.get("gate_outcome", ""), "unmapped"),
        "recommendation": None, "reason": None, "cost_usd": 0.0,
        "input_tokens": 0, "output_tokens": 0, "approvers": [], "gate": None,
    }

    try:
        triage.early_check(request, log)
        privileged = triage.check_registered(request, log, FIRST)
    except triage.SelfApprovalBlocked:
        row["gate"] = "blocked_at_triage"
        return row

    rec = triage.recommend(request, triage.gather_evidence(request), model_fn)
    usage = rec["model_output"].get("usage", {}) if isinstance(rec["model_output"], dict) else {}
    row.update(recommendation=rec["recommendation"], reason=rec["reason"], cost_usd=rec["cost_usd"],
               input_tokens=usage.get("input_tokens", 0), output_tokens=usage.get("output_tokens", 0))

    decision = "confirm" if rec["recommendation"] == "approve" else "decline"
    first_id = request["requester"] if request.get("approver_is_requester") else FIRST
    try:
        record = triage.confirm(request, rec, first_id, decision, log)
        if privileged and decision == "confirm":
            record = triage.confirm(request, rec, SECOND, decision, log, prior=record)
    except triage.SelfApprovalBlocked:
        row["gate"] = "blocked_self_approval"
        return row

    row["approvers"] = list(record.approvers)
    if not record.permitted:
        row["gate"] = "declined"
        return row
    triage.execute(record)
    row["gate"] = "granted"
    return row


def evaluate(model_fn: Callable[[str], Any], repeats: int = 3, out_dir: Path | None = None,
             max_cost: float = MAX_TOTAL_COST_USD) -> dict[str, Any]:
    stamp = dt.datetime.now(dt.UTC).strftime("%Y%m%dT%H%M%SZ")
    out_dir = out_dir or RUNS / stamp
    out_dir.mkdir(parents=True, exist_ok=True)
    fixtures = load_fixtures()

    results: list[list[dict[str, Any]]] = []
    spent = 0.0
    stopped = None
    for n in range(1, repeats + 1):
        log = out_dir / f"repeat_{n}" / "audit_log.jsonl"
        rows = []
        for fixture in fixtures:
            if spent > max_cost:
                stopped = f"cost guardrail: USD {spent:.6f} > {max_cost} before repeat {n}, {fixture['id']}"
                break
            row = run_one(fixture, model_fn, log)
            spent += row["cost_usd"]
            rows.append(row)
        results.append(rows)
        if stopped:
            break

    summary = summarise(results, spent, stopped)
    (out_dir / "results.json").write_text(
        json.dumps({"summary": summary, "repeats": results}, indent=2), encoding="utf-8")
    summary["out_dir"] = str(out_dir)
    return summary


def summarise(results: list[list[dict[str, Any]]], spent: float, stopped: str | None) -> dict[str, Any]:
    per_repeat = []
    for rows in results:
        asked = [r for r in rows if r["recommendation"] is not None]
        per_repeat.append({
            "recommendation_correct": sum(r["recommendation"] == r["expected_recommendation"] for r in asked),
            "asked": len(asked),
            "gate_correct": sum(r["gate"] == r["expected_gate"] for r in rows),
            "samples": len(rows),
            "two_approver_grants": sum(r["gate"] == "granted" and len(r["approvers"]) == 2 for r in rows),
        })
    misses = sorted({(r["request_id"], r["recommendation"], r["expected_recommendation"])
                     for rows in results for r in rows
                     if r["recommendation"] is not None and r["recommendation"] != r["expected_recommendation"]})
    tokens_in = sum(r["input_tokens"] for rows in results for r in rows)
    tokens_out = sum(r["output_tokens"] for rows in results for r in rows)
    return {"repeats": len(results), "per_repeat": per_repeat,
            "recommendation_misses": [list(m) for m in misses],
            "total_cost_usd": round(spent, 6), "input_tokens": tokens_in, "output_tokens": tokens_out,
            "stopped": stopped}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repeats", type=int, default=3)
    args = parser.parse_args()

    import model_openai
    summary = evaluate(model_openai.make_model_fn(), args.repeats)
    for i, rep in enumerate(summary["per_repeat"], 1):
        print(f"repeat {i}: recommendation {rep['recommendation_correct']}/{rep['asked']} "
              f"(RQ-005 not asked: blocked at triage) | gate outcome {rep['gate_correct']}/{rep['samples']} "
              f"| two-approver grants {rep['two_approver_grants']}")
    print(f"misses: {summary['recommendation_misses'] or 'none'}")
    print(f"tokens in/out: {summary['input_tokens']}/{summary['output_tokens']} "
          f"| total cost USD {summary['total_cost_usd']}")
    if summary["stopped"]:
        print(f"STOPPED: {summary['stopped']}")
    print(f"results: {summary['out_dir']}")


if __name__ == "__main__":
    main()
