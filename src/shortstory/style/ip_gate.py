"""Reject sparks that name living authors or copyrighted franchises."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Sequence, Tuple

# Intentionally imperfect lists — expand over time. Matching is case-insensitive.
LIVING_AUTHOR_PATTERNS: Sequence[str] = (
    r"\bstephen\s+king\b",
    r"\bg\.?\s*r\.?\s*r\.?\s*martin\b",
    r"\bgeorge\s+r\.?\s*r\.?\s*martin\b",
    r"\bneil\s+gaiman\b",
    r"\bmargaret\s+atwood\b",
    r"\bsalman\s+rushdie\b",
    r"\bkazuo\s+ishiguro\b",
    r"\bcolm\s+t[oó]ib[ií]n\b",
    r"\belena\s+ferrante\b",
    r"\bharuki\s+murakami\b",
    r"\bomar\s+el\s+akkad\b",
    r"\bbrian\s+evenson\b",
    r"\bkelly\s+link\b",
    r"\bcarmen\s+maria\s+machado\b",
    r"\bocean\s+vuong\b",
    r"\bsally\s+rooney\b",
    r"\bbrandon\s+sanderson\b",
    r"\bn\.?\s*k\.?\s*jemisin\b",
    r"\btana\s+french\b",
    r"\bgillian\s+flynn\b",
)

FRANCHISE_PATTERNS: Sequence[str] = (
    r"\bharry\s+potter\b",
    r"\bhogwarts\b",
    r"\bstar\s+wars\b",
    r"\bstar\s+trek\b",
    r"\bmiddle[- ]earth\b",
    r"\blord\s+of\s+the\s+rings\b",
    r"\bgame\s+of\s+thrones\b",
    r"\bwesteros\b",
    r"\bmarvel\b",
    r"\bdc\s+comics\b",
    r"\bbatman\b",
    r"\bsuperman\b",
    r"\bwonder\s+woman\b",
    r"\bspider[- ]?man\b",
    r"\bdune\b",
    r"\barrakis\b",
    r"\bwitcher\b",
    r"\bdiscworld\b",
    r"\bnarnia\b",
    r"\bpokemon\b",
    r"\bpokémon\b",
    r"\bfrozen\b",
    r"\belas?a\b",  # too broad? skip - remove Elsa
    r"\bmickey\s+mouse\b",
    r"\bstudio\s+ghibli\b",
    r"\binception\b",  # film title as plot request often IP-adjacent; keep mild
)


@dataclass(frozen=True)
class IPGateResult:
    """Result of scanning a spark or style request."""

    ok: bool
    matches: Tuple[str, ...]
    explanation: str


def check_ip_safety(text: str) -> IPGateResult:
    """Scan text for named living authors or franchise references.

    Args:
        text: Spark, premise request, or style instruction.

    Returns:
        IPGateResult. ok=False means the request must be rejected.
    """
    matches: List[str] = []
    for pattern in LIVING_AUTHOR_PATTERNS:
        found = re.search(pattern, text or "", flags=re.IGNORECASE)
        if found:
            matches.append(found.group(0))
    for pattern in FRANCHISE_PATTERNS:
        # Drop overly broad patterns that were placeholders
        if pattern in (r"\belas?a\b",):
            continue
        found = re.search(pattern, text or "", flags=re.IGNORECASE)
        if found:
            matches.append(found.group(0))

    if not matches:
        return IPGateResult(ok=True, matches=(), explanation="")

    unique = tuple(dict.fromkeys(matches))
    explanation = (
        "Rejected for IP safety: this tool will not imitate named living authors "
        "or use existing copyrighted characters, worlds, or franchise plots. "
        f"Matched: {', '.join(unique)}. "
        "Rephrase using your own premise, setting, and voice references from "
        "your writing in style.yaml."
    )
    return IPGateResult(ok=False, matches=unique, explanation=explanation)


def require_ip_safe(text: str) -> None:
    """Raise ValueError if text fails the IP gate."""
    result = check_ip_safety(text)
    if not result.ok:
        raise ValueError(result.explanation)
