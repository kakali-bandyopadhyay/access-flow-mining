import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "mcp"))

from server import check_prior_approval, check_sod_conflict, get_request, lookup_policy


def _requests():
    with (ROOT / "mcp" / "sample_requests.json").open(encoding="utf-8") as handle:
        return json.load(handle)["requests"]


def test_each_sample_request_resolves_policy_prior_and_conflict_facts():
    requests = _requests()
    assert len(requests) == 11  # RQ-011 added after pre-registration (DEVIATIONS)
    for request in requests:
        policy = lookup_policy(request["entitlement"])
        prior = check_prior_approval(request["requester"], request["entitlement"])
        conflict = check_sod_conflict(request["requester"], request["entitlement"])
        assert policy["found"] and prior["found"] and conflict["found"]
        assert request["expected_recommendation"] in {"approve", "escalate", "reject"}

    policy = lookup_policy("market-data-write")
    assert policy["tier"] == "privileged"
    assert policy["prior_approval_validity_days"] == 180
    assert policy["sod_conflicts_with"] == ["order-router-write"]


def test_prior_approval_tools_return_expiry_and_partial_approval_facts():
    expired = check_prior_approval("USR-UK-002", "market-data-write")["records"][0]
    assert expired["age_days"] == 191
    assert expired["validity_days"] == 180
    assert expired["within_validity"] is False

    recent = check_prior_approval("USR-US-003", "order-router-read")["records"][0]
    assert recent["age_days"] == 12
    assert recent["within_validity"] is True
    assert recent["complete"] is True

    partial = check_prior_approval("USR-UK-008", "payments-gateway-deploy")["records"][0]
    assert partial["manager_confirmed"] is True
    assert partial["app_owner_confirmed"] is False
    assert partial["complete"] is False

    policy_drift = check_prior_approval("USR-US-009", "prod-db-admin")["records"][0]
    assert policy_drift["age_days"] == 120
    assert policy_drift["validity_days"] == 90
    assert policy_drift["within_validity"] is False


def test_sod_tool_finds_only_registered_conflict_for_sample_set():
    requests = _requests()
    results = {row["id"]: check_sod_conflict(row["requester"], row["entitlement"]) for row in requests}
    assert results["RQ-007"]["conflict_found"] is True
    assert results["RQ-007"]["conflicts"] == ["order-router-write"]
    assert all(not results[request_id]["conflict_found"] for request_id in results if request_id != "RQ-007")


def test_get_request_exposes_request_facts_without_gate_action():
    for request in _requests():
        assert get_request(request["id"]) == request
    assert get_request("RQ-000") is None
    assert get_request("RQ-004")["expected_recommendation"] == "approve"
    assert get_request("RQ-004")["gate_outcome"] == "SelfApprovalBlocked"
    assert get_request("RQ-005")["gate_outcome"] == "blocked at triage"


def test_request_expectations_and_support_matrix_are_explicit():
    requests = _requests()
    expected = {
        "RQ-001": "approve", "RQ-002": "escalate", "RQ-003": "approve",
        "RQ-004": "approve", "RQ-005": "approve", "RQ-006": "escalate",
        "RQ-007": "escalate", "RQ-008": "escalate", "RQ-009": "escalate",
        "RQ-010": "reject", "RQ-011": "approve",
    }
    assert {row["id"]: row["expected_recommendation"] for row in requests} == expected
    for row in requests:
        facts = {
            "lookup_policy": lookup_policy(row["entitlement"])["found"],
            "check_prior_approval": check_prior_approval(row["requester"], row["entitlement"])["found"],
            "check_sod_conflict": check_sod_conflict(row["requester"], row["entitlement"])["found"],
        }
        assert all(facts.values()), (row["id"], facts)
        assert row["expected_recommendation"] in {"approve", "escalate", "reject"}
