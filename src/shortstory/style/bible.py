"""Load and render the writer's style bible."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import yaml

_REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_STYLE_PATH = _REPO_ROOT / "style.yaml"


@dataclass
class StyleBible:
    """Writer-controlled style constraints for generation."""

    pov: str = "third_limited"
    tense: str = "past"
    tone: str = ""
    rhythm: str = ""
    ban_em_dashes: bool = True
    banned_phrases: List[str] = field(default_factory=list)
    voice_references: List[str] = field(default_factory=list)

    def to_prompt_block(self) -> str:
        """Render a stable system-prompt block (cache-friendly prefix)."""
        lines = [
            "## Style bible (author-controlled)",
            f"- POV: {self.pov}",
            f"- Tense: {self.tense}",
        ]
        if self.tone:
            lines.append(f"- Tone: {self.tone}")
        if self.rhythm:
            lines.append(f"- Rhythm: {self.rhythm}")
        if self.ban_em_dashes:
            lines.append(
                "- Em dashes: Do NOT use em dashes (—) in generated prose. "
                "Use commas, periods, or parentheses instead."
            )
        if self.banned_phrases:
            lines.append("- Banned phrases (never use):")
            for phrase in self.banned_phrases:
                lines.append(f"  - {phrase}")
        if self.voice_references:
            lines.append(
                "- Voice references (imitate rhythm/diction only; these are the "
                "author's own writing — do not copy plot or characters):"
            )
            for idx, ref in enumerate(self.voice_references, start=1):
                cleaned = ref.strip()
                if cleaned:
                    lines.append(f"  Reference {idx}:")
                    lines.append(f'  """{cleaned}"""')
        return "\n".join(lines)


def load_style_bible(path: Optional[Path] = None) -> StyleBible:
    """Load style.yaml from disk.

    Args:
        path: Optional override path.

    Returns:
        StyleBible instance (defaults if file missing).
    """
    style_path = Path(path) if path else DEFAULT_STYLE_PATH
    if not style_path.exists():
        return StyleBible()
    with style_path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    return StyleBible(
        pov=str(data.get("pov", "third_limited")),
        tense=str(data.get("tense", "past")),
        tone=str(data.get("tone", "") or ""),
        rhythm=str(data.get("rhythm", "") or ""),
        ban_em_dashes=bool(data.get("ban_em_dashes", True)),
        banned_phrases=[str(p) for p in (data.get("banned_phrases") or [])],
        voice_references=[str(v) for v in (data.get("voice_references") or [])],
    )
