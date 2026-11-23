# Project Structure

```
ShortStory/
├── src/
│   └── shortstory/          # Main package
│       ├── __init__.py      # Package initialization
│       ├── pipeline.py      # ShortStoryPipeline class
│       ├── api/             # API layer
│       │   ├── routes.py    # Flask route handlers
│       │   └── helpers.py   # API helper functions
│       ├── services/        # Service layer (business logic)
│       │   ├── story_validation_service.py
│       │   ├── story_export_service.py
│       │   ├── job_service.py
│       │   └── story_service.py
│       ├── providers/       # LLM provider implementations
│       ├── utils/           # Utility modules
│       └── ...              # Other modules
│
├── examples/                # Example scripts
│   └── sample_story.py      # Example pipeline usage
│
├── tests/                   # Unit tests
│   ├── __init__.py
│   ├── test_pipeline.py     # Pipeline tests
│   ├── test_story_validation_service.py
│   ├── test_story_export_service.py
│   ├── test_job_service.py
│   └── test_story_service.py
│
├── docs/                    # Documentation (future)
│
├── .gitignore              # Git ignore rules
├── requirements.txt        # Python dependencies
│
├── README.md               # Main documentation
├── CONCEPTS.md             # Core principles (DRY source of truth)
├── pipeline.md             # Pipeline architecture
├── ARCHITECTURE.md         # Application architecture (NEW)
├── REQUIREMENTS_TRACKER.md # Requirements tracker
├── tasks.md                # Task notes
├── planning.md             # Product requirements document
└── PROJECT_STRUCTURE.md     # This file
```

## Directory Purposes

### `src/shortstory/`
Main package containing the pipeline implementation and service layer. Follows modular design with clear separation of concerns:

- **`api/`**: HTTP route handlers (thin wrappers around services)
- **`services/`**: Business logic layer (validation, CRUD, export, jobs)
- **`pipeline.py`**: Story generation pipeline (5-stage process)
- **`providers/`**: LLM provider implementations
- **`utils/`**: Utility modules (storage, validation, word counting, etc.)

### `examples/`
Example scripts demonstrating pipeline usage. Start here to understand how to use the pipeline.

### `tests/`
Unit tests for pipeline functionality. Includes tests for word count enforcement, distinctiveness validation, and voice consistency.

### Documentation Files

**Core Documentation:**
- **README.md**: Quick start and overview
- **CONCEPTS.md**: Core principles and terminology (single source of truth)
- **pipeline.md**: Detailed pipeline architecture
- **planning.md**: Product requirements document (PRD)

**Development & Tracking:**
- **REQUIREMENTS_TRACKER.md**: Functional and non-functional requirements checklist
- **tasks.md**: Task tracking
- **PROJECT_STRUCTURE.md**: This file

**Setup & Configuration:**
- **SETUP_GOOGLE.md**: Google Gemini API setup
- **STORAGE_IMPLEMENTATION.md**: Storage backends and configuration
- **STORAGE_MIGRATION.md**: Migration guide

**Deployment & Production:**
- **DEPLOYMENT.md**: Production deployment guide
- **PRODUCTION_IMPROVEMENTS.md**: Production improvements summary
- **BACKGROUND_JOBS.md**: Background job processing

**Testing & Quality:**
- **TESTING.md**: Testing guide
- **TEST_COVERAGE_IMPROVEMENTS.md**: Test coverage improvement plans

**Architecture & Models:**
- **ARCHITECTURE.md**: Application architecture with service layer (✅ **NEW**)
- **ARCHITECTURAL_REFACTORING.md**: Refactoring suggestions
- **STORY_MODEL_STANDARDIZATION.md**: Story model standardization
- **stories/STORY_JSON_SCHEMA.md**: Story JSON schema
- **SERVICE_LAYER_IMPLEMENTATION.md**: Service layer implementation guide
- **SERVICE_INTEGRATION_SUMMARY.md**: Service integration summary

## Current Structure

The project follows a layered architecture:

```
src/shortstory/
├── api/                      # HTTP Layer
│   ├── routes.py            # Route handlers (thin wrappers)
│   └── helpers.py           # API helper functions
│
├── services/                 # Service Layer (Business Logic) ✅ NEW
│   ├── story_validation_service.py    # Input validation
│   ├── story_export_service.py        # Export operations
│   ├── job_service.py                 # Background jobs
│   └── story_service.py                # CRUD operations
│
├── pipeline.py              # Story Generation Pipeline
│
├── providers/               # LLM Provider Layer
│   ├── factory.py           # Provider factory
│   └── gemini.py           # Gemini provider implementation
│
└── utils/                   # Utility Layer
    ├── repository.py        # Storage abstraction
    ├── db_storage.py        # Database storage
    ├── storage.py           # File storage
    ├── validation.py        # Distinctiveness validation
    ├── word_count.py        # Word count validation
    └── ...                  # Other utilities
```

## Future Structure

Additional services will be added after pipeline refactoring:

```
src/shortstory/services/
├── story_generation_service.py    # Pipeline orchestration (planned)
└── story_revision_service.py      # Revision orchestration (planned)
```

