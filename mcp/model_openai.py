"""OpenAI model_fn for triage.recommend(). Synthetic data only.

The model gives a recommendation and nothing else. Cost is computed here from
the API's reported token usage and the prices in .env; anything the model says
about cost is overwritten. Output that is not a JSON object is passed on in a
shape that triage._normalise() turns into 'escalate', with the cost kept.

.env (never committed):
    OPENAI_API_KEY=...
    OPENAI_MODEL=<mini model id>
    OPENAI_PRICE_INPUT_PER_MTOK=<USD per 1M input tokens, from the pricing page>
    OPENAI_PRICE_OUTPUT_PER_MTOK=<USD per 1M output tokens>
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Callable, Mapping

ENV_FILE = Path(__file__).resolve().parents[1] / ".env"
SETTINGS = ("OPENAI_MODEL", "OPENAI_PRICE_INPUT_PER_MTOK", "OPENAI_PRICE_OUTPUT_PER_MTOK")


class ModelConfigError(RuntimeError):
    """A required setting is missing or invalid. Names the setting, never its value."""


def _price(env: Mapping[str, str], key: str) -> float:
    try:
        value = float(env[key])
    except (KeyError, TypeError, ValueError):
        raise ModelConfigError(f"{key} must be a number (USD per 1M tokens)") from None
    if value < 0:
        raise ModelConfigError(f"{key} must not be negative")
    return value


def _tokens(usage: Any, *names: str) -> int:
    for name in names:
        value = getattr(usage, name, None)
        if isinstance(value, int):
            return value
    return 0


def make_model_fn(client: Any = None, env: Mapping[str, str] | None = None) -> Callable[[str], dict[str, Any]]:
    """Return model_fn(prompt) -> dict for triage.recommend().

    ``client`` and ``env`` are injectable so tests run with no key and no network.
    """
    if env is None:
        from dotenv import load_dotenv
        load_dotenv(ENV_FILE)
        env = os.environ

    missing = [key for key in SETTINGS if not env.get(key)]
    if client is None and not env.get("OPENAI_API_KEY"):
        missing.insert(0, "OPENAI_API_KEY")
    if missing:
        raise ModelConfigError(f"missing in .env: {', '.join(missing)}")

    model = env["OPENAI_MODEL"]
    price_in = _price(env, "OPENAI_PRICE_INPUT_PER_MTOK")
    price_out = _price(env, "OPENAI_PRICE_OUTPUT_PER_MTOK")

    if client is None:
        from openai import OpenAI
        client = OpenAI(api_key=env["OPENAI_API_KEY"])

    def call(prompt: str) -> dict[str, Any]:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
        usage = getattr(response, "usage", None)
        tokens_in = _tokens(usage, "prompt_tokens", "input_tokens")
        tokens_out = _tokens(usage, "completion_tokens", "output_tokens")
        cost = round(tokens_in * price_in / 1e6 + tokens_out * price_out / 1e6, 8)

        content = response.choices[0].message.content or ""
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            parsed = None
        if not isinstance(parsed, dict):
            # Keeps the cost; recommendation None -> _normalise() escalates.
            parsed = {"recommendation": None, "reason": "model output was not a JSON object",
                      "raw": content[:500]}

        parsed["cost_usd"] = cost  # computed from usage; the model's own claim is discarded
        parsed["usage"] = {"model": model, "input_tokens": tokens_in, "output_tokens": tokens_out,
                           "usage_reported": usage is not None}
        return parsed

    return call
