# Service Layer Refactoring Opportunities for routes.py

## Overview

The `routes.py` file currently mixes HTTP handling with business logic, making it difficult to test, maintain, and reuse. This document identifies opportunities to extract business logic into a service layer, following the Single Responsibility Principle and improving separation of concerns.

## Current Issues

1. **Business logic in route handlers** (~400+ lines of business logic)
2. **Direct repository access** from routes
3. **Complex validation logic** scattered across routes
4. **Pipeline orchestration** mixed with HTTP concerns
5. **Error handling** duplicated across routes
6. **Background job logic** mixed with route handlers
7. **Response building** partially in routes, partially in helpers

## Proposed Service Layer Structure

```
src/shortstory/services/
├── __init__.py
├── story_service.py          # Core story operations
├── story_generation_service.py # Story generation orchestration
├── story_revision_service.py  # Story revision operations
├── story_validation_service.py # Input validation
├── story_export_service.py     # Export operations
└── job_service.py            # Background job management
```

---

## 1. Story Generation Service

### Current Location
- `routes.py` lines 94-395 (`generate_story` route)

### Business Logic to Extract

#### 1.1 Input Validation (lines 124-186)
**Current Code:**
```python
idea = data.get('idea', '').strip()
# ... 60+ lines of validation logic
```

**Proposed Service Method:**
```python
# story_validation_service.py
class StoryValidationService:
    def validate_generation_input(
        self, 
        idea: str, 
        character: Optional[Dict], 
        theme: Optional[str], 
        genre: Optional[str]
    ) -> Dict[str, Any]:
        """Validate story generation input parameters."""
        # Extract all validation logic here
```

**Benefits:**
- Reusable validation logic
- Easier to test validation rules independently
- Can be used by both routes and background jobs

#### 1.2 Story Generation Orchestration (lines 231-340)
**Current Code:**
```python
premise = pipeline.capture_premise(idea, character, theme, validate=True)
outline = pipeline.generate_outline(genre=genre)
# ... full pipeline execution
```

**Proposed Service Method:**
```python
# story_generation_service.py
class StoryGenerationService:
    def __init__(
        self, 
        repository: StoryRepository,
        pipeline_factory: Callable
    ):
        self.repository = repository
        self.pipeline_factory = pipeline_factory
    
    def generate_story(
        self,
        idea: str,
        character: Optional[Dict],
        theme: Optional[str],
        genre: str = "General Fiction",
        max_word_count: int = 7500
    ) -> Dict[str, Any]:
        """Generate a complete story through the full pipeline."""
        # Extract all pipeline orchestration
        # Extract metadata building
        # Extract story data building
        # Handle saving to repository
```

**Benefits:**
- Single place for generation logic
- Reusable by routes and background jobs
- Easier to test generation flow
- Can add caching, retry logic, etc.

#### 1.3 Metadata Extraction (lines 240-300)
**Current Code:**
```python
tone = scaffold.get('tone', constraints.get('tone', 'balanced'))
# ... complex metadata extraction
```

**Proposed Service Method:**
```python
# story_generation_service.py
def _extract_story_metadata(
    self,
    scaffold: Dict[str, Any],
    genre_config: Dict[str, Any],
    idea: str,
    character: Optional[Dict]
) -> Dict[str, Any]:
    """Extract and build story metadata from pipeline outputs."""
```

**Benefits:**
- Centralized metadata building
- Consistent metadata structure
- Easier to modify metadata schema

---

## 2. Story Retrieval Service

### Current Location
- `routes.py` lines 397-427 (`get_story` route)

### Business Logic to Extract

#### 2.1 Story Loading with Word Count (lines 412-422)
**Current Code:**
```python
story = get_story_or_404(story_id)
pipeline = get_pipeline()
body = get_story_body(story)
word_count = pipeline.word_validator.count_words(body)
story["word_count"] = word_count
```

**Proposed Service Method:**
```python
# story_service.py
class StoryService:
    def get_story_with_metrics(self, story_id: str) -> Dict[str, Any]:
        """Get story with recalculated word count and metrics."""
        story = self.repository.load(story_id)
        if not story:
            raise NotFoundError("Story", story_id)
        
        # Recalculate word count
        body = get_story_body(story)
        word_count = self._count_words(body)
        story["word_count"] = word_count
        story["max_words"] = story.get("max_words", MAX_WORD_COUNT)
        
        return story
```

**Benefits:**
- Consistent word count calculation
- Can add additional metrics (readability, etc.)
- Reusable across endpoints

---

## 3. Story Update Service

### Current Location
- `routes.py` lines 429-509 (`update_story` route)

### Business Logic to Extract

#### 3.1 Update Validation (lines 453-497)
**Current Code:**
```python
body_text = data.get('body') or data.get('text', '')
# ... validation logic
word_count, is_valid = pipeline.word_validator.validate(body_text, raise_error=False)
```

**Proposed Service Method:**
```python
# story_service.py
def update_story_body(
    self,
    story_id: str,
    body_text: str
) -> Dict[str, Any]:
    """Update story body with validation."""
    # Validate story exists
    # Validate body text
    # Calculate word count
    # Update repository
    # Return updated story
```

**Benefits:**
- Consistent update logic
- Can add versioning, audit trails
- Reusable validation

---

## 4. Story Revision Service

### Current Location
- `routes.py` lines 764-917 (`revise_story` route)

### Business Logic to Extract

#### 4.1 Revision Orchestration (lines 828-893)
**Current Code:**
```python
pipeline = get_pipeline(genre=story_genre, genre_config=story_genre_config)
revised_draft = pipeline.revise(draft=temp_draft, use_llm=use_llm)
# ... revision history management
```

**Proposed Service Method:**
```python
# story_revision_service.py
class StoryRevisionService:
    def revise_story(
        self,
        story_id: str,
        use_llm: bool = True
    ) -> Dict[str, Any]:
        """Revise a story and create new revision entry."""
        # Load story
        # Create pipeline
        # Run revision
        # Update revision history
        # Save to repository
        # Return revised story
```

**Benefits:**
- Centralized revision logic
- Consistent revision history management
- Can add revision comparison, rollback, etc.

#### 4.2 Revision History Management (lines 867-882)
**Current Code:**
```python
new_version = story["current_revision"] + 1
story["revision_history"].append({...})
story["current_revision"] = new_version
```

**Proposed Service Method:**
```python
# story_revision_service.py
def _add_revision_to_history(
    self,
    story: Dict[str, Any],
    revised_body: str,
    word_count: int
) -> Dict[str, Any]:
    """Add a new revision to story's revision history."""
```

**Benefits:**
- Consistent revision history format
- Can add revision metadata (who, why, etc.)
- Easier to implement revision comparison

---

## 5. Story Validation Service

### Current Location
- `routes.py` lines 511-565 (`validate_text` route)
- Scattered validation throughout routes

### Business Logic to Extract

#### 5.1 Text Validation (lines 535-565)
**Current Code:**
```python
word_count, is_valid = pipeline.word_validator.validate(data['text'], raise_error=False)
response = {
    **word_count_response(word_count),
    "is_valid": is_valid,
    "distinctiveness": check_distinctiveness(data['text'])
}
```

**Proposed Service Method:**
```python
# story_validation_service.py
class StoryValidationService:
    def validate_story_text(
        self,
        text: str,
        include_memorability: bool = False,
        character: Optional[Dict] = None,
        outline: Optional[Dict] = None,
        premise: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Validate story text and return comprehensive validation results."""
        # Word count validation
        # Distinctiveness check
        # Optional memorability scoring
        # Return structured validation response
```

**Benefits:**
- Single validation API
- Consistent validation results
- Can add more validation rules easily

---

## 6. Story Export Service

### Current Location
- `routes.py` lines 1065-1138 (`export_story` route)

### Business Logic to Extract

#### 6.1 Export Format Validation (lines 1093-1099)
**Current Code:**
```python
valid_formats = ['pdf', 'markdown', 'txt', 'docx', 'epub']
if format_type not in valid_formats:
    raise ValidationError(...)
```

**Proposed Service Method:**
```python
# story_export_service.py
class StoryExportService:
    VALID_FORMATS = ['pdf', 'markdown', 'txt', 'docx', 'epub']
    
    def validate_export_format(self, format_type: str) -> str:
        """Validate export format."""
    
    def export_story(
        self,
        story_id: str,
        format_type: str
    ) -> Response:
        """Export story in specified format."""
        # Validate format
        # Load story
        # Generate export
        # Return file response
```

**Benefits:**
- Centralized export logic
- Consistent format validation
- Can add export caching, batch exports, etc.

---

## 7. Background Job Service

### Current Location
- `routes.py` lines 188-212, 808-825, 1114-1131

### Business Logic to Extract

#### 7.1 Job Enqueueing (scattered across routes)
**Current Code:**
```python
if use_bg_jobs:
    queue = get_queue('default')
    job = queue.enqueue(generate_story_job, ...)
    return jsonify({"status": "queued", "job_id": job.id}), 202
```

**Proposed Service Method:**
```python
# job_service.py
class JobService:
    def enqueue_story_generation(
        self,
        idea: str,
        character: Optional[Dict],
        theme: Optional[str],
        genre: str,
        max_word_count: int
    ) -> Dict[str, Any]:
        """Enqueue story generation job."""
        # Check if background jobs available
        # Enqueue job
        # Return job status response
    
    def enqueue_story_revision(
        self,
        story_id: str,
        use_llm: bool = True
    ) -> Dict[str, Any]:
        """Enqueue story revision job."""
    
    def enqueue_story_export(
        self,
        story_id: str,
        format_type: str
    ) -> Dict[str, Any]:
        """Enqueue story export job."""
```

**Benefits:**
- Consistent job enqueueing
- Centralized job configuration
- Easier to add job prioritization, retries, etc.

---

## 8. Story Listing Service

### Current Location
- `routes.py` lines 675-726 (`list_all_stories` route)

### Business Logic to Extract

#### 8.1 Pagination and Filtering (lines 689-720)
**Current Code:**
```python
page = request.args.get('page', 1, type=int)
per_page = request.args.get('per_page', 50, type=int)
genre = request.args.get('genre', None, type=str)
# ... validation and filtering
result = get_story_repository().list(page=page, per_page=per_page, genre=genre)
```

**Proposed Service Method:**
```python
# story_service.py
def list_stories(
    self,
    page: int = 1,
    per_page: int = 50,
    genre: Optional[str] = None
) -> Dict[str, Any]:
    """List stories with pagination and optional genre filter."""
    # Validate pagination parameters
    # Validate genre format
    # Call repository
    # Return paginated results
```

**Benefits:**
- Consistent pagination logic
- Reusable filtering
- Can add sorting, search, etc.

---

## 9. Story Comparison Service

### Current Location
- `routes.py` lines 957-1063 (`compare_story_versions` route)

### Business Logic to Extract

#### 9.1 Version Comparison (lines 1005-1062)
**Current Code:**
```python
v1_data = next((r for r in revision_history if r.get("version") == version1), None)
# ... comparison logic
```

**Proposed Service Method:**
```python
# story_revision_service.py
def compare_versions(
    self,
    story_id: str,
    version1: Optional[int] = None,
    version2: Optional[int] = None
) -> Dict[str, Any]:
    """Compare two versions of a story."""
    # Load story
    # Validate versions exist
    # Calculate differences
    # Return comparison data
```

**Benefits:**
- Reusable comparison logic
- Can add diff algorithms, change tracking
- Easier to test comparison logic

---

## 10. Error Handling Service

### Current Location
- Scattered across all routes (try/except blocks)

### Business Logic to Extract

#### 10.1 Error Translation (lines 348-395, 894-917)
**Current Code:**
```python
except ValueError as e:
    error_msg = str(e)
    if "premise" in error_msg.lower():
        raise ValidationError(...)
```

**Proposed Service Method:**
```python
# error_handling_service.py (or in each service)
class ErrorHandlingMixin:
    def handle_generation_error(self, error: Exception) -> Exception:
        """Translate low-level errors to domain errors."""
        # Map ValueError -> ValidationError
        # Map ConnectionError -> ServiceUnavailableError
        # etc.
```

**Benefits:**
- Consistent error handling
- Centralized error translation
- Easier to add error logging, metrics

---

## Implementation Status

### ✅ Phase 1: Independent Services (COMPLETED)

**Services Implemented:**
1. ✅ `StoryValidationService` - Complete input validation service
   - Location: `src/shortstory/services/story_validation_service.py`
   - Features: Generation input validation, body validation, format validation, pagination validation
   
2. ✅ `StoryExportService` - Story export operations
   - Location: `src/shortstory/services/story_export_service.py`
   - Features: Format validation, story export orchestration
   
3. ✅ `JobService` - Background job management
   - Location: `src/shortstory/services/job_service.py`
   - Features: Job enqueueing, status checking, result retrieval
   
4. ✅ `StoryService` - CRUD operations (partial)
   - Location: `src/shortstory/services/story_service.py`
   - Features: Story retrieval, updates, listing, saving
   - Note: Minimal pipeline dependency (only for word counting)

**Next Steps:**
- Update routes to use these services (can be done incrementally)
- Add tests for each service
- Proceed with Phase 2 once pipeline refactoring is complete

## Implementation Strategy

### ⚠️ Pipeline Dependency Consideration

**Important**: If `pipeline.py` is being refactored, consider the dependency:

**Pipeline Methods Used by Services:**
- `pipeline.capture_premise(idea, character, theme, validate=True)`
- `pipeline.generate_outline(genre=genre)`
- `pipeline.scaffold(genre=genre)`
- `pipeline.draft()`
- `pipeline.revise(draft=None, use_llm=True)`
- `pipeline.word_validator.count_words(text)`
- `pipeline.word_validator.validate(text, raise_error=False)`
- `pipeline.genre_config` (property)

**Recommendation**: 
- **If pipeline API is stable**: Proceed with all phases
- **If pipeline API might change**: Use phased approach below
- **Best practice**: Coordinate with pipeline refactoring to ensure API compatibility

### Phase 1: Extract Independent Services (No Pipeline Dependency)
**Can proceed regardless of pipeline refactoring status**

1. Create `StoryValidationService`
   - No pipeline dependency
   - Move all validation logic from routes
   - Update routes to use service
   - Test validation independently

2. Create `StoryService` (CRUD operations)
   - Minimal pipeline dependency (only for word counting)
   - Extract story retrieval, update, listing
   - Can abstract word counting behind interface if needed

3. Create `StoryExportService`
   - No pipeline dependency
   - Extract export format handling
   - Extract export logic

4. Create `JobService`
   - No pipeline dependency
   - Extract job enqueueing logic
   - Centralize job management

### Phase 2: Extract Pipeline-Dependent Services
**Wait for pipeline refactoring to stabilize, OR proceed if API is stable**

1. Create `StoryGenerationService`
   - **Depends on**: `capture_premise()`, `generate_outline()`, `scaffold()`, `draft()`, `revise()`
   - **Risk**: If pipeline API changes, this service will need updates
   - **Mitigation**: Use pipeline factory pattern, abstract behind interface

2. Create `StoryRevisionService`
   - **Depends on**: `revise()`, `word_validator`
   - **Risk**: Medium - revision method signature might change
   - **Mitigation**: Wrap pipeline calls in adapter if needed

3. Extract comparison logic
   - **Depends on**: Story data structure (not pipeline directly)
   - **Risk**: Low - mostly data manipulation

### Phase 3: Refactor Routes
1. Simplify route handlers to thin wrappers
2. Remove direct repository access
3. Remove business logic from routes
4. Add comprehensive error handling

### Alternative: Parallel Development Strategy

If pipeline refactoring is ongoing, you can:

1. **Create service interfaces** (abstract base classes)
   - Define expected pipeline interface
   - Services depend on interface, not concrete pipeline
   - Pipeline refactoring can implement same interface

2. **Use adapter pattern**
   - Create adapter that wraps pipeline
   - Services use adapter
   - Adapter can adapt to new pipeline API

3. **Coordinate API contracts**
   - Agree on stable pipeline interface
   - Document expected method signatures
   - Services can be built against contract

---

## Benefits Summary

### Testability
- Services can be tested independently
- Mock services in route tests
- Test business logic without HTTP layer

### Reusability
- Services can be used by:
  - HTTP routes
  - Background jobs
  - CLI commands
  - Future API versions

### Maintainability
- Single place for business logic
- Easier to understand code flow
- Easier to modify behavior

### Separation of Concerns
- Routes handle HTTP only
- Services handle business logic
- Repository handles persistence

### Consistency
- Consistent validation across endpoints
- Consistent error handling
- Consistent data structures

---

## Example: Before and After

### Before (Current)
```python
@flask_app.route('/api/generate', methods=['POST'])
def generate_story():
    data = request.get_json() or {}
    idea = data.get('idea', '').strip()
    # ... 60 lines of validation
    # ... 100 lines of pipeline orchestration
    # ... 50 lines of metadata building
    # ... 30 lines of error handling
    return jsonify(build_canonical_story_response(story_data))
```

### After (Proposed)
```python
@flask_app.route('/api/generate', methods=['POST'])
def generate_story():
    try:
        data = request.get_json() or {}
        
        # Validate input
        validation_service.validate_generation_input(
            idea=data.get('idea'),
            character=data.get('character'),
            theme=data.get('theme'),
            genre=data.get('genre')
        )
        
        # Generate story
        story_data = generation_service.generate_story(
            idea=data.get('idea'),
            character=data.get('character'),
            theme=data.get('theme'),
            genre=data.get('genre', 'General Fiction'),
            max_word_count=data.get('max_word_count', MAX_WORD_COUNT)
        )
        
        # Return response
        return jsonify(build_canonical_story_response(story_data))
    
    except ValidationError as e:
        raise  # Handled by error handler
    except ServiceUnavailableError as e:
        raise  # Handled by error handler
```

---

## Next Steps

1. **Review and approve** this refactoring plan
2. **Create service layer structure** (directories, base classes)
3. **Start with Phase 1** (validation service)
4. **Incrementally refactor** one route at a time
5. **Add tests** for each service
6. **Update documentation** as services are created
