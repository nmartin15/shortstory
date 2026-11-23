"""
Helper functions for API responses and story data manipulation.

This module contains utility functions used by route handlers for:
- Building standardized API responses
- Extracting and formatting story data
- Accessing Flask application context (repository, limiter, pipeline)
- Validating story IDs
"""

import re
from typing import Any, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from flask_limiter import Limiter
    from src.shortstory.pipeline import ShortStoryPipeline
    from src.shortstory.utils.repository import StoryRepository

from flask import current_app, g
from src.shortstory.utils import MAX_WORD_COUNT
from src.shortstory.genres import get_genre_config
from src.shortstory.pipeline import ShortStoryPipeline
from src.shortstory.utils.errors import ValidationError


def word_count_response(word_count: int, max_words: int = MAX_WORD_COUNT) -> Dict[str, Any]:
    """
    Build standardized word count response.

    Args:
        word_count: The current word count of the story
        max_words: The maximum allowed word count (default: MAX_WORD_COUNT)

    Returns:
        dict: A dictionary containing word count information with keys:
            - word_count: Current word count
            - max_words: Maximum allowed words
            - remaining_words: Words remaining before limit
    """
    return {
        "word_count": word_count,
        "max_words": max_words,
        "remaining_words": max_words - word_count
    }


def build_canonical_story_response(
        story: Dict[str, Any], story_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Build canonical story response format.

    Standardizes the response structure across all story endpoints:
    {
        "id": "...",
        "body": "...",
        "text": "...",
        "word_count": 1234,
        "max_words": 7500,
        "metadata": {
            "genre": "...",
            "tone": "...",
            "distinctiveness": {...},
            "premise": "...",
            "outline": "..."
        }
    }

    Args:
        story: Story dictionary from repository
        story_id: Optional story ID to use if not present in story dict

    Returns:
        dict: Canonical story response format
    """
    # Extract story ID (handle both "id" and "story_id" formats, or use
    # provided story_id)
    story_id = story_id or story.get("id") or story.get("story_id", "")

    # Get body (pure narrative text)
    body = get_story_body(story)

    # Get text (composite markdown)
    text = get_story_text(story)

    # Get word count and max words
    word_count = story.get("word_count", 0)
    max_words = story.get("max_words", MAX_WORD_COUNT)

    # Build metadata object
    metadata = story.get("metadata", {})

    # Extract distinctiveness scores
    idea_dist = metadata.get("idea_distinctiveness", {})
    char_dist = metadata.get("character_distinctiveness", {})

    # Combine distinctiveness into single object
    distinctiveness = {
        "idea": idea_dist,
        "character": char_dist
    }

    # Build canonical metadata
    canonical_metadata = {
        "genre": story.get("genre", ""),
        "tone": metadata.get("tone", ""),
        "distinctiveness": distinctiveness,
        "premise": story.get("premise", {}),
        "outline": story.get("outline", {})
    }

    return {
        "id": story_id,
        "body": body,
        "text": text,
        "word_count": word_count,
        "max_words": max_words,
        "metadata": canonical_metadata
    }


def generate_story_text(story: Dict[str, Any]) -> str:
    """
    Generate markdown composite text from story body and metadata.

    This function creates the formatted markdown output that combines:
    - Story metadata (title, genre, character, theme, etc.)
    - Pure narrative body text

    Args:
        story: Story dictionary containing body and metadata fields

    Returns:
        str: Formatted markdown text with metadata headers and story body
    """
    # Extract body (pure narrative text)
    body = story.get("body", "")

    # If body doesn't exist, try to extract from legacy text field
    if not body and story.get("text"):
        # Try to extract body from legacy composite text
        # Look for "## Story" section or assume everything after metadata
        text = story.get("text", "")
        story_match = re.search(r'## Story\s*\n\s*\n(.+)$', text, re.DOTALL)
        if story_match:
            body = story_match.group(1).strip()
        else:
            # Fallback: use the whole text (backward compatibility)
            body = text

    # Extract metadata
    metadata = story.get("metadata", {})
    premise = story.get("premise", {})
    genre = story.get("genre", "General Fiction")
    genre_config = story.get("genre_config", {})

    # Build metadata fields
    idea = premise.get("idea", "") if isinstance(
        premise, dict) else str(premise) if premise else ""
    character = premise.get(
        "character",
        {}) if isinstance(
        premise,
        dict) else {}
    theme = premise.get("theme", "") if isinstance(premise, dict) else ""

    char_desc = character.get("description", "") if isinstance(
        character, dict) else str(character) if character else ""

    framework = genre_config.get(
        'framework', 'narrative_arc') if isinstance(
        genre_config, dict) else 'narrative_arc'
    outline_structure = genre_config.get(
        'outline', [
            'setup', 'complication', 'resolution']) if isinstance(
        genre_config, dict) else [
                'setup', 'complication', 'resolution']

    # Get tone, pace, POV from metadata or scaffold
    scaffold = story.get("scaffold", {})
    constraints = genre_config.get(
        'constraints',
        {}) if isinstance(
        genre_config,
        dict) else {}
    tone = metadata.get('tone') or scaffold.get('tone') or constraints.get(
        'tone',
        'balanced') if isinstance(
        scaffold,
        dict) else constraints.get(
            'tone',
            'balanced') if isinstance(
                constraints,
        dict) else 'balanced'
    pace = metadata.get('pace') or scaffold.get('pace') or constraints.get(
        'pace',
        'moderate') if isinstance(
        scaffold,
        dict) else constraints.get(
            'pace',
            'moderate') if isinstance(
                constraints,
        dict) else 'moderate'
    pov = metadata.get('pov') or scaffold.get('pov') or constraints.get(
        'pov_preference',
        'flexible') if isinstance(
        scaffold,
        dict) else constraints.get(
            'pov_preference',
            'flexible') if isinstance(
                constraints,
        dict) else 'flexible'

    # Get distinctiveness scores if available
    idea_dist = metadata.get('idea_distinctiveness', {})
    char_dist = metadata.get('character_distinctiveness', {})

    idea_score = idea_dist.get(
        'distinctiveness_score',
        0.0) if isinstance(
        idea_dist,
        dict) else 0.0
    char_score = char_dist.get(
        'distinctiveness_score',
        0.0) if isinstance(
        char_dist,
        dict) else 0.0

    cliche_msg = ""
    if isinstance(idea_dist, dict) and idea_dist.get('has_cliches'):
        cliches = idea_dist.get('found_cliches', [])
        cliche_msg = f"⚠️ Clichés: {', '.join(cliches)}"
    else:
        cliche_msg = "✓ No clichés"

    generic_msg = ""
    if isinstance(char_dist, dict) and char_dist.get('has_generic_archetype'):
        generic = char_dist.get('generic_elements', [])
        generic_msg = f"⚠️ Generic: {', '.join(generic)}"
    else:
        generic_msg = "✓ Distinctive"

    # Build the composite markdown
    story_text = f"""# {idea}

## Genre: {genre} | Framework: {framework} | Structure: {', '.join(outline_structure)}
**Tone:** {tone} | **Pace:** {pace} | **POV:** {pov}

## Character
{char_desc if char_desc else 'Not specified'}

## Theme
{theme if theme else 'Not specified'}

## Distinctiveness
Idea: {idea_score:.2f}/1.0 | Character: {char_score:.2f}/1.0
{cliche_msg}
{generic_msg}

## Story

{body}
"""
    return story_text


def get_story_body(story: Dict[str, Any]) -> str:
    """
    Get the pure narrative body text from a story.

    Handles both new format (body field) and legacy format (text field).

    Args:
        story: Story dictionary

    Returns:
        str: Pure narrative text without metadata
    """
    # New format: body field exists
    if "body" in story:
        return story.get("body", "")

    # Legacy format: extract from text field
    if "text" in story:
        text = story.get("text", "")
        # Try to extract body from composite text
        story_match = re.search(r'## Story\s*\n\s*\n(.+)$', text, re.DOTALL)
        if story_match:
            return story_match.group(1).strip()
        # If no "## Story" marker, assume the whole text is body (backward
        # compatibility)
        return text

    return ""


def get_story_text(story: Dict[str, Any]) -> str:
    """
    Get the full markdown composite text from a story.

    Generates the composite on demand if it doesn't exist.

    Args:
        story: Story dictionary

    Returns:
        str: Full markdown composite text
    """
    # If text field exists and body doesn't, use legacy text
    if "text" in story and "body" not in story:
        return story.get("text", "")

    # Generate composite from body + metadata
    return generate_story_text(story)


def get_story_repository() -> 'StoryRepository':
    """
    Get the story repository from current_app context.

    Uses Flask's application context to access the story repository
    that was registered during app initialization.

    Returns:
        Story repository instance from app extensions
    """
    return current_app.extensions['story_repository']


def get_limiter() -> 'Limiter':
    """
    Get the rate limiter from current_app context.

    Uses Flask's application context to access the limiter
    that was registered during app initialization.

    Returns:
        Limiter instance from app extensions
    """
    return current_app.extensions['limiter']


def create_pipeline(
    genre: Optional[str] = None,
    genre_config: Optional[Dict[str, Any]] = None,
    max_word_count: Optional[int] = None
) -> 'ShortStoryPipeline':
    """
    Create a request-scoped pipeline instance.

    This factory function creates a properly configured ShortStoryPipeline
    instance for use within a request handler. Each request gets its own
    pipeline instance to ensure isolation and prevent state leakage.

    Args:
        genre: Optional genre name
        genre_config: Optional genre configuration dict
        max_word_count: Optional maximum word count (default: MAX_WORD_COUNT)

    Returns:
        ShortStoryPipeline instance configured for the request
    """
    if max_word_count is None:
        max_word_count = MAX_WORD_COUNT

    # If genre_config not provided but genre is, fetch it
    if genre_config is None and genre:
        genre_config = get_genre_config(genre)

    return ShortStoryPipeline(
        max_word_count=max_word_count,
        genre=genre,
        genre_config=genre_config
    )


def get_pipeline(
    genre: Optional[str] = None,
    genre_config: Optional[Dict[str, Any]] = None,
    max_word_count: Optional[int] = None
) -> 'ShortStoryPipeline':
    """
    Get or create a request-scoped pipeline instance.

    Uses Flask's request context (g object) to store the pipeline
    for the duration of the request, ensuring each request gets
    exactly one pipeline instance.

    Args:
        genre: Optional genre name
        genre_config: Optional genre configuration dict
        max_word_count: Optional maximum word count (default: MAX_WORD_COUNT)

    Returns:
        ShortStoryPipeline instance for the current request
    """
    # Check if pipeline already exists in request context
    if not hasattr(g, 'pipeline'):
        g.pipeline = create_pipeline(
            genre=genre,
            genre_config=genre_config,
            max_word_count=max_word_count)
    else:
        # If genre/config changed, update the existing pipeline
        if genre and g.pipeline.genre != genre:
            g.pipeline.genre = genre
            if genre_config:
                g.pipeline.genre_config = genre_config
            elif genre:
                g.pipeline.genre_config = get_genre_config(genre)

    return g.pipeline


def validate_story_id(story_id: str) -> str:
    """
    Validate story ID format.
    
    Args:
        story_id: Story ID to validate
        
    Returns:
        Validated story ID
        
    Raises:
        ValidationError: If story ID format is invalid
    """
    pattern = r'^story_[a-f0-9]{8}$'
    if not re.match(pattern, story_id):
        raise ValidationError(
            f"Invalid story ID format: '{story_id}'. Expected format: 'story_XXXXXXXX' where X is a hexadecimal digit.",
            details={"field": "story_id", "expected_format": "story_[a-f0-9]{8}"}
        )
    return story_id


def get_story_or_404(story_id: str) -> Optional[Dict[str, Any]]:
    """
    Get story from repository, or return None.

    Uses current_app context to access the story repository.
    Validates story_id format before querying the database to prevent injection attacks.
    
    Args:
        story_id: Story ID (will be validated)
        
    Returns:
        Story dictionary or None if not found
        
    Raises:
        ValidationError: If story ID format is invalid
    Note: This function does NOT raise 404 errors - it returns None.
    Route handlers should check the return value and raise NotFoundError
    if the story is not found.
    """
    # Validate story_id format to prevent injection attacks
    # Even though we use parameterized queries, validating format adds defense in depth
    validate_story_id(story_id)
    
    repo = get_story_repository()
    return repo.load(story_id)
