"""
Unit tests for StoryValidationService.

Tests input validation logic for story operations.
"""

import pytest
from src.shortstory.services.story_validation_service import StoryValidationService
from src.shortstory.utils.errors import ValidationError
from src.shortstory.utils import MAX_WORD_COUNT
from tests.test_constants import (
    GENRE_GENERAL_FICTION,
    GENRE_HORROR,
    EMPTY_STRING,
    WHITESPACE_ONLY
)


class TestStoryValidationService:
    """Test suite for StoryValidationService."""
    
    @pytest.fixture
    def service(self):
        """Create a StoryValidationService instance."""
        return StoryValidationService()
    
    # Test validate_generation_input
    
    def test_validate_generation_input_valid(self, service):
        """Test validation with valid input."""
        result = service.validate_generation_input(
            idea="A lighthouse keeper collects lost voices in glass jars",
            character={"description": "A quiet keeper"},
            theme="What happens to stories we never tell?",
            genre=GENRE_GENERAL_FICTION
        )
        
        assert result["idea"] == "A lighthouse keeper collects lost voices in glass jars"
        assert result["character"]["description"] == "A quiet keeper"
        assert result["theme"] == "What happens to stories we never tell?"
        assert result["genre"] == GENRE_GENERAL_FICTION
    
    def test_validate_generation_input_missing_idea(self, service):
        """Test validation fails when idea is missing."""
        with pytest.raises(ValidationError) as exc_info:
            service.validate_generation_input(
                idea=None,
                character=None,
                theme=None,
                genre=GENRE_GENERAL_FICTION
            )
        
        assert "idea is required" in str(exc_info.value).lower()
        assert exc_info.value.details.get("field") == "idea"
    
    def test_validate_generation_input_empty_idea(self, service):
        """Test validation fails when idea is empty."""
        with pytest.raises(ValidationError) as exc_info:
            service.validate_generation_input(
                idea=EMPTY_STRING,
                character=None,
                theme=None,
                genre=GENRE_GENERAL_FICTION
            )
        
        # Empty string gets stripped and triggers "required" error
        assert "idea" in str(exc_info.value).lower()
        assert "required" in str(exc_info.value).lower() or "cannot be empty" in str(exc_info.value).lower()
    
    def test_validate_generation_input_whitespace_only_idea(self, service):
        """Test validation fails when idea is only whitespace."""
        with pytest.raises(ValidationError) as exc_info:
            service.validate_generation_input(
                idea=WHITESPACE_ONLY,
                character=None,
                theme=None,
                genre=GENRE_GENERAL_FICTION
            )
        
        assert "cannot be empty" in str(exc_info.value).lower()
    
    def test_validate_generation_input_idea_too_long(self, service):
        """Test validation fails when idea exceeds max length."""
        long_idea = "A" * (service.MAX_IDEA_LENGTH + 1)
        
        with pytest.raises(ValidationError) as exc_info:
            service.validate_generation_input(
                idea=long_idea,
                character=None,
                theme=None,
                genre=GENRE_GENERAL_FICTION
            )
        
        assert "too long" in str(exc_info.value).lower()
        assert exc_info.value.details["length"] == len(long_idea)
        assert exc_info.value.details["max_length"] == service.MAX_IDEA_LENGTH
    
    def test_validate_generation_input_character_string(self, service):
        """Test character can be provided as string."""
        result = service.validate_generation_input(
            idea="A story",
            character="A character description",
            theme=None,
            genre=GENRE_GENERAL_FICTION
        )
        
        assert result["character"]["description"] == "A character description"
    
    def test_validate_generation_input_character_dict(self, service):
        """Test character can be provided as dict."""
        result = service.validate_generation_input(
            idea="A story",
            character={"description": "A character", "name": "John"},
            theme=None,
            genre=GENRE_GENERAL_FICTION
        )
        
        assert result["character"]["description"] == "A character"
        assert result["character"]["name"] == "John"
    
    def test_validate_generation_input_character_empty_dict(self, service):
        """Test empty character dict is normalized to None."""
        result = service.validate_generation_input(
            idea="A story",
            character={},
            theme=None,
            genre=GENRE_GENERAL_FICTION
        )
        
        assert result["character"] is None
    
    def test_validate_generation_input_character_invalid_type(self, service):
        """Test validation fails when character is invalid type."""
        with pytest.raises(ValidationError) as exc_info:
            service.validate_generation_input(
                idea="A story",
                character=123,  # Invalid type
                theme=None,
                genre=GENRE_GENERAL_FICTION
            )
        
        assert "must be a dictionary or string" in str(exc_info.value).lower()
        assert exc_info.value.details["field"] == "character"
    
    def test_validate_generation_input_character_description_too_long(self, service):
        """Test validation fails when character description is too long."""
        long_desc = "A" * (service.MAX_CHARACTER_DESC_LENGTH + 1)
        
        with pytest.raises(ValidationError) as exc_info:
            service.validate_generation_input(
                idea="A story",
                character={"description": long_desc},
                theme=None,
                genre=GENRE_GENERAL_FICTION
            )
        
        assert "too long" in str(exc_info.value).lower()
        assert exc_info.value.details["field"] == "character.description"
    
    def test_validate_generation_input_theme_too_long(self, service):
        """Test validation fails when theme is too long."""
        long_theme = "A" * (service.MAX_THEME_LENGTH + 1)
        
        with pytest.raises(ValidationError) as exc_info:
            service.validate_generation_input(
                idea="A story",
                character=None,
                theme=long_theme,
                genre=GENRE_GENERAL_FICTION
            )
        
        assert "too long" in str(exc_info.value).lower()
        assert exc_info.value.details["field"] == "theme"
    
    def test_validate_generation_input_theme_invalid_type(self, service):
        """Test validation fails when theme is invalid type."""
        with pytest.raises(ValidationError) as exc_info:
            service.validate_generation_input(
                idea="A story",
                character=None,
                theme=123,  # Invalid type
                genre=GENRE_GENERAL_FICTION
            )
        
        assert "must be a string" in str(exc_info.value).lower()
        assert exc_info.value.details["field"] == "theme"
    
    def test_validate_generation_input_genre_default(self, service):
        """Test genre defaults to General Fiction if not provided."""
        result = service.validate_generation_input(
            idea="A story",
            character=None,
            theme=None,
            genre=None
        )
        
        assert result["genre"] == "General Fiction"
    
    def test_validate_generation_input_genre_invalid_type(self, service):
        """Test validation fails when genre is invalid type."""
        with pytest.raises(ValidationError) as exc_info:
            service.validate_generation_input(
                idea="A story",
                character=None,
                theme=None,
                genre=123  # Invalid type
            )
        
        assert "must be a string" in str(exc_info.value).lower()
        assert exc_info.value.details["field"] == "genre"
    
    # Test validate_story_body
    
    def test_validate_story_body_valid(self, service):
        """Test validation with valid body text."""
        body_text = "This is a valid story body with reasonable length."
        result = service.validate_story_body(body_text)
        
        assert result["body_text"] == body_text
        assert result["max_words"] == MAX_WORD_COUNT
    
    def test_validate_story_body_missing(self, service):
        """Test validation fails when body is missing."""
        with pytest.raises(ValidationError) as exc_info:
            service.validate_story_body("")
        
        assert "required" in str(exc_info.value).lower()
        assert exc_info.value.details["field"] == "body"
    
    def test_validate_story_body_invalid_type(self, service):
        """Test validation fails when body is not a string."""
        with pytest.raises(ValidationError) as exc_info:
            service.validate_story_body(123)  # Invalid type
        
        assert "must be a string" in str(exc_info.value).lower()
        assert exc_info.value.details["field"] == "body"
    
    def test_validate_story_body_too_long(self, service):
        """Test validation fails when body exceeds character limit."""
        # Create text that exceeds max_words * 10 characters
        long_body = "A" * (MAX_WORD_COUNT * 10 + 1)
        
        with pytest.raises(ValidationError) as exc_info:
            service.validate_story_body(long_body)
        
        assert "too long" in str(exc_info.value).lower()
        assert exc_info.value.details["field"] == "body"
    
    # Test validate_export_format
    
    def test_validate_export_format_valid(self, service):
        """Test validation with valid export formats."""
        for format_type in ['pdf', 'markdown', 'txt', 'docx', 'epub']:
            result = service.validate_export_format(format_type)
            assert result == format_type
    
    def test_validate_export_format_invalid(self, service):
        """Test validation fails with invalid export format."""
        with pytest.raises(ValidationError) as exc_info:
            service.validate_export_format("invalid_format")
        
        assert "invalid format" in str(exc_info.value).lower()
        assert exc_info.value.details["format_type"] == "invalid_format"
        assert "valid_formats" in exc_info.value.details
    
    # Test validate_genre_format
    
    def test_validate_genre_format_valid(self, service):
        """Test validation with valid genre formats."""
        valid_genres = [
            "General Fiction",
            "Science-Fiction",
            "Horror_Thriller",
            "Romance 2024",
            "Mystery123"
        ]
        
        for genre in valid_genres:
            result = service.validate_genre_format(genre)
            assert result == genre
    
    def test_validate_genre_format_invalid(self, service):
        """Test validation fails with invalid genre format."""
        invalid_genres = [
            "Genre<script>",
            "Genre/../../etc",
            "Genre&command",
            "Genre|pipe"
        ]
        
        for genre in invalid_genres:
            with pytest.raises(ValidationError) as exc_info:
                service.validate_genre_format(genre)
            
            assert "invalid genre format" in str(exc_info.value).lower()
    
    # Test validate_template_genre_format
    
    def test_validate_template_genre_format_valid(self, service):
        """Test validation with valid template genre formats."""
        valid_genres = [
            "General Fiction",
            "Science Fiction/Fantasy",
            "Horror & Thriller",
            "Romance/Contemporary"
        ]
        
        for genre in valid_genres:
            result = service.validate_template_genre_format(genre)
            assert result == genre
    
    def test_validate_template_genre_format_invalid(self, service):
        """Test validation fails with invalid template genre format."""
        with pytest.raises(ValidationError) as exc_info:
            service.validate_template_genre_format("Genre<script>")
        
        assert "invalid genre format" in str(exc_info.value).lower()
    
    # Test validate_pagination_params
    
    def test_validate_pagination_params_valid(self, service):
        """Test validation with valid pagination parameters."""
        result = service.validate_pagination_params(page=1, per_page=50)
        
        assert result["page"] == 1
        assert result["per_page"] == 50
    
    def test_validate_pagination_params_defaults(self, service):
        """Test pagination defaults when not provided."""
        result = service.validate_pagination_params()
        
        assert result["page"] == 1
        assert result["per_page"] == 50
    
    def test_validate_pagination_params_page_too_low(self, service):
        """Test page is normalized to 1 if too low."""
        result = service.validate_pagination_params(page=0, per_page=50)
        assert result["page"] == 1
        
        result = service.validate_pagination_params(page=-1, per_page=50)
        assert result["page"] == 1
    
    def test_validate_pagination_params_per_page_too_low(self, service):
        """Test per_page is normalized to 50 if too low."""
        result = service.validate_pagination_params(page=1, per_page=0)
        assert result["per_page"] == 50
        
        result = service.validate_pagination_params(page=1, per_page=-1)
        assert result["per_page"] == 50
    
    def test_validate_pagination_params_per_page_too_high(self, service):
        """Test per_page is capped at 100 to prevent DoS."""
        result = service.validate_pagination_params(page=1, per_page=200)
        assert result["per_page"] == 100
    
    # Test validate_version_number
    
    def test_validate_version_number_valid(self, service):
        """Test validation with valid version numbers."""
        for version in [1, 2, 10, 100]:
            result = service.validate_version_number(version)
            assert result == version
    
    def test_validate_version_number_invalid(self, service):
        """Test validation fails with invalid version number."""
        with pytest.raises(ValidationError) as exc_info:
            service.validate_version_number(0)
        
        assert "must be a positive integer" in str(exc_info.value).lower()
        
        with pytest.raises(ValidationError) as exc_info:
            service.validate_version_number(-1)
        
        assert "must be a positive integer" in str(exc_info.value).lower()
    
    def test_validate_version_number_custom_field_name(self, service):
        """Test validation with custom field name."""
        with pytest.raises(ValidationError) as exc_info:
            service.validate_version_number(0, field_name="version1")
        
        assert "version1" in str(exc_info.value).lower()
