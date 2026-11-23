"""
Unit tests for StoryExportService.

Tests story export operations.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from src.shortstory.services.story_export_service import StoryExportService
from src.shortstory.utils.errors import ValidationError, NotFoundError
from tests.test_constants import GENRE_GENERAL_FICTION


class TestStoryExportService:
    """Test suite for StoryExportService."""
    
    @pytest.fixture
    def service(self):
        """Create a StoryExportService instance."""
        return StoryExportService()
    
    @pytest.fixture
    def mock_story(self):
        """Create a mock story dictionary."""
        return {
            "id": "story_abc123",
            "premise": {
                "idea": "A lighthouse keeper collects lost voices"
            },
            "body": "The story begins...",
            "genre": GENRE_GENERAL_FICTION
        }
    
    def test_export_story_valid_format(self, service, mock_story):
        """Test export with valid format."""
        with patch('src.shortstory.services.story_export_service.get_story_or_404') as mock_get, \
             patch('src.shortstory.services.story_export_service.get_story_text') as mock_get_text, \
             patch('src.shortstory.services.story_export_service.export_story_from_dict') as mock_export:
            
            mock_get.return_value = mock_story
            mock_get_text.return_value = "# A lighthouse keeper\n\nThe story begins..."
            mock_export.return_value = Mock(status_code=200)
            
            result = service.export_story("story_abc123", "pdf")
            
            mock_get.assert_called_once_with("story_abc123")
            mock_get_text.assert_called_once_with(mock_story)
            mock_export.assert_called_once()
            assert mock_export.call_args[0][0] == mock_story
            assert mock_export.call_args[0][1] == "story_abc123"
            assert mock_export.call_args[0][2] == "pdf"
    
    def test_export_story_invalid_format(self, service):
        """Test export fails with invalid format."""
        with pytest.raises(ValidationError) as exc_info:
            service.export_story("story_abc123", "invalid_format")
        
        assert "invalid format" in str(exc_info.value).lower()
        assert exc_info.value.details["format_type"] == "invalid_format"
    
    def test_export_story_not_found(self, service):
        """Test export fails when story not found."""
        with patch('src.shortstory.services.story_export_service.get_story_or_404') as mock_get:
            mock_get.return_value = None
            
            with pytest.raises(NotFoundError) as exc_info:
                service.export_story("story_abc123", "pdf")
            
            assert "Story" in str(exc_info.value)
            assert "story_abc123" in str(exc_info.value)
    
    def test_export_story_all_formats(self, service, mock_story):
        """Test export works with all valid formats."""
        formats = ['pdf', 'markdown', 'txt', 'docx', 'epub']
        
        for format_type in formats:
            with patch('src.shortstory.services.story_export_service.get_story_or_404') as mock_get, \
                 patch('src.shortstory.services.story_export_service.get_story_text') as mock_get_text, \
                 patch('src.shortstory.services.story_export_service.export_story_from_dict') as mock_export:
                
                mock_get.return_value = mock_story
                mock_get_text.return_value = "# Story\n\nContent"
                mock_export.return_value = Mock(status_code=200)
                
                result = service.export_story("story_abc123", format_type)
                
                assert mock_export.call_args[0][2] == format_type
