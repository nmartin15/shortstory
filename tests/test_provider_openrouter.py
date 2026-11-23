"""Tests for the provider layer (mock only — never calls a real model)."""

from src.shortstory.providers import MockProvider, GenerateResult


def test_mock_provider_returns_queued_responses():
    provider = MockProvider(responses=["alpha", "beta"])
    first = provider.generate("sys", "prompt1")
    second = provider.generate("sys", "prompt2")
    assert first.text == "alpha"
    assert second.text == "beta"
    assert first.model == "mock/test-model"
    assert len(provider.calls) == 2
    assert provider.calls[0]["prompt"] == "prompt1"


def test_mock_provider_stub_when_queue_empty():
    provider = MockProvider(model_name="mock/x")
    result = provider.generate("s", "p")
    assert isinstance(result, GenerateResult)
    assert "mock" in result.text


def test_openrouter_requires_api_key(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    from src.shortstory.providers.openrouter import OpenAICompatibleProvider
    import pytest

    with pytest.raises(ValueError, match="OPENROUTER_API_KEY"):
        OpenAICompatibleProvider(model_name="qwen/qwen3.8-27b", api_key="")
