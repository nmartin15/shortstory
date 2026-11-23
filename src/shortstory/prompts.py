"""Load prompt templates from the prompts/ directory."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
PROMPTS_DIR = _REPO_ROOT / "prompts"


@lru_cache(maxsize=32)
def load_prompt(name: str) -> str:
    """Load a Markdown prompt template by stem name.

    Args:
        name: File stem, e.g. 'premise' for prompts/premise.md.

    Returns:
        Prompt text.

    Raises:
        FileNotFoundError: If the prompt file is missing.
    """
    path = PROMPTS_DIR / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"Prompt template not found: {path}")
    return path.read_text(encoding="utf-8").strip()


def clear_prompt_cache() -> None:
    """Clear cached prompts (tests)."""
    load_prompt.cache_clear()
