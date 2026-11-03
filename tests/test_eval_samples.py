"""eval_samples tests: fake models, tmp_path output, no API key, no network."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "mcp"))

import eval_samples
import triage

PRIVILEGED = {"RQ-002", "RQ-006", "RQ-007", "RQ-008", "RQ-009", "RQ-010", "RQ-011"}


def fake(recommendation, cost=0.0001, prompts=None):
    def call(prompt):
        if prompts is not None:
            prompts.append(prompt)
        return {"recommendation": recommendation, "reason": "fake", "cost_usd": cost,
                "usage": {"input_tokens": 500, "output_tokens": 40}}
    return call


def rows_by_id(summary_dir):
    data = json.loads((Path(summary_dir) / "results.json").read_text(encoding="utf-8"))
    return {r["request_id"]: r for r in data["repeats"][0]}


def test_always_approve_drives_two_approvers_on_every_privileged_sample(tmp_path):
    summary = eval_samples.evaluate(fake("approve"), repeats=1, out_dir=tmp_path)
    rows = rows_by_id(summary["out_dir"])
    for rid in PRIVILEGED:
        assert rows[rid]["approvers"] == [eval_samples.FIRST, eval_samples.SECOND], rid
        assert rows[rid]["gate"] == "granted"
    assert rows["RQ-001"]["approvers"] == [eval_samples.FIRST]
    assert rows["RQ-004"]["gate"] == "blocked_self_approval"
    assert summary["per_repeat"][0]["preregistered"]["two_approver_grants"] == 6
    assert summary["per_repeat"][0]["added"]["two_approver_grants"] == 1


def test_rq005_is_blocked_before_the_model(tmp_path):
    prompts = []
    summary = eval_samples.evaluate(fake("approve", prompts=prompts), repeats=1, out_dir=tmp_path)
    rows = rows_by_id(summary["out_dir"])
    assert rows["RQ-005"]["gate"] == "blocked_at_triage"
    assert rows["RQ-005"]["recommendation"] is None
    assert len(prompts) == 10
    assert summary["per_repeat"][0]["preregistered"]["asked"] == 9
    assert summary["per_repeat"][0]["added"]["asked"] == 1


def test_always_escalate_grants_nothing_and_scores_the_privileged_misses(tmp_path):
    summary = eval_samples.evaluate(fake("escalate"), repeats=1, out_dir=tmp_path)
    rows = rows_by_id(summary["out_dir"])
    assert all(r["gate"] != "granted" for r in rows.values())
    missed = {m[0] for m in summary["recommendation_misses"]}
    assert {"RQ-001", "RQ-003", "RQ-004", "RQ-010", "RQ-011"} <= missed


def test_fixture_keys_never_reach_a_prompt(tmp_path):
    prompts = []
    eval_samples.evaluate(fake("escalate", prompts=prompts), repeats=1, out_dir=tmp_path)
    for prompt in prompts:
        for key in triage.FIXTURE_KEYS:
            assert key not in prompt


def test_each_repeat_has_its_own_audit_log(tmp_path):
    eval_samples.evaluate(fake("approve"), repeats=2, out_dir=tmp_path)
    for n in (1, 2):
        events = [json.loads(x)["event"] for x in
                  (tmp_path / f"repeat_{n}" / "audit_log.jsonl").read_text(encoding="utf-8").splitlines()]
        assert events.count("executed") == 9  # RQ-001, RQ-003 + seven privileged; RQ-004/005 blocked


def test_cost_guardrail_stops_the_run(tmp_path):
    summary = eval_samples.evaluate(fake("escalate", cost=0.02), repeats=3, out_dir=tmp_path, max_cost=0.05)
    assert summary["stopped"] and summary["total_cost_usd"] <= 0.05 + 0.02


def test_rq011_is_granted_only_after_two_approvers_when_the_model_approves(tmp_path):
    summary = eval_samples.evaluate(fake("approve"), repeats=1, out_dir=tmp_path)
    row = rows_by_id(summary["out_dir"])["RQ-011"]
    assert row["gate"] == "granted" and row["approvers"] == [eval_samples.FIRST, eval_samples.SECOND]
    assert row["expected_gate"] == "granted"


def test_added_samples_are_scored_apart_from_the_preregistered_ten(tmp_path):
    summary = eval_samples.evaluate(fake("escalate"), repeats=1, out_dir=tmp_path)
    rep = summary["per_repeat"][0]
    assert rep["preregistered"]["samples"] == 10 and rep["added"]["samples"] == 1


def test_results_record_the_rules_version(tmp_path):
    summary = eval_samples.evaluate(fake("escalate"), repeats=1, out_dir=tmp_path)
    assert summary["rules_version"] == triage.RULES_VERSION
    saved = json.loads((tmp_path / "results.json").read_text(encoding="utf-8"))
    assert saved["summary"]["rules_version"] == triage.RULES_VERSION
