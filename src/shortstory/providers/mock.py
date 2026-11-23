"""Deterministic mock provider for tests (never calls a real model)."""

from __future__ import annotations

from typing import List, Optional

from .base import BaseProvider, GenerateResult


class MockProvider(BaseProvider):
    """Returns scripted responses; records every call for assertions."""

    def __init__(
        self,
        model_name: str = "mock/test-model",
        responses: Optional[List[str]] = None,
        prompt_tokens: int = 100,
        completion_tokens: int = 200,
    ) -> None:
        """Initialize with optional queued responses.

        Args:
            model_name: Fake model slug.
            responses: FIFO queue of reply strings. Exhausted queue returns a stub.
            prompt_tokens: Reported input tokens per call.
            completion_tokens: Reported output tokens per call.
        """
        self._model_name = model_name
        self._responses = list(responses or [])
        self._prompt_tokens = prompt_tokens
        self._completion_tokens = completion_tokens
        self.calls: List[dict] = []

    @property
    def model_name(self) -> str:
        """Return the fake model slug."""
        return self._model_name

    def check_availability(self) -> bool:
        """Mock provider is always available."""
        return True

    def generate(
        self,
        system: str,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> GenerateResult:
        """Return the next queued response and record the call."""
        self.calls.append(
            {
                "system": system,
                "prompt": prompt,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
        )
        if self._responses:
            text = self._responses.pop(0)
        else:
            text = f"[mock output for {self._model_name}]"
        return GenerateResult(
            text=text,
            model=self._model_name,
            prompt_tokens=self._prompt_tokens,
            completion_tokens=self._completion_tokens,
            finish_reason="stop",
        )

    def enqueue(self, text: str) -> None:
        """Append a response to the queue."""
        self._responses.append(text)
