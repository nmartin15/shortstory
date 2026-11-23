"""Selectable story structure frameworks."""

from __future__ import annotations

from typing import Dict

FRAMEWORKS: Dict[str, str] = {
    "story_circle": (
        "Story Circle (adapted Dan Harmon): "
        "(1) You — establish protagonist in a zone of comfort; "
        "(2) Need — they want something; "
        "(3) Go — enter an unfamiliar situation; "
        "(4) Search — adapt to it; "
        "(5) Find — get what they wanted; "
        "(6) Take — pay a heavy price; "
        "(7) Return — back to familiar; "
        "(8) Change — having changed. "
        "Map these beats across 6–12 scenes."
    ),
    "try_fail": (
        "Try-fail cycles: Protagonist pursues a concrete goal through escalating "
        "attempts. Alternate try/fail (or try/succeed-with-cost) cycles that raise "
        "stakes. End with a decisive confrontation where the need (not just the want) "
        "is answered. Map cycles across 6–12 scenes."
    ),
    "mice": (
        "MICE quotient nesting (Orson Scott Card framing as structure only — do not "
        "imitate any author's prose): nest Milieu, Idea, Character, and Event threads. "
        "Open outermost thread first; close threads in reverse order. Assign each scene "
        "a primary MICE focus and note nested opens/closes. Use 6–12 scenes."
    ),
}


def list_frameworks() -> Dict[str, str]:
    """Return framework id → description."""
    return dict(FRAMEWORKS)


def get_framework_prompt(framework_id: str) -> str:
    """Return the framework instruction block.

    Raises:
        ValueError: If framework_id is unknown.
    """
    key = (framework_id or "").strip().lower().replace("-", "_")
    if key not in FRAMEWORKS:
        raise ValueError(
            f"Unknown framework '{framework_id}'. "
            f"Choose one of: {', '.join(sorted(FRAMEWORKS))}"
        )
    return FRAMEWORKS[key]
