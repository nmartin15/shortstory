"""Checkpoints, story filesystem, IP gate, word counts."""

import pytest

from src.shortstory.pipeline import (
    CheckpointError,
    allocate_evenly,
    approve_outline,
    approve_premise,
    assemble_draft,
    count_words,
    create_spark,
    sum_target_words,
)
from src.shortstory.pipeline.engine import make_engine
from src.shortstory.pipeline.stages import draft_scenes, generate_outline, generate_premises
from src.shortstory.providers import MockProvider
from src.shortstory.style import check_ip_safety, require_ip_safe
from src.shortstory.storage import read_text, require_story, update_meta_field, write_text


def test_ip_gate_rejects_franchise():
    result = check_ip_safety("A Harry Potter fanfic about Hogwarts")
    assert result.ok is False
    with pytest.raises(ValueError, match="IP safety"):
        require_ip_safe("in the style of Stephen King")


def test_ip_gate_allows_original():
    assert check_ip_safety("A night clerk in Flagstaff finds a ledger that rewrites itself").ok


def test_spark_and_checkpoints(tmp_path):
    paths = create_spark(
        "A night clerk in Flagstaff finds a ledger that rewrites itself",
        slug="flagstaff-ledger",
        stories_root=tmp_path,
        init_git=False,
    )
    assert paths.spark.exists()
    assert paths.root.name == "flagstaff-ledger"

    provider = MockProvider(
        responses=[
            "## Option 1\n- Protagonist: Mira\n",
            "## Scene 1 — open\n- POV: Mira\n- Location: lobby\n- Goal: hide\n"
            "- Obstacle: boss\n- Turn: found out\n- Value shift: safe→exposed\n"
            "- target_words: 2500\n\n"
            "## Scene 2 — close\n- POV: Mira\n- Location: street\n- Goal: flee\n"
            "- Obstacle: rain\n- Turn: returns\n- Value shift: fleeing→facing\n"
            "- target_words: 2500\n",
            "Scene one prose about the ledger.",
            "Scene two prose in the rain.",
        ]
    )
    engine = make_engine(paths, provider, budget_cap_usd=10.0)

    generate_premises(engine)
    assert "awaiting your approval" in read_text(paths.premise)

    with pytest.raises(CheckpointError):
        generate_outline(engine)

    approve_premise(paths)
    generate_outline(engine, framework="try_fail", target_words=5000)
    assert sum_target_words(read_text(paths.outline)) == 5000

    with pytest.raises(CheckpointError):
        draft_scenes(engine)

    approve_outline(paths)
    written = draft_scenes(engine)
    assert len(written) == 2
    assemble_draft(paths)
    assert "RAW DRAFT" in read_text(paths.draft)
    assert count_words(read_text(paths.draft)) > 0


def test_allocate_evenly():
    assert allocate_evenly(100, 3) == [34, 33, 33]
