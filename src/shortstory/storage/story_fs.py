"""Plain-Markdown per-story workspace on disk."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

_REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_STORIES_ROOT = _REPO_ROOT / "stories"

SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class StoryNotFoundError(FileNotFoundError):
    """Raised when a story folder does not exist."""


@dataclass(frozen=True)
class StoryPaths:
    """Resolved paths for one story workspace."""

    root: Path
    spark: Path
    premise: Path
    outline: Path
    scenes_dir: Path
    continuity: Path
    draft: Path
    provenance: Path
    costs: Path
    meta: Path


def slugify(text: str) -> str:
    """Convert free text into a filesystem-safe slug."""
    text = (text or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-{2,}", "-", text).strip("-")
    return text[:80] or "untitled"


def validate_slug(slug: str) -> str:
    """Validate and return a slug.

    Raises:
        ValueError: If the slug is invalid.
    """
    slug = (slug or "").strip().lower()
    if not SLUG_PATTERN.match(slug):
        raise ValueError(
            f"Invalid story slug '{slug}'. Use lowercase letters, numbers, and hyphens."
        )
    return slug


def get_story_paths(slug: str, stories_root: Optional[Path] = None) -> StoryPaths:
    """Build the path map for a story slug."""
    slug = validate_slug(slug)
    root = (stories_root or DEFAULT_STORIES_ROOT) / slug
    return StoryPaths(
        root=root,
        spark=root / "00_spark.md",
        premise=root / "01_premise.md",
        outline=root / "02_outline.md",
        scenes_dir=root / "scenes",
        continuity=root / "03_continuity.md",
        draft=root / "draft_v1.md",
        provenance=root / "provenance.jsonl",
        costs=root / "costs.jsonl",
        meta=root / "meta.yaml",
    )


def init_story(
    spark_text: str,
    *,
    slug: Optional[str] = None,
    stories_root: Optional[Path] = None,
    init_git: bool = True,
) -> StoryPaths:
    """Create a new story folder from a spark.

    Args:
        spark_text: Raw writer input.
        slug: Optional explicit slug; otherwise derived from spark.
        stories_root: Override stories directory.
        init_git: Initialize a git repo inside the story folder for edit history.

    Returns:
        StoryPaths for the new workspace.

    Raises:
        FileExistsError: If the story folder already exists.
    """
    derived = slug or slugify(spark_text.split("\n", 1)[0])
    paths = get_story_paths(derived, stories_root)
    if paths.root.exists():
        raise FileExistsError(f"Story already exists: {paths.root}")

    paths.root.mkdir(parents=True, exist_ok=False)
    paths.scenes_dir.mkdir(parents=True, exist_ok=True)
    write_text(
        paths.spark,
        "# Spark (raw input — your words)\n\n"
        "This is the seed. Edit freely.\n\n"
        f"{spark_text.strip()}\n",
    )
    write_text(
        paths.meta,
        "status: spark\n"
        "approved_premise: false\n"
        "approved_outline: false\n"
        "target_words: 5000\n"
        "framework: story_circle\n"
        "raw_draft: true\n"
        "note: Output is a raw draft for you to rewrite — never a finished story.\n",
    )
    # Touch empty logs so tools can append immediately
    paths.provenance.touch()
    paths.costs.touch()

    if init_git:
        _git_init(paths.root)

    return paths


def require_story(slug: str, stories_root: Optional[Path] = None) -> StoryPaths:
    """Return paths for an existing story or raise."""
    paths = get_story_paths(slug, stories_root)
    if not paths.root.exists():
        raise StoryNotFoundError(f"Story not found: {paths.root}")
    return paths


def list_stories(stories_root: Optional[Path] = None) -> List[str]:
    """List story slugs under the stories root."""
    root = stories_root or DEFAULT_STORIES_ROOT
    if not root.exists():
        return []
    return sorted(
        path.name
        for path in root.iterdir()
        if path.is_dir() and not path.name.startswith(".")
    )


def write_text(path: Path, content: str) -> None:
    """Write UTF-8 text, creating parents as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def read_text(path: Path) -> str:
    """Read UTF-8 text; empty string if missing."""
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def scene_path(paths: StoryPaths, index: int) -> Path:
    """Return path for scene N (1-based) as zero-padded markdown."""
    if index < 1:
        raise ValueError("Scene index must be >= 1")
    return paths.scenes_dir / f"{index:02d}.md"


def list_scene_files(paths: StoryPaths) -> List[Path]:
    """List scene markdown files in order."""
    if not paths.scenes_dir.exists():
        return []
    return sorted(paths.scenes_dir.glob("*.md"))


def update_meta_field(paths: StoryPaths, key: str, value: object) -> None:
    """Update a single top-level key in meta.yaml (simple line-based)."""
    content = read_text(paths.meta)
    lines = content.splitlines()
    key_prefix = f"{key}:"
    rendered = _render_yaml_value(value)
    replaced = False
    new_lines: List[str] = []
    for line in lines:
        if line.startswith(key_prefix):
            new_lines.append(f"{key}: {rendered}")
            replaced = True
        else:
            new_lines.append(line)
    if not replaced:
        new_lines.append(f"{key}: {rendered}")
    write_text(paths.meta, "\n".join(new_lines) + "\n")


def read_meta(paths: StoryPaths) -> dict:
    """Parse meta.yaml into a dict (minimal YAML subset via PyYAML)."""
    import yaml

    raw = read_text(paths.meta)
    if not raw.strip():
        return {}
    data = yaml.safe_load(raw) or {}
    return data if isinstance(data, dict) else {}


def is_premise_approved(paths: StoryPaths) -> bool:
    """Return True if the premise checkpoint is approved."""
    return bool(read_meta(paths).get("approved_premise"))


def is_outline_approved(paths: StoryPaths) -> bool:
    """Return True if the outline checkpoint is approved."""
    return bool(read_meta(paths).get("approved_outline"))


def _render_yaml_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value)
    if any(ch in text for ch in (":", "#", "\n", "'", '"')):
        return repr(text)
    return text


def _git_init(path: Path) -> None:
    """Initialize git in the story folder; ignore failure if git missing."""
    try:
        subprocess.run(
            ["git", "init"],
            cwd=str(path),
            check=False,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            ["git", "add", "-A"],
            cwd=str(path),
            check=False,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Initial spark"],
            cwd=str(path),
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return
