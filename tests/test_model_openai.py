"""model_openai tests: a fake client, so no API key and no network."""

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "mcp"))

import model_openai
import triage
from server import get_request

ENV = {"OPENAI_MODEL": "test-mini", "OPENAI_PRICE_INPUT_PER_MTOK": "0.40",
       "OPENAI_PRICE_OUTPUT_PER_MTOK": "1.60"}


class FakeClient:
    def __init__(self, content, usage=SimpleNamespace(prompt_tokens=1000, completion_tokens=50)):
        self.calls = []

        def create(**kwargs):
            self.calls.append(kwargs)
            message = SimpleNamespace(content=content)
            return SimpleNamespace(choices=[SimpleNamespace(message=message)], usage=usage)

        self.chat = SimpleNamespace(completions=SimpleNamespace(create=create))


def test_cost_comes_from_usage_and_prices():
    client = FakeClient('{"recommendation": "approve", "reason": "ok"}')
    out = model_openai.make_model_fn(client, ENV)("prompt")
    assert out["cost_usd"] == pytest.approx(1000 * 0.40 / 1e6 + 50 * 1.60 / 1e6)
    assert out["usage"] == {"model": "test-mini", "input_tokens": 1000, "output_tokens": 50,
                            "usage_reported": True}
    assert client.calls[0]["model"] == "test-mini"
    assert client.calls[0]["response_format"] == {"type": "json_object"}


def test_the_models_own_cost_claim_is_discarded():
    client = FakeClient('{"recommendation": "approve", "reason": "ok", "cost_usd": 0}')
    out = model_openai.make_model_fn(client, ENV)("prompt")
    assert out["cost_usd"] > 0


def test_non_json_output_escalates_and_keeps_the_cost():
    client = FakeClient("Sure! I approve this request.")
    fn = model_openai.make_model_fn(client, ENV)
    request = get_request("RQ-001")
    record = triage.recommend(request, triage.gather_evidence(request), fn)
    assert record["recommendation"] == "escalate"
    assert record["cost_usd"] > 0


def test_end_to_end_recommendation_through_triage():
    client = FakeClient('{"recommendation": "Approve", "reason": "live prior approval"}')
    request = get_request("RQ-001")
    record = triage.recommend(request, triage.gather_evidence(request),
                              model_openai.make_model_fn(client, ENV))
    assert record["recommendation"] == "approve"
    assert "<justification>" in client.calls[0]["messages"][0]["content"]


def test_missing_settings_are_named_and_values_never_shown():
    with pytest.raises(model_openai.ModelConfigError) as err:
        model_openai.make_model_fn(None, {"OPENAI_MODEL": "m", "OPENAI_PRICE_INPUT_PER_MTOK": "1"})
    message = str(err.value)
    assert "OPENAI_API_KEY" in message and "OPENAI_PRICE_OUTPUT_PER_MTOK" in message


@pytest.mark.parametrize("bad", ["abc", "-1", ""])
def test_bad_prices_are_refused(bad):
    env = dict(ENV, OPENAI_PRICE_INPUT_PER_MTOK=bad)
    with pytest.raises(model_openai.ModelConfigError):
        model_openai.make_model_fn(FakeClient("{}"), env)


def test_missing_usage_is_flagged_not_hidden():
    client = FakeClient('{"recommendation": "approve", "reason": "ok"}', usage=None)
    out = model_openai.make_model_fn(client, ENV)("prompt")
    assert out["usage"]["usage_reported"] is False and out["cost_usd"] == 0
