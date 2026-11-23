"""CLI primary interface for the private drafting tool."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional

import click
from dotenv import load_dotenv

from .cost import CostTracker
from .pipeline import (
    CheckpointError,
    approve_outline,
    approve_premise,
    assemble_draft,
    continuity_check,
    create_spark,
    draft_scenes,
    generate_outline,
    generate_premises,
    list_frameworks,
    redraft_scene,
)
from .pipeline.engine import make_engine
from .provenance import compare_optional
from .providers import create_provider, get_draft_model_name, get_premium_model_name
from .storage import (
    DEFAULT_STORIES_ROOT,
    list_stories,
    read_text,
    require_story,
)
from .exports import export_docx, export_epub, export_pdf

load_dotenv()

REPO_ROOT = Path(__file__).resolve().parents[2]
MONTHLY_TOTALS = REPO_ROOT / "data" / "monthly_costs.jsonl"


def _provider(premium: bool):
    model = get_premium_model_name() if premium else get_draft_model_name()
    return create_provider(model_name=model)


def _engine(slug: str, premium: bool = False, stories_root: Optional[Path] = None):
    paths = require_story(slug, stories_root)
    return make_engine(
        paths,
        _provider(premium),
        monthly_totals_path=MONTHLY_TOTALS,
        temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
    )


@click.group()
@click.option(
    "--stories-root",
    type=click.Path(path_type=Path),
    default=None,
    help="Override stories directory",
)
@click.pass_context
def main(ctx: click.Context, stories_root: Optional[Path]) -> None:
    """shortstoryfun — private short-story drafting (raw drafts only)."""
    ctx.ensure_object(dict)
    ctx.obj["stories_root"] = stories_root or DEFAULT_STORIES_ROOT


@main.command("spark")
@click.argument("text", required=False)
@click.option("--file", "spark_file", type=click.Path(exists=True, path_type=Path))
@click.option("--slug", default=None, help="Optional story slug")
@click.pass_context
def spark_cmd(ctx: click.Context, text: Optional[str], spark_file: Optional[Path], slug: Optional[str]) -> None:
    """Save your raw spark and create a story folder."""
    if spark_file:
        text = spark_file.read_text(encoding="utf-8")
    if not text:
        text = click.get_text_stream("stdin").read()
    if not text.strip():
        raise click.UsageError("Provide spark text, --file, or stdin.")
    paths = create_spark(text, slug=slug, stories_root=ctx.obj["stories_root"])
    click.echo(f"Created story workspace: {paths.root}")
    click.echo("Next: shortstory premise <slug>")


@main.command("premise")
@click.argument("slug")
@click.option("--premium", is_flag=True, help="Use PREMIUM_MODEL (never automatic)")
@click.pass_context
def premise_cmd(ctx: click.Context, slug: str, premium: bool) -> None:
    """Generate 3 premise options (checkpoint: you must approve before outline)."""
    engine = _engine(slug, premium=premium, stories_root=ctx.obj["stories_root"])
    generate_premises(engine)
    click.echo(f"Wrote {engine.paths.premise}")
    click.echo("Edit the file, pick/edit one option, then: shortstory approve-premise <slug>")
    click.echo(engine.costs.format_report())


@main.command("approve-premise")
@click.argument("slug")
@click.pass_context
def approve_premise_cmd(ctx: click.Context, slug: str) -> None:
    """Approve the premise after you edit it."""
    paths = require_story(slug, ctx.obj["stories_root"])
    approve_premise(paths)
    click.echo("Premise approved. Next: shortstory outline <slug>")


@main.command("outline")
@click.argument("slug")
@click.option(
    "--framework",
    type=click.Choice(sorted(list_frameworks().keys()), case_sensitive=False),
    default="story_circle",
)
@click.option("--words", default=5000, show_default=True, help="Target story word count")
@click.option("--premium", is_flag=True)
@click.pass_context
def outline_cmd(ctx: click.Context, slug: str, framework: str, words: int, premium: bool) -> None:
    """Generate a 6–12 scene outline (requires approved premise)."""
    engine = _engine(slug, premium=premium, stories_root=ctx.obj["stories_root"])
    try:
        generate_outline(engine, framework=framework, target_words=words)
    except CheckpointError as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(f"Wrote {engine.paths.outline}")
    click.echo("Edit if needed, then: shortstory approve-outline <slug>")
    click.echo(engine.costs.format_report())


@main.command("approve-outline")
@click.argument("slug")
@click.pass_context
def approve_outline_cmd(ctx: click.Context, slug: str) -> None:
    """Approve the outline — unlocks scene drafting."""
    paths = require_story(slug, ctx.obj["stories_root"])
    approve_outline(paths)
    click.echo("Outline approved. Next: shortstory draft <slug>")


@main.command("draft")
@click.argument("slug")
@click.option("--scene", type=int, default=None, help="Draft only this scene number")
@click.option("--premium", is_flag=True, help="Use PREMIUM_MODEL for this run only")
@click.pass_context
def draft_cmd(ctx: click.Context, slug: str, scene: Optional[int], premium: bool) -> None:
    """Draft scenes (one model call each). Requires approved outline."""
    engine = _engine(slug, premium=premium, stories_root=ctx.obj["stories_root"])
    try:
        written = draft_scenes(engine, only_scene=scene)
    except CheckpointError as exc:
        raise click.ClickException(str(exc)) from exc
    for path in written:
        click.echo(f"Wrote {path}")
    click.echo(engine.costs.format_report())


@main.command("redraft")
@click.argument("slug")
@click.argument("scene", type=int)
@click.option("--premium", is_flag=True)
@click.pass_context
def redraft_cmd(ctx: click.Context, slug: str, scene: int, premium: bool) -> None:
    """Redraft a single scene."""
    engine = _engine(slug, premium=premium, stories_root=ctx.obj["stories_root"])
    try:
        path = redraft_scene(engine, scene)
    except CheckpointError as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(f"Rewrote {path}")
    click.echo(engine.costs.format_report())


@main.command("continuity")
@click.argument("slug")
@click.option("--premium", is_flag=True)
@click.pass_context
def continuity_cmd(ctx: click.Context, slug: str, premium: bool) -> None:
    """Continuity report only — does not rewrite."""
    engine = _engine(slug, premium=premium, stories_root=ctx.obj["stories_root"])
    try:
        continuity_check(engine)
    except CheckpointError as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(f"Wrote {engine.paths.continuity}")
    click.echo(engine.costs.format_report())


@main.command("assemble")
@click.argument("slug")
@click.pass_context
def assemble_cmd(ctx: click.Context, slug: str) -> None:
    """Stitch scenes into draft_v1.md with word counts."""
    paths = require_story(slug, ctx.obj["stories_root"])
    try:
        assemble_draft(paths)
    except CheckpointError as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(f"Wrote {paths.draft} (RAW DRAFT)")


@main.command("cost")
@click.argument("slug")
@click.pass_context
def cost_cmd(ctx: click.Context, slug: str) -> None:
    """Show cost report for a story."""
    paths = require_story(slug, ctx.obj["stories_root"])
    tracker = CostTracker(paths.costs, monthly_totals_path=MONTHLY_TOTALS)
    click.echo(tracker.format_report())


@main.command("diff")
@click.argument("slug")
@click.pass_context
def diff_cmd(ctx: click.Context, slug: str) -> None:
    """Report how much of each model-written file you changed."""
    from .provenance import ProvenanceLog

    paths = require_story(slug, ctx.obj["stories_root"])
    log = ProvenanceLog(paths.provenance)
    click.echo(compare_optional(log.latest_output_for_stage("premise"), read_text(paths.premise), "01_premise.md"))
    click.echo(compare_optional(log.latest_output_for_stage("outline"), read_text(paths.outline), "02_outline.md"))
    for scene_file in sorted((paths.scenes_dir.glob("*.md"))):
        stage = f"scene_{scene_file.stem}"
        baseline = log.latest_output_for_stage(stage)
        # Prefer redraft baseline if newer exists — latest_output_for_stage only by exact stage
        redraft = log.latest_output_for_stage(f"{stage}_redraft")
        if redraft:
            baseline = redraft
        click.echo(compare_optional(baseline, read_text(scene_file), f"scenes/{scene_file.name}"))
    if paths.draft.exists():
        click.echo(compare_optional(None, read_text(paths.draft), "draft_v1.md"))


@main.command("list")
@click.pass_context
def list_cmd(ctx: click.Context) -> None:
    """List story slugs."""
    for slug in list_stories(ctx.obj["stories_root"]):
        click.echo(slug)


@main.command("export")
@click.argument("slug")
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["md", "txt", "docx", "pdf", "epub"], case_sensitive=False),
    default="md",
)
@click.option("--out", "out_path", type=click.Path(path_type=Path), default=None)
@click.pass_context
def export_cmd(ctx: click.Context, slug: str, fmt: str, out_path: Optional[Path]) -> None:
    """Export assembled draft (md/txt/docx/pdf/epub)."""
    paths = require_story(slug, ctx.obj["stories_root"])
    text = read_text(paths.draft)
    if not text.strip():
        raise click.ClickException("No draft_v1.md yet. Run assemble first.")
    title = f"{slug} (raw draft)"
    fmt = fmt.lower()
    if fmt == "md":
        target = out_path or Path(f"{slug}_draft.md")
        target.write_text(text, encoding="utf-8")
        click.echo(f"Wrote {target}")
        return
    if fmt == "txt":
        # export_txt returns Flask response; write bytes via helper path
        target = out_path or Path(f"{slug}_draft.txt")
        target.write_text(text, encoding="utf-8")
        click.echo(f"Wrote {target}")
        return

    # For binary formats, use export helpers' generation logic by calling
    # underlying builders when Flask response is awkward in CLI.
    from . import exports as export_mod

    if fmt == "pdf":
        resp = export_pdf(text, title, slug)
    elif fmt == "docx":
        resp = export_docx(text, title, slug)
    else:
        resp = export_epub(text, title, slug)

    # Flask send_file response — pull bytes from response data if possible
    data = resp.get_data()
    target = out_path or Path(f"{slug}_draft.{fmt}")
    target.write_bytes(data)
    click.echo(f"Wrote {target}")


@main.command("frameworks")
def frameworks_cmd() -> None:
    """List structure frameworks."""
    for key, desc in list_frameworks().items():
        click.echo(f"{key}: {desc[:100]}…")


def run() -> None:
    """Entrypoint for `python -m shortstory.cli_app`."""
    try:
        main(obj={})
    except BrokenPipeError:
        sys.exit(0)


if __name__ == "__main__":
    run()
