"""
Unit tests for JobService.

Tests background job management operations.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from src.shortstory.services.job_service import JobService, RQ_AVAILABLE
from src.shortstory.utils.errors import NotFoundError, ServiceUnavailableError


class TestJobService:
    """Test suite for JobService."""
    
    @pytest.fixture
    def mock_flask_app(self):
        """Create a mock Flask app with config."""
        app = Mock()
        app.config = {'USE_BACKGROUND_JOBS': True}
        return app
    
    @pytest.fixture
    def service(self, mock_flask_app):
        """Create a JobService instance."""
        return JobService(flask_app=mock_flask_app)
    
    @pytest.fixture
    def mock_job(self):
        """Create a mock RQ job."""
        job = Mock()
        job.id = "job_abc123"
        job.get_status.return_value = "finished"
        job.created_at = datetime.now()
        job.started_at = datetime.now()
        job.ended_at = datetime.now()
        job.is_finished = True
        job.is_failed = False
        job.result = {"status": "completed", "story_id": "story_xyz789"}
        job.exc_info = None
        return job
    
    def test_is_background_jobs_enabled_with_app(self, service, mock_flask_app):
        """Test checking if background jobs are enabled with Flask app."""
        # This test only passes if RQ is available
        expected = RQ_AVAILABLE and mock_flask_app.config.get('USE_BACKGROUND_JOBS', False)
        assert service.is_background_jobs_enabled() == expected
    
    @pytest.mark.skipif(not RQ_AVAILABLE, reason="RQ not available")
    def test_is_background_jobs_enabled_without_app(self):
        """Test checking if background jobs are enabled without Flask app."""
        service = JobService()
        with patch('src.shortstory.services.job_service.current_app') as mock_app:
            mock_app.config = {'USE_BACKGROUND_JOBS': True}
            assert service.is_background_jobs_enabled() == True
    
    def test_is_background_jobs_enabled_disabled(self, mock_flask_app):
        """Test checking when background jobs are disabled."""
        mock_flask_app.config = {'USE_BACKGROUND_JOBS': False}
        service = JobService(flask_app=mock_flask_app)
        assert service.is_background_jobs_enabled() == False
    
    @pytest.mark.skipif(not RQ_AVAILABLE, reason="RQ not available")
    def test_enqueue_story_generation(self, service):
        """Test enqueueing story generation job."""
        with patch('src.shortstory.services.job_service.get_queue') as mock_get_queue:
            mock_queue = Mock()
            mock_job = Mock()
            mock_job.id = "job_abc123"
            mock_queue.enqueue.return_value = mock_job
            mock_get_queue.return_value = mock_queue
            
            result = service.enqueue_story_generation(
                idea="A story",
                character={"description": "A character"},
                theme="A theme",
                genre="General Fiction",
                max_word_count=7500
            )
            
            assert result["status"] == "queued"
            assert result["job_id"] == "job_abc123"
            assert "message" in result
            mock_queue.enqueue.assert_called_once()
    
    @pytest.mark.skipif(not RQ_AVAILABLE, reason="RQ not available")
    def test_enqueue_story_generation_not_enabled(self):
        """Test enqueueing fails when background jobs not enabled."""
        mock_app = Mock()
        mock_app.config = {'USE_BACKGROUND_JOBS': False}
        service = JobService(flask_app=mock_app)
        
        with pytest.raises(ServiceUnavailableError) as exc_info:
            service.enqueue_story_generation(
                idea="A story",
                character=None,
                theme=None
            )
        
        assert "background jobs are not available" in str(exc_info.value).lower()
    
    @pytest.mark.skipif(not RQ_AVAILABLE, reason="RQ not available")
    def test_enqueue_story_revision(self, service):
        """Test enqueueing story revision job."""
        with patch('src.shortstory.services.job_service.get_queue') as mock_get_queue:
            mock_queue = Mock()
            mock_job = Mock()
            mock_job.id = "job_rev123"
            mock_queue.enqueue.return_value = mock_job
            mock_get_queue.return_value = mock_queue
            
            result = service.enqueue_story_revision(
                story_id="story_abc123",
                use_llm=True
            )
            
            assert result["status"] == "queued"
            assert result["job_id"] == "job_rev123"
            assert result["story_id"] == "story_abc123"
            mock_queue.enqueue.assert_called_once()
    
    @pytest.mark.skipif(not RQ_AVAILABLE, reason="RQ not available")
    def test_enqueue_story_export(self, service):
        """Test enqueueing story export job."""
        with patch('src.shortstory.services.job_service.get_queue') as mock_get_queue:
            mock_queue = Mock()
            mock_job = Mock()
            mock_job.id = "job_exp123"
            mock_queue.enqueue.return_value = mock_job
            mock_get_queue.return_value = mock_queue
            
            result = service.enqueue_story_export(
                story_id="story_abc123",
                format_type="pdf"
            )
            
            assert result["status"] == "queued"
            assert result["job_id"] == "job_exp123"
            assert result["story_id"] == "story_abc123"
            assert result["format_type"] == "pdf"
            mock_queue.enqueue.assert_called_once()
    
    @pytest.mark.skipif(not RQ_AVAILABLE, reason="RQ not available")
    def test_get_job_status(self, service, mock_job):
        """Test getting job status."""
        with patch('src.shortstory.services.job_service.get_job') as mock_get_job:
            mock_get_job.return_value = mock_job
            
            status = service.get_job_status("job_abc123")
            
            assert status["job_id"] == "job_abc123"
            assert status["status"] == "finished"
            assert status["result"] is not None
            assert status["story_id"] == "story_xyz789"
    
    @pytest.mark.skipif(not RQ_AVAILABLE, reason="RQ not available")
    def test_get_job_status_not_found(self, service):
        """Test getting status for non-existent job."""
        with patch('src.shortstory.services.job_service.get_job') as mock_get_job:
            mock_get_job.return_value = None
            
            with pytest.raises(NotFoundError) as exc_info:
                service.get_job_status("job_nonexistent")
            
            assert "Job" in str(exc_info.value)
    
    @pytest.mark.skipif(not RQ_AVAILABLE, reason="RQ not available")
    def test_get_job_status_failed(self, service):
        """Test getting status for failed job."""
        mock_job = Mock()
        mock_job.id = "job_failed"
        mock_job.get_status.return_value = "failed"
        mock_job.is_finished = False
        mock_job.is_failed = True
        mock_job.exc_info = "Some error occurred"
        
        with patch('src.shortstory.services.job_service.get_job') as mock_get_job:
            mock_get_job.return_value = mock_job
            
            status = service.get_job_status("job_failed")
            
            assert status["status"] == "failed"
            assert status["error"] == "Some error occurred"
    
    @pytest.mark.skipif(not RQ_AVAILABLE, reason="RQ not available")
    def test_get_job_result(self, service, mock_job):
        """Test getting job result."""
        with patch('src.shortstory.services.job_service.get_job') as mock_get_job:
            mock_get_job.return_value = mock_job
            
            result = service.get_job_result("job_abc123")
            
            assert result["status"] == "completed"
            assert result["result"]["story_id"] == "story_xyz789"
    
    @pytest.mark.skipif(not RQ_AVAILABLE, reason="RQ not available")
    def test_get_job_result_not_finished(self, service):
        """Test getting result for unfinished job."""
        mock_job = Mock()
        mock_job.id = "job_running"
        mock_job.is_finished = False
        mock_job.get_status.return_value = "started"
        
        with patch('src.shortstory.services.job_service.get_job') as mock_get_job:
            mock_get_job.return_value = mock_job
            
            result = service.get_job_result("job_running")
            
            assert result["status"] == "started"
            assert "message" in result
    
    @pytest.mark.skipif(not RQ_AVAILABLE, reason="RQ not available")
    def test_get_job_result_failed(self, service):
        """Test getting result for failed job."""
        mock_job = Mock()
        mock_job.id = "job_failed"
        mock_job.is_finished = True
        mock_job.is_failed = True
        mock_job.exc_info = "Job execution failed"
        
        with patch('src.shortstory.services.job_service.get_job') as mock_get_job:
            mock_get_job.return_value = mock_job
            
            with pytest.raises(ServiceUnavailableError) as exc_info:
                service.get_job_result("job_failed")
            
            assert "job failed" in str(exc_info.value).lower()
    
    def test_get_job_status_rq_not_available(self):
        """Test getting job status when RQ is not available."""
        # Create service with RQ_AVAILABLE = False
        with patch('src.shortstory.services.job_service.RQ_AVAILABLE', False):
            service = JobService()
            
            with pytest.raises(ServiceUnavailableError) as exc_info:
                service.get_job_status("job_abc123")
            
            assert "background jobs are not available" in str(exc_info.value).lower()
