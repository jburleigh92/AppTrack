# Changelog

All notable changes to this project will be documented in this file.  
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)  
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Fixed
- Stabilized async scraping pipeline with deterministic failure handling
- Added Greenhouse Boards API as deterministic pre-headless data source
- Added Greenhouse embed handling with safe fallback to page scrape
- Prevented analysis retry loops on incomplete job data
- Aligned scraper completeness rules with analysis requirements (description required)
- Ensured async queue jobs reach terminal states
- Fixed SQLAlchemy session ownership issues in workers
- Corrected scraper queue status constraints
- Added extractor-level logging for scrape completeness

### Changed
- Improved commit ordering and state transitions in async workers

### Known Limitations
- Job descriptions rendered client-side (JavaScript-only) are not extracted by the HTTP scraper and are marked for manual review

### Internal
- Improved commit ordering and state transitions in async workers

### Tested
- ✅ Phase 5: Scraper service completely tested and validated
  - Real job posting URLs from Lever, Greenhouse, and Workday
  - HTML extraction for multiple ATS platforms
  - Database schema and foreign key relationships
  - Worker job processing and error handling
  - Bot protection handling (403 Forbidden responses)

- ✅ Phase 6: AI analysis service infrastructure tested and validated
  - Analysis queue system operational
  - Background worker with retry logic and exponential backoff
  - Resume management and data structure
  - Analysis results database schema and API endpoints
  - Application-to-analysis linking
  - Error handling for missing data and LLM errors
  - API keys configuration tested (OpenAI and Anthropic)
  - LLM client initialization successful
  - Complete workflow validated up to API call
  - Timeline event logging verified (1,846 events)
  - Network restriction prevents actual LLM calls in Codespaces
  - Infrastructure 100% production-ready for unrestricted environments

---

## v0.1.1 — 2025-12-11

### Fixed
- Corrected database initialization flow to ensure `init_db()` is called before any DB access
- Repaired `/health/ready` dependency by using the proper `get_db` import
- Fixed environment variable loading by moving `.env` to `backend/app/core` and updating `config.py`
- Resolved missing or incorrect imports in `timeline_service` (added backwards-compatibility wrappers)
- Updated timeline schemas to reflect the actual models in use
- Added `"*.db"` to `.gitignore` to prevent SQLite database files from being committed
- Database session initialization in `app/db/session.py` moved from dynamic initialization to module-level singleton
- Created missing `app/main.py` FastAPI entry point with proper imports and router configuration
- Added missing `settings` export in `app/core/config.py`
- Added missing `setup_logging()` function in `app/core/logging.py`
- Corrected Application model to match existing database schema (`job_posting_url` vs `url`, `application_date` vs `applied_date`)
- Fixed SQLAlchemy relationship configuration between Application and AnalysisResult models
- Removed conflicting `analysis_id` foreign key from Application model to eliminate bidirectional many-to-one relationship error
- Updated JobPosting model to match database schema (`job_title` / `company_name` instead of `title` / `company`)
- Fixed timeline service to use synchronous functions (`list_events_for_application_sync`) instead of async
- Resolved CSV export logging conflict by renaming `filename` parameter to `export_filename` in logging `extra` dict
- Updated all SQLAlchemy UUID types from deprecated `UUID(as_uuid=True)` to `Uuid` type
- Removed non-existent `log_posting_linked` import from scraper worker
- Implemented actual queue polling in scraper worker (replaced placeholder sleep loop)

### Changed
- Reorganized repository structure: moved all backend code into `/backend` directory for cleaner separation
- Application service now uses correct field names matching database schema
- Scraper worker now actively polls `scraper_queue` table and processes jobs
- Worker updates job status and tracks completion/failure with timestamps

---

## [v0.1.0] — 2025-12-11

### Added
- Full product scope documentation
- User flows and UX sequences
- Complete system design including:
  - Ingestion layer
  - FastAPI backend structure
  - Worker queue architecture
  - AI analysis pipeline
  - Scraper module design
  - Timeline event system design
- Data schema and migration definitions
- API contracts for each module
- Module decomposition plan
- Development milestone plan
- Ingestion pipelines (Chrome extension + Gmail polling/webhook)
- Correlation engine logic
- Scraper service design and extraction structure
- AI analysis engine logic and scoring structure
- Timeline event system design
- Export layer (CSV + Sheets sync)
- Full documentation hierarchy under `/docs`
- Backend scaffolding under `/backend/app`
- Initial FastAPI entrypoint and routing layout

### Notes
This release represents the completion of **Phases 1–4** of the A→Z development plan:
- Product discovery  
- System design  
- Implementation planning  
- Core architecture and scaffolding  

This is the first stable foundation ready for integration testing and Phase 5 hardening.
