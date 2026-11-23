"""Factory for draft and premium OpenRouter providers."""

from __future__ import annotations

import logging
import os
from typing import Optional

from .base import BaseProvider
from .openrouter import OpenAICompatibleProvider

logger = logging.getLogger(__name__)

DEFAULT_DRAFT_MODEL = "qwen/qwen3.8-27b"
DEFAULT_PREMIUM_MODEL = "moonshotai/kimi-k3.1-pro"
ALTERNATE_DRAFT_MODEL = "deepseek/deepseek-v4.1-flash"

_draft_provider: Optional[BaseProvider] = None
_premium_provider: Optional[BaseProvider] = None


def get_draft_model_name() -> str:
    """Return DRAFT_MODEL from env (cheap volume tier)."""
    return os.getenv("DRAFT_MODEL", DEFAULT_DRAFT_MODEL).strip()


def get_premium_model_name() -> str:
    """Return PREMIUM_MODEL from env (opt-in strong tier)."""
    return os.getenv("PREMIUM_MODEL", DEFAULT_PREMIUM_MODEL).strip()


def create_provider(
    model_name: Optional[str] = None,
    *,
    premium: bool = False,
    api_key: Optional[str] = None,
) -> BaseProvider:
    """Create an OpenRouter-backed provider.

    Args:
        model_name: Explicit model slug. If omitted, uses DRAFT_MODEL or PREMIUM_MODEL.
        premium: When True and model_name is omitted, use PREMIUM_MODEL.
        api_key: Optional API key override.

    Returns:
        Configured BaseProvider.
    """
    if model_name is None:
        model_name = get_premium_model_name() if premium else get_draft_model_name()

    provider = OpenAICompatibleProvider(model_name=model_name, api_key=api_key)
    logger.info("Created OpenRouter provider for model=%s", provider.model_name)
    return provider


def get_default_provider(*, premium: bool = False) -> BaseProvider:
    """Get a cached draft or premium provider instance.

    Premium is never selected automatically — callers must pass premium=True
    (or use a CLI/UI flag).
    """
    global _draft_provider, _premium_provider

    if premium:
        if _premium_provider is None:
            _premium_provider = create_provider(premium=True)
        return _premium_provider

    if _draft_provider is None:
        _draft_provider = create_provider(premium=False)
    return _draft_provider


def reset_default_provider() -> None:
    """Clear cached providers (tests / config reload)."""
    global _draft_provider, _premium_provider
    _draft_provider = None
    _premium_provider = None
    logger.info("Reset cached LLM providers")


# Backward-compatible alias used by older call sites during migration
def get_default_client(*, premium: bool = False) -> BaseProvider:
    """Alias for get_default_provider."""
    return get_default_provider(premium=premium)
