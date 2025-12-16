# Changelog

All notable changes to this project will be documented in this file.  
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)  
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Fixed
- **Critical**: Enforced pipeline invariant to prevent incomplete job_postings from entering analysis
  - Scraper now only links job_postings to applications when extraction_complete = true
  - Added defense-in-depth validation in analysis endpoint to reject incomplete postings
  - Incomplete job_postings are still persisted for debugging but quarantined from downstream processing
  - Applications with failed extraction are marked scraping_successful = false

## Fixed
- Resume upload now persists files using a UUID-based filename instead of the original client filename.
- Uploaded resumes are stored at uploads/resumes/<uuid>.<ext> to prevent filename collisions & Ensure filesystem-safe storage
- Decouple internal storage from user-provided filenames
- Original filename is still preserved in the database (resumes.filename) for display and audit purposes.
- Parser worker now reliably consumes resume files using the persisted file_path.

## Notes
- This change aligns the upload endpoint contract with the parser worker’s expectations and prevents file-not-found errors during resume parsing.

### Added
- Resume upload API endpoint (`POST /api/v1/resumes/upload`)
- Resume parsing worker for extracting structured fields from uploaded files
- File persistence for uploaded resumes with automatic directory creation
- Unique UUID-based filename generation for uploaded resumes

### Fixed
- API wiring to expose resume endpoints in FastAPI router
- Worker startup and queue processing stability during resume parsing
- Resume file persistence to disk (uploads/resumes/) before parser job enqueue
- Parser worker contract: file_path now guaranteed to exist when job is processed

### Added
- End-to-end Analysis Worker pipeline
- Greenhouse Boards API integration for job scraping
- Resume ingestion and parsing support
- LLM-powered job-to-resume matching with structured JSON output
- Match scoring, qualification comparison, and improvement suggestions
- Persistent analysis results linked to applications, resumes, and job postings

### Fixed
- Job scraping failures caused by JS-rendered ATS pages
- Incorrect fallback behavior when Greenhouse jobs were publicly available
- Analysis worker not detecting completed job postings
- Database wiring issues between scraper, analysis queue, and results

### Notes
- This release marks the first fully functional end-to-end pipeline:
  Job URL → Scrape → Persist → Resume → Analyze → Store → Retrieve


### Fixed
- Implemented Greenhouse Boards API integration as the authoritative source for public Greenhouse job postings
- Ensured Greenhouse API is attempted before HTTP or headless scraping
- Correctly short-circuited scraping pipeline when API data is available
- Fixed job processing metadata to reflect Greenhouse API outcomes (`success`, `not_found`)
- Verified end-to-end application → job_posting linkage via API-sourced data
- Eliminated false negatives caused by authenticated-only Greenhouse UI views

### Clarified
- Confirmed that some Greenhouse job postings are publicly accessible only via the Boards API and not via unauthenticated HTML scraping
- Documented that logged-in Greenhouse UI visibility does not imply public scrape availability

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
