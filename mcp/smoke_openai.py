"""One real model call on one synthetic request. No gate, no audit log, no grant.

    python mcp/smoke_openai.py RQ-001
"""

import sys

import model_openai
import triage
from server import get_request

request_id = sys.argv[1] if len(sys.argv) > 1 else "RQ-001"
request = get_request(request_id)
if request is None:
    sys.exit(f"no such request: {request_id}")

record = triage.recommend(request, triage.gather_evidence(request), model_openai.make_model_fn())
usage = record["model_output"].get("usage", {}) if isinstance(record["model_output"], dict) else {}
print(f"{request_id}: {record['recommendation']} | {record['reason']}")
print(f"tokens in/out: {usage.get('input_tokens')}/{usage.get('output_tokens')} | cost USD {record['cost_usd']}")
