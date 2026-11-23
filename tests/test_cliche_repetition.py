"""Cliché and repetition filter tests."""

from src.shortstory.quality import (
    detect_cliches,
    detect_repetition,
    first_flagged_paragraph,
)
from src.shortstory.pipeline.wordcount import allocate_evenly, count_words


def test_detect_cliches():
    text = "In that moment, her heart pounded as time seemed to stand still."
    report = detect_cliches(text)
    assert report.has_cliches
    phrases = {h.phrase for h in report.hits}
    assert "in that moment" in phrases
    assert "her heart pounded" in phrases


def test_first_flagged_paragraph():
    text = "Clean paragraph.\n\nIn that moment everything changed.\n\nAlso clean."
    report = detect_cliches(text)
    para = first_flagged_paragraph(text, report)
    assert para is not None
    assert "in that moment" in para.lower()


def test_detect_repetition():
    sentence = "The door refused to open no matter what."
    text = f"{sentence} Something else. {sentence}"
    report = detect_repetition(text)
    assert report.has_repetition
    assert any("door refused" in s for s in report.repeated_sentences)


def test_word_count_math():
    assert count_words("one two three") == 3
    assert sum(allocate_evenly(5000, 8)) == 5000
