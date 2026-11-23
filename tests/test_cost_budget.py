"""Cost tracking and budget cap tests."""

import pytest

from src.shortstory.cost import BudgetExceededError, CostTracker, estimate_cost_usd


def test_estimate_cost_qwen():
    cost = estimate_cost_usd("qwen/qwen3.8-27b", prompt_tokens=1_000_000, completion_tokens=1_000_000)
    assert cost == pytest.approx(0.035 + 1.50)


def test_budget_cap_stops_run(tmp_path):
    tracker = CostTracker(tmp_path / "costs.jsonl", budget_cap_usd=0.01)
    tracker.record(
        stage="premise",
        model="qwen/qwen3.8-27b",
        prompt_tokens=1000,
        completion_tokens=1000,
        cost_usd=0.008,
    )
    with pytest.raises(BudgetExceededError):
        tracker.record(
            stage="outline",
            model="qwen/qwen3.8-27b",
            prompt_tokens=1000,
            completion_tokens=1000,
            cost_usd=0.005,
        )


def test_stage_summary(tmp_path):
    tracker = CostTracker(tmp_path / "costs.jsonl")
    tracker.record(stage="premise", model="m", prompt_tokens=10, completion_tokens=10, cost_usd=0.1)
    tracker.record(stage="outline", model="m", prompt_tokens=10, completion_tokens=10, cost_usd=0.2)
    tracker.record(stage="premise", model="m", prompt_tokens=10, completion_tokens=10, cost_usd=0.05)
    summary = tracker.stage_summary()
    assert summary["premise"] == pytest.approx(0.15)
    assert summary["outline"] == pytest.approx(0.2)
    assert "story total" in tracker.format_report()
