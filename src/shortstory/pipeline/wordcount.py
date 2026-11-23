"""Word count helpers for outlines and assembly."""

from __future__ import annotations

import re
from typing import Dict, List, Tuple


def count_words(text: str) -> int:
    """Count whitespace-separated words in text."""
    return len(re.findall(r"\b\w+\b", text or ""))


def parse_scene_target_words(outline_md: str) -> List[Tuple[int, int]]:
    """Extract (scene_number, target_words) pairs from an outline.

    Looks for headings like '## Scene N' and a '- target_words: N' field.
    """
    scenes: List[Tuple[int, int]] = []
    current_scene: int | None = None
    for line in (outline_md or "").splitlines():
        heading = re.match(r"^##\s+Scene\s+(\d+)\b", line.strip(), flags=re.IGNORECASE)
        if heading:
            current_scene = int(heading.group(1))
            continue
        if current_scene is None:
            continue
        target = re.match(r"^-\s*target_words\s*:\s*(\d+)", line.strip(), flags=re.IGNORECASE)
        if target:
            scenes.append((current_scene, int(target.group(1))))
            current_scene = None
    return scenes


def sum_target_words(outline_md: str) -> int:
    """Sum target_words across outline scenes."""
    return sum(words for _, words in parse_scene_target_words(outline_md))


def allocate_evenly(total_words: int, scene_count: int) -> List[int]:
    """Split total_words across scene_count scenes as evenly as possible."""
    if scene_count <= 0:
        raise ValueError("scene_count must be >= 1")
    base = total_words // scene_count
    remainder = total_words % scene_count
    return [base + (1 if i < remainder else 0) for i in range(scene_count)]


def word_count_report(scene_texts: Dict[int, str], target_total: int | None = None) -> str:
    """Build a Markdown word-count report for assembled scenes."""
    lines = ["# Word count report", ""]
    total = 0
    for index in sorted(scene_texts):
        n = count_words(scene_texts[index])
        total += n
        lines.append(f"- Scene {index}: {n} words")
    lines.append(f"- **Total:** {total} words")
    if target_total is not None:
        lines.append(f"- **Target:** {target_total} words")
        lines.append(f"- **Delta:** {total - target_total:+d} words")
    lines.append("")
    lines.append("_This file is a RAW DRAFT for the author to rewrite._")
    return "\n".join(lines)
