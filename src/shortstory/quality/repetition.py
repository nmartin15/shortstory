"""Repetition checks for scene prose."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from typing import List, Tuple


@dataclass(frozen=True)
class RepetitionReport:
    """Repeated content findings."""

    repeated_sentences: List[str]
    repeated_ngrams: List[Tuple[str, int]]

    @property
    def has_repetition(self) -> bool:
        """True if notable repetition was found."""
        return bool(self.repeated_sentences or self.repeated_ngrams)


def _normalize_sentence(sentence: str) -> str:
    return re.sub(r"\s+", " ", sentence.strip().lower())


def detect_repetition(text: str, *, ngram_size: int = 5, min_ngram_count: int = 3) -> RepetitionReport:
    """Flag duplicate sentences and overused word n-grams.

    Args:
        text: Prose to scan.
        ngram_size: Word n-gram length.
        min_ngram_count: Minimum repeats to flag an n-gram.

    Returns:
        RepetitionReport.
    """
    text = text or ""
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
    counts = Counter(_normalize_sentence(s) for s in sentences if len(s.split()) >= 4)
    repeated_sentences = [s for s, n in counts.items() if n >= 2]

    words = re.findall(r"[A-Za-z']+", text.lower())
    ngrams: Counter[str] = Counter()
    if len(words) >= ngram_size:
        for i in range(len(words) - ngram_size + 1):
            gram = " ".join(words[i : i + ngram_size])
            ngrams[gram] += 1
    repeated_ngrams = [
        (gram, count)
        for gram, count in ngrams.most_common(20)
        if count >= min_ngram_count
    ]

    return RepetitionReport(
        repeated_sentences=repeated_sentences,
        repeated_ngrams=repeated_ngrams,
    )
