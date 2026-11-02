"""Synthetic access policy and reference-data MCP tools."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP


ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"


def _load_json(name: str) -> dict[str, Any]:
    with (DATA / name).open(encoding="utf-8") as handle:
        return json.load(handle)


_POLICIES = {row["entitlement"]: row for row in _load_json("entitlements.json")["entitlements"]}
_HOLDINGS = _load_json("holdings.json")["holdings"]
_PRIOR_APPROVALS = _load_json("prior_approvals.json")["prior_approvals"]
_REQUESTS = {row["id"]: row for row in _load_json("../sample_requests.json")["requests"]}

mcp = FastMCP("synthetic-access-policy-reference")


def get_request(id: str) -> dict[str, Any] | None:
    """Return a synthetic sample request by ID for the separate triage script."""
    request = _REQUESTS.get(id)
    return dict(request) if request is not None else None


def lookup_policy(entitlement: str) -> dict[str, Any]:
    """Return the registered tier, approver path, validity, and SoD policy."""
    policy = _POLICIES.get(entitlement)
    if policy is None:
        return {"found": False, "entitlement": entitlement}
    return {"found": True, **policy}


def check_prior_approval(requester: str, entitlement: str) -> dict[str, Any]:
    """Return prior approval facts and validity status without recommending action."""
    policy = _POLICIES.get(entitlement)
    if policy is None:
        return {"found": False, "requester": requester, "entitlement": entitlement, "records": []}
    validity = policy["prior_approval_validity_days"]
    records = []
    for source in _PRIOR_APPROVALS:
        if source["requester"] != requester or source["entitlement"] != entitlement:
            continue
        complete = bool(source["manager_confirmed"] and source["app_owner_confirmed"])
        records.append({
            **source,
            "complete": complete,
            "within_validity": int(source["age_days"]) <= validity,
            "validity_days": validity,
        })
    return {
        "found": True,
        "requester": requester,
        "entitlement": entitlement,
        "validity_days": validity,
        "has_records": bool(records),
        "records": records,
    }


def check_sod_conflict(requester: str, entitlement: str) -> dict[str, Any]:
    """Return conflicting current holdings for the requested entitlement."""
    policy = _POLICIES.get(entitlement)
    if policy is None:
        return {"found": False, "requester": requester, "entitlement": entitlement, "conflict_found": False, "conflicts": []}
    current = [row["entitlement"] for row in _HOLDINGS if row["requester"] == requester]
    conflicts = sorted(set(current).intersection(policy["sod_conflicts_with"]))
    return {
        "found": True,
        "requester": requester,
        "entitlement": entitlement,
        "policy_conflicts": list(policy["sod_conflicts_with"]),
        "current_holdings": sorted(current),
        "conflicts": conflicts,
        "conflict_found": bool(conflicts),
    }


mcp.tool()(lookup_policy)
mcp.tool()(check_prior_approval)
mcp.tool()(check_sod_conflict)


if __name__ == "__main__":
    mcp.run()
