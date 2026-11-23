"""Quality filters for drafted scenes."""

from .cliches import (
    ClicheHit,
    ClicheReport,
    detect_cliches,
    detect_cliches_with_style,
    first_flagged_paragraph,
)
from .repetition import RepetitionReport, detect_repetition

__all__ = [
    "ClicheHit",
    "ClicheReport",
    "RepetitionReport",
    "detect_cliches",
    "detect_cliches_with_style",
    "detect_repetition",
    "first_flagged_paragraph",
]
