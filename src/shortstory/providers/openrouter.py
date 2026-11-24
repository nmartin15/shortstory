"""OpenAI-compatible provider pointed at OpenRouter."""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Optional

from .base import BaseProvider, GenerateResult

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_TIMEOUT_SECONDS = 120
DEFAULT_MAX_RETRIES = 3


class OpenAICompatibleProvider(BaseProvider):
    """Hosted chat completions via an OpenAI-compatible HTTP API.

    Defaults to OpenRouter. Intended for DRAFT_MODEL and PREMIUM_MODEL only;
    no local/Ollama backends.
    """

    def __init__(
        self,
        model_name: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        max_retries: int = DEFAULT_MAX_RETRIES,
        site_url: Optional[str] = None,
        app_name: str = "shortstoryfun",
    ) -> None:
        """Initialize the provider.

        Args:
            model_name: OpenRouter model slug.
            api_key: API key (defaults to OPENROUTER_API_KEY).
            base_url: API base URL (defaults to OpenRouter).
            timeout_seconds: Per-request timeout.
            max_retries: Retries with exponential backoff.
            site_url: Optional HTTP-Referer for OpenRouter rankings.
            app_name: Optional X-Title header value.

        Raises:
            ValueError: If API key or model name is missing.
            ImportError: If the openai package is not installed.
        """
        self._model_name = (model_name or "").strip()
        if not self._model_name:
            raise ValueError("model_name is required")

        self._api_key = (api_key or os.getenv("OPENROUTER_API_KEY", "")).strip()
        if not self._api_key:
            raise ValueError(
                "OPENROUTER_API_KEY is required. Create a key at "
                "https://openrouter.ai/keys with a spending limit, then set it in .env."
            )

        self._base_url = (base_url or os.getenv("OPENROUTER_BASE_URL", DEFAULT_BASE_URL)).rstrip(
            "/"
        )
        self._timeout_seconds = timeout_seconds
        self._max_retries = max(1, max_retries)
        self._site_url = site_url or os.getenv("OPENROUTER_SITE_URL", "http://localhost")
        self._app_name = app_name

        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ImportError(
                "The openai package is required for OpenRouter. Install with: pip install openai"
            ) from exc

        self._client = OpenAI(
            api_key=self._api_key,
            base_url=self._base_url,
            timeout=self._timeout_seconds,
            default_headers={
                "HTTP-Referer": self._site_url,
                "X-Title": self._app_name,
            },
        )

    @property
    def model_name(self) -> str:
        """Return the configured model slug."""
        return self._model_name

    def check_availability(self) -> bool:
        """Return True when an API key and client are configured."""
        return bool(self._api_key and self._client)

    def generate(
        self,
        system: str,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> GenerateResult:
        """Call chat completions with retries and clear errors.

        Stable content (system) is sent first so providers that support
        prompt caching can reuse it across scene calls.
        """
        messages = [
            {"role": "system", "content": system or ""},
            {"role": "user", "content": prompt or ""},
        ]

        last_error: Optional[Exception] = None
        for attempt in range(1, self._max_retries + 1):
            try:
                # Disable/minimize chain-of-thought so reasoning models don't
                # burn max_tokens and return empty content (finish_reason=length).
                # Prefer a large enough budget: reasoning models count thinking
                # toward max_tokens and can return empty content when truncated.
                effective_max = max(max_tokens, 2048)
                response = self._client.chat.completions.create(
                    model=self._model_name,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=effective_max,
                    extra_body={
                        "reasoning": {"effort": "minimal", "exclude": True},
                    },
                )
                return self._parse_response(response)
            except Exception as exc:  # noqa: BLE001 - surface provider errors cleanly
                last_error = exc
                if attempt >= self._max_retries or not self._is_retryable(exc):
                    break
                delay = min(2 ** (attempt - 1), 16)
                logger.warning(
                    "OpenRouter call failed (attempt %s/%s): %s; retrying in %ss",
                    attempt,
                    self._max_retries,
                    exc,
                    delay,
                )
                time.sleep(delay)

        raise RuntimeError(
            f"OpenRouter generation failed for model '{self._model_name}': {last_error}"
        ) from last_error

    def _parse_response(self, response: Any) -> GenerateResult:
        """Extract text and usage from an OpenAI-compatible response."""
        choice = response.choices[0] if response.choices else None
        if choice is None or choice.message is None:
            raise RuntimeError("OpenRouter returned an empty response")

        message = choice.message
        text = (message.content or "").strip()
        if not text:
            # Some reasoning models put usable text only in reasoning fields
            for attr in ("reasoning", "reasoning_content"):
                alt = getattr(message, attr, None)
                if isinstance(alt, str) and alt.strip():
                    text = alt.strip()
                    break
        if not text:
            finish_reason = getattr(choice, "finish_reason", None)
            raise RuntimeError(
                f"OpenRouter returned empty content for model '{self._model_name}' "
                f"(finish_reason={finish_reason}). Try DRAFT_MODEL=deepseek/deepseek-v4.1-flash "
                "or raise max_tokens."
            )

        usage = getattr(response, "usage", None)
        prompt_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
        completion_tokens = int(getattr(usage, "completion_tokens", 0) or 0)
        finish_reason = getattr(choice, "finish_reason", None)

        return GenerateResult(
            text=text,
            model=self._model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            finish_reason=finish_reason,
        )

    @staticmethod
    def _is_retryable(exc: Exception) -> bool:
        """Return True for transient network/rate-limit failures."""
        name = type(exc).__name__.lower()
        message = str(exc).lower()
        retry_markers = (
            "timeout",
            "timed out",
            "rate limit",
            "429",
            "500",
            "502",
            "503",
            "504",
            "connection",
            "temporarily",
        )
        if any(marker in name for marker in ("timeout", "ratelimit", "apiconnection", "internalserver")):
            return True
        return any(marker in message for marker in retry_markers)
