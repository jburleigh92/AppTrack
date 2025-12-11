# Repository Structure

This document provides a full, detailed breakdown of the AppTrack repository.  
It reflects the backend service, browser extension, and the complete documentation set.

---

## Top-Level Structure

```
AppTrack/
├── backend/  
├── extension/  
└── docs/  
```

Each section is expanded in detail below.

---

# 1. Backend Structure (`backend/`)

```

backend/
├── app/
│   ├── **init**.py
│   ├── main.py                          # FastAPI application entry point
│   │
│   ├── api/                             # API layer (routes, dependencies, error handlers)
│   │   ├── **init**.py
│   │   ├── routes/
│   │   │   ├── **init**.py              # Router aggregator
│   │   │   ├── applications.py          # Application resource endpoints
│   │   │   ├── job_postings.py          # Job posting resource endpoints
│   │   │   ├── resumes.py               # Resume upload and management endpoints
│   │   │   ├── analysis.py              # Analysis results endpoints
│   │   │   ├── timeline.py              # Timeline events endpoints
│   │   │   ├── queue.py                 # Queue status endpoints
│   │   │   ├── settings.py              # Settings management endpoints
│   │   │   ├── capture.py               # Browser/email capture endpoints
│   │   │   └── internal.py              # Internal worker callback endpoints
│   │   │
│   │   ├── dependencies/
│   │   │   ├── **init**.py
│   │   │   ├── auth.py                  # Authentication dependencies (future)
│   │   │   └── database.py              # Database session dependency
│   │   │
│   │   └── error_handlers/
│   │       ├── **init**.py              # Exception handler registration
│   │       └── handlers.py              # Custom exception handler implementations
│   │
│   ├── core/                            # Core configuration and utilities
│   │   ├── **init**.py
│   │   ├── config.py                    # Application settings (Pydantic BaseSettings)
│   │   ├── security.py                  # Security utilities (CSRF, tokens, etc.)
│   │   └── logging.py                   # Structured logging configuration
│   │
│   ├── db/                              # Database layer
│   │   ├── **init**.py
│   │   ├── base.py                      # SQLAlchemy declarative base
│   │   ├── session.py                   # Database engine and session factory
│   │   ├── models/
│   │   │   ├── **init**.py
│   │   │   ├── application.py           # Application model
│   │   │   ├── job_posting.py           # Job posting and scraped posting models
│   │   │   ├── resume.py                # Resume and parsed resume data models
│   │   │   ├── analysis.py              # Analysis results model
│   │   │   ├── timeline.py              # Timeline events model
│   │   │   ├── queue.py                 # Queue models (scraper, parser, analysis)
│   │   │   ├── email.py                 # Processed email UID model
│   │   │   └── settings.py              # Settings model
│   │   │
│   │   └── migrations/
│   │       ├── env.py                   # Alembic environment configuration
│   │       └── versions/                # Migration version files
│   │
│   ├── schemas/                         # Pydantic request/response schemas
│   │   ├── **init**.py
│   │   ├── application.py
│   │   ├── job_posting.py
│   │   ├── resume.py
│   │   ├── analysis.py
│   │   ├── timeline.py
│   │   ├── queue.py
│   │   ├── settings.py
│   │   └── common.py                    # Standard pagination/error schemas
│   │
│   ├── services/                        # Business logic services
│   │   ├── **init**.py
│   │   ├── application_service.py       # Application CRUD and business logic
│   │   │
│   │   ├── scraping/                    # Web scraping services
│   │   │   ├── **init**.py
│   │   │   ├── scraper.py               # Web scraping operations
│   │   │   └── extractor.py             # HTML/content extraction logic
│   │   │
│   │   ├── parsing/                     # Resume parsing services
│   │   │   ├── **init**.py
│   │   │   ├── pdf_parser.py            # PDF resume parsing
│   │   │   ├── docx_parser.py           # DOCX resume parsing
│   │   │   └── text_parser.py           # Plain-text resume parsing
│   │   │
│   │   └── analysis/                    # AI analysis modules
│   │       ├── **init**.py
│   │       ├── llm_client.py            # OpenAI/Anthropic client wrapper
│   │       └── analyzer.py              # Orchestration of job-vs-resume analysis
│   │
│   └── workers/                         # Background job processors
│       ├── **init**.py
│       ├── scraper_worker.py            # Scraper queue worker
│       ├── parser_worker.py             # Resume parser worker
│       └── analysis_worker.py           # Analysis computation worker
│
├── alembic.ini                          # Alembic migration config
├── pyproject.toml                       # Project dependencies and build system
├── .env.example                         # Example environment settings
└── README.md                            # Backend-specific documentation

```

---

# 2. Browser Extension Structure (`extension/`)

```

extension/
└── (browser extension source code)

```

*NOTE: This section expands as you add UI, messaging, and manifest files.*

---

# 3. Documentation Structure (`docs/`)

```

docs/
├── 01-product/
│   └── README.md
│
├── 02-architecture/
│   ├── README.md
│   ├── flows-and-sequence-diagrams.md
│   └── repository-structure.md          # THIS FILE
│
├── 03-system-design/
│   ├── README.md
│   └── nfr.md                           # Non-functional requirements
│
├── 04-api-contracts/
│   └── README.md
│
├── 05-schemas/
│   ├── README.md
│   └── data-schema-design.md            # Full database schema specification
│
├── 06-modules/
│   └── README.md
│
├── 07-implementation-plan/
│   └── README.md
│
├── 08-testing/
│   └── README.md
│
├── 09-observability/
│   └── README.md
│
├── 10-operations/
│   └── README.md
│
└── 11-prompts/
└── README.md

```
