# Job Application Tracker - Product Scope

**Document Version:** 1.0  
**Last Updated:** December 10, 2025  
**Status:** Final Specification

---

## Executive Summary

The Job Application Tracker is a personal productivity tool that helps job seekers manage their application pipeline through automated data capture, intelligent organization, and AI-powered resume-job matching. The system combines browser extension capture, email monitoring, web scraping, and AI analysis to provide a comprehensive view of all job applications in a single dashboard.

**Target User:** Individual job seeker managing 10-100+ applications  
**Deployment Model:** Single-user local application (no network exposure, localhost-only)  
**Core Value Proposition:** Automate application tracking and get AI-powered insights on resume-job fit

---

## System Overview

### What It Does

The Job Application Tracker automatically captures job applications from multiple sources and enriches them with structured data:

1. **Browser Extension Capture:** Detects when user submits application on job boards (LinkedIn, Indeed, Greenhouse, Lever), captures company name, job title, and URL
2. **Email Monitoring:** Polls email inbox for application confirmation emails, extracts application details automatically
3. **Web Scraping:** Retrieves full job posting content from URLs, parses HTML to extract structured data (description, requirements, salary, location)
4. **Resume Parsing:** Uploads resume files (PDF, DOCX, TXT), extracts structured data (contact info, skills, experience, education)
5. **AI Analysis:** Matches resume against job posting using LLM, generates match score (0-100) and qualification assessment
6. **Unified Dashboard:** Single interface to view all applications, track status, view analysis results, and manage pipeline

### What It Doesn't Do

- **Not a job search engine:** Does not find jobs for you
- **Not a multi-user platform:** Single user per installation, no sharing or collaboration
- **Not cloud-hosted:** Runs locally on user's machine, no SaaS deployment
- **Not a cover letter generator:** Focuses on tracking, not application creation
- **Not a networking tool:** No contact management or CRM features in MVP

---

## Core Features (MVP)

### Feature 1: Browser Extension Capture

**Description:** Chrome extension that detects job application submissions on supported job boards and automatically records them in the tracker.

**User Flow:**
1. User browses to job board (LinkedIn, Indeed, Greenhouse, Lever)
2. User fills out application form and clicks "Submit" or "Apply"
3. Extension detects form submission, extracts data from page
4. Extension POSTs data to local backend API
5. User sees confirmation: "Application tracked! View in dashboard"

**Data Captured:**
- Company name (from form or page DOM)
- Job title (from form or page DOM)
- Job posting URL (current page URL)
- Application date (today's date)
- Job board source (for audit trail)

**Duplicate Detection:** If application already exists (same company + title + date within 7 days OR same URL), show modal: "Already tracked. View existing or create anyway?"

**Error Handling:** If backend unavailable, queue request locally in browser storage, retry every 30 seconds (max 3 retries), show offline indicator

### Feature 2: Email Ingestion

**Description:** Background service that monitors email inbox for application confirmation emails and automatically creates application records.

**User Flow:**
1. User configures IMAP settings in tracker (server, username, password, folder)
2. Service polls inbox every 5 minutes (configurable)
3. Service fetches unread emails from target folder
4. Service parses email for application confirmation patterns
5. Service extracts company, job title, URL from email body
6. Service POSTs data to backend API
7. Service marks email as processed (UID tracked for idempotency)

**Email Parsing Patterns:**
- Subject: "Application for", "Your application", "Thank you for applying"
- Sender: Known job boards (greenhouse.io, lever.co, workday.com)
- Body keywords: "position", "application received", "job"

**Confidence Scoring:**
- High confidence (2+ patterns): Create application normally
- Low confidence (1 pattern): Create application with `needs_review=true` flag

**Fallback Extraction:**
- Company: Email body → sender domain → "Company from [domain]"
- Job title: Email subject → body → "Position from [domain]"

**Idempotency:** Email UID recorded in database, prevents duplicate processing even if mark-as-read fails

### Feature 3: Job Posting Scraper

**Description:** Background workers that retrieve full job posting content from URLs and extract structured data.

**User Flow:**
1. Application created with job posting URL (via browser or email)
2. Backend enqueues scraping job in queue
3. Scraper worker dequeues job, performs HTTP GET
4. Worker parses HTML with BeautifulSoup, extracts data
5. Worker stores raw HTML and extracted data in database
6. Worker reports success/failure to backend via callback
7. Backend links job posting to application, creates timeline event

**Data Extracted:**
- Job title (confirmation)
- Company name (confirmation)
- Job description (full text)
- Requirements (parsed section)
- Nice-to-have (parsed section)
- Salary range (if present)
- Location (if present)
- Employment type (full-time, part-time, contract, etc.)

**Supported Job Boards:**
- LinkedIn (specific parsing logic)
- Indeed (specific parsing logic)
- Greenhouse (specific parsing logic)
- Lever (specific parsing logic)
- Generic fallback (best-effort extraction)

**Rate Limiting:** 10 requests per minute per domain (configurable)

**Error Handling:**
- HTTP 404: Mark failed permanently, no retry
- HTTP 403: Mark failed permanently (access denied)
- CAPTCHA detected: Mark failed, user can paste content manually
- Timeout/5xx: Retry with exponential backoff (1m, 5m, 15m)
- Rate limit (429): Retry with longer backoff (5m, 15m, 30m)

**Deduplication:** Check for recent scrape (< 7 days) before HTTP request, reuse existing data if found

### Feature 4: Resume Upload and Parsing

**Description:** Upload resume file, parse into structured data, maintain single active resume.

**User Flow:**
1. User uploads resume file via dashboard (PDF, DOCX, or TXT)
2. Backend validates file (size < 10MB, supported format)
3. Backend saves file to disk with secure permissions
4. Backend enqueues parsing job
5. Parser worker extracts text from file (format-specific parser)
6. Worker detects resume sections (contact, experience, education, skills)
7. Worker stores structured data in database
8. Worker reports success/failure to backend via callback
9. Backend marks new resume as active, archives previous active resume

**Supported Formats:**
- PDF (text-based only, not scanned images)
- DOCX (Microsoft Word)
- TXT (plain text)

**Data Extracted:**
- Contact: Email, phone, location
- Skills: Array of skill keywords
- Experience: Array of {company, title, dates, responsibilities}
- Education: Array of {institution, degree, major, year}
- Certifications: Array of certification names
- Summary: Objective or summary section
- Raw text: Unstructured text if section detection fails

**Active Resume:** Only one resume can be active at a time (enforced by database constraint). When new resume parsed successfully, previous active resume archived.

**Error Handling:**
- Encrypted PDF: Mark failed, notify user "Resume is password protected"
- Scanned PDF: Mark failed, notify user "Resume is scanned image - upload text-based PDF"
- Corrupted file: Mark failed, notify user "File corrupted - upload again"
- Encoding error: Try UTF-8 → Latin-1 → CP1252 fallback
- Section detection failure: Store raw text, mark `extraction_complete=false`

**No Retry:** Parsing failures are permanent (user must re-upload corrected file)

### Feature 5: AI-Powered Resume-Job Matching

**Description:** Automatically analyze resume against job posting using LLM, generate match score and qualification assessment.

**User Flow:**
1. Application has linked job posting (scraped) AND active resume exists
2. User clicks "Analyze" button OR auto-analysis triggers after scraping
3. Backend enqueues analysis job
4. Analysis worker fetches job posting and resume data
5. Worker builds structured prompt for LLM
6. Worker calls LLM API (OpenAI or Anthropic)
7. Worker parses JSON response, validates data
8. Worker stores analysis result in database
9. Worker reports success/failure to backend via callback
10. Backend links analysis to application, creates timeline event
11. Dashboard shows match score and qualifications

**Analysis Output:**
- Match score: Integer 0-100 (overall fit)
- Matched qualifications: Array of qualifications user meets
- Missing qualifications: Array of qualifications user lacks
- Skill suggestions: Array of tips to improve application

**LLM Configuration:**
- Provider: OpenAI or Anthropic (configurable)
- Model: gpt-4 or claude-sonnet-4 (configurable)
- Temperature: 0.3 (deterministic)
- Max tokens: 2000
- Timeout: 60 seconds

**Auto-Analysis:** If `settings.auto_analyze=true` (default), analysis job automatically enqueued after successful scraping

**Error Handling:**
- Invalid API key: Mark failed immediately, notify user in settings
- Rate limit (429): Retry with longer backoff (5m, 15m, 30m)
- Timeout: Retry with backoff (1m, 5m, 15m)
- Invalid JSON response: Retry (max 3 attempts)
- Missing preconditions (no resume/posting): Mark failed immediately
- Match score out of range: Clamp to [0, 100], log warning

**Cost Awareness:** Each analysis costs ~$0.01-0.05 depending on provider/model. User configures API key and pays for usage.

### Feature 6: Unified Dashboard

**Description:** Web interface to view, filter, sort, and manage all applications.

**Features:**
- List view: All applications with pagination, filtering, sorting, search
- Detail view: Single application with job posting, analysis, timeline
- Status management: Update application status (applied, screening, interview, offer, etc.)
- Notes: Add/edit notes for each application (markdown supported, max 10K chars)
- Timeline: View all events for application (submission, scraping, analysis, status changes)
- Manual triggers: Manually trigger scraping or analysis for specific application
- Export: Download applications as CSV or JSON

**Filters:**
- Status: Multiple selection (applied, screening, interview, etc.)
- Date range: Application date from/to
- Match score: Minimum match score (if analyzed)
- Needs review: Show only applications flagged for review
- Search: Full-text search on company name, job title, notes

**Sorting:**
- Application date (default: descending)
- Company name (alphabetical)
- Job title (alphabetical)
- Match score (descending, nulls last)
- Created date (descending)

**Pagination:**
- Default: 25 per page
- Options: 10, 25, 50, 100 per page
- Max: 100 per page

### Feature 7: Timeline and Audit Trail

**Description:** Immutable log of all events for each application, provides complete history.

**Event Types:**
- `application_submitted`: Application created (source: browser, email, manual)
- `status_changed`: Status updated (includes old and new status)
- `job_scraped`: Job posting successfully scraped
- `job_scraped_failed`: Scraping failed (includes error reason)
- `analysis_completed`: AI analysis completed (includes match score)
- `analysis_failed`: Analysis failed (includes error reason)
- `note_updated`: Notes edited (includes preview of new note)
- `email_received`: Application detected from email (includes subject, sender)
- `manual_interview_scheduled`: User manually added interview event
- `manual_email_sent`: User manually logged email sent
- `manual_phone_call`: User manually logged phone call
- `manual_other`: User manually added custom event

**Event Data:** Each event includes JSONB data with event-specific fields (e.g., old/new status, error reason, match score, etc.)

**Display:** Events shown in reverse chronological order (most recent first), can filter by event type

**Manual Events:** User can add custom timeline events (interview scheduled, phone call, email sent, etc.) with description field

---

## Architecture Principles

### Deployment

- **Single-user local application:** No multi-tenancy, no user authentication
- **Localhost-only:** Backend binds to 127.0.0.1, no network exposure
- **No cloud dependency:** All data stored locally (PostgreSQL database on same machine)
- **Process isolation:** Separate processes for API server, workers, email service

### Technology Stack

- **Backend:** FastAPI (Python 3.11+)
- **Database:** PostgreSQL 14+ (primary data store)
- **Queue:** SQLite or PostgreSQL tables (job queues for workers)
- **Workers:** Python processes (scraping, parsing, analysis)
- **Browser Extension:** JavaScript (Chrome Extension APIs)
- **Email Service:** Python with imaplib (IMAP polling)

### Data Flow

```
Browser Extension → POST /capture/browser → Backend API → Application DB + Scraper Queue
Email Service → POST /capture/email → Backend API → Application DB + Scraper Queue
Scraper Worker → Poll Queue → HTTP GET → Parse HTML → Store Results → POST /internal/scraper/results → Backend
Parser Worker → Poll Queue → Read File → Parse Content → Store Results → POST /internal/parser/results → Backend
Analysis Worker → Poll Queue → Fetch Data → Call LLM → Parse Response → Store Results → POST /internal/analysis/results → Backend
Dashboard → GET /applications → Backend API → Return JSON → Render UI
```

### Async Processing Mandatory

- **Scraping:** Always async (HTTP request unpredictable, 1-30 seconds)
- **Parsing:** Always async (file I/O + parsing, 1-10 seconds)
- **Analysis:** Always async (LLM API call, 5-60 seconds)
- **Email polling:** Always async (runs in background)

Rationale: Never block user-facing API requests. Return 201/202 immediately, process in background, notify via timeline when complete.

### Error Handling Philosophy

- **Graceful degradation:** Partial success better than total failure
- **User visibility:** Critical failures visible in timeline
- **Silent retry:** Transient failures retry automatically
- **Manual intervention:** Permanent failures require user action (e.g., paste content manually)
- **Data preservation:** Never lose user data (queue locally, retry indefinitely)

---

## System Constraints

### Performance

- Support 1000+ applications in database (reasonable for individual user)
- List applications in < 500ms (with pagination and filtering)
- Detail view in < 200ms (with eager loading)
- Scraping: 10 req/min per domain (avoid rate limits)
- Analysis: Limited by LLM API rate limits (typically 60 req/min)

### Scalability

- **Not multi-user:** No need to scale beyond single user
- **Not distributed:** Single machine deployment
- **Worker count:** Fixed number of workers (5 scrapers, 1 parser, 3 analyzers)
- **Queue depth:** Warn if queue > 500 jobs (system stress indicator)

### Storage

- **Database:** Expect 100MB-1GB for 1000 applications with full data
- **HTML storage:** ~100KB per job posting (prune after 90 days)
- **Resume files:** ~500KB per resume (keep all versions)
- **Total estimate:** 1-5GB for typical usage

### Security

- **No authentication:** Localhost-only, single user trusted
- **Internal API token:** Shared secret for worker callbacks (prevent external access)
- **File permissions:** Resume files chmod 600 (owner read/write only)
- **Credential storage:** Email password and LLM API key in OS keychain (future) or environment variables (MVP)
- **No HTTPS:** Localhost traffic, HTTPS not required

---

## Out of Scope (MVP)

### Explicitly Excluded Features

- **Multi-user support:** No user accounts, no authentication
- **Cloud deployment:** No SaaS hosting, no remote access
- **Mobile apps:** Desktop/laptop only (browser extension requires desktop Chrome)
- **Cover letter generation:** Not in scope (future feature)
- **Interview scheduling:** No calendar integration (manual timeline events only)
- **Networking/CRM:** No contact management, no relationship tracking
- **Salary negotiation:** No salary data analysis (future feature)
- **Job search:** Does not find jobs (user finds jobs, tracker tracks applications)
- **Application submission:** Does not submit applications (user submits, tracker captures)
- **Company research:** No company profiles or research tools
- **Offer comparison:** No structured offer management (use notes field)

### Technical Limitations Accepted

- **JavaScript rendering:** Scraper cannot handle JavaScript-heavy pages (static HTML only)
- **CAPTCHA:** Cannot bypass CAPTCHA (mark failed, user pastes manually)
- **Login walls:** Cannot authenticate to job boards (mark failed)
- **Scanned PDFs:** Cannot OCR (mark failed, user uploads text-based PDF)
- **Email parsing accuracy:** Best effort, some emails require manual review
- **LLM hallucination:** Analysis may contain inaccuracies (user judgment required)

---

## Success Criteria

### MVP Complete When:

1. ✅ User can install browser extension and capture applications from supported job boards
2. ✅ User can configure email monitoring and applications auto-detected from confirmation emails
3. ✅ Job postings automatically scraped within 1 hour of application creation
4. ✅ User can upload resume and parsing completes within 1 minute
5. ✅ AI analysis automatically triggered after scraping completes (if resume uploaded)
6. ✅ User can view all applications in dashboard with filtering and sorting
7. ✅ User can update application status and add notes
8. ✅ User can view timeline for each application showing all events
9. ✅ User can manually trigger scraping or analysis for any application
10. ✅ User can export all applications to CSV or JSON
11. ✅ System handles errors gracefully (no crashes, failures logged in timeline)
12. ✅ All data stored locally, no cloud dependency

### User Satisfaction Metrics (Qualitative)

- User can track 50+ applications without manual data entry
- User saves 5+ minutes per application (no manual copy/paste)
- User has confidence in AI match scores (validates against own judgment)
- User can quickly find any application using search/filters
- User trusts system reliability (no data loss, consistent behavior)

---

## Future Enhancements (Post-MVP)

### Phase 2: Enhanced Features

- Cover letter generation (LLM-based, tailored to job posting)
- Interview scheduling integration (Google Calendar sync)
- Multi-resume support (different resumes for different job types)
- Offer comparison tool (structured offer data, side-by-side comparison)
- Analytics dashboard (application funnel, time-to-hire, success rate by source)

### Phase 3: Advanced Features

- Networking/CRM (contact management, relationship tracking)
- Salary negotiation assistant (market data, negotiation tips)
- Company research integration (Glassdoor, LinkedIn Company)
- Job recommendation (ML-based, suggest similar jobs)
- Application templates (save common answers, reuse across applications)

### Phase 4: Multi-User & Cloud

- Multi-user support (team job search, shared applications)
- Cloud deployment (SaaS model, remote access)
- Mobile apps (iOS, Android)
- Real-time notifications (push notifications for status changes)
- Collaboration features (share applications, team notes)

---

## Appendix: Use Cases

### Use Case 1: Active Job Seeker

**Profile:** Recent graduate applying to 100+ positions per month

**Workflow:**
1. Browse LinkedIn, find interesting jobs
2. Apply directly on company website, browser extension captures data
3. Receive confirmation emails, email service auto-detects applications
4. Review dashboard weekly, see which applications analyzed
5. Prioritize applications with high match scores (80+)
6. Update status as applications progress (screening → interview → offer)
7. Add notes after each interview
8. Export data at end of search to analyze what worked

**Key Features Used:**
- Browser extension (primary capture method)
- Email ingestion (backup, catches missed captures)
- AI analysis (prioritization)
- Status tracking (pipeline management)
- Notes (interview prep, follow-up reminders)
- Export (post-search analysis)

### Use Case 2: Passive Job Seeker

**Profile:** Employed professional, applying to 5-10 selective positions per month

**Workflow:**
1. Receive recruiter emails with job opportunities
2. Email service auto-detects applications from recruiter emails
3. Upload tailored resume for each application type
4. Review AI analysis to decide which roles to prioritize
5. Manually add timeline events (phone screens, on-sites)
6. Track offer details in notes field
7. Compare offers side-by-side using dashboard

**Key Features Used:**
- Email ingestion (primary capture method)
- Multi-resume support (tailored resumes)
- AI analysis (opportunity assessment)
- Manual timeline events (detailed tracking)
- Notes (offer details, negotiations)

### Use Case 3: Career Changer

**Profile:** Professional transitioning to new industry, applying to 30-50 positions

**Workflow:**
1. Apply to diverse roles across multiple job boards
2. Browser extension captures all applications
3. Upload resume highlighting transferable skills
4. Review analysis to understand gaps (missing qualifications)
5. Update resume based on skill suggestions
6. Re-run analysis to see improvement
7. Focus applications on roles with 70+ match score
8. Track which companies respond (conversion rate by industry)

**Key Features Used:**
- Browser extension (multi-source capture)
- AI analysis (gap identification)
- Skill suggestions (resume improvement)
- Re-analysis (iteration)
- Filtering (focus on viable opportunities)
- Timeline (conversion tracking)

---

**End of Product Scope Document**
