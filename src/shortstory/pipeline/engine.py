"""Shared generation helper: provider + cost + provenance + budget."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from ..cost import BudgetExceededError, CostTracker, estimate_cost_usd
from ..provenance import ProvenanceLog
from ..providers.base import BaseProvider, GenerateResult
from ..style import StyleBible, load_style_bible
from ..storage import StoryPaths


@dataclass
class EngineContext:
    """Per-story generation context."""

    paths: StoryPaths
    provider: BaseProvider
    costs: CostTracker
    provenance: ProvenanceLog
    style: StyleBible
    temperature: float = 0.7


def build_system_prefix(style: StyleBible, stage_instructions: str) -> str:
    """Stable system prompt: IP rules + style bible + stage role.

    Ordering puts stable content first for prompt-caching friendliness.
    """
    parts = [
        "You are assisting a single author with private short-story drafting.",
        "Output is always a RAW DRAFT for the author to rewrite — never finished work.",
        "Never imitate a named living author.",
        "Never use copyrighted characters, worlds, franchise plots, or trademarked settings.",
        "Voice references, if any, come only from the author's own writing in the style bible.",
        style.to_prompt_block(),
        "## Stage instructions",
        stage_instructions.strip(),
    ]
    return "\n\n".join(parts)


def make_engine(
    paths: StoryPaths,
    provider: BaseProvider,
    *,
    budget_cap_usd: Optional[float] = None,
    monthly_totals_path: Optional[Path] = None,
    temperature: float = 0.7,
    style: Optional[StyleBible] = None,
) -> EngineContext:
    """Build an EngineContext for a story workspace."""
    costs = CostTracker(
        paths.costs,
        budget_cap_usd=budget_cap_usd,
        monthly_totals_path=monthly_totals_path,
    )
    return EngineContext(
        paths=paths,
        provider=provider,
        costs=costs,
        provenance=ProvenanceLog(paths.provenance),
        style=style or load_style_bible(),
        temperature=temperature,
    )


def generate_logged(
    engine: EngineContext,
    *,
    stage: str,
    stage_instructions: str,
    prompt: str,
    max_tokens: int = 4096,
    temperature: Optional[float] = None,
    include_style: bool = True,
) -> GenerateResult:
    """Run one model call with budget check, cost log, and provenance.

    Args:
        engine: Story engine context.
        stage: Stage name for logs.
        stage_instructions: Stage role text (from prompts/).
        prompt: User/content prompt (variable portion last).
        max_tokens: Completion budget.
        temperature: Optional override.
        include_style: When False, skip the style bible (useful for continuity).

    Returns:
        GenerateResult from the provider.

    Raises:
        BudgetExceededError: If the projected cost exceeds the cap.
    """
    if include_style:
        system = build_system_prefix(engine.style, stage_instructions)
    else:
        system = (
            "You are a continuity checker for a private short-story draft.\n"
            "Report contradictions only. Do not rewrite prose.\n\n"
            f"## Stage instructions\n{stage_instructions.strip()}"
        )
    temp = engine.temperature if temperature is None else temperature

    # Pre-check against a conservative projected cost using max_tokens as out estimate
    projected = estimate_cost_usd(
        engine.provider.model_name,
        prompt_tokens=max(len(system + prompt) // 4, 1),
        completion_tokens=max_tokens,
    )
    engine.costs.ensure_within_budget(projected)

    result = engine.provider.generate(
        system=system,
        prompt=prompt,
        temperature=temp,
        max_tokens=max_tokens,
    )

    cost_record = engine.costs.record(
        stage=stage,
        model=result.model,
        prompt_tokens=result.prompt_tokens,
        completion_tokens=result.completion_tokens,
        story_slug=engine.paths.root.name,
    )
    engine.provenance.append(
        stage=stage,
        model=result.model,
        temperature=temp,
        system=system,
        prompt=prompt,
        output=result.text,
        prompt_tokens=result.prompt_tokens,
        completion_tokens=result.completion_tokens,
        cost_usd=cost_record.cost_usd,
        finish_reason=result.finish_reason,
    )
    return result


# Re-export for callers
__all__ = [
    "BudgetExceededError",
    "EngineContext",
    "build_system_prefix",
    "generate_logged",
    "make_engine",
]
