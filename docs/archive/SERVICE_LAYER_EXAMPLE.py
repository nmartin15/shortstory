"""
Example service layer implementation for routes.py refactoring.

This file demonstrates how services would be structured and used.
This is a reference implementation - actual services should be in src/shortstory/services/
"""

from typing import Dict, Any, Optional, Callable
from datetime import datetime
import uuid
import logging

from src.shortstory.utils.repository import StoryRepository
from src.shortstory.pipeline import ShortStoryPipeline
from src.shortstory.genres import get_genre_config
from src.shortstory.utils import check_distinctiveness, MAX_WORD_COUNT
from src.shortstory.utils.story_builder import build_story_data
from src.shortstory.utils.errors import ValidationError, NotFoundError, ServiceUnavailableError
from src.shortstory.api.helpers import get_story_body, get_story_text

logger = logging.getLogger(__name__)


# ============================================================================
# Story Validation Service
# ============================================================================

class StoryValidationService:
    """Service for validating story input parameters."""
    
    MAX_IDEA_LENGTH = 2000
    MAX_CHARACTER_DESC_LENGTH = 2000
    MAX_THEME_LENGTH = 1000
    
    def validate_generation_input(
        self,
        idea: Optional[str],
        character: Optional[Dict[str, Any]],
        theme: Optional[str],
        genre: Optional[str]
    ) -> Dict[str, Any]:
        """
        Validate story generation input parameters.
        
        Args:
            idea: Story idea/premise
            character: Character description (dict or None)
            theme: Story theme (optional)
            genre: Story genre (optional)
            
        Returns:
            Dict with validated and normalized input
            
        Raises:
            ValidationError: If validation fails
        """
        # Validate idea
        if not idea or not isinstance(idea, str):
            raise ValidationError(
                "Story idea is required. Please provide a creative premise for your story.",
                details={"field": "idea"}
            )
        
        idea = idea.strip()
        if not idea:
            raise ValidationError(
                "Story idea cannot be empty.",
                details={"field": "idea"}
            )
        
        if len(idea) > self.MAX_IDEA_LENGTH:
            raise ValidationError(
                f"Story idea is too long (maximum {self.MAX_IDEA_LENGTH} characters). "
                "Please provide a more concise premise.",
                details={
                    "field": "idea",
                    "length": len(idea),
                    "max_length": self.MAX_IDEA_LENGTH
                }
            )
        
        # Normalize and validate character
        normalized_character = None
        if character:
            if isinstance(character, str):
                normalized_character = {"description": character}
            elif isinstance(character, dict):
                normalized_character = character
            else:
                raise ValidationError(
                    "Character must be a dictionary or string if provided.",
                    details={"field": "character", "type": type(character).__name__}
                )
            
            # Validate character description length
            char_desc = normalized_character.get("description", "")
            if char_desc and len(char_desc) > self.MAX_CHARACTER_DESC_LENGTH:
                raise ValidationError(
                    f"Character description is too long (maximum {self.MAX_CHARACTER_DESC_LENGTH} characters).",
                    details={
                        "field": "character.description",
                        "length": len(char_desc),
                        "max_length": self.MAX_CHARACTER_DESC_LENGTH
                    }
                )
        
        # Validate theme
        normalized_theme = None
        if theme:
            if not isinstance(theme, str):
                raise ValidationError(
                    "Theme must be a string if provided.",
                    details={"field": "theme", "type": type(theme).__name__}
                )
            normalized_theme = theme.strip()
            if normalized_theme and len(normalized_theme) > self.MAX_THEME_LENGTH:
                raise ValidationError(
                    f"Theme is too long (maximum {self.MAX_THEME_LENGTH} characters).",
                    details={
                        "field": "theme",
                        "length": len(normalized_theme),
                        "max_length": self.MAX_THEME_LENGTH
                    }
                )
        
        # Validate genre
        normalized_genre = genre or "General Fiction"
        if normalized_genre and not isinstance(normalized_genre, str):
            raise ValidationError(
                "Genre must be a string if provided.",
                details={"field": "genre", "type": type(normalized_genre).__name__}
            )
        
        return {
            "idea": idea,
            "character": normalized_character,
            "theme": normalized_theme,
            "genre": normalized_genre
        }
    
    def validate_story_body(
        self,
        body_text: str,
        max_words: int = MAX_WORD_COUNT
    ) -> Dict[str, Any]:
        """
        Validate story body text.
        
        Args:
            body_text: Story body text to validate
            max_words: Maximum allowed word count
            
        Returns:
            Dict with validation results:
                - word_count: int
                - is_valid: bool
                - remaining_words: int
                
        Raises:
            ValidationError: If validation fails
        """
        if not body_text:
            raise ValidationError(
                "Story body/text is required.",
                details={"field": "body"}
            )
        
        if not isinstance(body_text, str):
            raise ValidationError(
                "Story body/text must be a string.",
                details={"field": "body", "type": type(body_text).__name__}
            )
        
        # Rough character limit check (10 chars per word max)
        if len(body_text) > max_words * 10:
            raise ValidationError(
                f"Story body is too long (maximum {max_words * 10:,} characters).",
                details={
                    "field": "body",
                    "length": len(body_text),
                    "max_length": max_words * 10
                }
            )
        
        # Word count validation would be done by pipeline
        # This is just structural validation
        return {
            "body_text": body_text,
            "max_words": max_words
        }


# ============================================================================
# Story Generation Service
# ============================================================================

class StoryGenerationService:
    """Service for generating complete stories through the pipeline."""
    
    def __init__(
        self,
        repository: StoryRepository,
        pipeline_factory: Callable[[str, Optional[Dict]], ShortStoryPipeline]
    ):
        """
        Initialize story generation service.
        
        Args:
            repository: Story repository for persistence
            pipeline_factory: Factory function to create pipeline instances
        """
        self.repository = repository
        self.pipeline_factory = pipeline_factory
        self.validation_service = StoryValidationService()
    
    def generate_story(
        self,
        idea: str,
        character: Optional[Dict[str, Any]],
        theme: Optional[str],
        genre: str = "General Fiction",
        max_word_count: int = MAX_WORD_COUNT
    ) -> Dict[str, Any]:
        """
        Generate a complete story through the full pipeline.
        
        Args:
            idea: Story idea/premise
            character: Character description (optional)
            theme: Story theme (optional)
            genre: Story genre (default: "General Fiction")
            max_word_count: Maximum word count (default: MAX_WORD_COUNT)
            
        Returns:
            Complete story data dictionary
            
        Raises:
            ValidationError: If input validation fails
            ServiceUnavailableError: If generation service is unavailable
        """
        # Validate input
        validated = self.validation_service.validate_generation_input(
            idea=idea,
            character=character,
            theme=theme,
            genre=genre
        )
        
        idea = validated["idea"]
        character = validated["character"]
        theme = validated["theme"]
        genre = validated["genre"]
        
        # Get genre configuration
        genre_config = get_genre_config(genre)
        if genre_config is None:
            raise ServiceUnavailableError(
                "genre_config",
                f"Genre configuration service unavailable for genre: {genre}"
            )
        
        # Create pipeline instance
        pipeline = self.pipeline_factory(genre=genre, genre_config=genre_config)
        pipeline.max_word_count = max_word_count
        
        # Run full pipeline
        premise = pipeline.capture_premise(idea, character, theme, validate=True)
        outline = pipeline.generate_outline(genre=genre)
        scaffold = pipeline.scaffold(genre=genre)
        draft = pipeline.draft()
        revised_draft = pipeline.revise()
        
        # Extract metadata
        metadata = self._extract_story_metadata(
            scaffold=scaffold,
            genre_config=genre_config,
            idea=idea,
            character=character
        )
        
        # Get revised story text
        revised_story_text = revised_draft.get('text', '')
        story_word_count = pipeline.word_validator.count_words(revised_story_text)
        
        # Generate story ID
        story_id = f"story_{uuid.uuid4().hex[:8]}"
        
        # Convert Pydantic models to dicts for storage
        premise_dict = self._model_to_dict(premise)
        outline_dict = self._model_to_dict(outline)
        
        # Build standardized story data
        story_data = build_story_data(
            story_id=story_id,
            premise=premise_dict,
            outline=outline_dict,
            genre=genre,
            genre_config=genre_config,
            body=revised_story_text,
            word_count=story_word_count,
            scaffold=scaffold,
            metadata=metadata,
            draft=draft,
            revised_draft=revised_draft,
            max_words=max_word_count
        )
        
        # Save to repository
        self.repository.save(story_data)
        
        logger.info(f"Successfully generated story {story_id}")
        
        return story_data
    
    def _extract_story_metadata(
        self,
        scaffold: Dict[str, Any],
        genre_config: Dict[str, Any],
        idea: str,
        character: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Extract and build story metadata from pipeline outputs.
        
        Args:
            scaffold: Scaffold data from pipeline
            genre_config: Genre configuration
            idea: Story idea
            character: Character description
            
        Returns:
            Metadata dictionary
        """
        constraints = genre_config.get('constraints', {})
        
        # Extract tone, pace, POV from scaffold or constraints
        tone = (
            scaffold.get('tone', constraints.get('tone', 'balanced'))
            if isinstance(scaffold, dict)
            else constraints.get('tone', 'balanced')
        )
        pace = (
            scaffold.get('pace', constraints.get('pace', 'moderate'))
            if isinstance(scaffold, dict)
            else constraints.get('pace', 'moderate')
        )
        pov = (
            scaffold.get('pov', constraints.get('pov_preference', 'flexible'))
            if isinstance(scaffold, dict)
            else constraints.get('pov_preference', 'flexible')
        )
        
        # Calculate distinctiveness scores
        idea_dist = check_distinctiveness(idea)
        char_dist = check_distinctiveness(None, character=character)
        
        return {
            "tone": tone,
            "pace": pace,
            "pov": pov,
            "idea_distinctiveness": idea_dist,
            "character_distinctiveness": char_dist
        }
    
    def _model_to_dict(self, model: Any) -> Dict[str, Any]:
        """Convert Pydantic model to dict, handling both v1 and v2 APIs."""
        if hasattr(model, 'model_dump'):
            return model.model_dump(exclude_none=True)
        elif hasattr(model, 'dict'):
            return model.dict(exclude_none=True)
        elif isinstance(model, dict):
            return model
        else:
            return {}


# ============================================================================
# Story Service (CRUD Operations)
# ============================================================================

class StoryService:
    """Service for story CRUD operations."""
    
    def __init__(
        self,
        repository: StoryRepository,
        pipeline_factory: Callable[[], ShortStoryPipeline]
    ):
        """
        Initialize story service.
        
        Args:
            repository: Story repository for persistence
            pipeline_factory: Factory function to create pipeline instances
        """
        self.repository = repository
        self.pipeline_factory = pipeline_factory
    
    def get_story(self, story_id: str) -> Dict[str, Any]:
        """
        Get a story by ID with recalculated metrics.
        
        Args:
            story_id: Story identifier
            
        Returns:
            Story data dictionary
            
        Raises:
            NotFoundError: If story not found
        """
        story = self.repository.load(story_id)
        if not story:
            raise NotFoundError("Story", story_id)
        
        # Recalculate word count
        pipeline = self.pipeline_factory()
        body = get_story_body(story)
        word_count = pipeline.word_validator.count_words(body)
        
        # Update story with current metrics
        story["word_count"] = word_count
        story["max_words"] = story.get("max_words", MAX_WORD_COUNT)
        
        return story
    
    def update_story_body(
        self,
        story_id: str,
        body_text: str
    ) -> Dict[str, Any]:
        """
        Update a story's body text with validation.
        
        Args:
            story_id: Story identifier
            body_text: New story body text
            
        Returns:
            Updated story data dictionary
            
        Raises:
            NotFoundError: If story not found
            ValidationError: If body text is invalid
        """
        # Load story
        story = self.repository.load(story_id)
        if not story:
            raise NotFoundError("Story", story_id)
        
        # Validate body text
        pipeline = self.pipeline_factory()
        word_count, is_valid = pipeline.word_validator.validate(
            body_text, raise_error=False
        )
        
        if not is_valid:
            raise ValidationError(
                f"Story exceeds word limit ({word_count:,} > {MAX_WORD_COUNT:,} words). "
                "Please reduce the length.",
                details={
                    "word_count": word_count,
                    "max_words": MAX_WORD_COUNT
                }
            )
        
        # Update story
        story["body"] = body_text
        story["word_count"] = word_count
        story["max_words"] = story.get("max_words", MAX_WORD_COUNT)
        story["updated_at"] = datetime.now().isoformat()
        
        # Save to repository
        self.repository.update(story_id, {
            "body": body_text,
            "word_count": word_count,
            "updated_at": story["updated_at"]
        })
        
        return story
    
    def list_stories(
        self,
        page: int = 1,
        per_page: int = 50,
        genre: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        List stories with pagination and optional genre filter.
        
        Args:
            page: Page number (1-indexed)
            per_page: Items per page
            genre: Optional genre filter
            
        Returns:
            Dict with 'stories' list and 'pagination' metadata
        """
        # Validate pagination parameters
        if page < 1:
            page = 1
        if per_page < 1 or per_page > 100:
            per_page = min(max(per_page, 1), 100)
        
        # Validate genre format if provided
        if genre:
            import re
            if not re.match(r'^[a-zA-Z0-9\s_-]+$', genre):
                raise ValidationError(
                    f"Invalid genre format: '{genre}'. "
                    "Genre must contain only alphanumeric characters, spaces, hyphens, and underscores.",
                    details={"genre": genre}
                )
        
        # Get stories from repository
        return self.repository.list(page=page, per_page=per_page, genre=genre)


# ============================================================================
# Example: How Routes Would Use Services
# ============================================================================

def example_route_with_service():
    """
    Example showing how a route would use the service layer.
    
    This is much cleaner than the current implementation!
    """
    # In app.py or routes.py, services would be initialized:
    # story_service = StoryService(repository, pipeline_factory)
    # generation_service = StoryGenerationService(repository, pipeline_factory)
    # validation_service = StoryValidationService()
    
    # Route handler becomes thin wrapper:
    @flask_app.route('/api/generate', methods=['POST'])
    @limiter_instance.limit(lambda: current_app.config["GENERATE_RATE_LIMIT"])
    def generate_story():
        """Generate a new short story from user input."""
        try:
            data = request.get_json() or {}
            
            # Check for background job request
            use_background = data.get('background', False)
            if use_background and RQ_AVAILABLE:
                # Use job service to enqueue
                job_service = JobService()
                return job_service.enqueue_story_generation(
                    idea=data.get('idea'),
                    character=data.get('character'),
                    theme=data.get('theme'),
                    genre=data.get('genre', 'General Fiction'),
                    max_word_count=data.get('max_word_count', MAX_WORD_COUNT)
                )
            
            # Synchronous generation using service
            story_data = generation_service.generate_story(
                idea=data.get('idea'),
                character=data.get('character'),
                theme=data.get('theme'),
                genre=data.get('genre', 'General Fiction'),
                max_word_count=data.get('max_word_count', MAX_WORD_COUNT)
            )
            
            # Return canonical response
            return jsonify(build_canonical_story_response(story_data))
        
        except ValidationError:
            raise  # Handled by error handler
        except ServiceUnavailableError:
            raise  # Handled by error handler
        except Exception as e:
            # Translate to appropriate error
            error_handling_service.handle_generation_error(e)
            raise
