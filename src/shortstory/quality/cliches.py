"""Cliché phrase detection for scene quality passes."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Sequence

from ..style.bible import StyleBible, load_style_bible

DEFAULT_CLICHES: Sequence[str] = (
    "it was a dark and stormy night",
    "once upon a time",
    "little did they know",
    "in that moment",
    "her heart pounded",
    "his eyes widened",
    "time seemed to stand still",
    "without warning",
    "out of nowhere",
    "a single tear",
    "the air was thick with tension",
    "delve",
    "tapestry",
)


@dataclass(frozen=True)
class ClicheHit:
    """One matched cliché phrase."""

    phrase: str
    index: int


@dataclass(frozen=True)
class ClicheReport:
    """Cliché scan result."""

    hits: List[ClicheHit]

    @property
    def has_cliches(self) -> bool:
        """True if any hits were found."""
        return bool(self.hits)


def detect_cliches(text: str, phrases: Sequence[str] | None = None) -> ClicheReport:
    """Find banned/cliché phrases in text (case-insensitive).

    Args:
        text: Prose to scan.
        phrases: Optional phrase list; defaults to DEFAULT_CLICHES.

    Returns:
        ClicheReport with hit locations.
    """
    phrases = list(phrases) if phrases is not None else list(DEFAULT_CLICHES)
    hits: List[ClicheHit] = []
    lower = text or ""
    for phrase in phrases:
        if not phrase:
            continue
        for match in re.finditer(re.escape(phrase), lower, flags=re.IGNORECASE):
            hits.append(ClicheHit(phrase=phrase, index=match.start()))
    return ClicheReport(hits=hits)


def detect_cliches_with_style(text: str, style: StyleBible | None = None) -> ClicheReport:
    """Detect using style bible banned phrases plus defaults."""
    style = style or load_style_bible()
    phrases = list(dict.fromkeys([*DEFAULT_CLICHES, *style.banned_phrases]))
    return detect_cliches(text, phrases)


def first_flagged_paragraph(text: str, report: ClicheReport) -> str | None:
    """Return the first paragraph containing a cliché hit, if any."""
    if not report.hits:
        return None
    paragraphs = re.split(r"\n\s*\n", text or "")
    cursor = 0
    hit_index = min(h.index for h in report.hits)
    for para in paragraphs:
        end = cursor + len(para)
        if cursor <= hit_index <= end:
            return para.strip()
        cursor = end + 2  # account for split gap
    return paragraphs[0].strip() if paragraphs else None
