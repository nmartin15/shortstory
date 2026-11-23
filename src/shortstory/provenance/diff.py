"""Measure how much of a model-written file the human changed."""

from __future__ import annotations

import difflib
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class DiffReport:
    """Human-edit distance versus a model baseline.

    Attributes:
        baseline_chars: Characters in the model output baseline.
        current_chars: Characters in the current file.
        changed_ratio: Fraction of baseline that differs (0.0–1.0+).
        percent_changed: changed_ratio * 100.
        identical: True if texts match exactly.
    """

    baseline_chars: int
    current_chars: int
    changed_ratio: float
    percent_changed: float
    identical: bool


def percent_changed(baseline: str, current: str) -> DiffReport:
    """Estimate how much of the model text was altered.

    Uses SequenceMatcher ratio: changed_ratio = 1 - similarity.
    Empty baseline with non-empty current counts as 100% human-authored.

    Args:
        baseline: Original model-written text.
        current: Current on-disk text after human edits.

    Returns:
        DiffReport with percent_changed.
    """
    baseline = baseline or ""
    current = current or ""
    if baseline == current:
        return DiffReport(
            baseline_chars=len(baseline),
            current_chars=len(current),
            changed_ratio=0.0,
            percent_changed=0.0,
            identical=True,
        )
    if not baseline:
        return DiffReport(
            baseline_chars=0,
            current_chars=len(current),
            changed_ratio=1.0,
            percent_changed=100.0,
            identical=False,
        )

    matcher = difflib.SequenceMatcher(a=baseline, b=current)
    similarity = matcher.ratio()
    changed_ratio = 1.0 - similarity
    return DiffReport(
        baseline_chars=len(baseline),
        current_chars=len(current),
        changed_ratio=changed_ratio,
        percent_changed=round(changed_ratio * 100.0, 2),
        identical=False,
    )


def format_diff_report(path_label: str, report: DiffReport) -> str:
    """Format a single-file diff report line."""
    if report.identical:
        return f"{path_label}: unchanged (0% edited)"
    return (
        f"{path_label}: ~{report.percent_changed:.1f}% changed "
        f"(baseline {report.baseline_chars} chars → {report.current_chars} chars)"
    )


def compare_optional(baseline: Optional[str], current: str, label: str) -> str:
    """Compare when baseline may be missing."""
    if baseline is None:
        return f"{label}: no model baseline in provenance yet"
    return format_diff_report(label, percent_changed(baseline, current))
