"""Pipeline stages: spark → premise → outline → draft → quality → continuity → assemble."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Dict, List, Optional

from ..prompts import load_prompt
from ..quality import (
    detect_cliches_with_style,
    detect_repetition,
    first_flagged_paragraph,
)
from ..storage import (
    StoryPaths,
    init_story,
    is_outline_approved,
    is_premise_approved,
    list_scene_files,
    read_meta,
    read_text,
    require_story,
    scene_path,
    update_meta_field,
    write_text,
)
from .engine import EngineContext, generate_logged
from .structures import get_framework_prompt
from .wordcount import count_words, sum_target_words, word_count_report

logger = logging.getLogger(__name__)

DRAFT_BANNER = (
    "> **RAW DRAFT** — Generated for you to rewrite. Not a finished story.\n\n"
)


class CheckpointError(RuntimeError):
    """Raised when a required human checkpoint has not been approved."""


def create_spark(
    spark_text: str,
    *,
    slug: Optional[str] = None,
    stories_root=None,
    init_git: bool = True,
) -> StoryPaths:
    """Save raw spark and create the story workspace."""
    from ..style import require_ip_safe

    require_ip_safe(spark_text)
    return init_story(
        spark_text,
        slug=slug,
        stories_root=stories_root,
        init_git=init_git,
    )


def generate_premises(engine: EngineContext) -> str:
    """Generate 3 premise options into 01_premise.md (not yet approved)."""
    from ..style import require_ip_safe

    spark = read_text(engine.paths.spark)
    require_ip_safe(spark)
    prompt = (
        f"Author spark:\n\n{spark.strip()}\n\n"
        "Generate three distinct premise options as specified."
    )
    result = generate_logged(
        engine,
        stage="premise",
        stage_instructions=load_prompt("premise"),
        prompt=prompt,
        max_tokens=4000,
    )
    if not result.text.strip():
        raise RuntimeError(
            "Premise generation returned empty text. "
            "Try DRAFT_MODEL=deepseek/deepseek-v4.1-flash in .env and rerun."
        )
    body = (
        "# Premise options (pick or edit one, then approve)\n\n"
        "Status: **awaiting your approval** — no prose will be drafted until you approve.\n\n"
        f"{result.text.strip()}\n"
    )
    write_text(engine.paths.premise, body)
    update_meta_field(engine.paths, "status", "premise")
    update_meta_field(engine.paths, "approved_premise", False)
    return body


def approve_premise(paths: StoryPaths) -> None:
    """Mark premise as approved after the author edits/selects."""
    if not paths.premise.exists() or not read_text(paths.premise).strip():
        raise CheckpointError("No premise file to approve. Run premise generation first.")
    update_meta_field(paths, "approved_premise", True)
    update_meta_field(paths, "status", "premise_approved")


def generate_outline(
    engine: EngineContext,
    *,
    framework: str = "story_circle",
    target_words: int = 5000,
) -> str:
    """Generate a 6–12 scene outline. Requires approved premise."""
    if not is_premise_approved(engine.paths):
        raise CheckpointError(
            "Premise not approved. Edit 01_premise.md, then run approve-premise."
        )
    framework_block = get_framework_prompt(framework)
    premise = read_text(engine.paths.premise)
    spark = read_text(engine.paths.spark)
    prompt = (
        f"Framework:\n{framework_block}\n\n"
        f"Story target word count: {target_words}\n\n"
        f"Spark:\n{spark.strip()}\n\n"
        f"Approved premise material:\n{premise.strip()}\n\n"
        "Write the scene outline now. Ensure target_words sum to the story target."
    )
    result = generate_logged(
        engine,
        stage="outline",
        stage_instructions=load_prompt("outline"),
        prompt=prompt,
        # Reasoning models spend many tokens internally; leave headroom for content.
        max_tokens=12000,
    )
    if not result.text.strip():
        raise RuntimeError("Outline generation returned empty text.")
    body = (
        f"# Outline ({framework}, target {target_words} words)\n\n"
        "Status: **awaiting your approval** — drafting is locked until you approve.\n\n"
        f"{result.text.strip()}\n"
    )
    write_text(engine.paths.outline, body)
    update_meta_field(engine.paths, "framework", framework)
    update_meta_field(engine.paths, "target_words", target_words)
    update_meta_field(engine.paths, "status", "outline")
    update_meta_field(engine.paths, "approved_outline", False)
    return body


def approve_outline(paths: StoryPaths) -> None:
    """Mark outline as approved."""
    if not paths.outline.exists() or not read_text(paths.outline).strip():
        raise CheckpointError("No outline file to approve. Run outline generation first.")
    update_meta_field(paths, "approved_outline", True)
    update_meta_field(paths, "status", "outline_approved")


def _require_draft_ready(paths: StoryPaths) -> None:
    if not is_premise_approved(paths):
        raise CheckpointError("Premise not approved.")
    if not is_outline_approved(paths):
        raise CheckpointError("Outline not approved. Nothing is drafted until you approve.")


def _parse_scene_briefs(outline_md: str) -> List[Dict[str, str]]:
    """Split outline into scene brief dicts."""
    briefs: List[Dict[str, str]] = []
    chunks = re.split(r"(?=^##\s+Scene\s+\d+)", outline_md, flags=re.MULTILINE)
    for chunk in chunks:
        match = re.match(r"^##\s+Scene\s+(\d+)\b[^\n]*\n(.*)$", chunk.strip(), flags=re.DOTALL)
        if not match:
            continue
        briefs.append({"number": match.group(1), "body": match.group(2).strip()})
    return briefs


def _prior_context(paths: StoryPaths, scene_index: int) -> str:
    """Short summaries of prior scenes + last ~300 words of previous scene."""
    parts: List[str] = []
    for path in list_scene_files(paths):
        try:
            idx = int(path.stem)
        except ValueError:
            continue
        if idx >= scene_index:
            break
        text = read_text(path)
        words = text.split()
        summary = " ".join(words[:80])
        parts.append(f"Scene {idx} summary: {summary}…")
    if scene_index > 1:
        prev = scene_path(paths, scene_index - 1)
        if prev.exists():
            prev_words = read_text(prev).split()
            tail = " ".join(prev_words[-300:])
            parts.append(f"End of previous scene (last words):\n{tail}")
    return "\n\n".join(parts) if parts else "(none — this is the opening scene)"


def draft_scenes(
    engine: EngineContext,
    *,
    only_scene: Optional[int] = None,
) -> List[Path]:
    """Draft scenes one call at a time. Requires outline approval."""
    _require_draft_ready(engine.paths)
    outline = read_text(engine.paths.outline)
    briefs = _parse_scene_briefs(outline)
    if not briefs:
        raise RuntimeError("Could not parse scenes from outline. Check 02_outline.md headings.")

    written: List[Path] = []
    for brief in briefs:
        index = int(brief["number"])
        if only_scene is not None and index != only_scene:
            continue
        target_match = re.search(r"target_words\s*:\s*(\d+)", brief["body"], flags=re.I)
        target_words = int(target_match.group(1)) if target_match else 500
        # ~2 tokens/word for prose + large reasoning-headroom for OpenRouter models
        max_tokens = min(max(int(target_words * 4), 6000), 16000)
        prompt = (
            f"Scene {index} brief:\n{brief['body']}\n\n"
            f"Continuity context:\n{_prior_context(engine.paths, index)}\n\n"
            f"Write scene {index} now (~{target_words} words)."
        )
        result = generate_logged(
            engine,
            stage=f"scene_{index:02d}",
            stage_instructions=load_prompt("scene_draft"),
            prompt=prompt,
            max_tokens=max_tokens,
        )
        prose = quality_pass_scene(engine, result.text, scene_index=index)
        out = scene_path(engine.paths, index)
        write_text(out, DRAFT_BANNER + prose.strip() + "\n")
        written.append(out)
        logger.info("Drafted scene %s (%s words)", index, count_words(prose))

    update_meta_field(engine.paths, "status", "drafting")
    return written


def redraft_scene(engine: EngineContext, scene_index: int) -> Path:
    """Redraft a single scene."""
    _require_draft_ready(engine.paths)
    path = scene_path(engine.paths, scene_index)
    existing = read_text(path)
    outline = read_text(engine.paths.outline)
    briefs = {int(b["number"]): b["body"] for b in _parse_scene_briefs(outline)}
    brief = briefs.get(scene_index, "")
    prompt = (
        f"Scene {scene_index} brief:\n{brief}\n\n"
        f"Continuity context:\n{_prior_context(engine.paths, scene_index)}\n\n"
        f"Current scene draft:\n{existing}\n\n"
        "Redraft this scene."
    )
    result = generate_logged(
        engine,
        stage=f"scene_{scene_index:02d}_redraft",
        stage_instructions=load_prompt("scene_redraft"),
        prompt=prompt,
        max_tokens=5000,
    )
    prose = quality_pass_scene(engine, result.text, scene_index=scene_index)
    write_text(path, DRAFT_BANNER + prose.strip() + "\n")
    return path


def quality_pass_scene(engine: EngineContext, text: str, *, scene_index: int) -> str:
    """Run cliché + repetition checks; regenerate one flagged paragraph once."""
    cliches = detect_cliches_with_style(text, engine.style)
    repetition = detect_repetition(text)
    if not cliches.has_cliches and not repetition.has_repetition:
        if engine.style.ban_em_dashes:
            text = text.replace("—", ", ").replace("–", ", ")
        return text

    paragraph = first_flagged_paragraph(text, cliches) if cliches.has_cliches else None
    if paragraph is None and repetition.repeated_sentences:
        # Find a paragraph containing a repeated sentence
        for para in re.split(r"\n\s*\n", text):
            if repetition.repeated_sentences[0] in para.lower():
                paragraph = para.strip()
                break
    if not paragraph:
        return text

    prompt = (
        f"Flagged paragraph from scene {scene_index}:\n\n{paragraph}\n\n"
        f"Cliché hits: {[h.phrase for h in cliches.hits[:5]]}\n"
        f"Repetition notes: {repetition.repeated_ngrams[:3]}"
    )
    try:
        result = generate_logged(
            engine,
            stage=f"scene_{scene_index:02d}_quality",
            stage_instructions=load_prompt("quality_paragraph"),
            prompt=prompt,
            max_tokens=800,
            temperature=0.5,
        )
        replacement = result.text.strip()
        if replacement:
            text = text.replace(paragraph, replacement, 1)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Quality paragraph regen failed: %s", exc)

    if engine.style.ban_em_dashes:
        text = text.replace("—", ", ").replace("–", ", ")
    return text


def continuity_check(engine: EngineContext) -> str:
    """Report continuity issues without auto-rewriting."""
    _require_draft_ready(engine.paths)
    scenes = []
    for path in list_scene_files(engine.paths):
        text = re.sub(r"^>\s*\*\*RAW DRAFT\*\*.*\n\n", "", read_text(path), count=1).strip()
        words = text.split()
        # Compress: opening + closing snippet per scene (full dump burns reasoning budget)
        if len(words) > 220:
            snippet = " ".join(words[:120]) + " […] " + " ".join(words[-80:])
        else:
            snippet = text
        scenes.append(f"### {path.name} ({count_words(text)} words)\n{snippet}")
    if not scenes:
        raise RuntimeError("No scenes to check. Draft scenes first.")
    outline = read_text(engine.paths.outline)
    prompt = (
        f"Outline (for name/timeline reference):\n{outline[:4000]}\n\n"
        f"Scene excerpts:\n\n" + "\n\n".join(scenes)
    )
    result = generate_logged(
        engine,
        stage="continuity",
        stage_instructions=load_prompt("continuity"),
        prompt=prompt,
        max_tokens=12000,
        temperature=0.2,
        include_style=False,
    )
    body = result.text.strip() + "\n"
    write_text(engine.paths.continuity, body)
    update_meta_field(engine.paths, "status", "continuity")
    return body


_BANNER_RE = re.compile(
    r"(?is)^(?:>\s*)?\*{0,2}RAW DRAFT\*{0,2}[^\n]*\n+",
)


def _clean_scene_prose(text: str) -> str:
    """Strip draft banners and leftover labels from a scene file."""
    text = _BANNER_RE.sub("", text or "", count=1).strip()
    # Drop accidental mid-file banner lines the model sometimes echoes
    lines = [
        line
        for line in text.splitlines()
        if not re.search(r"(?i)raw draft", line)
    ]
    return "\n".join(lines).strip()


def assemble_draft(paths: StoryPaths, *, print_title: Optional[str] = None) -> str:
    """Stitch scenes into continuous short-story prose for rewriting/print.

    Internal scene files stay as scaffolding. The assembled draft uses blank-line
    breaks between movements — not screenplay-style scene headings.
    """
    _require_draft_ready(paths)
    scene_texts: Dict[int, str] = {}
    for path in list_scene_files(paths):
        try:
            idx = int(path.stem)
        except ValueError:
            continue
        cleaned = _clean_scene_prose(read_text(path))
        if cleaned:
            scene_texts[idx] = cleaned
    if not scene_texts:
        raise RuntimeError("No scenes found to assemble.")

    meta = read_meta(paths)
    target = int(meta.get("target_words") or sum_target_words(read_text(paths.outline)) or 0)
    title = print_title or meta.get("title") or "The Heron"
    body_parts = [
        DRAFT_BANNER,
        f"# {title}\n",
        "_Raw draft for rewrite — not a finished story._\n",
    ]
    # Continuous prose: blank line between movements, no Scene N headings
    for idx in sorted(scene_texts):
        body_parts.append(scene_texts[idx])
        body_parts.append("")
    body_parts.append("---\n")
    body_parts.append(word_count_report(scene_texts, target_total=target or None))
    assembled = "\n".join(body_parts).strip() + "\n"
    write_text(paths.draft, assembled)
    # Also write a clean print twin without the trailing analytics block
    print_body = "\n\n".join(
        [f"# {title}", ""]
        + [scene_texts[idx] for idx in sorted(scene_texts)]
    ).strip() + "\n"
    write_text(paths.root / "print.md", print_body)
    update_meta_field(paths, "status", "assembled")
    return assembled


def load_story(slug: str, stories_root=None) -> StoryPaths:
    """Convenience wrapper around require_story."""
    return require_story(slug, stories_root)
