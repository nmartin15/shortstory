"""Scene-based drafting pipeline with human checkpoints.

Legacy ShortStoryPipeline remains importable for older tests/services
during migration; new code should use the stage functions below.
"""

from .stages import (
    CheckpointError,
    approve_outline,
    approve_premise,
    assemble_draft,
    continuity_check,
    create_spark,
    draft_scenes,
    generate_outline,
    generate_premises,
    load_story,
    quality_pass_scene,
    redraft_scene,
)
from .structures import FRAMEWORKS, get_framework_prompt, list_frameworks
from .wordcount import allocate_evenly, count_words, sum_target_words

try:
    from ..pipeline_legacy import ShortStoryPipeline
except ImportError:  # pragma: no cover - legacy optional during cleanup
    ShortStoryPipeline = None  # type: ignore

__all__ = [
    "CheckpointError",
    "FRAMEWORKS",
    "ShortStoryPipeline",
    "allocate_evenly",
    "approve_outline",
    "approve_premise",
    "assemble_draft",
    "continuity_check",
    "count_words",
    "create_spark",
    "draft_scenes",
    "generate_outline",
    "generate_premises",
    "get_framework_prompt",
    "list_frameworks",
    "load_story",
    "quality_pass_scene",
    "redraft_scene",
    "sum_target_words",
]
