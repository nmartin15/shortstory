"""LLM provider implementations (OpenRouter by default)."""

from .base import BaseProvider, GenerateResult
from .factory import (
    ALTERNATE_DRAFT_MODEL,
    DEFAULT_DRAFT_MODEL,
    DEFAULT_PREMIUM_MODEL,
    create_provider,
    get_default_provider,
    get_draft_model_name,
    get_premium_model_name,
    reset_default_provider,
)
from .mock import MockProvider
from .openrouter import OpenAICompatibleProvider

__all__ = [
    "ALTERNATE_DRAFT_MODEL",
    "BaseProvider",
    "DEFAULT_DRAFT_MODEL",
    "DEFAULT_PREMIUM_MODEL",
    "GenerateResult",
    "MockProvider",
    "OpenAICompatibleProvider",
    "create_provider",
    "get_default_provider",
    "get_draft_model_name",
    "get_premium_model_name",
    "reset_default_provider",
]
