# Job Application Tracker - User Flows & Interaction Design

**Document Version:** 1.0  
**Last Updated:** December 10, 2025  
**Status:** Final UX Specification

---

## Table of Contents

1. [Overview](#1-overview)
2. [Core User Flows](#2-core-user-flows)
3. [Error & Edge Case Flows](#3-error--edge-case-flows)
4. [System Interaction Patterns](#4-system-interaction-patterns)
5. [State Transitions](#5-state-transitions)

---

## 1. Overview

### Design Principles

**Minimize User Friction**
- Capture should be 1-2 clicks (browser extension)
- Zero-config email monitoring (after initial setup)
- Sensible defaults for all fields

**Progressive Enhancement**
- System works with minimal data
- Additional data improves experience
- Optional features don't block core flow

**Fail Gracefully**
- Partial data better than blocking user
- `needs_review` flag for uncertain data
- Timeline events show what went wrong

**Async by Default**
- Never block on scraping/parsing/analysis
- Show progress indicators
- Notify on completion

---

## 2. Core User Flows

### 2.1 Browser Extension Capture

**User Story:** As a job seeker, I want to quickly save applications as I submit them on job boards.

**Flow:**

1. **User submits application on job board**
   - User fills out application form
   - User clicks "Submit Application"
   - Job board shows confirmation

2. **Extension detects submission**
   - Content script detects form submission
   - Extracts: company name, job title, URL
   - Shows popup: "Application detected"

3. **User confirms capture**
   - Popup shows extracted data
   - User can edit if incorrect
   - User clicks "Save Application"

4. **Extension sends to backend**
   - POST /capture/browser
   - Extension shows "Saving..."

5. **Backend processes request**
   ```
   IF duplicate detected THEN
     Return 409 with duplicate details
   ELSE
     Create application with defaults
     Set needs_review if data uncertain
     Create timeline event "application_submitted"
     Enqueue scraper job (priority 50)
     Return 201 with application ID
   END IF
   ```

6. **Extension shows result**
   - Success: "Application saved! We'll fetch details."
   - Duplicate: Modal with options:
     - "View existing application"
     - "Create anyway" (sets force_create=true)
   - Error: "Failed to save. Try manual entry."

7. **Background scraping (async)**
   - Scraper worker dequeues job
   - Fetches job posting HTML
   - Extracts structured data
   - Updates application.posting_id
   - Creates timeline event "job_scraped"

8. **Background analysis (async, if enabled)**
   - If auto_analyze=true AND active resume exists
   - Analysis worker dequeues job
   - Generates match score and suggestions
   - Updates application.analysis_id
   - Creates timeline event "analysis_completed"

**Timeline:**
- Immediate: Application saved (1-2s)
- 10-60s: Job posting scraped
- 30-120s: Analysis completed (if enabled)

**Edge Cases:**
- Unknown company/title → Use "Unknown", set needs_review=true
- Invalid URL → Store anyway, scraping fails gracefully
- Extension offline → Queue locally, sync on reconnect
- Backend down → Queue locally, retry every 30s

---

### 2.2 Email Ingestion

**User Story:** As a job seeker, I want the system to automatically detect confirmation emails.

**Flow:**

1. **User receives confirmation email**
   - Job board sends email: "Thank you for applying..."
   - Email lands in inbox

2. **Email service polls inbox** (every 5 minutes)
   - Connects to IMAP server
   - Fetches unread emails in configured folder

3. **Email service parses email**
   - Checks subject line patterns (e.g., "Application received")
   - Checks sender domain (e.g., @lever.co, @greenhouse.io)
   - Extracts: company, title, URL, date
   - Calculates confidence score

4. **Email service sends to backend**
   - POST /capture/email (with internal token)
   - Includes email_uid for idempotency

5. **Backend processes email**
   ```
   IF email_uid already processed THEN
     Return 200 with skipped=true
   ELSE
     Check for duplicate application
     IF duplicate THEN
       Return 409 (but email service ignores this)
     ELSE
       Create application
       Set needs_review=true if low confidence
       Record email_uid
       Create timeline event "email_received"
       Enqueue scraper job (priority 25)
       Return 201
     END IF
   END IF
   ```

6. **Email service marks as read**
   - Mark email as read in IMAP
   - Log success

7. **Background processing (same as browser flow)**
   - Scraping → Analysis (if enabled)

**Timeline:**
- 0-5 min: Email detected (depends on poll)
- 10-60s: Job posting scraped
- 30-120s: Analysis completed (if enabled)

**Edge Cases:**
- Low confidence parsing → needs_review=true, user reviews
- Email already processed → Return 200, mark as read silently
- IMAP connection failure → Retry every 60s indefinitely
- IMAP auth failure → Stop polling, show error in settings

---

### 2.3 Manual Entry

**User Story:** As a job seeker, I want to manually enter applications the system didn't detect.

**Flow:**

1. **User opens dashboard**
   - Clicks "Add Application" button

2. **User fills form**
   - Company name (required)
   - Job title (required)
   - Application date (default: today)
   - Job posting URL (optional)
   - Status (default: applied)
   - Notes (optional)

3. **User submits form**
   - Frontend validates required fields
   - POST /applications

4. **Backend creates application**
   ```
   Validate required fields
   Check for duplicates (if URL provided)
   IF duplicate AND not force_create THEN
     Return 409
   ELSE
     Create application with source='manual'
     needs_review=false (user-provided trusted)
     Create timeline event "application_submitted"
     IF URL provided THEN
       Enqueue scraper job (priority 50)
     END IF
     Return 201
   END IF
   ```

5. **Frontend shows success**
   - Redirect to application detail page
   - Show success toast

6. **Background processing** (if URL provided)
   - Scraping → Analysis (if enabled)

**Timeline:**
- Immediate: Application created
- 10-60s: Job posting scraped (if URL provided)
- 30-120s: Analysis completed (if enabled & URL provided)

---

### 2.4 Resume Upload

**User Story:** As a job seeker, I want to upload my resume for AI analysis.

**Flow:**

1. **User opens resume management**
   - Clicks "Resumes" in navigation

2. **User uploads file**
   - Clicks "Upload Resume"
   - Selects .pdf, .docx, or .txt file
   - File size < 10MB

3. **Frontend uploads file**
   - POST /resumes/upload (multipart/form-data)
   - Shows upload progress bar

4. **Backend validates and saves**
   ```
   Validate file size (<10MB)
   Validate extension (.pdf, .docx, .txt)
   Validate MIME type matches extension
   IF invalid THEN
     Return 400 with specific error
   ELSE
     Save file to disk with UUID filename
     Set permissions chmod 600
     Create resume record (status='uploaded')
     Enqueue parser job
     Return 201 with resume ID
   END IF
   ```

5. **Frontend shows success**
   - Redirect to resume detail page
   - Shows status: "Parsing..."

6. **Background parsing (async)**
   - Parser worker dequeues job
   - Parses file (PDF → pdfplumber, DOCX → python-docx, TXT → encoding detection)
   - Extracts sections (experience, education, skills)
   - Stores resume_data
   - Archives previous active resume (if any)
   - Marks new resume as active
   - Updates status='parsed'
   - POST result to /internal/parser/results

7. **Frontend updates status**
   - Polls resume status every 5s
   - Shows "Parsed successfully!" on completion
   - Shows error message on failure

**Timeline:**
- Immediate: File uploaded (1-3s)
- 5-30s: Resume parsed

**Edge Cases:**
- Encrypted PDF → Fail with "Resume is password protected"
- Scanned PDF → Fail with "Resume is scanned image"
- Corrupted DOCX → Fail with "File corrupted"
- Section detection fails → Store raw text, set extraction_complete=false

---

### 2.5 Manual Analysis Trigger

**User Story:** As a job seeker, I want to analyze how well my resume matches a job.

**Flow:**

1. **User views application detail**
   - Sees "Analysis" section
   - Shows status: "Not analyzed" or "Analyzing..."

2. **User clicks "Analyze"**
   - Button only enabled if:
     - Active resume exists
     - Job posting exists (scraped)

3. **Frontend sends request**
   - POST /applications/{id}/analyze

4. **Backend validates and enqueues**
   ```
   Check active resume exists
   Check job posting exists
   IF preconditions not met THEN
     Return 400 with specific error
   ELSE
     Enqueue analysis job (priority=100)
     Return 202 with job ID
   END IF
   ```

5. **Frontend shows progress**
   - Shows "Analyzing..." with spinner
   - Polls job status every 5s

6. **Background analysis (async)**
   - Analysis worker dequeues job
   - Validates preconditions again
   - Fetches resume data and job posting
   - Builds prompt
   - Calls LLM API
   - Parses response
   - Stores analysis_result
   - Updates application.analysis_id
   - Creates timeline event "analysis_completed"
   - POST result to /internal/analysis/results

7. **Frontend shows results**
   - Redirects to analysis result page
   - Shows:
     - Match score (0-100)
     - Qualifications met (list)
     - Qualifications missing (list)
     - Suggestions (list)

**Timeline:**
- Immediate: Job enqueued (1s)
- 10-60s: Analysis completed

**Edge Cases:**
- No active resume → Error: "Upload resume before analyzing"
- No job posting → Error: "Scrape job posting before analyzing"
- API key missing → Error: "Configure LLM API key in settings"
- LLM timeout → Retry up to 3 times

---

### 2.6 Status Update

**User Story:** As a job seeker, I want to update application status as I progress.

**Flow:**

1. **User views application detail**
   - Sees current status badge

2. **User clicks status dropdown**
   - Shows options: Applied, Screening, Interview, Offer, Rejected, Withdrawn

3. **User selects new status**
   - Frontend sends immediately (no "Save" button)
   - PATCH /applications/{id}/status

4. **Backend updates status**
   ```
   Validate status is valid enum
   Load application with FOR UPDATE (optimistic lock)
   Check updated_at matches
   IF stale THEN
     Return 409 with current data
   ELSE
     Update status, updated_at
     Create timeline event "status_changed"
     Commit transaction
     Return 200
   END IF
   ```

5. **Frontend updates UI**
   - Updates status badge
   - Shows timeline event: "Status changed to Interview"
   - Shows success toast

**Timeline:**
- Immediate: Status updated (< 1s)

**Edge Cases:**
- Concurrent update → 409 Conflict, show current data, ask user to retry

---

### 2.7 Export Applications

**User Story:** As a job seeker, I want to export my applications for tracking in spreadsheet.

**Flow:**

1. **User clicks "Export"**
   - Selects format: CSV or JSON
   - Optionally filters by status/date

2. **Frontend requests export**
   - GET /export/applications.csv?status=applied,screening
   - Or GET /export/applications.json

3. **Backend generates export**
   ```
   Build query with filters
   Stream rows (for large datasets)
   Format as CSV or JSON
   Set Content-Disposition: attachment
   Return 200
   ```

4. **Browser downloads file**
   - Filename: applications_2025-12-10.csv
   - Opens in default CSV viewer or downloads

**Timeline:**
- Immediate: File downloads (1-5s depending on size)

---

## 3. Error & Edge Case Flows

### 3.1 Duplicate Detection (Browser)

**Scenario:** User applies to same job twice

**Flow:**

1. **Extension captures second application**
   - POST /capture/browser

2. **Backend detects duplicate**
   ```
   Find existing by company+title+date (±7 days)
   OR by URL
   Rank matches by confidence
   Return 409 with duplicate details
   ```

3. **Extension shows modal**
   - "Possible duplicate application"
   - Shows existing application:
     - Company, Title, Date
     - Link to view
   - Options:
     - "View existing" → Opens dashboard
     - "Create anyway" → Sets force_create=true, retries

4. **If user chooses "Create anyway"**
   - POST /capture/browser?force_create=true
   - Backend skips duplicate check
   - Creates application normally

---

### 3.2 Scraper Failure (CAPTCHA)

**Scenario:** Job board shows CAPTCHA

**Flow:**

1. **Scraper worker attempts to fetch**
   - HTTP GET to job posting URL
   - Detects CAPTCHA in response

2. **Worker marks job failed**
   ```
   Update queue job: status='failed', error_message='CAPTCHA detected'
   Create timeline event "job_scraped_failed"
   POST to /internal/scraper/results
   ```

3. **Backend processes failure**
   ```
   Update application
   Create timeline event with details
   ```

4. **User sees in timeline**
   - Event: "Job scraping failed: CAPTCHA detected"
   - Suggestion: "Paste job description manually"

5. **User can manually paste**
   - Clicks "Edit" on application
   - Pastes description into notes field
   - Or clicks "Retry scraping" (if issue resolved)

---

### 3.3 Resume Parsing Failure (Scanned PDF)

**Scenario:** User uploads scanned resume PDF

**Flow:**

1. **Parser worker attempts to parse**
   - Opens PDF with pdfplumber
   - Detects no extractable text (images only)

2. **Worker marks job failed**
   ```
   Update queue job: status='failed', error_message='Resume is scanned image'
   Update resume: status='failed', error_message='...'
   POST to /internal/parser/results
   ```

3. **Frontend shows error**
   - Polls resume status
   - Shows error: "Resume is scanned image - upload text PDF"
   - Shows "Upload new resume" button

4. **User uploads text-based PDF**
   - Follows normal upload flow
   - New resume replaces failed one

---

### 3.4 Analysis Failure (No API Key)

**Scenario:** User triggers analysis without configuring LLM API key

**Flow:**

1. **User clicks "Analyze"**
   - POST /applications/{id}/analyze

2. **Backend enqueues job**
   - Returns 202

3. **Analysis worker attempts processing**
   ```
   Fetch LLM API key from settings
   IF not found THEN
     Mark job failed
     error_message='LLM API key not configured'
     POST result
   END IF
   ```

4. **Frontend shows error**
   - Polls job status
   - Shows error in timeline: "Analysis failed: Configure LLM API key"
   - Shows link to settings

5. **User configures API key**
   - Navigates to Settings
   - Enters OpenAI or Anthropic API key
   - PATCH /settings validates key
   - Shows success

6. **User retries analysis**
   - Returns to application
   - Clicks "Analyze" again
   - Works this time

---

### 3.5 Email Service Connection Failure

**Scenario:** Email service can't connect to IMAP

**Flow:**

1. **Email service attempts connection**
   - Every 60 seconds
   - Connection refused or times out

2. **After 3 failures**
   - Logs WARNING
   - Continues retrying

3. **User checks settings**
   - Settings page shows:
     - Email monitoring: ⚠️ Connection issues
     - Last successful poll: 10 minutes ago
     - Error: "Cannot connect to imap.gmail.com:993"

4. **User fixes configuration**
   - Corrects IMAP server or port
   - PATCH /settings
   - Backend validates with test connection

5. **Email service reconnects**
   - Next poll succeeds
   - Settings shows: ✅ Connected

---

### 3.6 Optimistic Lock Conflict

**Scenario:** Two browser tabs update same application simultaneously

**Flow:**

1. **Tab A loads application**
   - GET /applications/123
   - Receives: {id: 123, status: 'applied', updated_at: '2025-12-10T10:00:00Z'}

2. **Tab B loads application**
   - Same response

3. **Tab A updates status to 'screening'**
   - PATCH /applications/123/status
   - Body: {status: 'screening', updated_at: '2025-12-10T10:00:00Z'}
   - Backend updates successfully
   - updated_at changes to '2025-12-10T10:01:00Z'

4. **Tab B updates status to 'interview'**
   - PATCH /applications/123/status
   - Body: {status: 'interview', updated_at: '2025-12-10T10:00:00Z'}
   - Backend detects stale updated_at
   - Returns 409 Conflict with current data

5. **Tab B shows modal**
   - "This application was updated in another tab"
   - Shows current status: 'screening'
   - Options:
     - "Refresh" → Reload application
     - "Override" → Retry with latest updated_at

---

## 4. System Interaction Patterns

### 4.1 Polling Pattern (Frontend → Backend)

**When to poll:**
- Resume parsing status (every 5s until complete/failed)
- Scraping job status (every 5s until complete/failed)
- Analysis job status (every 5s until complete/failed)

**Stop conditions:**
- Status becomes 'complete' or 'failed'
- User navigates away
- Max 5 minutes elapsed

**Example:**
```javascript
const pollJobStatus = async (jobId) => {
  const maxAttempts = 60; // 5 minutes
  let attempts = 0;
  
  while (attempts < maxAttempts) {
    const response = await fetch(`/queue/scraper/jobs/${jobId}`);
    const data = await response.json();
    
    if (data.status === 'complete' || data.status === 'failed') {
      return data;
    }
    
    await sleep(5000); // 5 seconds
    attempts++;
  }
  
  throw new Error('Polling timeout');
};
```

---

### 4.2 Callback Pattern (Workers → Backend)

**When workers complete jobs:**
- POST to /internal/{worker}/results
- Include: job_id, status, result_data, error_message
- Backend processes asynchronously
- Backend returns 200 immediately

**Retry logic:**
- Workers retry POST up to 3 times
- Backoff: 10s, 30s, 60s
- If all fail: Log CRITICAL, job stuck (watchdog cleanup)

---

### 4.3 Queue Processing Pattern (Workers)

**Worker main loop:**
```python
while not shutdown_requested:
  job = dequeue_next_job()  # SELECT ... FOR UPDATE SKIP LOCKED
  
  if job is None:
    sleep(10)  # No jobs available
    continue
  
  try:
    result = process_job(job)
    report_success(job.id, result)
  except RetryableError as e:
    schedule_retry(job)
  except PermanentError as e:
    mark_failed(job, str(e))
  except Exception as e:
    log_error(e)
    mark_failed(job, 'Internal error')
```

---

### 4.4 Timeline Event Pattern

**When to create timeline events:**
- Application lifecycle: submitted, status_changed, note_updated
- Background processing: job_scraped, job_scraped_failed, analysis_completed, analysis_failed
- Email ingestion: email_received
- User actions: manual events

**Best effort:**
- Timeline creation failures logged but don't block primary operation
- Example: Status update succeeds even if timeline event creation fails

---

## 5. State Transitions

### 5.1 Application Status

```
[Created] ──────────────────────────────────────┐
    │                                            │
    ├─→ [applied] ──→ [screening] ──→ [interview] ──→ [offer]
    │       │              │               │
    │       │              │               ├─→ [rejected]
    │       │              │               │
    │       │              └───────────────┘
    │       │                              
    │       └────────────────────────────→ [withdrawn]
    │
    └─────────────────────────────────────→ [rejected]
```

**Valid transitions:**
- applied → screening, interview, rejected, withdrawn
- screening → interview, rejected, withdrawn
- interview → offer, rejected, withdrawn
- offer → (terminal)
- rejected → (terminal)
- withdrawn → (terminal)

---

### 5.2 Resume Status

```
[Created] ──→ [uploaded] ──→ [processing] ──┬──→ [parsed]
                                            │
                                            └──→ [failed]
```

**State descriptions:**
- uploaded: File saved, not yet processed
- processing: Parser worker has dequeued job
- parsed: Parsing succeeded, resume_data exists
- failed: Parsing failed, error_message populated

---

### 5.3 Queue Job Status

```
[Created] ──→ [pending] ──→ [processing] ──┬──→ [complete]
                ↑               │           │
                │               │           └──→ [failed]
                │               │
                └───────────────┘
                  (retry after backoff)
```

**State descriptions:**
- pending: Waiting for worker to dequeue
- processing: Worker has dequeued and is processing
- complete: Job succeeded
- failed: Job failed permanently (no more retries)

**Transitions:**
- pending → processing: Worker dequeues
- processing → complete: Worker succeeds
- processing → failed: Worker fails (permanent error or max retries)
- processing → pending: Worker fails (retryable error, attempts < max)

---

**End of User Flows Specification**
