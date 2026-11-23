# Application Architecture

> **See [pipeline.md](pipeline.md) for detailed pipeline architecture.**  
> **See [CONCEPTS.md](CONCEPTS.md) for core principles and terminology.**

## Overview

The ShortStory application follows a **layered architecture** with clear separation of concerns:

1. **HTTP Layer** (`api/`) - Handles HTTP requests/responses
2. **Service Layer** (`services/`) - Contains business logic
3. **Pipeline Layer** (`pipeline.py`) - Story generation pipeline
4. **Provider Layer** (`providers/`) - LLM provider abstractions
5. **Repository Layer** (`utils/repository.py`) - Data persistence abstraction
6. **Utility Layer** (`utils/`) - Shared utilities

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    HTTP Layer (Flask)                        │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  routes.py - Route Handlers (thin wrappers)         │   │
│  │  - /api/generate                                     │   │
│  │  - /api/story/<id>                                   │   │
│  │  - /api/story/<id>/export                            │   │
│  │  - /api/job/<id>                                     │   │
│  └──────────────────────────────────────────────────────┘   │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                    Service Layer                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  StoryValidationService                              │   │
│  │  - Input validation                                  │   │
│  │  - Format validation                                 │   │
│  │  - Pagination validation                             │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  StoryService                                        │   │
│  │  - CRUD operations                                   │   │
│  │  - Word count calculation                            │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  StoryExportService                                  │   │
│  │  - Export orchestration                              │   │
│  │  - Format validation                                 │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  JobService                                          │   │
│  │  - Background job management                          │   │
│  │  - Job status checking                               │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  StoryGenerationService (planned)                   │   │
│  │  - Pipeline orchestration                            │   │
│  └──────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  StoryRevisionService (planned)                      │   │
│  │  - Revision orchestration                            │   │
│  └──────────────────────────────────────────────────────┘   │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                    Pipeline Layer                           │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  ShortStoryPipeline                                  │   │
│  │  1. capture_premise()                               │   │
│  │  2. generate_outline()                              │   │
│  │  3. scaffold()                                      │   │
│  │  4. draft()                                         │   │
│  │  5. revise()                                        │   │
│  └──────────────────────────────────────────────────────┘   │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                    Provider Layer                           │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  BaseLLMClient (interface)                           │   │
│  │  └── GeminiProvider                                  │   │
│  └──────────────────────────────────────────────────────┘   │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                    Repository Layer                         │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  StoryRepository (interface)                         │   │
│  │  ├── DatabaseStoryRepository                        │   │
│  │  └── FileStoryRepository                            │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Layer Responsibilities

### HTTP Layer (`api/`)

**Purpose:** Handle HTTP requests and responses

**Responsibilities:**
- Parse HTTP requests
- Validate request format
- Call appropriate services
- Format HTTP responses
- Handle HTTP errors (404, 400, 500, etc.)
- Apply rate limiting

**Key Files:**
- `api/routes.py` - Route handlers (thin wrappers around services)
- `api/helpers.py` - Response formatting, context helpers

**Principles:**
- Routes should be **thin** - minimal logic
- Delegate business logic to services
- Handle HTTP-specific concerns only

### Service Layer (`services/`)

**Purpose:** Encapsulate business logic

**Responsibilities:**
- Input validation
- Business rule enforcement
- Data transformation
- Orchestration of multiple operations
- Error handling and translation

**Services:**

1. **StoryValidationService**
   - Validates all input parameters
   - Format validation (export formats, genres)
   - Pagination parameter validation
   - Version number validation

2. **StoryService**
   - Story CRUD operations
   - Word count calculation
   - Story listing with pagination
   - Story updates with validation
   - Story saving with optional body updates

3. **StoryExportService**
   - Export format validation
   - Export orchestration
   - File generation

4. **JobService**
   - Background job enqueueing
   - Job status checking
   - Job result retrieval

5. **StoryGenerationService** (planned)
   - Pipeline orchestration
   - Story generation workflow
   - Metadata extraction

6. **StoryRevisionService** (planned)
   - Revision orchestration
   - Revision history management
   - Version comparison

**Principles:**
- Services are **independent** of HTTP layer
- Services can be used by routes, jobs, CLI, etc.
- Services use dependency injection for testability
- Services follow Single Responsibility Principle

### Pipeline Layer (`pipeline.py`)

**Purpose:** Transform creative premise into polished story

**Responsibilities:**
- Execute 5-stage story generation pipeline
- Maintain pipeline state
- Coordinate between stages
- Validate pipeline constraints

**See [pipeline.md](pipeline.md) for detailed pipeline architecture.**

### Provider Layer (`providers/`)

**Purpose:** Abstract LLM provider implementations

**Responsibilities:**
- Provide unified interface for LLM operations
- Handle provider-specific configuration
- Manage API communication
- Implement retry logic

**Key Files:**
- `providers/factory.py` - Provider factory
- `providers/gemini.py` - Gemini provider implementation

### Repository Layer (`utils/repository.py`)

**Purpose:** Abstract data persistence

**Responsibilities:**
- Provide unified interface for storage operations
- Handle storage backend differences
- Manage data serialization
- Implement caching (optional)

**Implementations:**
- `DatabaseStoryRepository` - SQLite database storage
- `FileStoryRepository` - JSON file storage

**See [STORAGE_IMPLEMENTATION.md](STORAGE_IMPLEMENTATION.md) for storage details.**

### Utility Layer (`utils/`)

**Purpose:** Shared utilities and helpers

**Key Modules:**
- `validation.py` - Distinctiveness validation
- `word_count.py` - Word count validation
- `errors.py` - Custom exception classes
- `story_builder.py` - Story data structure building
- `type_converters.py` - Type conversion utilities

## Data Flow

### Story Generation Flow

```
1. HTTP Request → routes.py
2. routes.py → StoryValidationService (validate input)
3. routes.py → StoryGenerationService (orchestrate generation)
4. StoryGenerationService → ShortStoryPipeline
5. ShortStoryPipeline → LLM Provider (via providers/)
6. ShortStoryPipeline → StoryService (save story)
7. StoryService → StoryRepository
8. StoryRepository → Database/File Storage
9. Response ← routes.py
```

### Story Retrieval Flow

```
1. HTTP Request → routes.py
2. routes.py → StoryService.get_story()
3. StoryService → StoryRepository.load()
4. StoryRepository → Database/File Storage
5. StoryService → Pipeline (word count calculation)
6. Response ← routes.py
```

### Background Job Flow

```
1. HTTP Request → routes.py
2. routes.py → JobService.enqueue_story_generation()
3. JobService → RQ Queue
4. Worker Process → generate_story_job()
5. generate_story_job() → StoryGenerationService
6. StoryGenerationService → ShortStoryPipeline
7. Result stored in RQ
8. Client polls /api/job/<id> → JobService.get_job_status()
```

## Design Patterns

### Service Layer Pattern

Services encapsulate business logic and provide a clean interface:

```python
# Route handler (thin wrapper)
@flask_app.route('/api/generate', methods=['POST'])
def generate_story():
    data = request.get_json()
    validated = _validation_service.validate_generation_input(...)
    story = _generation_service.generate_story(...)
    return jsonify(build_canonical_story_response(story))
```

### Repository Pattern

Repository abstracts storage implementation:

```python
# Service uses repository interface
class StoryService:
    def __init__(self, repository: StoryRepository):
        self.repository = repository
    
    def get_story(self, story_id: str):
        return self.repository.load(story_id)
```

### Factory Pattern

Provider factory creates appropriate LLM provider:

```python
# Factory creates provider based on configuration
provider = get_default_provider()  # Returns GeminiProvider
```

### Dependency Injection

Services accept dependencies via constructor:

```python
# Service with injected dependencies
service = StoryService(
    repository=get_story_repository(),
    pipeline_factory=get_pipeline
)
```

## Benefits of This Architecture

1. **Separation of Concerns**
   - Each layer has a single, well-defined responsibility
   - Changes in one layer don't affect others

2. **Testability**
   - Services can be tested independently
   - Mock dependencies easily
   - Test business logic without HTTP layer

3. **Reusability**
   - Services can be used by routes, jobs, CLI
   - Repository can switch storage backends
   - Providers can be swapped

4. **Maintainability**
   - Single place for business logic
   - Clear code organization
   - Easy to understand and modify

5. **Scalability**
   - Services can be extracted to microservices
   - Repository can scale storage independently
   - Providers can be load-balanced

## Service Layer Status

### ✅ Implemented Services

- **StoryValidationService** - Complete input validation
- **StoryExportService** - Export operations
- **JobService** - Background job management
- **StoryService** - CRUD operations (partial)

### ⏳ Planned Services (After Pipeline Refactoring)

- **StoryGenerationService** - Pipeline orchestration
- **StoryRevisionService** - Revision orchestration

## Integration Status

**Routes Using Services:**
- ✅ `/api/generate` - Uses ValidationService, JobService
- ✅ `/api/story/<id>` (GET) - Uses StoryService
- ✅ `/api/story/<id>` (PUT) - Uses StoryService
- ✅ `/api/stories` - Uses StoryService, ValidationService
- ✅ `/api/story/<id>/save` - Uses StoryService
- ✅ `/api/story/<id>/export` - Uses ExportService, ValidationService, JobService
- ✅ `/api/story/<id>/revise` - Uses JobService
- ✅ `/api/story/<id>/compare` - Uses ValidationService
- ✅ `/api/validate` - Uses ValidationService
- ✅ `/api/job/<id>` - Uses JobService
- ✅ `/api/job/<id>/result` - Uses JobService
- ✅ `/api/templates` - Uses ValidationService

**Routes Still Using Direct Logic:**
- ⏳ `/api/generate` - Pipeline orchestration (will use StoryGenerationService after pipeline refactoring)
- ⏳ `/api/story/<id>/revise` - Revision logic (will use StoryRevisionService after pipeline refactoring)
- ⏳ `/api/memorability/score` - Memorability scoring (can use new service if needed)

## Testing Strategy

### Unit Tests
- Each service has comprehensive unit tests
- Services are tested independently
- Dependencies are mocked

### Integration Tests
- Test service-repository interactions
- Test service-pipeline interactions
- Test route-service interactions

### Test Files
- `tests/test_story_validation_service.py` - 32 tests
- `tests/test_story_export_service.py` - 4 tests
- `tests/test_job_service.py` - 11 tests
- `tests/test_story_service.py` - 13 tests

## Future Improvements

1. **Complete Service Layer**
   - Implement StoryGenerationService
   - Implement StoryRevisionService
   - Move remaining logic from routes

2. **Service Composition**
   - Services can call other services
   - Avoid circular dependencies
   - Use dependency injection

3. **Caching Layer**
   - Add caching service
   - Cache frequently accessed data
   - Invalidate on updates

4. **Event System**
   - Add event publishing
   - Decouple services
   - Enable async processing

## Related Documentation

- [pipeline.md](pipeline.md) - Pipeline architecture details
- [SERVICE_LAYER_IMPLEMENTATION.md](SERVICE_LAYER_IMPLEMENTATION.md) - Service implementation guide
- [SERVICE_INTEGRATION_SUMMARY.md](SERVICE_INTEGRATION_SUMMARY.md) - Integration summary
- [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) - Project structure
- [CONCEPTS.md](CONCEPTS.md) - Core concepts and terminology
