# Job Application Tracker - Functional Requirements Specification

## 1. Core Functional Requirements

### 1.1 Browser Event Capture Subsystem

**BR-001: Extension Installation and Configuration**
- **Input:** User initiates browser extension installation from Chrome Web Store or local package
- **Output:** Extension installed, icon visible in browser toolbar, configuration page accessible
- **Success Rules:** Extension appears in chrome://extensions with "enabled" status; clicking icon opens popup interface
- **Failure Rules:** If installation fails, display browser-native error message; system does not proceed
- **Missing Data Behavior:** N/A - installation is atomic operation

**BR-002: Job Board Detection**
- **Input:** User navigates to web page in browser
- **Output:** Extension identifies if current page matches known job board patterns (LinkedIn Jobs, Indeed, Greenhouse ATS domains)
- **Success Rules:** Extension maintains whitelist of job board domains/URL patterns; match returns true for monitored sites
- **Failure Rules:** Non-matching domains return false; extension remains dormant
- **Missing Data Behavior:** If URL cannot be parsed, treat as non-job-board page
- **Cross-Module:** Detection status may be displayed in extension popup UI

**BR-003: Form Submission Interception**
- **Input:** User submits form on detected job board page (via submit button click or Enter key)
- **Output:** Extension captures form submission event before or immediately after submission completes
- **Success Rules:** Event listener intercepts `submit` event or mutation observer detects post-submission DOM changes indicating success
- **Failure Rules:** If event cannot be captured (user leaves page too quickly, JavaScript errors), no data captured; no user interruption
- **Missing Data Behavior:** If submission cannot be definitively detected, extension does not trigger capture workflow
- **Cross-Module:** Triggers BR-004 extraction workflow

**BR-004: Metadata Extraction from Job Board**
- **Input:** Intercepted form submission event and current page DOM
- **Output:** Structured data object containing: job_title, company_name, application_timestamp, job_posting_url, job_board_source
- **Success Rules:** 
  - job_title: Extract from page heading (h1, h2) or form field labeled "Job Title" or similar
  - company_name: Extract from page metadata, company logo alt text, or form field
  - application_timestamp: Current browser timestamp (ISO 8601 format)
  - job_posting_url: Current page URL, cleaned of query parameters except job ID
  - job_board_source: Domain name (e.g., "linkedin.com", "indeed.com")
- **Failure Rules:** If any required field (job_title, company_name) cannot be extracted, mark extraction as incomplete but proceed to confirmation
- **Missing Data Behavior:** 
  - If job_posting_url cannot be determined, set to null
  - If company_name missing, set to "Unknown Company"
  - If job_title missing, set to "Unknown Position"
- **Cross-Module:** Extracted data passed to BR-005

**BR-005: User Confirmation Modal**
- **Input:** Extracted metadata object from BR-004
- **Output:** Modal overlay displayed on current page showing extracted data with editable fields and Confirm/Cancel buttons
- **Success Rules:** Modal renders within 2 seconds of form submission; all extracted fields pre-populated and editable; modal blocks interaction with underlying page
- **Failure Rules:** If modal cannot render (DOM manipulation blocked), log error to browser console and abandon capture
- **Missing Data Behavior:** Empty or "Unknown" fields displayed with visual indicator that data needs manual entry
- **Cross-Module:** On Confirm, sends data to Application Record Manager (ARM-001); on Cancel, discards data

**BR-006: Background Communication**
- **Input:** Confirmed application data from BR-005
- **Output:** Data transmitted from browser extension to local backend service via HTTP POST
- **Success Rules:** POST request to http://localhost:[PORT]/api/applications/capture with JSON payload; receives 201 Created response
- **Failure Rules:** 
  - If backend unreachable (connection refused), display error toast: "Cannot connect to tracking service. Ensure application is running."
  - If 4xx/5xx response, display error with response message
  - Retry logic: Retry once after 5 seconds; if second attempt fails, offer "Save for Later" option
- **Missing Data Behavior:** Backend validates required fields; returns 400 if validation fails
- **Cross-Module:** Interfaces with Application Record Manager backend API

---

### 1.2 Email Ingestion Subsystem

**EI-001: Email Account Connection**
- **Input:** User provides email connection details via configuration interface: IMAP server, port, username, password, target folder name
- **Output:** System establishes and validates IMAP connection; stores encrypted credentials locally
- **Success Rules:** Successful IMAP login; system can list folders; target folder exists or is created
- **Failure Rules:** 
  - If authentication fails, display error: "Invalid credentials. Please verify username and password."
  - If target folder cannot be accessed, display error: "Cannot access folder [name]. Check folder name and permissions."
- **Missing Data Behavior:** If target folder not specified, default to "INBOX"
- **Cross-Module:** Credentials stored via secure storage mechanism (system keychain or encrypted file)

**EI-002: Email Polling**
- **Input:** Configured IMAP connection and polling interval (default: 5 minutes)
- **Output:** Background process retrieves unread emails from target folder at specified interval
- **Success Rules:** Process connects to IMAP server, issues SEARCH UNSEEN command, retrieves matching email UIDs
- **Failure Rules:** 
  - If connection lost during polling, log error and retry on next interval
  - If authentication expires, log error and notify user to re-authenticate
- **Missing Data Behavior:** If no unread emails, polling returns empty set; no action taken
- **Cross-Module:** Retrieved emails passed to EI-003

**EI-003: Confirmation Email Detection**
- **Input:** Email message (headers + body) from EI-002
- **Output:** Boolean classification: is_application_confirmation (true/false)
- **Success Rules:** Email classified as confirmation if:
  - Subject line contains patterns: "application received", "application submitted", "thank you for applying", "confirm.*application"
  - Sender domain matches known job board domains OR company domains in existing application records
  - Body contains patterns: "your application", "application for [job title]", "position.*has been received"
- **Failure Rules:** If email does not match patterns, classify as false; email remains unread
- **Missing Data Behavior:** If email body cannot be decoded, attempt header-only classification
- **Cross-Module:** Confirmed emails passed to EI-004

**EI-004: Email Parsing and Extraction**
- **Input:** Confirmed application email from EI-003
- **Output:** Structured data object: company_name, job_title, application_timestamp, job_posting_url (optional), email_subject, email_sender, email_received_timestamp
- **Success Rules:**
  - company_name: Extract from sender domain, email signature, or body text mentioning "at [Company]"
  - job_title: Extract from subject line or body text patterns: "application for [title]", "position: [title]"
  - application_timestamp: Use email received timestamp as proxy
  - job_posting_url: Extract any URLs in email body matching job board patterns
  - email_subject, email_sender: Direct extraction from headers
- **Failure Rules:** If required fields (company_name, job_title) cannot be extracted, flag record as "needs_review" but still create
- **Missing Data Behavior:**
  - If company_name not found, extract from sender domain (e.g., "noreply@company.com" → "Company")
  - If job_title not found, set to "Position from [sender]"
  - If no job_posting_url found, set to null
- **Cross-Module:** Parsed data sent to Application Record Manager (ARM-001)

**EI-005: Email State Management**
- **Input:** Successfully parsed email from EI-004
- **Output:** Email marked as read in IMAP; email moved to processed subfolder (optional)
- **Success Rules:** IMAP STORE command sets \Seen flag; if move enabled, email moved to "Processed Applications" folder
- **Failure Rules:** If marking fails, log warning but continue (prevents reprocessing via local tracking of processed UIDs)
- **Missing Data Behavior:** N/A
- **Cross-Module:** Uses local database to track processed email UIDs to prevent duplicates even if IMAP operations fail

---

### 1.3 Job Posting Scraper Subsystem

**JS-001: Scrape Request Queuing**
- **Input:** Job posting URL from browser capture, email parsing, or manual entry
- **Output:** URL added to scraping queue with priority and timestamp
- **Success Rules:** Queue entry created with: url, source (browser/email/manual), priority (manual=high, browser=medium, email=low), created_at timestamp, status=pending
- **Failure Rules:** If URL invalid (malformed, non-HTTP/HTTPS), reject with error message
- **Missing Data Behavior:** If source not specified, default to "manual"
- **Cross-Module:** Queue processed by JS-002

**JS-002: URL Validation and Deduplication**
- **Input:** Job posting URL from queue
- **Output:** Validation result and deduplication check
- **Success Rules:**
  - URL validation: Must be valid HTTP/HTTPS, must resolve (DNS lookup succeeds)
  - Deduplication: Check if URL (normalized) already exists in scraped_postings table
  - If duplicate found and scrape age < 7 days, skip scrape and reuse existing data
  - If duplicate found and scrape age >= 7 days, re-scrape to get updated content
- **Failure Rules:** 
  - If URL does not resolve, mark queue item as failed with reason "URL_NOT_FOUND"
  - If duplicate and recent, mark queue item as skipped and link to existing posting record
- **Missing Data Behavior:** N/A
- **Cross-Module:** Validation success triggers JS-003; failure updates queue item status

**JS-003: HTTP Fetch with Rate Limiting**
- **Input:** Validated job posting URL from JS-002
- **Output:** Raw HTML content and HTTP response metadata
- **Success Rules:**
  - Respect rate limit: Maximum 10 requests per minute per domain
  - HTTP GET request with User-Agent header mimicking standard browser
  - Follow redirects (max 5)
  - Timeout after 30 seconds
  - Return HTML body, status code, final URL (after redirects), response headers
- **Failure Rules:**
  - If rate limit exceeded, delay request and retry after cooldown period
  - If timeout occurs, mark scrape as failed with reason "TIMEOUT"
  - If status code 4xx or 5xx, mark as failed with reason "HTTP_[code]"
  - If connection error (DNS, network), mark as failed with reason "CONNECTION_ERROR"
  - Failed scrapes: Retry up to 3 times with exponential backoff (1min, 5min, 15min)
- **Missing Data Behavior:** N/A - failure is explicit
- **Cross-Module:** Successful fetch passes HTML to JS-004; metadata logged for debugging

**JS-004: HTML Storage**
- **Input:** Raw HTML content from JS-003 and associated metadata
- **Output:** HTML stored in scraped_postings table with metadata
- **Success Rules:** Database insert with: url (normalized), html_content (full), fetch_timestamp, http_status, final_url, content_hash (for change detection)
- **Failure Rules:** If database insert fails, log error and mark queue item as failed
- **Missing Data Behavior:** N/A
- **Cross-Module:** Stored posting_id passed to JS-005 for parsing

**JS-005: Job Posting Content Extraction**
- **Input:** Raw HTML from JS-004 and job posting URL
- **Output:** Structured job data extracted from HTML
- **Success Rules:** Extract following fields using CSS selectors and pattern matching:
  - job_title: h1 tag, meta property="og:title", or patterns like <span class="job-title">
  - company_name: Meta tags, patterns like <div class="company-name">, or domain-based inference
  - job_description: Largest text block in main content area, often in <div class="description">
  - requirements: Text sections with headings "Requirements", "Qualifications", "What You'll Need" (case-insensitive)
  - nice_to_have: Text sections with headings "Nice to Have", "Bonus", "Preferred"
  - salary_range: Regex patterns: $XX,XXX - $XX,XXX, $XXk-$XXXk, salary range extraction
  - location: Meta tags, patterns like <span class="location">, or text patterns "Location: [place]"
  - employment_type: Patterns: Full-time, Part-time, Contract, Internship
  - All extracted text normalized: excess whitespace removed, HTML entities decoded
- **Failure Rules:** If critical field (job_title, job_description) extraction fails, mark extraction as incomplete but store partial data
- **Missing Data Behavior:**
  - If job_title missing, attempt extraction from page title or URL slug
  - If company_name missing, extract from URL domain
  - If requirements/nice_to_have not found as distinct sections, attempt to split description into paragraphs and classify
  - If salary_range not found, set to null
  - If location not found, set to "Not specified"
  - If employment_type not found, set to "Not specified"
- **Cross-Module:** Extracted data stored in job_postings table; posting_id linked to application record via ARM-003

**JS-006: Scrape Failure Handling**
- **Input:** Failed scrape record from JS-003 with failure reason
- **Output:** User notification and fallback behavior
- **Success Rules:** 
  - User notified via dashboard notification: "Could not scrape [URL]: [reason]"
  - Application record still created with available metadata
  - Retry mechanism: Failed scrapes retried automatically at increasing intervals (as per JS-003)
  - After 3 failed attempts, mark as permanently failed and cease retries
- **Failure Rules:** N/A - this is the failure handler
- **Missing Data Behavior:** Job posting fields remain null; AI analysis can still run using job_title and manual notes if provided

---

### 1.4 Resume Parsing Subsystem

**RP-001: Resume Upload**
- **Input:** User uploads resume file via UI file picker (supported formats: PDF, DOCX, TXT)
- **Output:** File stored in local filesystem, parsing job queued
- **Success Rules:** 
  - File size < 10MB
  - File extension matches supported formats
  - File written to designated upload directory with UUID-based filename
  - Database record created in resumes table: filename, upload_timestamp, file_path, status=pending
- **Failure Rules:**
  - If file size exceeds limit, reject with error: "File too large. Maximum size is 10MB."
  - If unsupported format, reject with error: "Unsupported format. Please upload PDF, DOCX, or TXT."
  - If write fails, display error: "Could not save file. Check disk space and permissions."
- **Missing Data Behavior:** N/A - file upload is atomic
- **Cross-Module:** Triggers RP-002 parsing workflow

**RP-002: Text Extraction**
- **Input:** Resume file path and format from RP-001
- **Output:** Plain text content extracted from document
- **Success Rules:**
  - PDF: Use pdfplumber or PyPDF2 library; extract text page by page; concatenate with page breaks
  - DOCX: Use python-docx library; extract paragraphs and table content; preserve structure with newlines
  - TXT: Read file directly with UTF-8 encoding
  - Return extracted text with normalized whitespace (no excess newlines, consistent spacing)
- **Failure Rules:**
  - If PDF is image-based (scanned) with no text layer, fail with error: "PDF contains no extractable text. Please use a text-based PDF or run OCR first."
  - If DOCX is corrupted or password-protected, fail with error: "Could not read document. File may be corrupted or password-protected."
  - If text extraction library throws exception, log error and fail parsing
- **Missing Data Behavior:** If file is empty or contains only whitespace, fail with error: "Resume appears to be empty."
- **Cross-Module:** Extracted text passed to RP-003; parsing status updated in resumes table

**RP-003: Section Identification**
- **Input:** Plain text resume content from RP-002
- **Output:** Resume segmented into sections: contact_info, summary, experience, education, skills, certifications, other
- **Success Rules:**
  - Use keyword matching to identify section headers (case-insensitive):
    - Contact: "Contact", "Email", "Phone" (typically top of resume)
    - Summary: "Summary", "Objective", "Profile", "About"
    - Experience: "Experience", "Work History", "Employment", "Professional Experience"
    - Education: "Education", "Academic Background", "Degrees"
    - Skills: "Skills", "Technical Skills", "Competencies", "Technologies"
    - Certifications: "Certifications", "Licenses", "Credentials"
  - Sections defined by header position; content is text between headers
  - If section not found, assign empty string
- **Failure Rules:** If no sections identifiable (unstructured resume), place entire content in "other" section and log warning
- **Missing Data Behavior:** Missing sections remain null; parsing continues with available sections
- **Cross-Module:** Segmented resume passed to RP-004

**RP-004: Structured Data Extraction**
- **Input:** Segmented resume sections from RP-003
- **Output:** Structured resume data object
- **Success Rules:** Extract structured fields:
  - **Contact Info:**
    - email: Regex for email pattern
    - phone: Regex for phone patterns (US/international)
    - location: City, State patterns or address patterns
  - **Skills:** 
    - Extract comma-separated or bullet-pointed skill lists
    - Categorize if possible: programming languages, frameworks, tools, soft skills
    - Store as array of skill strings
  - **Experience:**
    - Extract job entries with: company name, job title, date range, responsibilities (bullet points)
    - Parse date ranges: "Jan 2020 - Present", "2018-2020", etc.
    - Store as array of experience objects
  - **Education:**
    - Extract: institution name, degree type, major/field, graduation year
    - Store as array of education objects
  - **Certifications:**
    - Extract certification names and issuing organizations
    - Store as array of certification strings
- **Failure Rules:** If structured extraction fails for any section, store raw text for that section instead
- **Missing Data Behavior:** 
  - If email not found, set to null (will prompt user to add manually)
  - If skills section empty, initialize as empty array
  - If experience/education unparseable, store as raw text strings
- **Cross-Module:** Structured data stored in resume_data table linked to resume record; resume status updated to "completed"

**RP-005: Resume Versioning**
- **Input:** New resume upload when existing resume already present
- **Output:** Previous resume archived; new resume set as active
- **Success Rules:**
  - Existing resume record flagged as archived: is_active=false, archived_at=current_timestamp
  - New resume record created with is_active=true
  - All future AI analyses use active resume
- **Failure Rules:** N/A - versioning is informational only
- **Missing Data Behavior:** If no existing resume, new resume becomes first active resume
- **Cross-Module:** AI Analysis Engine queries for active resume only

---

### 1.5 AI Analysis Engine Subsystem

**AI-001: Analysis Trigger**
- **Input:** Application record with linked job posting that has not been analyzed OR user manual trigger
- **Output:** Analysis job queued with application_id and posting_id
- **Success Rules:**
  - Analysis triggered automatically when: new application created AND job posting successfully scraped
  - Analysis can be manually triggered via UI button: "Run Analysis" or "Re-run Analysis"
  - Queue entry created with: application_id, posting_id, resume_id (active), status=pending, queued_at timestamp
- **Failure Rules:** 
  - If no active resume exists, reject with error: "Please upload a resume before running analysis."
  - If job posting has no description data, reject with error: "Job posting data incomplete. Cannot analyze."
- **Missing Data Behavior:** If optional job fields missing (requirements, nice_to_have), analysis proceeds with available data
- **Cross-Module:** Queue processed by AI-002; triggers after JS-005 completion

**AI-002: Prompt Construction**
- **Input:** Resume data from RP-004, job posting data from JS-005
- **Output:** Structured prompt for LLM API call
- **Success Rules:** Construct prompt with following sections:
  - System context: "You are a job application analyzer helping a job seeker understand how well their resume matches a job posting."
  - Resume input: Include resume summary, skills list, experience entries, education, certifications
  - Job posting input: Include job title, company, description, requirements, nice-to-have qualifications
  - Task instructions: "Analyze the match between this resume and job posting. Provide: (1) overall match score 0-100, (2) list of matched qualifications from job posting found in resume, (3) list of missing qualifications from job posting not found in resume, (4) top 3 skill emphasis suggestions."
  - Output format: "Return response as valid JSON with keys: match_score, matched_qualifications, missing_qualifications, skill_suggestions."
  - Prompt length: If combined resume + job posting exceeds 12,000 tokens, truncate job description while preserving requirements section
- **Failure Rules:** If prompt construction fails (data serialization error), log error and mark analysis as failed
- **Missing Data Behavior:** If resume sections missing, include note in prompt: "Resume section [X] not available."
- **Cross-Module:** Constructed prompt passed to AI-003

**AI-003: LLM API Call**
- **Input:** Structured prompt from AI-002
- **Output:** LLM response containing analysis results
- **Success Rules:**
  - API call to configured LLM endpoint (OpenAI GPT-4, Anthropic Claude, etc.)
  - Request parameters: temperature=0.3 (deterministic), max_tokens=2000, response format JSON
  - Timeout after 60 seconds
  - Return parsed JSON response
- **Failure Rules:**
  - If API returns error (rate limit, invalid key, server error), log error with details
  - If timeout, retry once after 10 seconds; if second timeout, mark analysis as failed
  - If response is not valid JSON, attempt to extract JSON from markdown code blocks; if still fails, mark as failed
  - Rate limiting: If 429 response, implement exponential backoff (1min, 5min, 15min) before retry
  - After 3 failed attempts, mark analysis as permanently failed and notify user
- **Missing Data Behavior:** N/A - response required for success
- **Cross-Module:** Response passed to AI-004; API key stored via secure configuration

**AI-004: Response Parsing and Validation**
- **Input:** LLM JSON response from AI-003
- **Output:** Validated and structured analysis result object
- **Success Rules:** Parse JSON and validate structure:
  - match_score: Integer 0-100; if outside range, clamp to boundaries
  - matched_qualifications: Array of strings; minimum 0 items
  - missing_qualifications: Array of strings; minimum 0 items
  - skill_suggestions: Array of strings; validate length 1-5 items
  - If arrays contain empty strings, filter them out
  - Store validated result in analysis_results table with: application_id, match_score, matched_qualifications (JSON), missing_qualifications (JSON), skill_suggestions (JSON), analyzed_at timestamp, model_used
- **Failure Rules:**
  - If required keys missing from JSON, mark analysis as failed: "Invalid response structure"
  - If match_score is non-numeric, attempt conversion; if fails, set to null and log warning
  - If arrays are not arrays, convert to empty arrays and log warning
- **Missing Data Behavior:**
  - If matched_qualifications empty, store as empty array (indicates no matches found)
  - If missing_qualifications empty, store as empty array (indicates perfect match)
  - If skill_suggestions missing or empty, generate generic suggestion: "Tailor resume to emphasize relevant experience."
- **Cross-Module:** Analysis result linked to application record; application status updated to include analysis_completed flag

**AI-005: Analysis Regeneration**
- **Input:** User request to re-run analysis for existing application
- **Output:** New analysis result replacing previous result
- **Success Rules:**
  - Previous analysis result archived (soft delete or versioned)
  - New analysis triggered following AI-001 through AI-004 workflow
  - Regeneration allowed unlimited times
  - Each regeneration records model_used and analyzed_at timestamp for auditability
- **Failure Rules:** If regeneration fails, previous analysis result remains visible
- **Missing Data Behavior:** N/A
- **Cross-Module:** Uses same workflow as initial analysis

---

### 1.6 Application Record Manager Subsystem

**ARM-001: Application Record Creation**
- **Input:** Application data from browser capture (BR-006), email ingestion (EI-004), or manual entry
- **Output:** New application record created in database
- **Success Rules:** Create record with:
  - Required fields: company_name, job_title, application_date, source (browser/email/manual)
  - Optional fields: job_posting_url, notes, custom_status
  - Generated fields: application_id (UUID), created_at timestamp, updated_at timestamp, status=applied
  - Return created application_id
- **Failure Rules:**
  - If required fields missing, return 400 error with validation details
  - If database constraint violation (unique constraint if implemented), return 409 error
- **Missing Data Behavior:**
  - If job_posting_url missing, set to null; scraping will not occur
  - If application_date missing, use current timestamp
  - If status not specified, default to "applied"
- **Cross-Module:** On success with job_posting_url, triggers JS-001 scraping; created application_id used for all subsequent operations

**ARM-002: Duplicate Detection**
- **Input:** Application data from ARM-001 before record creation
- **Output:** Duplicate check result indicating if similar application exists
- **Success Rules:** Check for duplicates using:
  - Exact match: Same company_name (case-insensitive) AND same job_title (case-insensitive) AND application_date within 7 days
  - URL match: Same job_posting_url (normalized)
  - If duplicate found, return existing application_id and flag
- **Failure Rules:** N/A - duplicate check is advisory only
- **Missing Data Behavior:** If job_posting_url is null, skip URL-based duplicate check
- **Cross-Module:** If duplicate found, present user with options: (1) Skip creation and view existing, (2) Create anyway (allow duplicates), (3) Update existing record

**ARM-003: Job Posting Linkage**
- **Input:** Application record and completed scraped job posting from JS-005
- **Output:** Application record updated with posting_id foreign key
- **Success Rules:**
  - Update application record: posting_id = scraped_posting_id, posting_linked_at = current_timestamp
  - Trigger AI-001 analysis if auto-analyze enabled
- **Failure Rules:** If update fails (record not found, FK constraint violation), log error but do not fail scraping
- **Missing Data Behavior:** N/A
- **Cross-Module:** Links scraping output to application; enables AI analysis trigger

**ARM-004: Status Management**
- **Input:** Application ID and new status value
- **Output:** Application status updated, status change logged in timeline
- **Success Rules:**
  - Allowed status values: applied, screening, interview_scheduled, interviewed, offer_received, accepted, rejected, withdrawn
  - Update application record: status = new_status, status_updated_at = current_timestamp
  - Create timeline event (see TL-001) recording status change
- **Failure Rules:**
  - If invalid status value provided, return 400 error: "Invalid status value"
  - If application_id not found, return 404 error
- **Missing Data Behavior:** N/A - status is explicit value
- **Cross-Module:** Status changes create timeline events; status displayed in dashboard

**ARM-005: Manual Notes Update**
- **Input:** Application ID and notes text (markdown supported)
- **Output:** Application record updated with notes
- **Success Rules:**
  - Update application record: notes = new_notes_text, updated_at = current_timestamp
  - Notes length limited to 10,000 characters
  - Markdown preserved as-is (rendering handled by UI layer)
- **Failure Rules:**
  - If notes exceed length limit, return 400 error: "Notes too long. Maximum 10,000 characters."
  - If application_id not found, return 404 error
- **Missing Data Behavior:** If notes empty or null, clear existing notes
- **Cross-Module:** Notes displayed in application detail view

**ARM-006: Application Deletion**
- **Input:** Application ID
- **Output:** Application record soft-deleted or permanently deleted based on configuration
- **Success Rules:**
  - Soft delete (default): Set deleted_at = current_timestamp, is_deleted = true
  - Hard delete (if configured): Remove record from database; cascade delete linked records (timeline events, analysis results)
  - Deletion logged in system audit log
- **Failure Rules:** If application_id not found, return 404 error
- **Missing Data Behavior:** N/A
- **Cross-Module:** Deleted applications excluded from dashboard queries; linked job postings remain for potential future use

---

### 1.7 Timeline & Event Tracking Subsystem

**TL-001: Event Creation**
- **Input:** Event type, application_id, event data (JSON), timestamp (optional)
- **Output:** Timeline event record created
- **Success Rules:** Create record with:
  - Event types: application_submitted, status_changed, job_scraped, analysis_completed, note_added, email_received, interview_scheduled (manual), email_sent (manual)
  - Required fields: event_type, application_id, event_data (JSON), occurred_at timestamp
  - event_data structure varies by type:
    - status_changed: {old_status, new_status}
    - job_scraped: {posting_id, url}
    - analysis_completed: {analysis_id, match_score}
    - note_added: {note_preview (first 100 chars)}
    - email_received: {email_subject, email_sender}
- **Failure Rules:** If application_id invalid, return 400 error
- **Missing Data Behavior:** If occurred_at not provided, use current timestamp
- **Cross-Module:** Events created by ARM-004 (status changes), JS-005 (scraping), AI-004 (analysis), ARM-005 (notes)

**TL-002: Timeline Retrieval**
- **Input:** Application ID, optional date range filter
- **Output:** Ordered list of timeline events for application
- **Success Rules:**
  - Query timeline_events table for application_id
  - Order by occurred_at descending (most recent first)
  - Apply date range filter if provided
  - Return array of event objects with: event_id, event_type, event_data, occurred_at
- **Failure Rules:** If application_id not found, return empty array (not an error)
- **Missing Data Behavior:** If no events exist, return empty array
- **Cross-Module:** Timeline displayed in application detail view

**TL-003: Manual Event Addition**
- **Input:** Application ID, event type (interview_scheduled, email_sent, phone_call, other), event description, date/time
- **Output:** Manual timeline event created
- **Success Rules:**
  - Allow users to add manual events not automatically captured
  - Store with event_type prefix "manual_" to distinguish from system events
  - event_data contains: {description, manually_added_by_user: true}
- **Failure Rules:** If application_id invalid, return 400 error
- **Missing Data Behavior:** If date/time not provided, use current timestamp
- **Cross-Module:** Manual events displayed alongside automatic events in timeline

---

### 1.8 Data Export Subsystem

**EX-001: Export Request**
- **Input:** Export format (CSV, JSON), date range filter (optional), status filter (optional), include_analysis flag (boolean)
- **Output:** Export job queued or immediate export file generated
- **Success Rules:**
  - Supported formats: CSV (default), JSON
  - Date range: Filter applications by application_date
  - Status filter: Array of status values to include
  - include_analysis: If true, include AI analysis results in export; if false, exclude
- **Failure Rules:** If invalid format specified, return 400 error: "Unsupported format. Use CSV or JSON."
- **Missing Data Behavior:**
  - If no filters specified, export all non-deleted applications
  - If include_analysis=false or not specified, exclude analysis data

**EX-002: CSV Export Generation**
- **Input:** Filtered application records from EX-001
- **Output:** CSV file with application data
- **Success Rules:** Generate CSV with columns:
  - Basic: company_name, job_title, application_date, status, source, job_posting_url
  - Analysis (if include_analysis=true): match_score, matched_qualifications_count, missing_qualifications_count
  - Notes: notes (truncated to 500 chars or full based on user preference)
  - Timestamps: created_at, updated_at
  - CSV properly escapes commas, quotes, newlines in text fields
  - Header row included
  - UTF-8 encoding with BOM for Excel compatibility
- **Failure Rules:** If CSV generation fails (serialization error), return 500 error
- **Missing Data Behavior:**
  - Empty fields rendered as empty string in CSV
  - If analysis not run, analysis columns show "N/A" or empty
- **Cross-Module:** Export file saved to temp directory, filename generated as: job_tracker_export_[timestamp].csv

**EX-003: JSON Export Generation**
- **Input:** Filtered application records from EX-001
- **Output:** JSON file with application data
- **Success Rules:** Generate JSON array of application objects:
  - Each object contains all application fields
  - Nested objects for: job_posting (if linked), analysis_results (if include_analysis=true), timeline_events (optional, controlled by separate flag)
  - JSON properly formatted with 2-space indentation
  - UTF-8 encoding
- **Failure Rules:** If JSON serialization fails, return 500 error
- **Missing Data Behavior:** Null fields serialized as null in JSON
- **Cross-Module:** Export file saved to temp directory, filename: job_tracker_export_[timestamp].json

**EX-004: Export File Delivery**
- **Input:** Generated export file from EX-002 or EX-003
- **Output:** File download initiated or download link provided
- **Success Rules:**
  - Web UI: Trigger browser download with appropriate Content-Disposition header
  - File stored in temp directory for 24 hours for re-download
  - Success message displayed: "Export complete. [file_size] records exported."
- **Failure Rules:** If file cannot be read or delivered, display error: "Export file unavailable. Please retry."
- **Missing Data Behavior:** N/A
- **Cross-Module:** Cleanup job deletes export files older than 24 hours

---

### 1.9 Dashboard / View Layer Subsystem

**DV-001: Application List View**
- **Input:** Query parameters: filters (status, date range, company), sort field, sort direction, pagination (page, page_size)
- **Output:** Paginated list of application records with summary data
- **Success Rules:**
  - Default sort: application_date descending
  - Supported sort fields: application_date, company_name, job_title, status, match_score
  - Default page_size: 25; max page_size: 100
  - Return: array of application objects with fields: application_id, company_name, job_title, application_date, status, match_score (if available), source
  - Include pagination metadata: total_count, page, page_size, total_pages
  - Filters applied as AND conditions
- **Failure Rules:** If invalid sort field, return 400 error
- **Missing Data Behavior:** 
  - If match_score not available (analysis not run), display as null
  - If no applications match filters, return empty array with total_count=0
- **Cross-Module:** Primary dashboard view; queries Application Record Manager

**DV-002: Application Detail View**
- **Input:** Application ID
- **Output:** Complete application record with all related data
- **Success Rules:** Return object containing:
  - Application fields: all fields from ARM-001
  - Job posting: If linked, include job_title, company_name, description, requirements, salary_range, location, employment_type
  - Analysis results: If available, include match_score, matched_qualifications (array), missing_qualifications (array), skill_suggestions (array)
  - Timeline: Array of events from TL-002
  - Related records: Count of emails received, manual notes
- **Failure Rules:** If application_id not found, return 404 error
- **Missing Data Behavior:**
  - If job posting not linked, job_posting field is null
  - If analysis not run, analysis_results field is null
  - If no timeline events, timeline array is empty
- **Cross-Module:** Aggregates data from multiple subsystems

**DV-003: Dashboard Statistics**
- **Input:** Date range filter (optional)
- **Output:** Aggregate statistics for dashboard overview
- **Success Rules:** Calculate and return:
  - Total applications count
  - Applications by status (breakdown)
  - Average match score (for analyzed applications)
  - Recent activity: applications submitted in last 7 days, 30 days
  - Top companies applied to (by count)
  - Status distribution percentages
- **Failure Rules:** N/A - statistics are best-effort
- **Missing Data Behavior:**
  - If no applications, all counts return 0
  - If no analyzed applications, average match score returns null
- **Cross-Module:** Uses aggregation queries across Application Record Manager

**DV-004: Search Functionality**
- **Input:** Search query string, search scope (all/company/title)
- **Output:** List of applications matching search query
- **Success Rules:**
  - Case-insensitive search
  - Search scopes:
    - all: Search across company_name, job_title, notes
    - company: Search company_name only
    - title: Search job_title only
  - Partial matching supported (LIKE %query%)
  - Results sorted by relevance (exact matches first, then partial matches)
  - Return format same as DV-001 (paginated list)
- **Failure Rules:** If query empty or less than 2 characters, return 400 error: "Search query too short"
- **Missing Data Behavior:** If no matches found, return empty array
- **Cross-Module:** Queries Application Record Manager with search filters

---

## 2. Edge Cases the System Must Handle

### 2.1 Browser Event Capture Edge Cases

**EC-BR-001: Rapid Multiple Submissions**
- **Scenario:** User submits multiple applications in quick succession (< 5 seconds apart) on same job board
- **System Behavior:** Each submission triggers independent capture workflow; modal shown for each but queued to prevent UI overlap; user confirms each sequentially

**EC-BR-002: Page Navigation Before Confirmation**
- **Scenario:** User closes tab or navigates away before confirming capture modal
- **System Behavior:** Modal dismissed; data not saved; no error shown; extension remains ready for next submission

**EC-BR-003: Job Board Site Structure Change**
- **Scenario:** Job board updates HTML structure; extraction selectors no longer match
- **System Behavior:** Extraction returns partial or empty data; user sees "Unknown Company" / "Unknown Position" in modal; user must manually enter data; system logs extraction failure for developer review

**EC-BR-004: Browser Extension Disabled**
- **Scenario:** User disables extension or extension crashes
- **System Behavior:** No capture occurs; applications submitted normally; user must manually add applications via dashboard; no data loss for previously captured applications

**EC-BR-005: Backend Service Not Running**
- **Scenario:** User submits application but local backend service is offline
- **System Behavior:** Extension shows error toast: "Cannot connect to tracking service"; offers "Retry" and "Save for Later" buttons; if "Save for Later" clicked, data stored in browser local storage; on next backend connection, stored data synced automatically

**EC-BR-006: Duplicate Capture from Same Page**
- **Scenario:** User re-submits same application form (e.g., after error, or testing)
- **System Behavior:** Duplicate detection (ARM-002) identifies existing application; user prompted: "Application already tracked. View existing or create new?"

---

### 2.2 Email Ingestion Edge Cases

**EC-EI-001: Non-Standard Email Format**
- **Scenario:** Confirmation email with unusual structure; no subject line patterns match; body is plain text without standard formatting
- **System Behavior:** Email not classified as confirmation; remains unread; not processed; no application created; user must manually add application if desired

**EC-EI-002: Email with Multiple Job Applications**
- **Scenario:** Single email confirms multiple applications (e.g., batch submission confirmation)
- **System Behavior:** Parser attempts to extract all job titles mentioned; creates separate application records for each identifiable job; if cannot disambiguate, creates single record with note: "Multiple positions mentioned: [list]"

**EC-EI-003: Forwarded Confirmation Email**
- **Scenario:** User forwards confirmation from another email account; email has "Fwd:" prefix, forwarding headers
- **System Behavior:** Parser strips "Fwd:" prefix from subject; extracts original sender from forwarded headers if available; processes as normal confirmation email

**EC-EI-004: HTML-Only Email with No Plain Text**
- **Scenario:** Email body is HTML only, no plain text alternative
- **System Behavior:** Parser extracts text from HTML using BeautifulSoup or similar; strips tags; processes extracted text; if HTML unparseable (malformed), email skipped with log entry

**EC-EI-005: Email in Wrong Folder**
- **Scenario:** Confirmation email arrives in inbox but user configured system to monitor "Job Applications" folder
- **System Behavior:** Email not processed; user must manually move email to monitored folder OR reconfigure email settings to monitor multiple folders OR manually add application

**EC-EI-006: IMAP Connection Lost Mid-Polling**
- **Scenario:** Network interruption or email server maintenance during polling
- **System Behavior:** Polling attempt fails; error logged; system waits for next polling interval; no data loss; when connection restored, resumes polling; unread emails still processed on next successful poll

**EC-EI-007: Email Arrives Before Browser Capture**
- **Scenario:** Email confirmation arrives within seconds of form submission; browser capture also occurs
- **System Behavior:** Two capture events for same application; duplicate detection (ARM-002) identifies match by job_title, company_name, and timestamp proximity (<5 min); system presents user with: "Application already captured via browser. Merge or keep separate?"

**EC-EI-008: Authentication Token Expires**
- **Scenario:** OAuth token or IMAP credentials expire after initial setup
- **System Behavior:** Polling fails with authentication error; system notifies user: "Email connection lost. Please re-authenticate."; polling paused until user re-enters credentials

---

### 2.3 Job Posting Scraper Edge Cases

**EC-JS-001: URL Returns 404**
- **Scenario:** Job posting removed or URL invalid
- **System Behavior:** Scrape fails with reason "HTTP_404"; application record still exists with available metadata (title, company from capture source); analysis cannot run; user notified: "Job posting no longer available at URL."

**EC-JS-002: Paywall or Login Required**
- **Scenario:** Job posting requires authentication to view (e.g., LinkedIn jobs requiring login)
- **System Behavior:** Scrape returns login page HTML; content extraction fails to find job data; scrape marked as failed with reason "AUTHENTICATION_REQUIRED"; user notified: "Job posting requires login. Cannot scrape automatically."; user can manually copy/paste job description into notes field

**EC-JS-003: Rate Limiting Triggered**
- **Scenario:** User adds 50 applications rapidly; all queue for scraping; domain rate limits hit
- **System Behavior:** Requests delayed according to rate limit (max 10/min per domain); scraping jobs processed over 5+ minutes; user sees "Scraping in progress..." status; no failures; all eventually processed

**EC-JS-004: JavaScript-Rendered Content**
- **Scenario:** Job posting page requires JavaScript execution to render content (SPA)
- **System Behavior:** Simple HTTP fetch returns minimal HTML skeleton; content extraction finds no job data; scrape marked as incomplete; system logs warning for potential future headless browser implementation; user notified: "Could not extract job details. Page may require JavaScript."

**EC-JS-005: Redirect Chain**
- **Scenario:** URL redirects multiple times before reaching final job posting
- **System Behavior:** HTTP client follows up to 5 redirects; final URL stored as final_url in scraped_postings; if redirect limit exceeded, scrape fails with reason "TOO_MANY_REDIRECTS"

**EC-JS-006: Extremely Large HTML**
- **Scenario:** Job posting page includes large embedded assets or very long description (>5MB HTML)
- **System Behavior:** HTTP client enforces 10MB response size limit; if exceeded, connection terminated and scrape fails with reason "RESPONSE_TOO_LARGE"; user notified: "Job posting page too large to process."

**EC-JS-007: No Job Description Found**
- **Scenario:** HTML successfully fetched but content extraction finds no description text
- **System Behavior:** Job posting record created with null description; extraction marked as partial success; AI analysis skipped or uses only job_title for analysis; user can manually paste description into notes

**EC-JS-008: Duplicate URL with Different Query Params**
- **Scenario:** Same job posting URL with different tracking parameters (e.g., ?source=linkedin vs ?source=indeed)
- **System Behavior:** URL normalization removes query parameters except essential ones (job ID, posting ID); deduplication check (JS-002) matches normalized URL; existing scraped content reused

---

### 2.4 Resume Parsing Edge Cases

**EC-RP-001: Scanned PDF Resume**
- **Scenario:** User uploads PDF that is image-based (scanned document) with no text layer
- **System Behavior:** Text extraction (RP-002) finds no text; parsing fails with error: "PDF contains no extractable text. Please use a text-based PDF or run OCR first."; resume record marked as failed; user must re-upload text-based version

**EC-RP-002: Password-Protected Document**
- **Scenario:** User uploads password-protected PDF or DOCX
- **System Behavior:** File access fails; parsing fails with error: "Document is password-protected. Please remove password and re-upload."; resume record marked as failed

**EC-RP-003: Unconventional Resume Format**
- **Scenario:** Resume with no clear sections, highly creative layout, or non-standard structure
- **System Behavior:** Section identification (RP-003) finds no matching headers; entire content placed in "other" section; structured extraction (RP-004) attempts to find skills and experience via pattern matching; if fails, stores raw text; AI analysis still runs but with lower confidence

**EC-RP-004: Multi-Page Resume with Headers/Footers**
- **Scenario:** Resume spans multiple pages with repeated name/contact info in headers/footers
- **System Behavior:** Text extraction includes headers/footers; section identification may misidentify repeated contact info; structured extraction filters duplicates by storing unique values only

**EC-RP-005: Resume in Unsupported Language**
- **Scenario:** User uploads resume in non-English language
- **System Behavior:** Text extraction succeeds; section identification fails (English keyword matching); structured extraction fails; raw text stored; user notified: "Resume appears to be in a non-English language. Analysis may be inaccurate."; AI analysis may still run but results unreliable

**EC-RP-006: Empty or Corrupted File**
- **Scenario:** File upload succeeds but file is corrupted or empty
- **System Behavior:** Text extraction fails or returns empty string; parsing fails with error: "Resume appears to be empty or corrupted. Please re-upload."; resume record marked as failed

**EC-RP-007: Multiple Resume Uploads in Quick Succession**
- **Scenario:** User uploads new resume while previous resume still parsing
- **System Behavior:** New upload queues independently; previous resume parsing continues; upon completion, previous marked as archived (is_active=false); new resume becomes active when parsing completes

---

### 2.5 AI Analysis Engine Edge Cases

**EC-AI-001: API Key Invalid or Missing**
- **Scenario:** LLM API key not configured or invalid
- **System Behavior:** Analysis fails immediately with error: "AI service not configured. Please add API key in settings."; analysis job marked as failed; user directed to settings page

**EC-AI-002: Rate Limit Exceeded**
- **Scenario:** User triggers analysis for many applications simultaneously; API rate limit hit
- **System Behavior:** API returns 429 status; analysis jobs retried with exponential backoff (1min, 5min, 15min); user sees "Analysis in progress (queued due to rate limit)" status; eventually all complete

**EC-AI-003: API Returns Non-JSON Response**
- **Scenario:** LLM returns plain text or malformed JSON
- **System Behavior:** Response parsing (AI-004) attempts to extract JSON from markdown code blocks; if fails, analysis marked as failed with reason "INVALID_RESPONSE"; user notified: "AI analysis failed. Please retry."; user can manually retry

**EC-AI-004: Extremely Low Match Score**
- **Scenario:** Resume has no relevant skills/experience for job; AI returns match score of 0-10
- **System Behavior:** Score stored as-is; user sees low score; missing_qualifications list is extensive; system does not suppress or hide low scores; user informed of significant mismatch

**EC-AI-005: Analysis Timeout**
- **Scenario:** API request hangs; no response after 60 seconds
- **System Behavior:** Request times out; retry once after 10 seconds; if second timeout, analysis marked as failed with reason "TIMEOUT"; user can manually retry

**EC-AI-006: Incomplete Job or Resume Data**
- **Scenario:** Job posting has only title and company (no description); resume has only skills (no experience)
- **System Behavior:** Analysis runs with available data; prompt includes note about missing sections; LLM provides best-effort analysis; match score may be less reliable; results include disclaimer: "Analysis based on limited data."

**EC-AI-007: API Cost Limit Reached**
- **Scenario:** User has configured API usage limit; limit exceeded
- **System Behavior:** Analysis job rejected before API call with error: "API usage limit reached. Increase limit in settings or wait for quota reset."; analysis not attempted

---

### 2.6 Application Record Manager Edge Cases

**EC-ARM-001: Duplicate Application Detection - User Chooses to Create Anyway**
- **Scenario:** Duplicate detected; user opts to create duplicate record
- **System Behavior:** New application record created despite duplicate; no linking between duplicates; both appear in dashboard; user responsible for managing duplicates

**EC-ARM-002: Conflicting Status Updates**
- **Scenario:** User updates status in UI; simultaneously, email ingestion attempts to update same application status
- **System Behavior:** Last-write-wins; most recent update based on timestamp persists; both status changes logged in timeline; user sees final status; no data corruption

**EC-ARM-003: Application Deleted with Linked Records**
- **Scenario:** User deletes application that has linked job posting, analysis results, timeline events
- **System Behavior:** Soft delete (default): Application marked deleted; linked records remain but application excluded from queries; Hard delete (if configured): Cascade delete removes timeline events and analysis results; job posting remains (may be linked to other applications)

**EC-ARM-004: Manual Entry with Invalid Data**
- **Scenario:** User manually enters application with future date or invalid company name (special characters, excessive length)
- **System Behavior:** Validation enforces: application_date cannot be future date (error: "Application date cannot be in the future"); company_name max length 200 chars (error: "Company name too long"); job_title max length 300 chars (error: "Job title too long"); special characters allowed in names

**EC-ARM-005: No Job URL Provided**
- **Scenario:** Application created without job_posting_url (manual entry or email didn't include URL)
- **System Behavior:** Application saved with job_posting_url=null; scraping does not occur; AI analysis cannot run (requires job description); user can manually add URL later to trigger scraping; user can paste job description into notes as workaround

---

### 2.7 Data Export Edge Cases

**EC-EX-001: Export with No Applications**
- **Scenario:** User requests export but no applications match filters
- **System Behavior:** Empty CSV generated with headers only OR JSON with empty array; file still downloadable; user notified: "Export complete. 0 records matched filters."

**EC-EX-002: Large Export (>10,000 Records)**
- **Scenario:** User exports all applications; very large dataset
- **System Behavior:** Export job queued instead of immediate; user sees "Export in progress..." message; file generated asynchronously; user notified when complete (email or dashboard notification); download link provided; CSV may be split into multiple files if exceeds 50MB

**EC-EX-003: Special Characters in Export Data**
- **Scenario:** Application notes or job descriptions contain commas, quotes, newlines, unicode characters
- **System Behavior:** CSV properly escapes special characters (double quotes for quotes, quoted fields for commas); unicode characters preserved with UTF-8 encoding; Excel compatibility maintained with BOM

**EC-EX-004: Export During Active Import**
- **Scenario:** User exports while system actively ingesting emails or scraping jobs
- **System Behavior:** Export reflects current database state at time of export query; newly created records during export not included; no data consistency issues; export file may be slightly stale

---

### 2.8 Dashboard / View Layer Edge Cases

**EC-DV-001: Search Query with Special Characters**
- **Scenario:** User searches for "C++ Developer" or "AT&T"
- **System Behavior:** Special characters treated as literals in search; wildcard characters (%, _) escaped if using SQL LIKE; regex characters escaped if using regex search; search executes successfully

**EC-DV-002: No Applications Exist**
- **Scenario:** New user accesses dashboard with zero applications
- **System Behavior:** Dashboard displays empty state message: "No applications tracked yet. Get started by installing the browser extension or manually adding an application."; includes links to setup instructions

**EC-DV-003: Concurrent Users (Single-User System)**
- **Scenario:** User opens dashboard in multiple browser tabs/windows simultaneously
- **System Behavior:** Each tab/window queries backend independently; no real-time synchronization; user must manually refresh to see changes from other tabs; no data corruption; last-write-wins for any update conflicts

**EC-DV-004: Extremely Long Job Title or Company Name**
- **Scenario:** Job title or company name exceeds typical display width (>100 characters)
- **System Behavior:** UI truncates display with ellipsis; full text visible on hover or in detail view; truncation does not affect stored data; search matches full text

**EC-DV-005: Filter Combination Returns No Results**
- **Scenario:** User applies filters (e.g., status=offer_received AND date range last 7 days) that match no applications
- **System Behavior:** Dashboard displays: "No applications match current filters. Try adjusting your filters."; filters remain active; user can clear filters to see all applications

---

## 3. Explicit Non-Requirements

The following capabilities are explicitly OUT OF SCOPE for the MVP and will NOT be implemented:

**NR-001: Multi-User Support**
- No user authentication, login, or account management
- No role-based access control or permissions
- No ability to share applications or collaborate with others
- Single-user deployment only

**NR-002: Cloud Synchronization**
- No cloud storage or backup of application data
- No cross-device synchronization
- Data stored locally only; user responsible for backups

**NR-003: Mobile Application**
- No native mobile app (iOS/Android)
- No mobile-responsive web interface
- Desktop browser-based interface only

**NR-004: Real-Time Notifications**
- No push notifications for status changes or deadlines
- No email/SMS alerts for interview reminders
- No desktop notifications for new applications captured

**NR-005: Interview Scheduling Integration**
- No calendar integration (Google Calendar, Outlook)
- No automatic interview scheduling or booking
- No meeting invite parsing or extraction

**NR-006: Communication Tracking**
- No email thread tracking or conversation history
- No recruiter contact management
- No tracking of phone calls or messages beyond manual timeline entries

**NR-007: Document Management**
- No storage of multiple resume versions
- No cover letter management or versioning
- No storage of reference letters, portfolios, or supporting documents

**NR-008: Advanced Analytics**
- No aggregate statistics or trend analysis
- No funnel visualization or conversion rates
- No time-to-hire metrics or benchmarking

**NR-009: Job Discovery/Search**
- No integrated job board search or scraping
- No job recommendation engine
- No job alerts or automated job matching

**NR-010: Application Autofill**
- No automation of filling out application forms
- No browser automation for application submission
- Tracking only, no submission assistance

**NR-011: Salary Negotiation Tools**
- No salary research or market rate comparison
- No negotiation script generation
- No compensation package analysis

**NR-012: Cover Letter Generation**
- No AI-generated cover letters
- No cover letter templates or customization
- No cover letter storage or versioning

**NR-013: Interview Preparation**
- No interview question database or generation
- No company research aggregation
- No mock interview or practice tools

**NR-014: Networking/Referral Tracking**
- No contact relationship management
- No referral source tracking
- No networking event or connection logging

**NR-015: Team Collaboration**
- No sharing applications with career coaches or mentors
- No commenting or feedback from others
- No permission management for shared access

**NR-016: Automated Follow-Up**
- No automated follow-up email generation
- No reminder scheduling for follow-ups
- No templates for thank-you notes or follow-up messages

**NR-017: Skill Gap Training**
- No recommendations for courses or training to fill skill gaps
- No integration with learning platforms
- No skill development tracking

**NR-018: Company Research**
- No automatic company information lookup
- No Glassdoor/LinkedIn company data integration
- No company culture or review aggregation

**NR-019: Application Deadline Tracking**
- No deadline reminders or alerts
- No countdown timers or urgency indicators
- No application prioritization based on deadlines

**NR-020: Multiple Resume Management**
- No A/B testing of different resume versions
- No tailored resume generation per application
- Single active resume only

**NR-021: Browser Support Beyond Chromium**
- No Firefox extension
- No Safari extension
- Chromium-based browsers only (Chrome, Edge, Brave)

**NR-022: Internationalization**
- No multi-language support beyond English
- No localization for different regions
- English-only interface and content

**NR-023: Data Import from Other Tools**
- No import from spreadsheets or other tracking tools
- No migration tools from competitors
- Manual data entry only for existing applications

**NR-024: API for Third-Party Integrations**
- No public API for external tools
- No webhooks or automation endpoints
- Closed system with no external integrations

**NR-025: Advanced Search**
- No full-text search with ranking
- No fuzzy matching or spell correction
- Basic keyword matching only

---

## 4. Acceptance Criteria

### 4.1 Browser Event Capture Subsystem

**AC-BR-001: Extension Installation**
- [ ] Extension installs successfully on Chrome and Edge browsers
- [ ] Extension icon visible in toolbar after installation
- [ ] Extension popup accessible by clicking icon
- [ ] Extension configuration page accessible from popup

**AC-BR-002: Job Board Detection**
- [ ] Extension correctly identifies LinkedIn Jobs pages
- [ ] Extension correctly identifies Indeed job pages
- [ ] Extension correctly identifies Greenhouse ATS-based job pages
- [ ] Extension remains dormant on non-job-board sites

**AC-BR-003: Application Submission Capture**
- [ ] Form submission detected on LinkedIn within 2 seconds
- [ ] Form submission detected on Indeed within 2 seconds
- [ ] Form submission detected on Greenhouse pages within 2 seconds
- [ ] Confirmation modal appears after submission detection

**AC-BR-004: Metadata Extraction Accuracy**
- [ ] Job title extracted correctly in 90%+ of test cases across supported job boards
- [ ] Company name extracted correctly in 90%+ of test cases
- [ ] Job posting URL captured with cleaned query parameters
- [ ] Application timestamp recorded in ISO 8601 format

**AC-BR-005: User Confirmation Flow**
- [ ] Modal displays within 2 seconds of submission
- [ ] All extracted fields are editable
- [ ] Confirm button saves data and closes modal
- [ ] Cancel button discards data without saving
- [ ] Missing fields clearly indicated with visual cues

**AC-BR-006: Backend Communication**
- [ ] Data successfully transmitted to backend on Confirm
- [ ] 201 Created response received and handled
- [ ] Connection errors display user-friendly error message
- [ ] Retry logic attempts second request after 5 seconds on failure
- [ ] "Save for Later" option stores data in browser local storage when backend unavailable

---

### 4.2 Email Ingestion Subsystem

**AC-EI-001: Email Connection**
- [ ] IMAP connection successfully established with valid credentials
- [ ] Invalid credentials result in clear error message
- [ ] Target folder accessible or created if not exists
- [ ] Credentials encrypted and stored securely

**AC-EI-002: Email Polling**
- [ ] Polling occurs at configured interval (default 5 minutes)
- [ ] Unread emails retrieved from target folder
- [ ] Polling continues after temporary connection failures
- [ ] Polling recovers gracefully after network interruptions

**AC-EI-003: Confirmation Detection**
- [ ] Confirmation emails from LinkedIn detected correctly
- [ ] Confirmation emails from Indeed detected correctly
- [ ] Confirmation emails from Greenhouse-based systems detected correctly
- [ ] Non-confirmation emails ignored and remain unread
- [ ] Detection accuracy > 85% across common confirmation email formats

**AC-EI-004: Email Parsing**
- [ ] Company name extracted from 80%+ of confirmation emails
- [ ] Job title extracted from 80%+ of confirmation emails
- [ ] Job posting URLs extracted when present in email body
- [ ] Application timestamp set to email received timestamp
- [ ] Records flagged as "needs_review" when critical data missing

**AC-EI-005: Email State Management**
- [ ] Processed emails marked as read in IMAP
- [ ] Duplicate processing prevented via local UID tracking
- [ ] Email moved to "Processed Applications" folder when configured
- [ ] Processing failures logged without halting email ingestion

---

### 4.3 Job Posting Scraper Subsystem

**AC-JS-001: Scrape Queuing**
- [ ] Job URLs successfully added to scraping queue
- [ ] Queue entries include source, priority, and timestamp
- [ ] Invalid URLs rejected with clear error messages
- [ ] Manual entries assigned high priority

**AC-JS-002: URL Deduplication**
- [ ] Duplicate URLs detected within 7-day window
- [ ] Normalized URLs match (query params removed)
- [ ] Recent duplicates skip re-scraping and reuse existing data
- [ ] Old duplicates (>7 days) trigger re-scrape

**AC-JS-003: HTTP Fetch**
- [ ] Rate limiting enforced: max 10 requests per minute per domain
- [ ] Requests timeout after 30 seconds
- [ ] Redirects followed up to 5 times
- [ ] User-Agent header includes standard browser signature
- [ ] Failed requests retried with exponential backoff (1min, 5min, 15min)

**AC-JS-004: HTML Storage**
- [ ] Raw HTML stored in database with metadata
- [ ] Fetch timestamp recorded
- [ ] HTTP status code stored
- [ ] Final URL (post-redirect) stored
- [ ] Content hash generated for change detection

**AC-JS-005: Content Extraction**
- [ ] Job title extracted successfully in 85%+ of test cases
- [ ] Company name extracted in 85%+ of test cases
- [ ] Job description extracted as coherent text block
- [ ] Requirements section identified and extracted when present
- [ ] Salary range extracted when present (regex patterns match common formats)
- [ ] Location extracted when present
- [ ] Employment type extracted when present
- [ ] Partial extractions stored when complete extraction fails

**AC-JS-006: Failure Handling**
- [ ] 404 errors result in "HTTP_404" failure reason
- [ ] Timeout errors result in "TIMEOUT" failure reason
- [ ] Connection errors result in "CONNECTION_ERROR" failure reason
- [ ] Failed scrapes retry up to 3 times
- [ ] Permanently failed scrapes notify user after final attempt
- [ ] Application records exist even when scraping fails

---

### 4.4 Resume Parsing Subsystem

**AC-RP-001: Resume Upload**
- [ ] PDF files < 10MB upload successfully
- [ ] DOCX files < 10MB upload successfully
- [ ] TXT files < 10MB upload successfully
- [ ] Files > 10MB rejected with clear error message
- [ ] Unsupported formats (JPG, PNG, etc.) rejected with clear error message
- [ ] Resume record created in database on successful upload

**AC-RP-002: Text Extraction**
- [ ] Text extracted from PDF files with text layer
- [ ] Text extracted from DOCX files
- [ ] TXT files read correctly with UTF-8 encoding
- [ ] Image-based PDFs fail with "no extractable text" error
- [ ] Password-protected files fail with appropriate error message
- [ ] Whitespace normalized in extracted text

**AC-RP-003: Section Identification**
- [ ] Contact info section identified in 80%+ of test resumes
- [ ] Experience section identified in 90%+ of test resumes
- [ ] Education section identified in 90%+ of test resumes
- [ ] Skills section identified in 85%+ of test resumes
- [ ] Unstructured resumes place content in "other" section without failure

**AC-RP-004: Structured Extraction**
- [ ] Email address extracted from contact section (regex pattern match)
- [ ] Phone number extracted from contact section
- [ ] Skills list extracted and stored as array
- [ ] Experience entries extracted with company, title, date range
- [ ] Education entries extracted with institution, degree, major
- [ ] Failed structured extractions fall back to raw text storage

**AC-RP-005: Resume Versioning**
- [ ] Previous resume marked as archived (is_active=false) when new resume uploaded
- [ ] New resume set as active (is_active=true)
- [ ] Only active resume used for AI analysis
- [ ] Archived resumes remain accessible for historical reference

---

### 4.5 AI Analysis Engine Subsystem

**AC-AI-001: Analysis Triggering**
- [ ] Analysis automatically triggered when application created with linked job posting
- [ ] Analysis manually triggered via "Run Analysis" button in UI
- [ ] Analysis not triggered when no active resume exists (error displayed)
- [ ] Analysis not triggered when job posting has no description (error displayed)

**AC-AI-002: Prompt Construction**
- [ ] Prompt includes resume summary, skills, experience, education
- [ ] Prompt includes job title, description, requirements, nice-to-have
- [ ] Prompt specifies JSON output format
- [ ] Prompt truncated to ~12,000 tokens if combined input too large
- [ ] Missing resume sections noted in prompt

**AC-AI-003: API Communication**
- [ ] API call successful with valid credentials
- [ ] API timeout set to 60 seconds
- [ ] Temperature set to 0.3 for deterministic output
- [ ] Max tokens set to 2000
- [ ] Rate limit errors (429) trigger exponential backoff retry
- [ ] Retry logic attempts up to 3 times before permanent failure

**AC-AI-004: Response Parsing**
- [ ] JSON response parsed successfully
- [ ] match_score validated as integer 0-100
- [ ] matched_qualifications parsed as array of strings
- [ ] missing_qualifications parsed as array of strings
- [ ] skill_suggestions parsed as array of strings
- [ ] Invalid match_score values clamped to 0-100 range
- [ ] Missing fields result in analysis failure with clear error

**AC-AI-005: Analysis Storage**
- [ ] Analysis results stored in analysis_results table
- [ ] Application record updated with analysis_completed flag
- [ ] Analyzed_at timestamp recorded
- [ ] Model_used field populated with LLM identifier
- [ ] Analysis results linked to application via application_id

**AC-AI-006: Re-analysis**
- [ ] Previous analysis archived when re-analysis triggered
- [ ] New analysis results replace displayed results
- [ ] Re-analysis allowed unlimited times
- [ ] Analysis history preserved for audit purposes

---

### 4.6 Application Record Manager Subsystem

**AC-ARM-001: Record Creation**
- [ ] Application created with required fields: company_name, job_title, application_date
- [ ] Optional fields stored when provided: job_posting_url, notes
- [ ] Generated fields populated: application_id (UUID), created_at, updated_at
- [ ] Default status set to "applied"
- [ ] Source field populated from capture origin (browser/email/manual)
- [ ] 400 error returned when required fields missing

**AC-ARM-002: Duplicate Detection**
- [ ] Duplicate detected when company_name + job_title match within 7 days
- [ ] Duplicate detected when job_posting_url matches (normalized)
- [ ] User prompted with options: view existing, create anyway, update existing
- [ ] Duplicate check does not prevent manual creation if user confirms

**AC-ARM-003: Job Posting Linkage**
- [ ] Application record updated with posting_id after successful scrape
- [ ] posting_linked_at timestamp recorded
- [ ] AI analysis triggered after linkage (if auto-analyze enabled)
- [ ] Linkage failure logged but does not halt scraping

**AC-ARM-004: Status Management**
- [ ] Status values validated against allowed list
- [ ] Status update creates timeline event
- [ ] status_updated_at timestamp recorded on change
- [ ] Invalid status values return 400 error
- [ ] Application_id not found returns 404 error

**AC-ARM-005: Notes Management**
- [ ] Notes stored as markdown text
- [ ] Notes length limited to 10,000 characters
- [ ] Notes exceeding limit return 400 error
- [ ] Empty notes clear existing notes field
- [ ] updated_at timestamp updated on notes change

**AC-ARM-006: Application Deletion**
- [ ] Soft delete sets deleted_at timestamp and is_deleted=true
- [ ] Hard delete removes record and cascades to linked records (if configured)
- [ ] Deleted applications excluded from dashboard queries
- [ ] Linked job postings remain for future use
- [ ] Application_id not found returns 404 error

---

### 4.7 Timeline & Event Tracking Subsystem

**AC-TL-001: Event Creation**
- [ ] Timeline event created for each status change
- [ ] Event type validated against allowed types
- [ ] event_data stored as JSON with correct structure per event type
- [ ] occurred_at timestamp defaults to current time if not provided
- [ ] Invalid application_id returns 400 error

**AC-TL-002: Timeline Retrieval**
- [ ] Events retrieved in descending order (most recent first)
- [ ] Date range filter applied when specified
- [ ] Empty array returned for application with no events
- [ ] Event objects include: event_id, event_type, event_data, occurred_at

**AC-TL-003: Manual Events**
- [ ] Manual events created via UI with user-specified details
- [ ] Manual events prefixed with "manual_" to distinguish from system events
- [ ] event_data includes manually_added_by_user flag
- [ ] Manual events displayed alongside automatic events

---

### 4.8 Data Export Subsystem

**AC-EX-001: Export Request**
- [ ] CSV format supported
- [ ] JSON format supported
- [ ] Date range filter applied when specified
- [ ] Status filter applied when specified
- [ ] include_analysis flag controls analysis data inclusion
- [ ] Invalid format returns 400 error

**AC-EX-002: CSV Export**
- [ ] CSV includes header row with column names
- [ ] Required columns present: company_name, job_title, application_date, status, source
- [ ] Analysis columns included when include_analysis=true
- [ ] Special characters (commas, quotes, newlines) properly escaped
- [ ] UTF-8 encoding with BOM for Excel compatibility
- [ ] Empty fields rendered as empty strings

**AC-EX-003: JSON Export**
- [ ] JSON formatted as array of application objects
- [ ] Nested objects included for job_posting and analysis_results when applicable
- [ ] JSON properly formatted with 2-space indentation
- [ ] UTF-8 encoding
- [ ] Null fields serialized as null in JSON

**AC-EX-004: File Delivery**
- [ ] Export file downloadable immediately after generation
- [ ] Filename includes timestamp: job_tracker_export_[timestamp].csv
- [ ] Success message displays record count
- [ ] Export files stored for 24 hours for re-download
- [ ] Cleanup job removes export files older than 24 hours

---

### 4.9 Dashboard / View Layer Subsystem

**AC-DV-001: Application List**
- [ ] Applications displayed in paginated list (default 25 per page)
- [ ] Default sort by application_date descending
- [ ] Sortable by: application_date, company_name, job_title, status, match_score
- [ ] Filterable by status (multi-select)
- [ ] Filterable by date range
- [ ] Filterable by company (search)
- [ ] Pagination metadata includes: total_count, page, page_size, total_pages
- [ ] Empty state displayed when no applications exist

**AC-DV-002: Application Detail**
- [ ] Detail view displays all application fields
- [ ] Linked job posting data displayed (if available)
- [ ] AI analysis results displayed (if available)
- [ ] Timeline events displayed in descending order
- [ ] 404 error for non-existent application_id
- [ ] Null job posting and analysis fields handled gracefully

**AC-DV-003: Dashboard Statistics**
- [ ] Total applications count displayed
- [ ] Applications by status breakdown displayed
- [ ] Average match score displayed (for analyzed applications)
- [ ] Recent activity counts (7-day, 30-day) displayed
- [ ] Top companies list displayed
- [ ] Statistics handle zero applications gracefully

**AC-DV-004: Search Functionality**
- [ ] Case-insensitive search across company_name, job_title, notes
- [ ] Partial matching supported (LIKE behavior)
- [ ] Search scope selectable: all, company, title
- [ ] Queries < 2 characters return 400 error
- [ ] Empty results return empty array with total_count=0
- [ ] Results sorted by relevance (exact matches first)

---

## Summary

This functional requirements specification provides a complete, detailed blueprint for implementing the Job Application Tracker MVP. Each requirement is designed to be:

- **Testable:** Clear inputs, outputs, and success/failure criteria
- **Unambiguous:** Different developers should implement the same behavior
- **Complete:** Covers happy paths, edge cases, and failure scenarios
- **Scoped:** Limited to MVP features with explicit non-requirements listed

The acceptance criteria provide objective measures for determining when each subsystem is complete and correct, ensuring consistent implementation across the development team.