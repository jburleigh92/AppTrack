# Job Application Tracker - Error State & Fallback Behavior Specification

**Document Version:** 1.0  
**Last Updated:** December 10, 2025  
**Status:** Final Specification

---

## Table of Contents

1. [Overview & Principles](#1-overview--principles)
2. [Error Severity Classification](#2-error-severity-classification)
3. [Exhaustive Error Catalogue](#3-exhaustive-error-catalogue)
4. [Mandatory System Fallback Rules](#4-mandatory-system-fallback-rules)
5. [Retry Policies](#5-retry-policies)
6. [Safe Default Values](#6-safe-default-values)
7. [Data Consistency Guarantees](#7-data-consistency-guarantees)
8. [Catastrophic Failure Protocols](#8-catastrophic-failure-protocols)
9. [Error Communication Matrix](#9-error-communication-matrix)

---

## 1. Overview & Principles

### Design Philosophy

**Principle 1: Fail Gracefully**
- System MUST never lose user data
- Partial success is better than total failure
- Incomplete data with `needs_review=true` is preferred over blocking user

**Principle 2: Fail Visibly**
- User MUST be informed of failures that affect their data
- Silent failures are ONLY permitted for retryable background operations
- Critical failures MUST create timeline events

**Principle 3: Isolate Failures**
- Worker failures MUST NOT crash API server
- Scraper failures MUST NOT prevent email ingestion
- One bad job MUST NOT poison entire queue

**Principle 4: Preserve Intent**
- If user initiated action (manual trigger), prioritize completion
- If system initiated action (auto-analyze), fail softly
- User-provided data (manual entry) is always trusted

**Principle 5: Deterministic Behavior**
- Same error MUST produce same behavior every time
- Retry logic MUST be predictable
- No randomness in error handling

---

## 2. Error Severity Classification

### Severity Levels

| Severity | Definition | System Response | User Impact |
|----------|-----------|-----------------|-------------|
| **CRITICAL** | Data loss or corruption risk | Abort immediately | Blocking error, requires action |
| **HIGH** | Feature unavailable but data safe | Mark failed, notify user | Partial functionality loss |
| **MEDIUM** | Degraded functionality | Continue with fallback | Minimal impact |
| **LOW** | Non-essential feature failure | Continue silently | No visible impact |

### Error Categories

| Category | Examples | Default Severity |
|----------|----------|------------------|
| **Data Integrity** | FK violation, duplicate key | CRITICAL |
| **External Service** | LLM API down, rate limited | HIGH |
| **Network Transient** | Timeout, connection refused | MEDIUM |
| **Parsing Failure** | Scanned PDF, malformed HTML | MEDIUM |
| **User Input** | Invalid URL, date in future | LOW |
| **Configuration** | Missing API key | CRITICAL |
| **Resource Exhaustion** | Disk full, connections exhausted | CRITICAL |

---

## 3. Exhaustive Error Catalogue

### 3.1 Browser Extension Errors

**ERR-EXT-001: Network Unavailable**
- Root Cause: Backend not running, port blocked
- Severity: HIGH
- Fallback: Queue locally, retry every 30s (max 3)
- User Message: "Offline - will sync when online"

**ERR-EXT-002: Backend 4xx Error**
- Root Cause: Validation error, duplicate detected
- Severity: MEDIUM
- Fallback: Show error message, allow retry
- User Message: Specific validation error

**ERR-EXT-003: Backend 5xx Error**
- Root Cause: Database unavailable, internal error
- Severity: HIGH
- Fallback: Retry with backoff (1s, 5s, 15s), then queue
- User Message: "Server error - retrying..."

**ERR-EXT-004: DOM Parsing Failed**
- Root Cause: Job board changed HTML structure
- Severity: LOW
- Fallback: Use "Unknown Company/Position"
- User Message: "Incomplete data - please review"

**ERR-EXT-005: Local Storage Full**
- Root Cause: Browser storage quota exceeded (5MB)
- Severity: HIGH
- Fallback: Clear old failed requests, show error
- User Message: "Storage full - please sync now"

**ERR-EXT-006: Duplicate User Rejection**
- Root Cause: User chose not to create duplicate
- Severity: LOW (expected)
- Fallback: No action
- User Message: "Already tracked" with link

### 3.2 Email Ingestion Errors

**ERR-EMAIL-001: IMAP Connection Failure**
- Root Cause: Invalid credentials, server down
- Severity: HIGH
- Fallback: Retry every 60s indefinitely
- User Message: Show in settings after 3 failures

**ERR-EMAIL-002: IMAP Auth Failed**
- Root Cause: Wrong password, 2FA required
- Severity: CRITICAL
- Fallback: Stop polling, log critical
- User Message: "Email auth failed - update credentials"

**ERR-EMAIL-003: Low Confidence Parsing**
- Root Cause: Non-standard email format
- Severity: LOW (expected)
- Fallback: Create with `needs_review=true`
- User Message: Timeline: "Auto-detected (needs review)"

**ERR-EMAIL-004: UID Already Processed**
- Root Cause: Retry after failed mark-as-read
- Severity: LOW (expected)
- Fallback: Return 200 OK with skipped=true
- User Message: None (silent)

**ERR-EMAIL-005: Folder Not Found**
- Root Cause: User deleted folder, typo
- Severity: HIGH
- Fallback: Stop polling
- User Message: "Email folder not found - check settings"

**ERR-EMAIL-006: Mark As Read Failed**
- Root Cause: Mailbox read-only, connection lost
- Severity: LOW
- Fallback: Continue (UID check prevents duplicate)
- User Message: None (silent)

**ERR-EMAIL-007: Backend Unavailable**
- Root Cause: Backend down, database unavailable
- Severity: HIGH
- Fallback: Retry POST (30s, 60s, 120s)
- User Message: Show in settings after 3 failures

### 3.3 Scraper Errors

**ERR-SCRAPE-001: HTTP Timeout**
- Root Cause: Slow server, large page
- Severity: MEDIUM
- Retry: Yes (1m, 5m, 15m)
- User Message: Timeline event after max retries

**ERR-SCRAPE-002: HTTP 404**
- Root Cause: Job removed, URL expired
- Severity: LOW
- Retry: No (permanent)
- User Message: Timeline: "Job posting removed"

**ERR-SCRAPE-003: HTTP 403**
- Root Cause: Login required, bot detection
- Severity: MEDIUM
- Retry: No (permanent)
- User Message: Timeline: "Access denied"

**ERR-SCRAPE-004: HTTP 429 Rate Limited**
- Root Cause: Too many requests
- Severity: MEDIUM
- Retry: Yes (5m, 15m, 30m)
- User Message: None until max retries

**ERR-SCRAPE-005: HTTP 5xx**
- Root Cause: Server down, overloaded
- Severity: MEDIUM
- Retry: Yes (1m, 5m, 15m)
- User Message: Timeline event after max retries

**ERR-SCRAPE-006: Connection Refused**
- Root Cause: Server down, DNS failure
- Severity: MEDIUM
- Retry: Yes (1m, 5m, 15m)
- User Message: Timeline event after max retries

**ERR-SCRAPE-007: SSL/TLS Error**
- Root Cause: Expired certificate
- Severity: HIGH
- Retry: No (security issue)
- User Message: Timeline: "SSL error - cannot scrape"

**ERR-SCRAPE-008: CAPTCHA Detected**
- Root Cause: Bot detection triggered
- Severity: MEDIUM
- Retry: No (cannot proceed)
- User Message: Timeline: "CAPTCHA - paste manually"

**ERR-SCRAPE-009: Login Wall**
- Root Cause: Job behind login
- Severity: MEDIUM
- Retry: No (cannot proceed)
- User Message: Timeline: "Login required"

**ERR-SCRAPE-010: HTML Parse Error**
- Root Cause: Malformed HTML
- Severity: LOW
- Retry: No (continue with partial)
- User Message: None (HTML preserved)

**ERR-SCRAPE-011: Extraction Failed**
- Root Cause: Unknown HTML structure
- Severity: LOW
- Retry: No (store HTML, mark incomplete)
- User Message: Timeline: "Could not extract - review needed"

**ERR-SCRAPE-012: Redirect Loop**
- Root Cause: Misconfigured server
- Severity: MEDIUM
- Retry: No (permanent)
- User Message: Timeline: "Too many redirects"

**ERR-SCRAPE-013: Content Too Large**
- Root Cause: Page includes large resources
- Severity: LOW
- Retry: No (truncate at 10MB)
- User Message: Timeline: "Content truncated"

**ERR-SCRAPE-014: Invalid Content-Type**
- Root Cause: URL points to file download
- Severity: LOW
- Retry: No (permanent)
- User Message: Timeline: "URL is not a web page"

**ERR-SCRAPE-015: Internal Rate Limit**
- Root Cause: Too many requests queued
- Severity: LOW
- Retry: Automatically (reprocess on next poll)
- User Message: None (silent)

### 3.4 Resume Parsing Errors

**ERR-RESUME-001: File Too Large**
- Root Cause: File > 10MB
- Severity: LOW
- Retry: No (user re-upload)
- User Message: "File exceeds 10MB limit"

**ERR-RESUME-002: Unsupported Format**
- Root Cause: File extension not .pdf/.docx/.txt
- Severity: LOW
- Retry: No (user re-upload)
- User Message: "Unsupported file format"

**ERR-RESUME-003: MIME Type Mismatch**
- Root Cause: File renamed incorrectly
- Severity: MEDIUM
- Retry: No (security)
- User Message: "File type mismatch"

**ERR-RESUME-004: File Write Failed**
- Root Cause: Disk full, permission denied
- Severity: CRITICAL
- Retry: No (system issue)
- User Message: "Cannot save file - contact support"

**ERR-RESUME-005: PDF Encrypted**
- Root Cause: User uploaded password-protected
- Severity: LOW
- Retry: No (user re-upload)
- User Message: "Resume is password protected"

**ERR-RESUME-006: PDF Scanned**
- Root Cause: PDF contains images only
- Severity: LOW
- Retry: No (user re-upload)
- User Message: "Resume is scanned image - upload text PDF"

**ERR-RESUME-007: DOCX Corrupted**
- Root Cause: File corruption, incomplete upload
- Severity: LOW
- Retry: No (user re-upload)
- User Message: "File corrupted - upload again"

**ERR-RESUME-008: Text Encoding Error**
- Root Cause: File uses unsupported encoding
- Severity: LOW
- Retry: Yes (try UTF-8, Latin-1, CP1252)
- User Message: "Cannot read file encoding" if all fail

**ERR-RESUME-009: Section Detection Failed**
- Root Cause: Non-standard resume format
- Severity: LOW
- Retry: No (store raw text)
- User Message: "Could not identify sections - review data"

**ERR-RESUME-010: Active Constraint Violation**
- Root Cause: Race condition, concurrent uploads
- Severity: MEDIUM
- Retry: Yes (retry transaction)
- User Message: None (internal retry succeeds)

**ERR-RESUME-011: Worker Crashed**
- Root Cause: OOM, segfault in library
- Severity: HIGH
- Retry: No (watchdog marks failed)
- User Message: "Parsing failed - upload again"

### 3.5 AI Analysis Errors

**ERR-ANALYSIS-001: No Active Resume**
- Root Cause: User deleted all resumes
- Severity: HIGH
- Retry: No (precondition)
- User Message: "Upload resume before analyzing"

**ERR-ANALYSIS-002: No Job Posting**
- Root Cause: Scraping not complete
- Severity: HIGH
- Retry: No (precondition)
- User Message: "Scrape job posting before analyzing"

**ERR-ANALYSIS-003: API Key Missing**
- Root Cause: User hasn't set up API key
- Severity: CRITICAL
- Retry: No (config error)
- User Message: "Configure LLM API key in settings"

**ERR-ANALYSIS-004: API Key Invalid**
- Root Cause: Typo, revoked key
- Severity: CRITICAL
- Retry: No (config error)
- User Message: "Invalid LLM API key - check settings"

**ERR-ANALYSIS-005: API Timeout**
- Root Cause: Large prompt, slow API
- Severity: MEDIUM
- Retry: Yes (1m, 5m, 15m)
- User Message: Timeline event after max retries

**ERR-ANALYSIS-006: Rate Limited**
- Root Cause: API rate limit exceeded
- Severity: MEDIUM
- Retry: Yes (5m, 15m, 30m)
- User Message: Timeline event after max retries

**ERR-ANALYSIS-007: API Server Error**
- Root Cause: LLM provider outage
- Severity: MEDIUM
- Retry: Yes (1m, 5m, 15m)
- User Message: Timeline event after max retries

**ERR-ANALYSIS-008: Invalid JSON**
- Root Cause: Model hallucinated invalid format
- Severity: MEDIUM
- Retry: Yes (max 3 attempts)
- User Message: "Analysis incomplete" if exhausted

**ERR-ANALYSIS-009: Missing Fields**
- Root Cause: Model didn't follow instructions
- Severity: MEDIUM
- Retry: Yes (max 3 attempts)
- User Message: Timeline event after max retries

**ERR-ANALYSIS-010: Score Out of Range**
- Root Cause: Model hallucination
- Severity: LOW
- Retry: No (clamp to [0, 100])
- User Message: None (logged only)

**ERR-ANALYSIS-011: Prompt Too Large**
- Root Cause: Very long resume or description
- Severity: MEDIUM
- Retry: No (truncate description)
- User Message: "Analysis based on truncated description"

**ERR-ANALYSIS-012: Worker Crashed**
- Root Cause: OOM, unhandled exception
- Severity: HIGH
- Retry: No (watchdog marks failed)
- User Message: "Analysis failed - retry manually"

---

## 4. Mandatory System Fallback Rules

### 4.1 Browser Extension Fallbacks

| Error | Backend Action | Extension Action | Data Integrity | Pipeline |
|-------|----------------|------------------|----------------|----------|
| Network Unavailable | N/A | Queue locally, retry every 30s | PROTECTED (queued) | PAUSED |
| Backend 400/409 | Return error | Show error, allow edit | SAFE | STOPPED |
| Backend 5xx | Return 503 | Retry with backoff, then queue | SAFE | PAUSED |
| DOM Parse Failed | Accept with defaults | Use "Unknown", set needs_review | SAFE | CONTINUE |
| Storage Full | N/A | Clear old requests, show error | AT RISK | STOPPED |
| Duplicate Rejected | Return 409 | Show modal with options | SAFE | STOPPED |

### 4.2 Email Ingestion Fallbacks

| Error | Backend Action | Email Service Action | Data Integrity | Pipeline |
|-------|----------------|----------------------|----------------|----------|
| IMAP Connection | N/A | Retry every 60s indefinitely | SAFE | PAUSED |
| IMAP Auth | N/A | Stop polling, log critical | SAFE | STOPPED |
| Low Confidence | Accept with needs_review | Create with flag | PROTECTED | CONTINUE |
| UID Processed | Return 200 skipped | Log debug, mark read | PROTECTED | SKIPPED |
| Folder Not Found | N/A | Log error, stop polling | SAFE | STOPPED |
| Mark Read Failed | N/A | Log warning, continue | PROTECTED | CONTINUE |
| Backend Down | N/A | Retry POST with backoff | SAFE | PAUSED |

### 4.3 Scraper Worker Fallbacks

| Error | Backend Action | Worker Action | Data Integrity | Pipeline |
|-------|----------------|---------------|----------------|----------|
| Timeout | Accept retry | Retry 1m→5m→15m | SAFE | RETRY |
| HTTP 404 | Mark failed, timeline | Mark failed permanently | SAFE | STOPPED |
| HTTP 403 | Mark failed, timeline | Mark failed permanently | SAFE | STOPPED |
| Rate Limited | Accept retry | Retry 5m→15m→30m | SAFE | RETRY |
| HTTP 5xx | Accept retry | Retry 1m→5m→15m | SAFE | RETRY |
| Connection Error | Accept retry | Retry 1m→5m→15m | SAFE | RETRY |
| SSL Error | Mark failed | Mark failed, log warning | SAFE | STOPPED |
| CAPTCHA | Mark failed, timeline | Mark failed permanently | SAFE | STOPPED |
| Login Wall | Mark failed, timeline | Mark failed permanently | SAFE | STOPPED |
| Parse Error | Accept partial | Store HTML, mark incomplete | PROTECTED | CONTINUE |
| Extraction Failed | Accept callback | Store HTML, mark incomplete | PROTECTED | CONTINUE |
| Redirect Loop | Mark failed | Mark failed permanently | SAFE | STOPPED |
| Content Too Large | Accept truncated | Truncate at 10MB | PROTECTED | CONTINUE |
| Invalid Type | Mark failed | Mark failed permanently | SAFE | STOPPED |
| Internal Rate Limit | N/A | Leave pending, reprocess | SAFE | PAUSED |

### 4.4 Parser Worker Fallbacks

| Error | Backend Action | Worker Action | Data Integrity | Pipeline |
|-------|----------------|---------------|----------------|----------|
| PDF Encrypted | Mark failed, update error | Mark failed, no retry | SAFE | STOPPED |
| PDF Scanned | Mark failed, update error | Mark failed, no retry | SAFE | STOPPED |
| DOCX Corrupted | Mark failed, update error | Mark failed, no retry | SAFE | STOPPED |
| Encoding Error | Mark failed if all fail | Try UTF-8→Latin-1→CP1252 | PROTECTED | RETRY |
| Section Failed | Accept partial | Store raw text, mark incomplete | PROTECTED | CONTINUE |
| Active Constraint | Reject callback, return 409 | Query active, retry transaction | PROTECTED | RETRY |
| Worker Crashed | Watchdog marks failed | N/A (process dead) | AT RISK | STOPPED |

### 4.5 Analysis Worker Fallbacks

| Error | Backend Action | Worker Action | Data Integrity | Pipeline |
|-------|----------------|---------------|----------------|----------|
| No Resume | Reject immediately | Mark failed, no retry | SAFE | STOPPED |
| No Posting | Reject immediately | Mark failed, no retry | SAFE | STOPPED |
| API Key Missing | Reject immediately | Mark failed, no retry | SAFE | STOPPED |
| API Key Invalid | Mark failed | Mark failed, no retry | SAFE | STOPPED |
| API Timeout | Accept retry | Retry 1m→5m→15m | SAFE | RETRY |
| Rate Limited | Accept retry | Retry 5m→15m→30m | SAFE | RETRY |
| Server Error | Accept retry | Retry 1m→5m→15m | SAFE | RETRY |
| Invalid JSON | Accept retry | Parse best effort, retry | PROTECTED | RETRY |
| Missing Fields | Accept retry | Mark for retry | SAFE | RETRY |
| Score Out of Range | Accept with clamped | Clamp to [0,100], continue | PROTECTED | CONTINUE |
| Prompt Too Large | Accept truncated | Truncate description | PROTECTED | CONTINUE |
| Worker Crashed | Watchdog marks failed | N/A (process dead) | SAFE | STOPPED |

---

## 5. Retry Policies

### 5.1 Scraper Job Retry

**Configuration:**
```yaml
max_attempts: 3
retry_on: [timeout, connection_error, http_500, http_502, http_503, http_429]
no_retry_on: [http_404, http_403, ssl_error, captcha, login_wall]
```

**Backoff Schedule:**

Standard Errors (timeout, 5xx, connection):
- Attempt 1: 0s (immediate)
- Attempt 2: 1 minute
- Attempt 3: 5 minutes
- Final: FAILED (6 min total elapsed)

Rate Limit (429):
- Attempt 1: 0s (immediate)
- Attempt 2: 5 minutes
- Attempt 3: 15 minutes
- Final: FAILED (20 min total elapsed)

**Deduplication:** Check for scrape < 7 days old before each attempt

### 5.2 Parser Job Retry

**Configuration:**
```yaml
max_attempts: 1
retry_on: []  # NO RETRY
```

**Rationale:** Parsing failures are permanent (file format issues)

**Encoding Fallback (not retry):** UTF-8 → Latin-1 → CP1252

### 5.3 Analysis Job Retry

**Configuration:**
```yaml
max_attempts: 3
retry_on: [timeout, rate_limit, http_500, http_502, http_503, invalid_json, missing_fields]
no_retry_on: [auth_error, api_key_missing, no_active_resume, no_job_posting]
```

**Backoff Schedule:** Same as scraper

**Precondition Check:** Before each retry, validate resume and posting exist

### 5.4 Email Ingestion Retry

**IMAP Connection:**
```yaml
retry_indefinitely: true
backoff: 60 seconds (fixed)
alert_after: 3 consecutive failures
```

**POST to /capture/email:**
```yaml
max_attempts: 3
backoff: [30s, 60s, 120s]
retry_on: [timeout, connection_error, http_503]
no_retry_on: [http_400, http_401, http_409]
```

### 5.5 Browser Extension Retry

**POST to /capture/browser:**
```yaml
max_attempts: 3
backoff: [1s, 5s, 15s]
retry_on: [timeout, connection_error, http_503]
no_retry_on: [http_400, http_409]
```

**If All Fail:** Queue in localStorage, background retry every 30s (max 10)

### 5.6 Worker Callback Retry

**POST to /internal/*:**
```yaml
max_attempts: 3
backoff: [10s, 30s, 60s]
retry_on: [timeout, connection_error, http_503]
no_retry_on: [http_400, http_401, http_404]
```

**If All Fail:** Log CRITICAL, job stuck in processing (watchdog cleanup)

---

## 6. Safe Default Values

### 6.1 Missing Application Data

| Field | Default Value | needs_review | Pipeline |
|-------|---------------|--------------|----------|
| company_name (empty) | "Unknown Company" | true | CONTINUE |
| job_title (empty) | "Unknown Position" | true | CONTINUE |
| application_date (missing) | TODAY | false | CONTINUE |
| job_posting_url (missing) | NULL | false | CONTINUE |
| status (missing) | "applied" | false | CONTINUE |
| source (missing) | "manual" | false | CONTINUE |

### 6.2 Missing Job Posting Data

| Field | Default Value | extraction_complete | Pipeline |
|-------|---------------|---------------------|----------|
| job_title | Copy from application | false | CONTINUE |
| company_name | Copy from application | false | CONTINUE |
| description | "(Could not extract)" | false | STOP ANALYSIS |
| requirements | NULL | true | CONTINUE |
| salary_range | NULL | true | CONTINUE |

### 6.3 Missing Resume Data

| Field | Default Value | extraction_complete | Pipeline |
|-------|---------------|---------------------|----------|
| email | NULL | true | CONTINUE |
| phone | NULL | true | CONTINUE |
| skills (empty) | [] | false | CONTINUE (degraded) |
| experience (empty) | [] | false | CONTINUE (degraded) |
| education (empty) | [] | true | CONTINUE |

### 6.4 Missing Email Metadata

| Field | Default Value | needs_review | Pipeline |
|-------|---------------|--------------|----------|
| company_name | From sender domain | true | CONTINUE |
| job_title | "Position from [domain]" | true | CONTINUE |
| job_posting_url | NULL | false | CONTINUE |
| application_date | Email received date | false | CONTINUE |

---

## 7. Data Consistency Guarantees

### 7.1 Race Condition: Scraper Completes, Application Deleted

**Protection:**
- Backend checks application exists before processing results
- If not found or is_deleted=true: Discard results, return 200 OK
- FK CASCADE ensures queue job deleted with application

**Guarantee:** No orphaned job postings for deleted applications

### 7.2 Race Condition: Parser Completes, Newer Resume Uploaded

**Protection:**
- Parser begins transaction, queries active resume FOR UPDATE
- If Resume B active: Archive B, activate A (last completion wins)
- Commit transaction with unique constraint enforcement

**Guarantee:** Exactly one resume active. Last parser to complete wins.

### 7.3 Race Condition: Two Workers Update Same Record

**Protection:**
```sql
SELECT * FROM queue WHERE status='pending' 
ORDER BY priority DESC LIMIT 1
FOR UPDATE SKIP LOCKED;
```

**Guarantee:** Worker 1 gets row lock, Worker 2 skips to next job

### 7.4 Optimistic Locking

**Mechanism:**
```sql
UPDATE applications SET status=?, updated_at=NOW()
WHERE id=? AND updated_at=?
```

**If zero rows updated:** Return 409 Conflict with current data

**Guarantee:** Lost updates prevented, user notified

### 7.5 Soft Delete Interaction

**Behavior:**
- Soft delete: is_deleted=true, deleted_at=NOW()
- Queue jobs remain (CASCADE doesn't trigger)
- Workers process jobs normally
- Backend discards results if is_deleted=true

**Guarantee:** Soft-deleted apps don't get timeline events

### 7.6 Transaction Atomicity

**Application Creation:**
```sql
BEGIN;
  INSERT INTO applications (...) RETURNING id;
  INSERT INTO timeline_events (...);
  IF url THEN INSERT INTO scraper_queue (...);
COMMIT;
```

**If Any Step Fails:** Entire transaction rolls back

**Guarantee:** All or nothing, no partial application

---

## 8. Catastrophic Failure Protocols

### 8.1 Database Unavailable

**Detection:** Connection refused, timeout, auth failure

**Immediate Actions:**
1. API returns 503 for all operations
2. Workers stop polling
3. Email service stops
4. Extension queues locally

**Recovery:**
1. Backend retries connection every 30s
2. On success: Resume all operations
3. Health check returns 200

**Alert:** Critical alert after 90 seconds

### 8.2 Queue Tables Locked/Corrupted

**Detection:** Lock timeout, table corruption

**Immediate Actions:**
1. Workers stop polling
2. API returns 503 for triggers
3. Log CRITICAL

**Recovery:**
1. Run VACUUM FULL on tables
2. Restart workers
3. Mark stuck jobs failed

### 8.3 LLM Provider Down

**Detection:** All analysis jobs failing with 503

**Immediate Actions:**
1. Analysis worker stops polling
2. Manual triggers return 503
3. Auto-analysis disabled
4. Dashboard shows warning

**Recovery:**
1. Worker retries every 5 minutes
2. On success: Resume operations
3. Backlog processed automatically

**Alert:** Warning after 15 minutes

### 8.4 Disk Full

**Detection:** IOError during file write

**Immediate Actions:**
1. Resume uploads return 507
2. Scraper worker stops
3. Database writes may fail
4. Log CRITICAL

**Recovery:**
1. Operator frees disk space
2. Restart affected workers

**Data Loss Risk:** Resume uploads during outage

### 8.5 Worker Crash

**Detection:** Process exit, systemd restart

**Immediate Actions:**
1. Systemd restarts worker
2. Job stuck in processing
3. Watchdog detects after 5 min
4. Watchdog marks failed

**Recovery:**
1. Worker restarts automatically
2. User can retry manually

---

## 9. Error Communication Matrix

### 9.1 Silent Errors (No User Notification)

- Email UID already processed (idempotency working)
- Scraper job retrying (transient failure)
- Analysis job retrying (transient failure)
- Queue dequeue conflict (normal concurrency)
- Optimistic lock retry (automatic recovery)

### 9.2 Timeline Event Required

- Scraper max retries exhausted
- Scraper CAPTCHA detected
- Scraper login wall
- Scraper 404
- Analysis max retries exhausted
- Analysis API key invalid
- Parser failed

### 9.3 UI Banner Required

| Error | Type | Message |
|-------|------|---------|
| Database unavailable | Critical | "System temporarily unavailable" |
| Disk full | Critical | "Storage full - uploads disabled" |
| LLM provider down | Warning | "AI analysis temporarily unavailable" |
| Email auth failed | Warning | "Email monitoring stopped - update credentials" |

### 9.4 User Confirmation Required

- Duplicate detected (409) → "View existing or create anyway?"
- Optimistic lock (409) → "Refresh or override?"
- Resume upload → "Archive current resume?"

---

**End of Error Handling Specification**
