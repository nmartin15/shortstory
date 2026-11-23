"""Per-call and per-story cost logging with optional budget cap."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .prices import estimate_cost_usd

logger = logging.getLogger(__name__)


@dataclass
class CostRecord:
    """One billed model call."""

    timestamp: str
    stage: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float
    story_slug: str = ""
    cached_prompt_tokens: int = 0


class BudgetExceededError(RuntimeError):
    """Raised when a run would exceed the configured budget cap."""


class CostTracker:
    """Append-only cost log for a story (and optional global monthly total)."""

    def __init__(
        self,
        costs_path: Path,
        *,
        budget_cap_usd: Optional[float] = None,
        monthly_totals_path: Optional[Path] = None,
    ) -> None:
        """Initialize tracker.

        Args:
            costs_path: Path to costs.jsonl for this story.
            budget_cap_usd: Stop before exceeding this story-run budget.
            monthly_totals_path: Optional path for running monthly totals.
        """
        self.costs_path = Path(costs_path)
        self.costs_path.parent.mkdir(parents=True, exist_ok=True)
        self.budget_cap_usd = budget_cap_usd
        if self.budget_cap_usd is None:
            env_cap = os.getenv("BUDGET_CAP_USD", "").strip()
            self.budget_cap_usd = float(env_cap) if env_cap else None
        self.monthly_totals_path = monthly_totals_path
        self._run_cost_usd = 0.0

    @property
    def run_cost_usd(self) -> float:
        """USD spent in the current tracker instance lifetime."""
        return self._run_cost_usd

    def story_total_usd(self) -> float:
        """Sum of all costs logged for this story file."""
        return sum(record.cost_usd for record in self.read_records())

    def read_records(self) -> List[CostRecord]:
        """Load all cost records from disk."""
        if not self.costs_path.exists():
            return []
        records: List[CostRecord] = []
        with self.costs_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                records.append(
                    CostRecord(
                        timestamp=data["timestamp"],
                        stage=data["stage"],
                        model=data["model"],
                        prompt_tokens=int(data.get("prompt_tokens", 0)),
                        completion_tokens=int(data.get("completion_tokens", 0)),
                        cost_usd=float(data.get("cost_usd", 0.0)),
                        story_slug=data.get("story_slug", ""),
                        cached_prompt_tokens=int(data.get("cached_prompt_tokens", 0)),
                    )
                )
        return records

    def ensure_within_budget(self, additional_usd: float = 0.0) -> None:
        """Raise if current run plus additional would exceed the cap.

        Args:
            additional_usd: Prospective next-call cost.

        Raises:
            BudgetExceededError: When the cap would be exceeded.
        """
        if self.budget_cap_usd is None:
            return
        projected = self._run_cost_usd + additional_usd
        if projected > self.budget_cap_usd:
            raise BudgetExceededError(
                f"Budget cap ${self.budget_cap_usd:.4f} would be exceeded "
                f"(run so far ${self._run_cost_usd:.4f}, next ~${additional_usd:.4f}). "
                "Raise BUDGET_CAP_USD or stop the run."
            )

    def record(
        self,
        *,
        stage: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        story_slug: str = "",
        cached_prompt_tokens: int = 0,
        cost_usd: Optional[float] = None,
    ) -> CostRecord:
        """Append one cost line and update totals.

        Args:
            stage: Pipeline stage name.
            model: Model slug.
            prompt_tokens: Input tokens.
            completion_tokens: Output tokens.
            story_slug: Story folder slug.
            cached_prompt_tokens: Cached input tokens if known.
            cost_usd: Optional precomputed cost; otherwise estimated from prices.

        Returns:
            The written CostRecord.

        Raises:
            BudgetExceededError: If recording would exceed the cap.
        """
        if cost_usd is None:
            cost_usd = estimate_cost_usd(
                model,
                prompt_tokens,
                completion_tokens,
                cached_prompt_tokens=cached_prompt_tokens,
            )

        self.ensure_within_budget(cost_usd)

        record = CostRecord(
            timestamp=datetime.now(timezone.utc).isoformat(),
            stage=stage,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=cost_usd,
            story_slug=story_slug,
            cached_prompt_tokens=cached_prompt_tokens,
        )
        with self.costs_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(record)) + "\n")

        self._run_cost_usd += cost_usd
        self._append_monthly_total(cost_usd)
        logger.info(
            "Cost recorded stage=%s model=%s tokens_in=%s tokens_out=%s cost=$%.6f",
            stage,
            model,
            prompt_tokens,
            completion_tokens,
            cost_usd,
        )
        return record

    def stage_summary(self) -> Dict[str, float]:
        """Return {stage: cost_usd} for this story."""
        summary: Dict[str, float] = {}
        for record in self.read_records():
            summary[record.stage] = summary.get(record.stage, 0.0) + record.cost_usd
        return summary

    def format_report(self) -> str:
        """Human-readable cost report for the story."""
        records = self.read_records()
        if not records:
            return "No model costs recorded yet."
        lines = ["Cost report:"]
        for stage, total in self.stage_summary().items():
            lines.append(f"  {stage}: ${total:.6f}")
        lines.append(f"  story total: ${self.story_total_usd():.6f}")
        lines.append(f"  this run: ${self._run_cost_usd:.6f}")
        monthly = self.monthly_total_usd()
        if monthly is not None:
            lines.append(f"  month-to-date: ${monthly:.6f}")
        return "\n".join(lines)

    def monthly_total_usd(self) -> Optional[float]:
        """Read month-to-date total if a monthly file is configured."""
        if self.monthly_totals_path is None or not self.monthly_totals_path.exists():
            return None
        month_key = datetime.now(timezone.utc).strftime("%Y-%m")
        with self.monthly_totals_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                data = json.loads(line)
                if data.get("month") == month_key:
                    return float(data.get("total_usd", 0.0))
        return 0.0

    def _append_monthly_total(self, cost_usd: float) -> None:
        """Update running monthly total file if configured."""
        if self.monthly_totals_path is None:
            return
        self.monthly_totals_path.parent.mkdir(parents=True, exist_ok=True)
        month_key = datetime.now(timezone.utc).strftime("%Y-%m")
        totals: Dict[str, float] = {}
        if self.monthly_totals_path.exists():
            with self.monthly_totals_path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    data = json.loads(line)
                    totals[data["month"]] = float(data.get("total_usd", 0.0))
        totals[month_key] = totals.get(month_key, 0.0) + cost_usd
        with self.monthly_totals_path.open("w", encoding="utf-8") as handle:
            for month, total in sorted(totals.items()):
                handle.write(json.dumps({"month": month, "total_usd": round(total, 8)}) + "\n")
