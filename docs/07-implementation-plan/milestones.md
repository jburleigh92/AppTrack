# Job Application Tracker - Development Milestones

**Document Version:** 1.0  
**Last Updated:** December 10, 2025  
**Status:** Final Implementation Plan

---

## Table of Contents

1. [Milestone Overview](#milestone-overview)
2. [M1: Database + Migrations](#m1-database--migrations)
3. [M2: Core Backend Scaffolding](#m2-core-backend-scaffolding)
4. [M3: Browser Capture Pipeline](#m3-browser-capture-pipeline)
5. [M4: Email Ingestion Pipeline](#m4-email-ingestion-pipeline)
6. [M5: Scraper Service](#m5-scraper-service)
7. [M6: Resume Management](#m6-resume-management)
8. [M7: AI Analysis](#m7-ai-analysis)
9. [M8: Timeline System](#m8-timeline-system)
10. [M9: Export + Polish](#m9-export--polish)
11. [Critical Path Summary](#critical-path-summary)

---

## Milestone Overview

| Milestone | Estimated Days | Dependencies | Risk Level |
|-----------|---------------|--------------|------------|
| M1: Database + Migrations | 2-3 | None | Low |
| M2: Core Backend | 3-4 | M1 | Low |
| M3: Browser Capture | 2-3 | M2 | Low |
| M4: Email Ingestion | 2-3 | M2 | Medium |
| M5: Scraper Service | 4-5 | M2 | Medium |
| M6: Resume Management | 3-4 | M2, M5 patterns | Medium |
| M7: AI Analysis | 3-4 | M5, M6 | Medium |
| M8: Timeline System | 2-3 | M3-M7 | Low |
| M9: Export + Polish | 3-4 | M1-M8 | Low |

**Total: 24-33 days (5-7 weeks solo developer)**

---

## M1: Database + Migrations

### Purpose
Establish foundational data layer with complete schema, migration tooling, and validated constraints.

### Key Deliverables

1. **PostgreSQL Setup**
   - Install PostgreSQL 14+
   - Create database and user
   - Configure connection pooling

2. **SQLAlchemy Configuration**
   - db.base module with Base class
   - db.session module with engine
   - get_db() dependency

3. **Alembic Setup**
   - Initialize Alembic
   - Configure auto-generation
   - Create migration script template

4. **ORM Models (all 12 tables)**
   - applications, job_postings, scraped_postings
   - resumes, resume_data
   - analysis_results, timeline_events
   - scraper_queue, parser_queue, analysis_queue
   - processed_email_uids, settings

5. **Indexes and Constraints**
   - All 28+ indexes
   - FK relationships with CASCADE
   - CHECK constraints
   - Partial unique index (active resume)
   - ENUM types

6. **Initial Migration**
   - Generate migration
   - Add custom SQL (triggers, indexes)
   - Insert settings default row

7. **Validation Scripts**
   - Verify schema completeness
   - Test constraints
   - Test migrations forward/backward

### Acceptance Criteria
✅ All tables created with correct types
✅ All indexes exist
✅ All constraints enforced
✅ Migrations run cleanly
✅ Connection pooling works
✅ Settings singleton exists

---

## M2: Core Backend Scaffolding

### Purpose
Establish FastAPI framework with complete infrastructure, error handling, and basic application CRUD.

### Key Deliverables

1. **FastAPI Bootstrap**
   - main.py with app instance
   - CORS middleware
   - Health check endpoint
   - Startup/shutdown handlers

2. **Configuration**
   - Pydantic Settings
   - Load from .env
   - Validate required fields
   - .env.example

3. **Structured Logging**
   - JSON and text formatters
   - Context processor
   - Log sanitization
   - Configure third-party libs

4. **Error Handling**
   - Global exception handler
   - Map exceptions to status codes
   - Standard error envelope
   - Custom exception classes

5. **Pydantic Schemas**
   - ErrorResponse, PaginationMetadata
   - ApplicationCreate, ApplicationResponse
   - Field validators

6. **Application Repository**
   - CRUD operations
   - List with pagination/filters
   - Duplicate detection queries
   - Optimistic locking

7. **Application Service**
   - Create with defaults
   - Update status/notes
   - Soft delete
   - Business rule validation

8. **Application API Routes**
   - POST /applications
   - GET /applications (list)
   - GET /applications/{id}
   - PATCH /applications/{id}/status
   - PATCH /applications/{id}/notes
   - DELETE /applications/{id}

9. **Authentication Middleware**
   - verify_internal_token()
   - Skip for public endpoints

10. **Development Tooling**
    - pyproject.toml with deps
    - black, ruff, mypy config
    - run_dev.sh script

### Acceptance Criteria
✅ FastAPI starts on localhost:8000
✅ Health check returns 200
✅ Settings loaded from .env
✅ Logging outputs JSON/text
✅ Error handler catches exceptions
✅ Application CRUD works
✅ Pagination works
✅ Filtering/sorting works
✅ Optimistic locking prevents lost updates
✅ OpenAPI docs at /docs

---

## M3: Browser Capture Pipeline

### Purpose
Implement browser extension capture flow with duplicate detection and URL normalization.

### Key Deliverables

1. **Text Normalizer**
   - normalize_for_comparison()
   - normalize_company_name()
   - normalize_job_title()

2. **URL Normalizer**
   - normalize_url()
   - remove_tracking_params()
   - validate_url_format()

3. **Duplicate Detector**
   - check_duplicate()
   - find_by_company_title_date()
   - find_by_url()
   - rank_duplicates()

4. **Capture Schemas**
   - BrowserCaptureRequest
   - BrowserCaptureResponse
   - DuplicateDetectedResponse

5. **Capture API Route**
   - POST /capture/browser
   - Duplicate detection
   - force_create override
   - Safe defaults
   - needs_review flag

6. **Queue Manager Stub**
   - enqueue_scraper_job() stub
   - enqueue_parser_job() stub
   - enqueue_analysis_job() stub

7. **Timeline Service Stub**
   - create_event() stub
   - list_events() stub

8. **Integration Tests**
   - Create application success
   - Detect duplicate (company+title+date)
   - Detect duplicate (URL)
   - Override with force_create
   - Apply safe defaults

### Acceptance Criteria
✅ Normalizers work correctly
✅ Duplicate detection accurate
✅ POST /capture/browser creates application
✅ 409 returned for duplicates
✅ force_create bypasses check
✅ Safe defaults applied
✅ needs_review flag set appropriately

---

## M4: Email Ingestion Pipeline

### Purpose
Implement email monitoring service with IMAP polling, parsing, and idempotency.

### Key Deliverables

1. **Email UID Repository**
   - is_processed()
   - mark_processed()
   - cleanup_old_uids()

2. **Email Deduplicator**
   - check_processed()
   - record_processed()
   - handle_duplicate()

3. **Email Capture Route**
   - POST /capture/email
   - Require internal auth
   - Check UID processed
   - Record UID atomically

4. **Email Capture Schema**
   - EmailCaptureRequest
   - EmailCaptureResponse

5. **Email Service - IMAP Client**
   - connect(), disconnect()
   - poll_inbox() main loop
   - fetch_unread_emails()
   - mark_as_read()

6. **Email Service - Pattern Detection**
   - Subject patterns
   - Sender domain patterns
   - Body keyword matching
   - Confidence scoring
   - Fallback extraction

7. **Email Service - API Integration**
   - POST to /capture/email
   - Handle responses (201, 200 skipped, 4xx, 5xx)
   - Retry logic with backoff

8. **Email Service - Configuration**
   - Load from settings
   - Validate required fields

9. **Error Handling**
   - IMAP connection failure
   - IMAP auth failure
   - Parsing fallback
   - Backend unavailable

10. **Standalone Script**
    - scripts/email_service.py
    - Signal handlers
    - Graceful shutdown

### Acceptance Criteria
✅ EmailUIDRepository enforces unique constraint
✅ POST /capture/email creates application
✅ Idempotency: same UID returns 200 skipped
✅ Email parsing detects patterns
✅ Fallback extraction works
✅ needs_review set for low confidence
✅ EmailService connects to IMAP
✅ Polls every 5 minutes
✅ POSTs to backend
✅ Handles errors with retry

---

## M5: Scraper Service

### Purpose
Implement complete web scraping pipeline with queue management, HTTP client, content extraction, and result processing.

### Key Deliverables

1. **Queue Repository**
   - enqueue/dequeue for all queue types
   - FOR UPDATE SKIP LOCKED
   - Update job status
   - Query metrics

2. **Job Posting Repository**
   - create_scraped_posting()
   - create_job_posting()
   - get_recent_scrape()

3. **Queue Manager Implementation**
   - Replace stubs with full logic
   - Priority levels
   - Transaction handling

4. **Retry Policy**
   - should_retry()
   - calculate_backoff()
   - is_permanent_error()

5. **HTTP Client**
   - get() with timeout
   - Follow redirects
   - Handle errors
   - Stream large responses

6. **Rate Limiter**
   - check_rate_limit()
   - record_request()
   - Sliding window (10 req/min)

7. **Content Extractor**
   - extract() main method
   - detect_job_board()
   - Board-specific extraction
   - Generic fallback

8. **Scraper Worker**
   - run() main loop
   - poll_queue()
   - process_job()
   - check_recent_scrape()
   - scrape_url()
   - report_success/failure()

9. **Scraper Result Processor**
   - process_success()
   - process_failure()
   - Link posting to application
   - Create timeline event
   - Trigger analysis if auto

10. **Internal Scraper Route**
    - POST /internal/scraper/results
    - Require auth
    - Process callback

11. **Queue Status Routes**
    - GET /queue/scraper
    - GET /queue/scraper/jobs/{id}

12. **Scraper Trigger Route**
    - POST /applications/{id}/scrape

13. **Worker Script**
    - scripts/scraper_worker.py

### Acceptance Criteria
✅ Queue dequeues with row lock
✅ Rate limiter enforces 10 req/min
✅ HTTP client handles all error types
✅ Content extractor parses job boards
✅ Scraper worker polls and processes
✅ Deduplication prevents duplicate scrapes
✅ Result processor updates application
✅ Timeline events created
✅ Auto-analysis triggered if enabled
✅ Worker handles graceful shutdown

---

## M6: Resume Management

### Purpose
Implement resume upload, parsing, and active resume enforcement.

### Key Deliverables

1. **File Storage**
   - save_file() with UUID
   - Set permissions (chmod 600)
   - check_disk_space()

2. **Resume Repository**
   - create(), update_status()
   - get_active_resume()
   - archive_resume(), activate_resume()
   - create_resume_data()

3. **Resume Service**
   - create_resume()
   - get_active_resume()
   - archive_and_activate()

4. **Resume Schemas**
   - ResumeUploadResponse
   - ResumeListItem
   - ResumeDataResponse

5. **Resume Routes**
   - POST /resumes/upload
   - GET /resumes
   - GET /resumes/{id}
   - GET /resumes/{id}/data

6. **PDF Parser**
   - parse() extract text
   - detect_encrypted()
   - detect_scanned()

7. **DOCX Parser**
   - parse() extract text
   - handle_corruption()

8. **Text Parser**
   - parse() with encoding detection
   - Try UTF-8→Latin-1→CP1252

9. **Section Detector**
   - detect_sections()
   - parse_contact_info()
   - parse_experience()
   - parse_education()
   - parse_skills()

10. **Parser Worker**
    - run() main loop
    - poll_queue() FIFO
    - process_job()
    - parse_file()
    - report_success/failure()

11. **Parser Result Processor**
    - process_success()
    - process_failure()
    - Archive old active resume
    - Activate new resume

12. **Internal Parser Route**
    - POST /internal/parser/results

13. **Worker Script**
    - scripts/parser_worker.py

### Acceptance Criteria
✅ File upload validates size/format
✅ Files saved with correct permissions
✅ PDF parser extracts text
✅ Section detector identifies sections
✅ Parser worker polls and processes
✅ Active resume constraint enforced
✅ Previous active archived
✅ New resume activated
✅ No retry for parsing failures

---

## M7: AI Analysis

### Purpose
Implement AI-powered resume-job matching with LLM integration.

### Key Deliverables

1. **Secrets Manager Stub**
   - get_secret() from env var

2. **Analysis Repository**
   - create(), get_by_id()
   - get_for_application()

3. **Analysis Validator**
   - validate_match_score()
   - validate_qualifications()
   - validate_required_fields()

4. **Prompt Builder**
   - build_prompt()
   - format_job_posting()
   - format_resume()
   - truncate_content()

5. **LLM Client**
   - generate_analysis()
   - call_openai()
   - call_anthropic()
   - parse_response()

6. **Response Parser**
   - parse_json()
   - strip_markdown_fences()
   - validate_schema()

7. **Analysis Worker**
   - run() main loop
   - poll_queue()
   - validate_preconditions()
   - fetch_data()
   - generate_analysis()
   - report_success/failure()

8. **Analysis Result Processor**
   - process_success()
   - process_failure()
   - Link analysis to application
   - Create timeline event

9. **Internal Analysis Route**
   - POST /internal/analysis/results

10. **Analysis Schemas**
    - AnalysisResultResponse

11. **Analysis Routes**
    - GET /analysis-results/{id}
    - GET /applications/{id}/analyses

12. **Analysis Trigger Route**
    - POST /applications/{id}/analyze

13. **Auto-Analysis Trigger**
    - Update scraper processor
    - Check auto_analyze setting

14. **Settings Integration**
    - LLM config in settings
    - Validate API key on update

15. **Worker Script**
    - scripts/analysis_worker.py

### Acceptance Criteria
✅ Prompt builder constructs valid prompt
✅ LLM client calls OpenAI/Anthropic
✅ Response parser extracts JSON
✅ Analysis worker polls and processes
✅ Preconditions validated
✅ Result processor updates application
✅ Timeline events created
✅ Auto-analysis triggers after scraping
✅ Settings validate LLM API key

---

## M8: Timeline System

### Purpose
Implement complete timeline event system across all services and workers.

### Key Deliverables

1. **Timeline Repository**
   - create_event()
   - list_events()
   - Filter by event_type

2. **Timeline Validator**
   - validate_event_type()
   - validate_event_data()
   - validate_manual_event()

3. **Timeline Service Implementation**
   - Replace stubs
   - Helper methods for each event type
   - Graceful error handling

4. **Timeline Schemas**
   - TimelineEventResponse
   - ManualEventRequest

5. **Timeline Routes**
   - GET /applications/{id}/timeline
   - POST /applications/{id}/timeline/events

6. **Integration in Services**
   - application_service: status_changed, note_updated
   - capture routes: application_submitted, email_received
   - scraper processor: job_scraped, job_scraped_failed
   - analysis processor: analysis_completed, analysis_failed

7. **Event Data Standards**
   - Document schemas for each event type

8. **Best Effort Error Handling**
   - Timeline failures don't block primary ops
   - Log errors appropriately

9. **Application Detail Enhancement**
   - Include recent timeline events

### Acceptance Criteria
✅ Timeline service creates events
✅ Validation works for all event types
✅ Timeline routes work
✅ All services create timeline events
✅ Scraper/parser/analysis create events
✅ Manual events work
✅ Timeline failures handled gracefully
✅ Event_data schemas documented

---

## M9: Export + Polish

### Purpose
Complete system with export, observability, and production readiness.

### Key Deliverables

1. **Settings Repository**
   - get_settings()
   - update_settings()
   - Deep merge JSONB

2. **Settings Service**
   - get_settings()
   - update_settings()
   - Validate email config
   - Validate LLM config

3. **Email Validator**
   - validate_config()
   - Test IMAP connection

4. **LLM Validator**
   - validate_api_key()
   - Test with minimal prompt

5. **Settings Routes**
   - GET /settings
   - PATCH /settings

6. **Export Service**
   - export_applications_csv()
   - export_applications_json()

7. **Export Routes**
   - GET /export/applications.csv
   - GET /export/applications.json

8. **Health Check Enhancement**
   - check_database()
   - check_disk_space()
   - check_queue_health()

9. **Health Check Route**
   - Update GET /health with components

10. **Watchdog Service**
    - run() periodic check
    - check_stuck_jobs()
    - mark_stuck_jobs_failed()

11. **Watchdog Script**
    - scripts/watchdog.py

12. **Cleanup Jobs**
    - scripts/cleanup.py
    - Functions for each cleanup task

13. **Logging Enhancement**
    - Request ID middleware
    - Request/response logging
    - Correlation IDs

14. **Observability**
    - Define metrics to collect
    - Document Prometheus format
    - Placeholder /metrics endpoint

15. **Error Recovery Docs**
    - Recovery procedures
    - Operator runbook

16. **Deployment Docs**
    - Deployment checklist
    - Systemd service files
    - Monitoring recommendations

17. **Code Quality**
    - Run black, ruff, mypy
    - Add docstrings
    - Remove debug code

18. **Documentation**
    - Update README
    - Create CHANGELOG
    - Update inline comments

### Acceptance Criteria
✅ Settings management works
✅ Email/LLM validation works
✅ Export CSV/JSON works
✅ Health check shows components
✅ Watchdog detects stuck jobs
✅ Cleanup script works
✅ Request/response logging
✅ Code formatted and linted
✅ Documentation complete
✅ End-to-end tests pass

---

## Critical Path Summary

### Foundation (Must Complete First)
1. **M1: Database** - Blocks ALL
2. **M2: Core Backend** - Blocks M3-M9

### Feature Tracks (Can Parallelize)
3. **M3: Browser Capture** - Independent
4. **M4: Email Ingestion** - Independent
5. **M5: Scraper Service** - Blocks M7
6. **M6: Resume Management** - Blocks M7

### Integration (Sequential)
7. **M7: AI Analysis** - Requires M5, M6
8. **M8: Timeline System** - Requires M3-M7
9. **M9: Export + Polish** - Requires M1-M8

### Optimal Execution Order

**Week 1:** M1 (2-3 days) + M2 (3-4 days)

**Week 2:** M3 (2-3 days) + M4 (2-3 days)

**Week 3-4:** M5 (4-5 days) + M6 (3-4 days) - overlap after M5 patterns established

**Week 4-5:** M7 (3-4 days) - after M5 and M6 complete

**Week 5-6:** M8 (2-3 days) + M9 (3-4 days)

**Total: 5-7 weeks for solo developer**

### Parallelization Opportunities

**Can Run in Parallel:**
- M3 + M4 (both capture, independent)
- M5 + M6 (after queue patterns from M5)

**Must Be Sequential:**
- M1 → M2 (foundation)
- M2 → M3, M4, M5, M6 (all depend on core)
- M5, M6 → M7 (analysis needs both)
- M3-M7 → M8 (timeline integrates all)
- M8 → M9 (export includes timeline)

### Risk Mitigation

**High-Risk Areas:**
1. M5 Scraping: HTML changes, rate limits, CAPTCHA
   - Mitigation: Store raw HTML, manual fallback

2. M6 Resume Parsing: Scanned PDFs, formats
   - Mitigation: Encoding fallbacks, needs_review flag

3. M7 LLM Integration: Rate limits, cost, invalid responses
   - Mitigation: Retry policies, validation, graceful failure

**Medium-Risk Areas:**
1. M4 Email Parsing: Non-standard formats
   - Mitigation: Fallback rules, needs_review flag

2. M3 Duplicate Detection: False positives
   - Mitigation: User override, confidence ranking

---

**End of Development Milestones**
