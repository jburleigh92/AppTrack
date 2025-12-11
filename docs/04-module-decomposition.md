# Job Application Tracker - System Module Decomposition

**Document Version:** 1.0  
**Last Updated:** December 10, 2025  
**Status:** Final Architecture Specification

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [API Layer Modules](#2-api-layer-modules)
3. [Domain Service Layer](#3-domain-service-layer)
4. [Data Access Layer](#4-data-access-layer)
5. [Worker Layer](#5-worker-layer)
6. [Integration Layer](#6-integration-layer)
7. [Infrastructure Layer](#7-infrastructure-layer)
8. [Module Dependency Graph](#8-module-dependency-graph)
9. [System Behavior Mapping](#9-system-behavior-mapping)

---

## 1. Architecture Overview

### Layered Architecture

```
┌────────────────────────────────────────────┐
│        INTEGRATION LAYER                   │
│  Browser Extension │ Email Service │ CLI   │
└────────────────────────────────────────────┘
                    ↓
┌────────────────────────────────────────────┐
│           API LAYER                        │
│  Routes │ Validation │ Response Formatting │
└────────────────────────────────────────────┘
                    ↓
┌────────────────────────────────────────────┐
│        DOMAIN SERVICE LAYER                │
│  Application │ Scraping │ Analysis │ etc.  │
└────────────────────────────────────────────┘
                    ↓
┌────────────────────────────────────────────┐
│        DATA ACCESS LAYER                   │
│  Repositories │ Query Builders │ Txn Mgmt  │
└────────────────────────────────────────────┘
                    ↓
┌────────────────────────────────────────────┐
│        INFRASTRUCTURE LAYER                │
│  Database │ Queue │ Logging │ Config      │
└────────────────────────────────────────────┘
```

**Dependency Rules:**
- Upper layers depend on lower layers
- Lower layers MUST NOT depend on upper layers
- Skip layers discouraged (use adjacent only)

---

## 2. API Layer Modules

### 2.1 api.routes.applications

**Purpose:** HTTP endpoint handlers for application CRUD

**Responsibilities:**
- Accept/validate HTTP requests
- Map requests to service calls
- Format responses into envelopes
- Handle pagination
- Emit audit events

**Non-responsibilities:**
- Business logic (delegate to services)
- Database access (use repositories)
- Queue management (delegate to services)

**Inputs:** HTTP requests (POST, GET, PATCH, DELETE)

**Outputs:** HTTP responses (200, 201, 400, 404, 409, 503)

**Depends on:**
- domain.application_service
- domain.duplicate_detector
- domain.queue_manager
- domain.timeline_service
- api.schemas.application

**Emits:**
- application.created
- application.updated
- application.deleted

### 2.2 api.routes.capture

**Purpose:** Browser extension and email service capture endpoints

**Responsibilities:**
- Handle POST /capture/browser
- Handle POST /capture/email (with auth)
- Apply source-specific validation
- Invoke duplicate detection
- Set needs_review flag
- Coordinate creation with timeline

**Non-responsibilities:**
- DOM parsing (extension does this)
- Email parsing (email service does this)

**Depends on:**
- domain.application_service
- domain.duplicate_detector
- domain.email_deduplicator
- api.middleware.auth

**Emits:**
- application.captured.browser
- application.captured.email
- duplicate.detected

### 2.3 api.routes.internal

**Purpose:** Internal worker callback endpoints

**Responsibilities:**
- Handle scraper result callbacks
- Handle parser result callbacks
- Handle analysis result callbacks
- Validate internal token
- Coordinate result processing

**Non-responsibilities:**
- Job processing (workers do this)
- Queue management (services handle)

**Depends on:**
- domain.scraper_result_processor
- domain.parser_result_processor
- domain.analysis_result_processor
- api.middleware.auth

**Emits:**
- scrape.completed
- parse.completed
- analysis.completed

### 2.4 api.middleware.error_handler

**Purpose:** Global exception handling

**Responsibilities:**
- Catch unhandled exceptions
- Map to HTTP status codes
- Format error responses
- Log errors
- Sanitize error messages

**Non-responsibilities:**
- Error recovery (services do this)

**Depends on:**
- infrastructure.logger
- api.schemas.common

### 2.5 api.middleware.auth

**Purpose:** Authentication middleware

**Responsibilities:**
- Validate internal API token
- Check Authorization header
- Return 401 for invalid
- Skip auth for public endpoints

**Non-responsibilities:**
- User authentication (MVP has none)

**Depends on:**
- infrastructure.config.settings

---

## 3. Domain Service Layer

### 3.1 domain.application_service

**Purpose:** Core business logic for applications

**Responsibilities:**
- Create with validation and defaults
- Update status with timeline
- Update notes with timeline
- Soft-delete
- Apply safe defaults
- Set needs_review flag
- Coordinate with duplicate detector
- Handle optimistic locking

**Non-responsibilities:**
- HTTP handling (API layer)
- Database queries (repositories)

**Depends on:**
- db.repositories.application_repository
- domain.duplicate_detector
- domain.queue_manager
- domain.timeline_service

**Emits:**
- application.created
- application.status_changed

### 3.2 domain.duplicate_detector

**Purpose:** Detect duplicate applications

**Responsibilities:**
- Normalize company and title
- Query duplicates by company+title+date
- Query duplicates by URL
- Rank matches by confidence
- Support force_create override

**Non-responsibilities:**
- User interaction (API layer)
- Database operations (repository)

**Depends on:**
- db.repositories.application_repository
- domain.normalizers.text_normalizer
- domain.normalizers.url_normalizer

**Emits:**
- duplicate.detected

### 3.3 domain.queue_manager

**Purpose:** Central queue management

**Responsibilities:**
- Enqueue scraper/parser/analysis jobs
- Update job status
- Handle retry scheduling
- Check max_attempts
- Query queue metrics
- Detect stuck jobs

**Non-responsibilities:**
- Job processing (workers)
- Result handling (processors)

**Depends on:**
- db.repositories.queue_repository
- domain.retry_policy

**Emits:**
- job.queued
- job.completed
- job.failed

### 3.4 domain.scraper_result_processor

**Purpose:** Process scraper callback results

**Responsibilities:**
- Validate result payload
- Update queue job
- Link posting to application
- Create timeline event
- Trigger analysis if auto_analyze
- Handle deleted applications

**Non-responsibilities:**
- Scraping (worker does this)

**Depends on:**
- db.repositories.application_repository
- db.repositories.queue_repository
- domain.queue_manager
- domain.timeline_service

**Emits:**
- scrape.result_processed
- analysis.auto_triggered

### 3.5 domain.parser_result_processor

**Purpose:** Process parser callback results

**Responsibilities:**
- Validate result payload
- Update queue job
- Update resume status
- Archive previous active resume
- Mark new resume as active
- Handle constraint violations

**Non-responsibilities:**
- Parsing (worker does this)

**Depends on:**
- db.repositories.resume_repository
- db.repositories.queue_repository
- db.transaction_manager

**Emits:**
- parse.result_processed
- resume.activated
- resume.archived

### 3.6 domain.analysis_result_processor

**Purpose:** Process analysis callback results

**Responsibilities:**
- Validate result payload
- Update queue job
- Link analysis to application
- Set analysis_completed flag
- Create timeline event
- Validate analysis data

**Non-responsibilities:**
- Analysis logic (worker)

**Depends on:**
- db.repositories.application_repository
- db.repositories.analysis_repository
- domain.timeline_service
- domain.validators.analysis_validator

**Emits:**
- analysis.result_processed

### 3.7 domain.timeline_service

**Purpose:** Manage timeline events

**Responsibilities:**
- Create events for lifecycle
- Create events for outcomes
- Create events for user actions
- Support manual events
- Query with filtering
- Handle failures gracefully

**Non-responsibilities:**
- Event processing/notification

**Depends on:**
- db.repositories.timeline_repository
- domain.validators.timeline_validator

**Emits:**
- timeline.event_created

### 3.8 domain.email_deduplicator

**Purpose:** Email UID idempotency

**Responsibilities:**
- Check if UID processed
- Record UID after success
- Support multi-account
- Handle race conditions

**Non-responsibilities:**
- Email parsing

**Depends on:**
- db.repositories.email_uid_repository
- db.transaction_manager

**Emits:**
- email.duplicate_detected

### 3.9 domain.retry_policy

**Purpose:** Calculate retry schedules

**Responsibilities:**
- Determine if retryable
- Calculate backoff delay
- Return retry_after timestamp
- Determine when dead

**Non-responsibilities:**
- Queue updates (queue_manager)

**Depends on:**
- infrastructure.config.settings

---

## 4. Data Access Layer

### 4.1 db.repositories.application_repository

**Purpose:** Data access for applications

**Responsibilities:**
- CRUD operations
- List with pagination/filters
- Full-text search
- Query duplicates
- Soft delete
- Optimistic locking
- Eager load relations

**Non-responsibilities:**
- Business logic
- Validation

**Depends on:**
- db.models.application
- db.session

### 4.2 db.repositories.queue_repository

**Purpose:** Data access for queues

**Responsibilities:**
- Enqueue job
- Dequeue with FOR UPDATE SKIP LOCKED
- Update job status
- Query metrics
- Query stuck jobs

**Non-responsibilities:**
- Retry logic
- Job processing

**Depends on:**
- db.models.queue
- db.session

### 4.3 db.repositories.job_posting_repository

**Purpose:** Data access for job postings

**Responsibilities:**
- Create scraped posting
- Create job posting
- Query recent scrapes
- Get with/without HTML

**Non-responsibilities:**
- Content extraction

**Depends on:**
- db.models.job_posting
- db.session

### 4.4 db.repositories.resume_repository

**Purpose:** Data access for resumes

**Responsibilities:**
- Create resume
- Update status
- Query active resume
- Archive resume
- Activate resume
- Create resume data

**Non-responsibilities:**
- Parsing

**Depends on:**
- db.models.resume
- db.session

### 4.5 db.repositories.analysis_repository

**Purpose:** Data access for analyses

**Responsibilities:**
- Create analysis
- Get by ID
- List for application

**Non-responsibilities:**
- Analysis generation

**Depends on:**
- db.models.analysis_result
- db.session

### 4.6 db.repositories.timeline_repository

**Purpose:** Data access for timeline

**Responsibilities:**
- Create event
- List with filters
- Sort by occurred_at

**Non-responsibilities:**
- Event validation

**Depends on:**
- db.models.timeline_event
- db.session

### 4.7 db.session

**Purpose:** Database session management

**Responsibilities:**
- Create engine with pooling
- Create session factory
- Provide get_db() dependency
- Configure pool settings

**Non-responsibilities:**
- Query execution
- Transaction management

**Depends on:**
- infrastructure.config.settings
- SQLAlchemy

### 4.8 db.transaction_manager

**Purpose:** Transaction coordination

**Responsibilities:**
- Begin/commit/rollback
- Retry transient errors
- Apply backoff
- Ensure atomicity

**Non-responsibilities:**
- Business logic

**Depends on:**
- db.session
- infrastructure.logger

---

## 5. Worker Layer

### 5.1 workers.scraper_worker

**Purpose:** Poll and process scraping jobs

**Responsibilities:**
- Poll queue (priority DESC)
- Dequeue with row lock
- Check recent scrape
- Perform HTTP GET
- Extract structured data
- Store HTML and data
- POST results to callback
- Handle retry scheduling
- Respect rate limits

**Non-responsibilities:**
- Result processing (backend)

**Depends on:**
- workers.scraping.http_client
- workers.scraping.content_extractor
- workers.scraping.rate_limiter
- db.repositories

**Emits:**
- scrape.started
- scrape.completed

### 5.2 workers.parser_worker

**Purpose:** Poll and process parsing jobs

**Responsibilities:**
- Poll queue (FIFO)
- Dequeue with row lock
- Read file from disk
- Extract text by format
- Parse sections
- Store structured data
- POST results to callback
- No retry (max_attempts=1)

**Non-responsibilities:**
- Active resume management (backend)

**Depends on:**
- workers.parsing.pdf_parser
- workers.parsing.docx_parser
- workers.parsing.text_parser
- workers.parsing.section_detector

**Emits:**
- parse.started
- parse.completed

### 5.3 workers.analysis_worker

**Purpose:** Poll and process analysis jobs

**Responsibilities:**
- Poll queue (priority DESC)
- Validate preconditions
- Fetch posting and resume
- Build prompt
- Call LLM API
- Parse response
- Store analysis
- POST results to callback
- Handle retry scheduling

**Non-responsibilities:**
- Result processing (backend)

**Depends on:**
- workers.analysis.llm_client
- workers.analysis.prompt_builder
- workers.analysis.response_parser

**Emits:**
- analysis.started
- analysis.completed

### 5.4 workers.scraping.http_client

**Purpose:** HTTP client for scraping

**Responsibilities:**
- Perform HTTP GET with timeout
- Follow redirects (max 3)
- Set User-Agent
- Handle errors
- Stream large responses
- Validate Content-Type

**Non-responsibilities:**
- Rate limiting (rate_limiter)
- Content extraction

**Depends on:**
- httpx library

### 5.5 workers.scraping.content_extractor

**Purpose:** Extract data from HTML

**Responsibilities:**
- Parse HTML with BeautifulSoup
- Detect job board
- Extract job-board-specific
- Generic fallback extraction
- Mark extraction_complete

**Non-responsibilities:**
- HTTP requests

**Depends on:**
- BeautifulSoup

### 5.6 workers.scraping.rate_limiter

**Purpose:** Enforce rate limits

**Responsibilities:**
- Track requests per domain
- Enforce 10 req/min limit
- Calculate delays
- Block if exceeded

**Non-responsibilities:**
- HTTP requests

**Depends on:**
- infrastructure.config.settings

### 5.7 workers.parsing.pdf_parser

**Purpose:** Extract text from PDF

**Responsibilities:**
- Open PDF with pdfplumber
- Extract text from pages
- Detect encrypted PDFs
- Detect scanned PDFs

**Non-responsibilities:**
- Section detection

**Depends on:**
- pdfplumber

### 5.8 workers.parsing.section_detector

**Purpose:** Identify resume sections

**Responsibilities:**
- Detect section headers
- Parse experience entries
- Parse education entries
- Extract skills list
- Extract contact info
- Store unrecognized text

**Non-responsibilities:**
- Text extraction

**Depends on:**
- Regular expressions

### 5.9 workers.analysis.llm_client

**Purpose:** Call LLM API

**Responsibilities:**
- Construct API request
- Set parameters
- Send HTTP POST
- Handle authentication
- Handle rate limiting
- Return raw response

**Non-responsibilities:**
- Prompt construction
- Response parsing

**Depends on:**
- httpx
- infrastructure.secrets_manager

### 5.10 workers.analysis.prompt_builder

**Purpose:** Construct prompts

**Responsibilities:**
- Build prompt template
- Format job posting
- Format resume
- Truncate over-long content
- Count tokens

**Non-responsibilities:**
- LLM calls

**Depends on:**
- Token counting library

### 5.11 workers.analysis.response_parser

**Purpose:** Parse LLM responses

**Responsibilities:**
- Parse JSON from response
- Strip markdown fences
- Validate schema
- Handle invalid JSON

**Non-responsibilities:**
- LLM calls

**Depends on:**
- JSON parsing

### 5.12 workers.watchdog

**Purpose:** Monitor stuck jobs

**Responsibilities:**
- Run periodic check
- Query stuck jobs
- Mark failed
- Create timeline events
- Log critical errors

**Non-responsibilities:**
- Job processing

**Depends on:**
- db.repositories.queue_repository
- domain.timeline_service

---

## 6. Integration Layer

### 6.1 integrations.browser_extension

**Purpose:** Chrome extension (separate codebase)

**Responsibilities:**
- Inject content script
- Detect form submission
- Extract from DOM
- POST to /capture/browser
- Queue failed requests
- Show status indicators

**Non-responsibilities:**
- Application storage (backend)

**Depends on:**
- Backend API
- Chrome Extension APIs

### 6.2 integrations.email_service

**Purpose:** IMAP email monitoring

**Responsibilities:**
- Connect to IMAP server
- Poll inbox every 5 minutes
- Parse emails for patterns
- Extract application data
- POST to /capture/email
- Record processed UIDs
- Mark as read

**Non-responsibilities:**
- Application storage (backend)

**Depends on:**
- Backend API
- imaplib

---

## 7. Infrastructure Layer

### 7.1 infrastructure.config.settings

**Purpose:** Configuration management

**Responsibilities:**
- Load from environment
- Load from .env file
- Validate required settings
- Provide typed access
- Use Pydantic

**Non-responsibilities:**
- Runtime changes (via /settings)

**Depends on:**
- Pydantic
- python-dotenv

### 7.2 infrastructure.secrets_manager

**Purpose:** Secure credential storage

**Responsibilities:**
- Store in OS keychain
- Retrieve securely
- Never log credentials
- Support rotation

**Non-responsibilities:**
- Validation

**Depends on:**
- keyring library

### 7.3 infrastructure.file_storage

**Purpose:** File storage abstraction

**Responsibilities:**
- Save file with UUID
- Set permissions (chmod 600)
- Create directories
- Validate disk space
- Support deletion

**Non-responsibilities:**
- Parsing

**Depends on:**
- File system
- infrastructure.config.settings

### 7.4 infrastructure.logger

**Purpose:** Structured logging

**Responsibilities:**
- Initialize logging
- Support JSON/text format
- Log to stdout/stderr
- Include context
- Support log levels
- Sanitize sensitive data

**Non-responsibilities:**
- Log aggregation

**Depends on:**
- Python logging
- infrastructure.config.settings

### 7.5 infrastructure.health_check

**Purpose:** System health monitoring

**Responsibilities:**
- Check database
- Check queue availability
- Check disk space
- Aggregate status
- Return health response

**Non-responsibilities:**
- Remediation

**Depends on:**
- db.session
- infrastructure.file_storage

---

## 8. Module Dependency Graph

### Critical Dependencies

```
api.routes.applications
  → domain.application_service
    → db.repositories.application_repository
      → db.session
        → infrastructure.config.settings

workers.scraper_worker
  → workers.scraping.http_client
  → workers.scraping.content_extractor
  → db.repositories.queue_repository
    → db.session

workers.analysis_worker
  → workers.analysis.llm_client
    → infrastructure.secrets_manager
  → workers.analysis.prompt_builder
  → workers.analysis.response_parser
```

---

## 9. System Behavior Mapping

### Behavior: Browser Capture

**Modules:**
1. integrations.browser_extension - Captures data
2. api.routes.capture - Receives POST
3. domain.application_service - Creates application
4. domain.duplicate_detector - Checks duplicates
5. db.repositories.application_repository - Stores
6. domain.timeline_service - Creates event
7. domain.queue_manager - Enqueues scraper

### Behavior: Web Scraping

**Modules:**
1. workers.scraper_worker - Dequeues job
2. workers.scraping.rate_limiter - Checks limit
3. workers.scraping.http_client - Performs GET
4. workers.scraping.content_extractor - Parses HTML
5. db.repositories.job_posting_repository - Stores
6. api.routes.internal - Receives callback
7. domain.scraper_result_processor - Processes
8. domain.timeline_service - Creates event

### Behavior: AI Analysis

**Modules:**
1. workers.analysis_worker - Dequeues job
2. db.repositories.job_posting_repository - Fetches posting
3. db.repositories.resume_repository - Fetches resume
4. workers.analysis.prompt_builder - Constructs prompt
5. workers.analysis.llm_client - Calls LLM
6. workers.analysis.response_parser - Parses JSON
7. db.repositories.analysis_repository - Stores
8. api.routes.internal - Receives callback
9. domain.analysis_result_processor - Processes
10. domain.timeline_service - Creates event

---

**End of Module Decomposition**
