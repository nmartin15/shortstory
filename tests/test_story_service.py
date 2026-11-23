"""
Unit tests for StoryService.

Tests story CRUD operations.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from src.shortstory.services.story_service import StoryService
from src.shortstory.utils.errors import ValidationError, NotFoundError
from src.shortstory.utils import MAX_WORD_COUNT
from tests.test_constants import GENRE_GENERAL_FICTION


class TestStoryService:
    """Test suite for StoryService."""
    
    @pytest.fixture
    def mock_repository(self):
        """Create a mock story repository."""
        repo = Mock()
        return repo
    
    @pytest.fixture
    def mock_pipeline_factory(self):
        """Create a mock pipeline factory."""
        def factory():
            pipeline = Mock()
            pipeline.word_validator = Mock()
            pipeline.word_validator.count_words.return_value = 1500
            pipeline.word_validator.validate.return_value = (1500, True)
            return pipeline
        return factory
    
    @pytest.fixture
    def service(self, mock_repository, mock_pipeline_factory):
        """Create a StoryService instance."""
        return StoryService(
            repository=mock_repository,
            pipeline_factory=mock_pipeline_factory
        )
    
    @pytest.fixture
    def mock_story(self):
        """Create a mock story dictionary."""
        return {
            "id": "story_abc123",
            "body": "The story begins with a lighthouse keeper...",
            "word_count": 1500,
            "max_words": MAX_WORD_COUNT,
            "genre": GENRE_GENERAL_FICTION
        }
    
    def test_get_story_success(self, service, mock_repository, mock_story):
        """Test getting story successfully."""
        mock_repository.load.return_value = mock_story
        
        result = service.get_story("story_abc123")
        
        assert result["id"] == "story_abc123"
        assert result["word_count"] == 1500
        assert result["max_words"] == MAX_WORD_COUNT
        mock_repository.load.assert_called_once_with("story_abc123")
    
    def test_get_story_not_found(self, service, mock_repository):
        """Test getting non-existent story."""
        mock_repository.load.return_value = None
        
        with pytest.raises(NotFoundError) as exc_info:
            service.get_story("story_nonexistent")
        
        assert "Story" in str(exc_info.value)
        assert "story_nonexistent" in str(exc_info.value)
    
    def test_get_story_recalculates_word_count(self, service, mock_repository, mock_story):
        """Test getting story recalculates word count."""
        mock_repository.load.return_value = mock_story
        
        # Create a new factory that returns a pipeline with different word count
        def custom_factory():
            pipeline = Mock()
            pipeline.word_validator = Mock()
            pipeline.word_validator.count_words.return_value = 2000
            return pipeline
        
        service._pipeline_factory = custom_factory
        
        result = service.get_story("story_abc123")
        
        assert result["word_count"] == 2000
    
    def test_update_story_body_success(self, service, mock_repository, mock_story):
        """Test updating story body successfully."""
        mock_repository.load.return_value = mock_story
        new_body = "Updated story text with new content."
        
        result = service.update_story_body("story_abc123", new_body)
        
        assert result["body"] == new_body
        assert result["word_count"] == 1500
        mock_repository.update.assert_called_once()
        update_args = mock_repository.update.call_args[0]
        assert update_args[0] == "story_abc123"
        assert update_args[1]["body"] == new_body
        assert update_args[1]["word_count"] == 1500
    
    def test_update_story_body_not_found(self, service, mock_repository):
        """Test updating non-existent story."""
        mock_repository.load.return_value = None
        
        with pytest.raises(NotFoundError) as exc_info:
            service.update_story_body("story_nonexistent", "New body")
        
        assert "Story" in str(exc_info.value)
    
    def test_update_story_body_exceeds_word_limit(self, service, mock_repository, mock_story):
        """Test updating story body that exceeds word limit."""
        mock_repository.load.return_value = mock_story
        
        # Create a factory that returns a pipeline with validation failure
        mock_pipeline = Mock()
        mock_pipeline.word_validator = Mock()
        mock_pipeline.word_validator.validate.return_value = (MAX_WORD_COUNT + 1, False)
        
        def custom_factory():
            return mock_pipeline
        
        service._pipeline_factory = custom_factory
        
        # Use a body that passes character limit but fails word count
        # MAX_WORD_COUNT * 10 = 75000 chars, so use something shorter
        # but with enough words to exceed word limit
        long_body = "word " * (MAX_WORD_COUNT + 100)  # Creates many words but reasonable char count
        
        with pytest.raises(ValidationError) as exc_info:
            service.update_story_body("story_abc123", long_body)
        
        assert "exceeds word limit" in str(exc_info.value).lower()
        assert exc_info.value.details["word_count"] == MAX_WORD_COUNT + 1
    
    def test_update_story_body_no_pipeline_factory(self, mock_repository, mock_story):
        """Test updating story body without pipeline factory."""
        service = StoryService(repository=mock_repository, pipeline_factory=None)
        mock_repository.load.return_value = mock_story
        
        with pytest.raises(ValidationError) as exc_info:
            service.update_story_body("story_abc123", "New body")
        
        assert "pipeline factory" in str(exc_info.value).lower()
    
    def test_list_stories_success(self, service, mock_repository):
        """Test listing stories successfully."""
        mock_result = {
            "stories": [{"id": "story_1"}, {"id": "story_2"}],
            "pagination": {
                "page": 1,
                "per_page": 50,
                "total": 2,
                "total_pages": 1,
                "has_next": False,
                "has_prev": False
            }
        }
        mock_repository.list.return_value = mock_result
        
        result = service.list_stories(page=1, per_page=50)
        
        assert len(result["stories"]) == 2
        assert result["pagination"]["total"] == 2
        mock_repository.list.assert_called_once_with(page=1, per_page=50, genre=None)
    
    def test_list_stories_with_genre(self, service, mock_repository):
        """Test listing stories with genre filter."""
        mock_result = {
            "stories": [{"id": "story_1"}],
            "pagination": {"page": 1, "per_page": 50, "total": 1}
        }
        mock_repository.list.return_value = mock_result
        
        result = service.list_stories(page=1, per_page=50, genre=GENRE_GENERAL_FICTION)
        
        mock_repository.list.assert_called_once_with(
            page=1, per_page=50, genre=GENRE_GENERAL_FICTION
        )
    
    def test_list_stories_normalizes_pagination(self, service, mock_repository):
        """Test listing stories normalizes pagination parameters."""
        mock_result = {
            "stories": [],
            "pagination": {"page": 1, "per_page": 50, "total": 0}
        }
        mock_repository.list.return_value = mock_result
        
        # Test with invalid pagination (should be normalized)
        service.list_stories(page=0, per_page=200)
        
        # Should normalize page to 1 and per_page to 100
        call_args = mock_repository.list.call_args
        assert call_args[1]["page"] == 1
        assert call_args[1]["per_page"] == 100
    
    def test_list_stories_validates_genre(self, service, mock_repository):
        """Test listing stories validates genre format."""
        with pytest.raises(ValidationError) as exc_info:
            service.list_stories(genre="Invalid<script>Genre")
        
        assert "invalid genre format" in str(exc_info.value).lower()
    
    def test_save_story_success(self, service, mock_repository, mock_story):
        """Test saving story successfully."""
        mock_repository.save.return_value = True
        
        result = service.save_story(mock_story)
        
        assert result is True
        mock_repository.save.assert_called_once_with(mock_story)
    
    def test_save_story_failure(self, service, mock_repository, mock_story):
        """Test saving story when repository returns False."""
        mock_repository.save.return_value = False
        
        result = service.save_story(mock_story)
        
        assert result is False
    
    def test_service_uses_get_story_repository_when_none_provided(self):
        """Test service uses get_story_repository when repository not provided."""
        with patch('src.shortstory.services.story_service.get_story_repository') as mock_get_repo:
            mock_repo = Mock()
            mock_repo.load.return_value = {"id": "story_1"}
            mock_get_repo.return_value = mock_repo
            
            service = StoryService()
            result = service.get_story("story_1")
            
            assert result["id"] == "story_1"
            mock_get_repo.assert_called_once()
