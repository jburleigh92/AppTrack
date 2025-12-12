# Job Application Tracker - Architecture Documentation

**Version:** 1.0  
**Last Updated:** December 10, 2025  
**Status:** Complete Architecture Specification

---

## Overview

This package contains the complete architecture documentation for the Job Application Tracker system - a personal productivity tool that helps job seekers manage their application pipeline through automated data capture, intelligent organization, and AI-powered resume-job matching.

---

## Document Structure

### 01-product-scope.md
**Complete product definition and scope**
- Executive summary
- Core features (MVP)
- System constraints
- Out of scope items
- Success criteria
- Use cases

### 02-api-contract.md
**Complete API and integration contracts**
- All REST endpoints with request/response schemas
- Authentication requirements
- Error handling standards
- Integration contracts (browser extension, email service, workers)
- Idempotency guarantees

### 03-error-handling.md
**Exhaustive error handling and fallback behaviors**
- Error severity classification
- Complete error catalogue (100+ error conditions)
- Mandatory fallback rules for every error
- Retry policies with backoff schedules
- Safe default values
- Data consistency guarantees
- Catastrophic failure protocols

### 04-module-decomposition.md
**System module architecture**
- Layered architecture overview
- Complete module breakdown by layer:
  - API Layer (routes, middleware, schemas)
  - Domain Service Layer (business logic)
  - Data Access Layer (repositories, ORM)
  - Worker Layer (scraper, parser, analysis)
  - Integration Layer (browser extension, email service)
  - Infrastructure Layer (config, logging, storage)
- Module dependencies
- System behavior mapping

### 05-development-milestones.md
**Implementation roadmap and milestones**
- 9 detailed milestones (M1-M9)
- Each milestone includes:
  - Purpose and deliverables
  - Acceptance criteria
  - Dependencies
  - Estimated effort (24-33 days total)
- Critical path analysis
- Parallelization opportunities
- Risk mitigation strategies

---

## System Architecture Summary

### Technology Stack
- **Backend:** FastAPI (Python 3.11+)
- **Database:** PostgreSQL 14+
- **Queue:** PostgreSQL tables (job queues)
- **Workers:** Python processes (scraping, parsing, analysis)
- **Browser Extension:** JavaScript (Chrome Extension APIs)
- **Email Service:** Python with imaplib

### Core Components

**Data Capture:**
- Browser extension captures applications from job boards
- Email service monitors inbox for confirmation emails
- Manual entry via dashboard

**Background Processing:**
- Scraper workers retrieve job posting content (HTML + structured data)
- Parser workers extract resume data from PDF/DOCX/TXT files
- Analysis workers match resume against job posting using LLM

**User Interface:**
- REST API for all operations
- Timeline events for audit trail
- Export to CSV/JSON

### Key Design Principles

1. **Single-user local application** - No multi-tenancy, localhost-only
2. **Async processing mandatory** - Never block user-facing requests
3. **Fail gracefully** - Partial success better than total failure
4. **Isolate failures** - Worker failures don't cascade
5. **Deterministic behavior** - Same error produces same behavior

---

## Implementation Guide

### Recommended Reading Order

1. **Start with 01-product-scope.md**
   - Understand what the system does and doesn't do
   - Review core features and constraints

2. **Read 04-module-decomposition.md**
   - Understand system architecture and module boundaries
   - See how components interact

3. **Reference 02-api-contract.md**
   - Use as specification during implementation
   - Verify all endpoints and schemas

4. **Study 03-error-handling.md**
   - Understand error scenarios before implementing
   - Reference fallback rules during development

5. **Follow 05-development-milestones.md**
   - Implement milestones in order (M1 → M9)
   - Use acceptance criteria to verify completion

### Development Phases

**Phase 1: Foundation (Week 1)**
- M1: Database + Migrations (2-3 days)
- M2: Core Backend Scaffolding (3-4 days)

**Phase 2: Capture Pipelines (Week 2)**
- M3: Browser Capture (2-3 days)
- M4: Email Ingestion (2-3 days)

**Phase 3: Background Processing (Week 3-4)**
- M5: Scraper Service (4-5 days)
- M6: Resume Management (3-4 days)

**Phase 4: AI Analysis (Week 4-5)**
- M7: AI Analysis (3-4 days)

**Phase 5: Integration & Polish (Week 5-6)**
- M8: Timeline System (2-3 days)
- M9: Export + Polish (3-4 days)

**Total: 5-7 weeks for solo developer working full-time**

---

## Key Features

### Automated Data Capture
- **Browser Extension:** Detects application submissions on LinkedIn, Indeed, Greenhouse, Lever
- **Email Monitoring:** Polls IMAP inbox for confirmation emails with pattern detection
- **Duplicate Detection:** Prevents duplicate applications (company+title+date or URL matching)

### Background Processing
- **Web Scraping:** Retrieves full job posting content with rate limiting (10 req/min per domain)
- **Resume Parsing:** Extracts structured data from PDF, DOCX, TXT files
- **AI Analysis:** Matches resume against job using LLM (match score 0-100, qualifications, suggestions)

### Data Management
- **Timeline Events:** Complete audit trail of all application lifecycle events
- **Status Tracking:** Update application status (applied → screening → interview → offer)
- **Notes:** Markdown-supported notes (max 10K chars) per application
- **Export:** Download all applications as CSV or JSON

### Error Resilience
- **Graceful Degradation:** Partial success better than total failure
- **Retry Policies:** Exponential backoff for transient errors (1m, 5m, 15m)
- **Idempotency:** Email UID tracking prevents duplicate processing
- **Fallback Values:** "Unknown Company/Position" with needs_review flag

---

## Architecture Highlights

### Async Processing
All long-running operations (scraping, parsing, analysis) are async:
- API returns 201/202 immediately
- Background workers poll queue and process jobs
- Results reported via internal callback API
- Timeline events created on completion/failure

### Queue Management
- **Priority levels:** Manual=100, Browser=50, Email=25, Auto=0
- **Retry policies:** Configurable max attempts and backoff
- **Worker isolation:** Separate processes for scraper, parser, analysis
- **Watchdog monitoring:** Detects stuck jobs (processing > 5 min)

### Data Consistency
- **Optimistic locking:** Prevents lost updates (check updated_at)
- **Foreign key cascades:** Clean deletion of related records
- **Active resume constraint:** Database enforces single active resume
- **Transaction atomicity:** All-or-nothing for multi-step operations

### Error Handling
- **100+ error scenarios documented** with explicit fallback behavior
- **Severity levels:** CRITICAL, HIGH, MEDIUM, LOW
- **Retry vs permanent errors:** Timeout retries, 404 fails permanently
- **Timeline events:** User-visible failures logged in timeline

---

## Testing Strategy

### Unit Tests
- Domain services with mocked repositories
- Validators and normalizers
- Retry policies and backoff calculations

### Integration Tests
- API endpoints with real database
- Worker end-to-end with mocked HTTP/LLM
- Queue operations with database
- Timeline event creation

### End-to-End Tests
- Complete flows: Browser capture → scraping → analysis
- Error scenarios: Worker crash, retry exhaustion, duplicate detection
- Idempotency: Email UID, worker callbacks

---

## Deployment

### Local Development
```bash
# Install PostgreSQL 14+
# Create database and user
# Copy .env.example to .env and configure

# Run migrations
alembic upgrade head

# Start backend
uvicorn app.main:app --reload

# Start workers (separate terminals)
python -m app.workers.scraper_worker
python -m app.workers.parser_worker
python -m app.workers.analysis_worker
python scripts/email_service.py
python scripts/watchdog.py
```

### Production Deployment
- Use systemd services for all processes
- Configure PostgreSQL with connection pooling
- Set up log rotation
- Monitor health check endpoint (/health)
- Configure email IMAP with app password
- Store LLM API key in environment variable

---

## API Endpoints Summary

**Public Endpoints:**
- Applications: CRUD, status updates, notes, triggers
- Capture: Browser extension, email ingestion
- Resumes: Upload, list, retrieve data
- Analysis: View results, trigger analysis
- Timeline: View events, add manual events
- Queue: Monitor status
- Settings: Get/update configuration
- Export: CSV, JSON

**Internal Endpoints (Workers Only):**
- /internal/scraper/results
- /internal/parser/results
- /internal/analysis/results

---

## Database Schema

**12 Tables:**
- applications (main entity)
- job_postings, scraped_postings (job data)
- resumes, resume_data (resume data)
- analysis_results (AI analysis)
- timeline_events (audit trail)
- scraper_queue, parser_queue, analysis_queue (job queues)
- processed_email_uids (email idempotency)
- settings (singleton configuration)

**28+ Indexes:**
- Primary keys, foreign keys
- Compound indexes for queries
- Partial indexes (active resume)
- Full-text search (GIN)
- JSONB indexes

---

## Contributing

This is a complete architecture specification ready for implementation. To contribute:

1. Follow the module decomposition strictly
2. Implement milestones in order (M1 → M9)
3. Reference API contract for all endpoints
4. Follow error handling specification for all errors
5. Add unit and integration tests for all modules
6. Update documentation for any changes

---

## License

Architecture documentation for personal job application tracker system.

---

## Contact

For questions about this architecture, refer to the individual document sections or the complete conversation transcript that generated these documents.

---

**Document Package Version:** 1.0  
**Generated:** December 10, 2025  
**Total Pages:** ~200+ pages of detailed architecture
