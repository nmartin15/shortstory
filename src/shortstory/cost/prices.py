"""Load per-model dollar prices from config."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Tuple

import yaml

_REPO_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_PRICES_PATH = _REPO_ROOT / "config" / "model_prices.yaml"


@lru_cache(maxsize=1)
def load_price_table(path: str | None = None) -> Dict[str, Any]:
    """Load and cache the model price YAML table.

    Args:
        path: Optional override path. Defaults to config/model_prices.yaml.

    Returns:
        Parsed YAML dict with 'models' and 'default' keys.
    """
    prices_path = Path(path) if path else _DEFAULT_PRICES_PATH
    if not prices_path.exists():
        return {
            "models": {},
            "default": {"input": 0.50, "output": 2.00, "cached_input": 0.25},
        }
    with prices_path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    data.setdefault("models", {})
    data.setdefault("default", {"input": 0.50, "output": 2.00, "cached_input": 0.25})
    return data


def get_model_rates(model: str, path: str | None = None) -> Tuple[float, float, float]:
    """Return (input, output, cached_input) dollars per 1M tokens for a model.

    Args:
        model: OpenRouter model slug.
        path: Optional prices file override.

    Returns:
        Tuple of rates in USD per million tokens.
    """
    table = load_price_table(path)
    rates = table["models"].get(model) or table["default"]
    return (
        float(rates.get("input", 0.50)),
        float(rates.get("output", 2.00)),
        float(rates.get("cached_input", rates.get("input", 0.50))),
    )


def estimate_cost_usd(
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    *,
    cached_prompt_tokens: int = 0,
    path: str | None = None,
) -> float:
    """Estimate dollar cost for a single call.

    Args:
        model: Model slug.
        prompt_tokens: Total prompt tokens (including cached if reported that way).
        completion_tokens: Completion tokens.
        cached_prompt_tokens: Tokens billed at cached_input rate.
        path: Optional prices file override.

    Returns:
        Estimated USD cost.
    """
    input_rate, output_rate, cached_rate = get_model_rates(model, path)
    billed_prompt = max(prompt_tokens - cached_prompt_tokens, 0)
    cost = (
        (billed_prompt / 1_000_000.0) * input_rate
        + (cached_prompt_tokens / 1_000_000.0) * cached_rate
        + (completion_tokens / 1_000_000.0) * output_rate
    )
    return round(cost, 8)


def clear_price_cache() -> None:
    """Clear cached price table (tests)."""
    load_price_table.cache_clear()
