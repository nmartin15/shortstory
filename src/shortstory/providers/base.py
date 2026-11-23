"""Provider interface for hosted LLM calls."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class GenerateResult:
    """Result of a single model generation call.

    Attributes:
        text: Generated text.
        model: Model slug used for the call.
        prompt_tokens: Input token count (0 if unknown).
        completion_tokens: Output token count (0 if unknown).
        finish_reason: Provider finish reason if available.
    """

    text: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    finish_reason: Optional[str] = None


class BaseProvider(ABC):
    """Abstract LLM provider used by the drafting pipeline."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the configured model slug."""

    @abstractmethod
    def generate(
        self,
        system: str,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> GenerateResult:
        """Generate text from a system prompt and user prompt.

        Args:
            system: Stable instructions (style bible, IP rules, stage role).
            prompt: Stage-specific content (premise, outline, scene brief).
            temperature: Sampling temperature.
            max_tokens: Maximum completion tokens.

        Returns:
            GenerateResult with text and token usage.

        Raises:
            RuntimeError: On exhausted retries or provider failure.
        """

    @abstractmethod
    def check_availability(self) -> bool:
        """Return True if credentials and client are usable."""
