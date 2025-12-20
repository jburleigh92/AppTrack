# PHASE 2 HARDENING EXECUTION PLAN
**AppTrack Integration & Stability Validation**

**Status**: In Progress
**Branch**: `claude/phase-2-hardening-9qTFZ`
**Objective**: Replace static paths with real data, validate end-to-end flows, surface failures

---

## CRITICAL FINDINGS FROM CODEBASE EXPLORATION

### 🔴 HIGH SEVERITY - BLOCKS PHASE 2 COMPLETION
1. **Static Job Discovery** (`/api/routes/jobs.py:43-110`)
   - 8 hardcoded job postings returned to all users
   - No connection to real job boards or ATS feeds
   - Comment explicitly states: "Current implementation returns curated static jobs for v1"

### 🟡 MEDIUM SEVERITY - STABILITY RISKS
1. **Silent Error Suppression** (multiple files)
   - Advisory layer: `except Exception: pass` at 15+ locations
   - Timeline service: Failed event creation returns `None` without logging
   - Application service: Overly strict validation (rejects literal "string")

2. **Error Visibility**
   - Generic 500 errors without request tracking IDs
   - No UI-facing error messages for common failure modes
   - Missing data errors not differentiated from system errors

### 🟢 LOW SEVERITY - KNOWN LIMITATIONS
1. **ATS Coverage**
   - Only Greenhouse has dedicated API integration
   - Lever, Workday fall back to HTML scraping
   - Custom ATSs require manual URL entry via browser extension

---

## PHASE 2 EXECUTION CHECKLIST

### ✅ CHECKLIST LEGEND
- **Static Assumption**: What's currently hardcoded/mocked
- **Real Replacement**: What will replace it
- **Verification**: How to confirm it works via UI or API

---

## 1️⃣ REPLACE STATIC JOB DISCOVERY

### Item 1.1: Remove Hardcoded Jobs
**File**: `backend/app/api/routes/jobs.py`

**(a) Static Assumption**:
- Line 43-110: 8 hardcoded job postings with fake URLs
- Line 18 comment: "Current implementation returns curated static jobs for v1"
- All users see identical job list regardless of resume

**(b) Real Replacement**:
- Return jobs from `JobPosting` table where `extraction_complete = true`
- Filter by match score (if `AnalysisResult` exists)
- Sort by relevance using skills from active resume
- Empty result set → return HTTP 200 with empty array + message

**(c) Verification**:
```bash
# Test 1: Upload resume with Python skills
curl -X POST /api/v1/resume/upload -F file=@python_resume.pdf

# Test 2: Capture a Python job via browser extension
curl -X POST /api/v1/applications/capture \
  -d '{"company_name":"Acme","job_title":"Python Engineer","job_posting_url":"https://boards.greenhouse.io/acme/jobs/123"}'

# Test 3: Wait for scraping to complete
curl /api/v1/applications/{app_id} | jq '.posting_id'

# Test 4: Discover jobs (should return scraped job)
curl /api/v1/jobs/discover | jq '.jobs[] | .job_title'
# Expected: "Python Engineer" appears in results

# Test 5: Upload resume with different skills (Java)
curl -X POST /api/v1/resume/upload -F file=@java_resume.pdf

# Test 6: Discover jobs again
curl /api/v1/jobs/discover | jq '.jobs[] | .job_title'
# Expected: Results change based on skills match
```

**UI Verification**:
1. Navigate to Jobs page
2. Verify jobs shown match resume skills
3. Upload different resume → verify jobs refresh
4. If no jobs exist → verify empty state message appears

---

### Item 1.2: Validate Resume-Indexed Discovery
**File**: `backend/app/api/routes/jobs.py`

**(a) Static Assumption**:
- Discovery matches against hardcoded `required_skills` arrays
- Match percentage calculated from static data

**(b) Real Replacement**:
- Extract skills from `ResumeData.user_skills` (already parsed)
- Match against `JobPosting.requirements` (extracted from real postings)
- Use skill keywords, not exact string matching
- Calculate relevance score: `matched_skills / total_job_skills * 100`

**(c) Verification**:
```python
# Test script: verify_discovery_matching.py
import requests

# 1. Upload resume with specific skills
resume_skills = ["Python", "FastAPI", "PostgreSQL", "Docker"]

# 2. Capture 3 jobs:
#    Job A: Matches 4/4 skills (100%)
#    Job B: Matches 2/4 skills (50%)
#    Job C: Matches 0/4 skills (0%)

# 3. Call discovery endpoint
response = requests.get("http://localhost:8000/api/v1/jobs/discover")
jobs = response.json()["jobs"]

# 4. Assert ordering
assert jobs[0]["match_percentage"] > jobs[1]["match_percentage"]
assert jobs[1]["match_percentage"] > jobs[2]["match_percentage"]

# 5. Assert Job C with 0% match is excluded or at bottom
assert jobs[-1]["match_percentage"] == 0 or len([j for j in jobs if j["match_percentage"] == 0]) == 0
```

**UI Verification**:
1. Jobs page shows match percentage badges
2. Jobs sorted by relevance (highest match first)
3. Zero-match jobs either hidden or labeled "Low Match"

---

### Item 1.3: Handle Empty Discovery Gracefully
**File**: `backend/app/api/routes/jobs.py`

**(a) Static Assumption**:
- Always returns 8 jobs (never empty)
- No handling for "no jobs available" state

**(b) Real Replacement**:
- Return HTTP 200 with empty array if no jobs match
- Include message: `{"jobs": [], "message": "No jobs found. Capture job postings to see them here."}`
- Do NOT return 404 (empty is a valid state, not an error)

**(c) Verification**:
```bash
# Test 1: Fresh database (no jobs captured)
curl /api/v1/jobs/discover
# Expected: {"jobs": [], "message": "No jobs found. Capture job postings to see them here."}

# Test 2: Capture one job, then delete it
curl -X POST /api/v1/applications/capture -d '{...}'
curl -X DELETE /api/v1/applications/{app_id}
curl /api/v1/jobs/discover
# Expected: Empty jobs array again
```

**UI Verification**:
1. Open Jobs page with no captured jobs
2. Verify empty state message displays: "No jobs yet. Use the browser extension to capture postings."
3. Verify no loading spinners stuck in infinite state
4. Verify no error banners or toasts appear

---

## 2️⃣ HARDEN ANALYSIS + RANKING

### Item 2.1: Validate Analysis Runs Reliably
**Files**:
- `backend/app/workers/analysis_worker.py`
- `backend/app/services/analysis/analyzer.py`

**(a) Static Assumption**:
- Analysis assumes job posting always has description
- Analysis assumes resume always has skills
- Missing data causes silent failure or infinite retry

**(b) Real Replacement**:
- Add explicit validation before enqueueing analysis job:
  ```python
  if not posting or not posting.extraction_complete:
      raise ValueError("Cannot analyze: job posting not ready")
  if not posting.description or len(posting.description) < 50:
      raise ValueError("Cannot analyze: job description too short")
  if not resume_data or not resume_data.user_skills:
      raise ValueError("Cannot analyze: resume has no skills extracted")
  ```
- Return validation errors as HTTP 422 (Unprocessable Entity)
- Surface error in UI with actionable message

**(c) Verification**:
```bash
# Test 1: Trigger analysis before scraping completes
APP_ID=$(curl -X POST /api/v1/applications/capture -d '{...}' | jq -r '.id')
curl -X POST /api/v1/analysis/${APP_ID}/analysis/run
# Expected: 422 {"error": "Cannot analyze: job posting not ready"}

# Test 2: Wait for scraping, then trigger analysis
sleep 10
curl -X POST /api/v1/analysis/${APP_ID}/analysis/run
# Expected: 202 {"job_id": "..."}

# Test 3: Check analysis completes within 60s
for i in {1..12}; do
  STATUS=$(curl /api/v1/applications/${APP_ID} | jq -r '.analysis_completed')
  if [ "$STATUS" = "true" ]; then echo "PASS"; exit 0; fi
  sleep 5
done
echo "FAIL: Analysis timed out"
```

**UI Verification**:
1. Capture job → verify "Analyzing..." indicator appears
2. Analysis completes → verify match score badge appears
3. Trigger analysis on incomplete job → verify error toast: "Job posting still loading. Try again in a moment."
4. Check timeline → verify `analysis_completed` event with match score

---

### Item 2.2: Ensure Ranking Queries are Deterministic
**File**: `backend/app/api/routes/jobs.py`

**(a) Static Assumption**:
- Jobs returned in insertion order or random order
- Match percentage ties not handled consistently

**(b) Real Replacement**:
- Add secondary sort: `ORDER BY match_percentage DESC, created_at DESC`
- Ensure consistent pagination (if added later)
- Cache match scores in `Application.match_score` (denormalized)

**(c) Verification**:
```python
# Test: Call discovery 10 times, verify identical ordering
results = []
for i in range(10):
    resp = requests.get("/api/v1/jobs/discover")
    job_ids = [j["id"] for j in resp.json()["jobs"]]
    results.append(job_ids)

# Assert all 10 results are identical
assert all(r == results[0] for r in results), "Ranking is non-deterministic"
```

**UI Verification**:
1. Refresh Jobs page 5 times
2. Verify job order remains consistent
3. Verify match scores don't change on refresh

---

### Item 2.3: Prevent UI Blocking on Long Analysis
**File**: `backend/app/api/routes/analysis.py`

**(a) Static Assumption**:
- Analysis runs synchronously (blocks HTTP request)
- Timeout could cause 504 Gateway Timeout

**(b) Real Replacement**:
- Already uses async queue (✅ GOOD)
- Verify UI polls for completion instead of blocking
- Add timeout badge in UI: "Analysis taking longer than usual (2 min elapsed)"

**(c) Verification**:
```bash
# Test 1: Simulate slow LLM (add 30s delay in analyzer)
# Verify API returns 202 immediately
time curl -X POST /api/v1/analysis/{app_id}/analysis/run
# Expected: <1 second response time

# Test 2: Check status endpoint doesn't block
curl /api/v1/applications/{app_id}
# Expected: analysis_completed = false (immediate response)
```

**UI Verification**:
1. Trigger analysis
2. Verify UI shows loading indicator (not frozen page)
3. Navigate to other pages → verify app remains responsive
4. After 2 minutes → verify "Still analyzing..." message appears
5. After completion → verify match score appears without page refresh

---

## 3️⃣ EXERCISE FULL APPLICATION LIFECYCLE

### Item 3.1: Validate Application Capture Without Manual DB Edits
**File**: `backend/app/services/application_service.py`

**(a) Static Assumption**:
- Validation checks for literal string `"string"` (lines 17-32)
- Rejects valid company names that happen to be "string"
- Requires manual SQL to bypass validation

**(b) Real Replacement**:
- Remove literal "string" checks (overly specific)
- Replace with semantic validation:
  ```python
  if not company_name or len(company_name.strip()) < 2:
      raise ValueError("Company name must be at least 2 characters")
  if company_name.strip().lower() in ["unknown", "n/a", "none", "null"]:
      raise ValueError("Please provide a valid company name")
  ```
- Same for job_title, job_posting_url

**(c) Verification**:
```bash
# Test 1: Capture job with valid data
curl -X POST /api/v1/applications/capture \
  -d '{"company_name":"Acme Corp","job_title":"Engineer","job_posting_url":"https://acme.com/jobs/123","notes":"Found via LinkedIn"}'
# Expected: 201 Created

# Test 2: Capture job with edge cases
curl -X POST /api/v1/applications/capture \
  -d '{"company_name":"X","job_title":"A","job_posting_url":"https://x.com","notes":""}'
# Expected: 422 {"error": "Company name must be at least 2 characters"}

# Test 3: Capture job with "Unknown" company
curl -X POST /api/v1/applications/capture \
  -d '{"company_name":"Unknown","job_title":"Engineer","job_posting_url":"https://example.com","notes":""}'
# Expected: 422 {"error": "Please provide a valid company name"}

# Test 4: Verify no manual DB edits needed
psql -d apptrack -c "SELECT COUNT(*) FROM applications WHERE company_name = 'Acme Corp';"
# Expected: 1 (job was captured successfully)
```

**UI Verification**:
1. Install browser extension
2. Navigate to any job posting (Greenhouse, Lever, or custom)
3. Click "Capture Application"
4. Verify success toast appears
5. Navigate to Applications page → verify job appears immediately
6. Verify timeline shows `application_created` event

---

### Item 3.2: Validate State Transitions Are Enforced
**File**: `backend/app/api/routes/applications.py`

**(a) Static Assumption**:
- Any status can transition to any other status
- No validation of state machine rules
- "applied" → "accepted" allowed (skips "interviewed")

**(b) Real Replacement**:
- Document allowed transitions (do NOT enforce strict FSM in Phase 2)
- Add warning in UI for unusual transitions
- Allow all transitions but log them in timeline with warnings

**(c) Verification**:
```bash
# Test 1: Normal flow
curl -X PATCH /api/v1/applications/{app_id} -d '{"status":"interviewed"}'
curl -X PATCH /api/v1/applications/{app_id} -d '{"status":"offered"}'
curl -X PATCH /api/v1/applications/{app_id} -d '{"status":"accepted"}'
# Expected: All succeed, 3 timeline events created

# Test 2: Unusual flow (applied → rejected)
curl -X PATCH /api/v1/applications/{app_id} -d '{"status":"rejected"}'
# Expected: Succeeds (no strict enforcement), timeline shows: applied → rejected

# Test 3: Query timeline
curl /api/v1/timeline/{app_id} | jq '.events[] | select(.event_type=="status_changed")'
# Expected: Shows all transitions with old_status and new_status
```

**UI Verification**:
1. Create application
2. Change status to "Interviewed" → verify badge updates
3. Change to "Rejected" → verify badge updates
4. Open timeline → verify both transitions recorded
5. Try changing "Rejected" back to "Interviewed" → verify allowed (no blocking)

---

### Item 3.3: Confirm Timeline Events Remain Append-Only
**File**: `backend/app/services/timeline_service.py`

**(a) Static Assumption**:
- Timeline events can be deleted or updated
- Event order can be manipulated

**(b) Real Replacement**:
- Verify no DELETE or UPDATE endpoints exist for timeline events
- Add DB constraint: `occurred_at DEFAULT NOW()` (already exists ✅)
- Verify events sorted by `occurred_at ASC` always

**(c) Verification**:
```bash
# Test 1: Attempt to delete timeline event
curl -X DELETE /api/v1/timeline/{event_id}
# Expected: 404 Not Found (no such endpoint)

# Test 2: Verify immutability via DB
psql -d apptrack -c "UPDATE timeline_events SET event_type = 'hacked' WHERE id = 1;"
# Expected: Should succeed (no DB-level constraint in Phase 2)
# But API should never expose UPDATE

# Test 3: Verify chronological order preserved
curl /api/v1/timeline/{app_id} | jq -r '.events[] | .occurred_at' | sort -c
# Expected: No errors (events already sorted)
```

**UI Verification**:
1. View application timeline
2. Verify events listed oldest → newest
3. Trigger multiple events (status changes, analysis runs)
4. Refresh page → verify event order unchanged
5. Verify no "Edit" or "Delete" buttons on timeline items

---

## 4️⃣ ERROR VISIBILITY & GUARDRAILS

### Item 4.1: Surface Missing Data Errors in UI
**Files**:
- `backend/app/api/error_handlers/handlers.py`
- `backend/app/services/analysis/analyzer.py`

**(a) Static Assumption**:
- Missing data errors logged but not returned to user
- Generic 500 error returned for validation failures
- UI shows "Something went wrong" with no details

**(b) Real Replacement**:
- Return HTTP 422 for `MissingDataError` with specific message:
  ```json
  {
    "error": {
      "code": 422,
      "message": "Cannot analyze: job posting not ready",
      "action": "Wait for scraping to complete, then try again"
    }
  }
  ```
- Add error mapping in `error_handlers/handlers.py`:
  ```python
  @app.exception_handler(MissingDataError)
  async def missing_data_handler(request, exc):
      return JSONResponse(status_code=422, content={"error": {...}})
  ```

**(c) Verification**:
```bash
# Test 1: Trigger analysis before posting ready
curl -X POST /api/v1/analysis/{app_id}/analysis/run
# Expected: 422 with actionable message

# Test 2: Capture job with invalid URL
curl -X POST /api/v1/applications/capture \
  -d '{"company_name":"Acme","job_title":"Engineer","job_posting_url":"not-a-url","notes":""}'
# Expected: 422 {"error": "Invalid URL format"}

# Test 3: Upload corrupt resume
curl -X POST /api/v1/resume/upload -F file=@corrupt.pdf
# Expected: 422 {"error": "Failed to parse resume: invalid PDF"}
```

**UI Verification**:
1. Trigger analysis on incomplete job
2. Verify error toast appears: "Cannot analyze: job posting not ready. Try again in a moment."
3. Wait for scraping → retry analysis → verify success
4. Upload corrupt resume → verify error message: "Failed to parse resume. Please upload a valid PDF."

---

### Item 4.2: Surface Failed Parsing in UI
**Files**:
- `backend/app/services/resume_parsing/parser.py`
- `backend/app/api/routes/resume.py`

**(a) Static Assumption**:
- Parsing failures return generic 500 error
- No indication of what failed (skills, experience, contact info)

**(b) Real Replacement**:
- Return partial success with warnings:
  ```json
  {
    "id": "resume-123",
    "extraction_complete": true,
    "warnings": [
      "No email address found",
      "No skills detected - please add manually"
    ]
  }
  ```
- UI shows warning banner with suggestions

**(c) Verification**:
```bash
# Test 1: Upload resume without email
curl -X POST /api/v1/resume/upload -F file=@no_email_resume.pdf
# Expected: 201 with warnings array

# Test 2: Upload resume with no skills section
curl -X POST /api/v1/resume/upload -F file=@minimal_resume.pdf
# Expected: 201 with warning: "No skills detected"

# Test 3: Verify job discovery still works with partial data
curl /api/v1/jobs/discover
# Expected: 200 (even with incomplete resume)
```

**UI Verification**:
1. Upload resume without email → verify warning: "No email found. Job alerts won't work."
2. Upload resume without skills → verify warning: "No skills detected. Job matching may be limited."
3. Verify warnings dismissible (don't block usage)
4. Verify resume still marked as "active" despite warnings

---

### Item 4.3: Surface Failed Discovery in UI
**File**: `backend/app/api/routes/jobs.py`

**(a) Static Assumption**:
- Empty discovery returns empty array (no context)
- User doesn't know WHY no jobs were found

**(b) Real Replacement**:
- Return diagnostic message in empty state:
  ```json
  {
    "jobs": [],
    "message": "No jobs found matching your resume",
    "diagnostics": {
      "resume_skills_count": 0,
      "total_jobs_in_system": 5,
      "reason": "No skills found in resume. Upload a resume with skills listed."
    }
  }
  ```

**(c) Verification**:
```bash
# Test 1: Upload resume with no skills
curl -X POST /api/v1/resume/upload -F file=@no_skills_resume.pdf

# Test 2: Capture jobs with Python requirement
curl -X POST /api/v1/applications/capture -d '{...Python job...}'

# Test 3: Discover jobs
curl /api/v1/jobs/discover | jq .
# Expected: Empty jobs, reason: "No skills found in resume"

# Test 4: Re-upload resume with Python skill
curl -X POST /api/v1/resume/upload -F file=@python_resume.pdf

# Test 5: Discover again
curl /api/v1/jobs/discover | jq '.jobs[] | .job_title'
# Expected: Python job now appears
```

**UI Verification**:
1. Upload resume without skills → navigate to Jobs
2. Verify message: "No jobs found. Upload a resume with skills to see matches."
3. Re-upload resume with skills → verify jobs appear
4. Verify empty state shows count: "5 jobs in system, none match your skills"

---

### Item 4.4: Surface Failed Analysis in UI
**Files**:
- `backend/app/workers/analysis_worker.py`
- `backend/app/api/routes/applications.py`

**(a) Static Assumption**:
- Analysis failures create timeline event but no UI indicator
- User sees "Analyzing..." spinner forever

**(b) Real Replacement**:
- Add `analysis_failed` flag to Application model (or infer from timeline)
- UI shows error badge: "Analysis failed - Retry"
- Clicking "Retry" calls `/api/v1/analysis/{app_id}/analysis/run` again

**(c) Verification**:
```bash
# Test 1: Simulate LLM failure (set invalid API key)
curl -X POST /api/v1/analysis/{app_id}/analysis/run
sleep 10
curl /api/v1/applications/{app_id} | jq '.analysis_completed'
# Expected: false

# Test 2: Check timeline for failure
curl /api/v1/timeline/{app_id} | jq '.events[] | select(.event_type=="analysis_failed")'
# Expected: Event exists with error reason

# Test 3: Retry with valid API key
curl -X POST /api/v1/analysis/{app_id}/analysis/run
sleep 10
curl /api/v1/applications/{app_id} | jq '.analysis_completed'
# Expected: true
```

**UI Verification**:
1. Trigger analysis (simulate failure by disconnecting API key)
2. Wait 60s → verify UI shows "Analysis failed" error badge
3. Click "Retry" → verify new analysis queued
4. Restore API key → verify analysis completes successfully
5. Verify timeline shows both `analysis_failed` and `analysis_completed` events

---

## 5️⃣ INTEGRATION VALIDATION

### Item 5.1: Validate Greenhouse API Integration
**File**: `backend/app/services/scraping/greenhouse_api.py`

**(a) Static Assumption**:
- Greenhouse API always returns 200
- No rate limiting or authentication errors
- Company slug extraction always succeeds

**(b) Real Replacement**:
- Handle 429 Too Many Requests → retry with exponential backoff
- Handle 404 Not Found → fall back to HTML scraping
- Handle missing company slug → extract from URL patterns

**(c) Verification**:
```bash
# Test 1: Valid Greenhouse URL
curl -X POST /api/v1/applications/capture \
  -d '{"company_name":"Stripe","job_title":"Engineer","job_posting_url":"https://boards.greenhouse.io/stripe/jobs/123456","notes":""}'
sleep 5
curl /api/v1/applications/{app_id} | jq '.posting_id'
# Expected: posting_id is not null

# Test 2: Greenhouse URL with gh_jid parameter
curl -X POST /api/v1/applications/capture \
  -d '{"company_name":"Acme","job_title":"Engineer","job_posting_url":"https://acme.com/careers?gh_jid=123456","notes":""}'
sleep 5
curl /api/v1/applications/{app_id} | jq '.posting_id'
# Expected: posting_id is not null (API call succeeded)

# Test 3: Invalid job ID (404)
curl -X POST /api/v1/applications/capture \
  -d '{"company_name":"Stripe","job_title":"Engineer","job_posting_url":"https://boards.greenhouse.io/stripe/jobs/999999999","notes":""}'
sleep 5
curl /api/v1/timeline/{app_id} | jq '.events[] | select(.event_type=="scrape_completed")'
# Expected: Event shows fallback to HTML scraping
```

**UI Verification**:
1. Capture Greenhouse job → verify scraping completes in <5s
2. Capture invalid Greenhouse URL → verify fallback scraping attempt
3. Check timeline → verify `scrape_completed` event shows source: "greenhouse"
4. Verify job posting extracted correctly (title, description, requirements)

---

### Item 5.2: Validate Non-Greenhouse Scraping
**File**: `backend/app/services/scraping/extractor.py`

**(a) Static Assumption**:
- HTML scraping always extracts clean data
- All ATSs have consistent HTML structure

**(b) Real Replacement**:
- Mark extraction as `needs_review = true` if:
  - Description < 100 chars
  - No requirements found
  - Job title doesn't match user-provided title
- Store partial data but block analysis until review

**(c) Verification**:
```bash
# Test 1: Capture Lever job
curl -X POST /api/v1/applications/capture \
  -d '{"company_name":"Figma","job_title":"Engineer","job_posting_url":"https://jobs.lever.co/figma/abc123","notes":""}'
sleep 10
curl /api/v1/applications/{app_id} | jq '.needs_review'
# Expected: Check if partial extraction occurred

# Test 2: Capture custom job board
curl -X POST /api/v1/applications/capture \
  -d '{"company_name":"Startup","job_title":"Engineer","job_posting_url":"https://startup.com/careers/123","notes":""}'
sleep 10
curl /api/v1/applications/{app_id}/posting | jq '.extraction_complete'
# Expected: May be false if scraping failed

# Test 3: Attempt analysis on partial extraction
curl -X POST /api/v1/analysis/{app_id}/analysis/run
# Expected: 422 if extraction incomplete
```

**UI Verification**:
1. Capture non-Greenhouse job
2. Wait for scraping → verify "Review Needed" badge if extraction incomplete
3. Click job → verify partial data shown with warning: "Some details missing"
4. Verify "Run Analysis" button disabled until extraction complete
5. Manual review → mark complete → verify analysis can now run

---

## 6️⃣ RACE CONDITION HANDLING

### Item 6.1: Validate Analysis Waits for Scraping
**File**: `backend/app/workers/analysis_worker.py`

**(a) Static Assumption**:
- Analysis assumes posting already exists when job is enqueued
- Race condition: capture → enqueue analysis → scraping still running

**(b) Real Replacement**:
- Already implemented smart retry logic (✅ lines 85-116)
- Validate it works end-to-end with UI

**(c) Verification**:
```bash
# Test: Trigger analysis immediately after capture
APP_ID=$(curl -X POST /api/v1/applications/capture -d '{...}' | jq -r '.id')
curl -X POST /api/v1/analysis/${APP_ID}/analysis/run
sleep 2
curl /api/v1/timeline/${APP_ID} | jq '.events[] | select(.event_type=="analysis_started")'
# Expected: Event exists (job enqueued)

# Wait for scraping
sleep 15
curl /api/v1/applications/${APP_ID} | jq '.analysis_completed'
# Expected: true (analysis auto-retried after scraping completed)
```

**UI Verification**:
1. Capture job → immediately click "Analyze"
2. Verify "Waiting for job details..." status appears
3. After scraping completes → verify analysis auto-runs
4. Verify no "Analysis failed" error appears
5. Verify timeline shows: scrape_completed → analysis_started → analysis_completed

---

### Item 6.2: Validate Scraping Doesn't Overwrite User Edits
**File**: `backend/app/workers/scraper_worker.py`

**(a) Static Assumption**:
- Scraping overwrites Application fields (company_name, job_title)
- User manually corrects company name → scraping re-breaks it

**(b) Real Replacement**:
- Only update `posting_id` link (never overwrite Application fields)
- JobPosting stores extracted data separately
- User sees both: "You entered: Acme" vs "Scraped: Acme Corp"

**(c) Verification**:
```bash
# Test 1: Capture job with typo
curl -X POST /api/v1/applications/capture \
  -d '{"company_name":"Goggle","job_title":"Engineer","job_posting_url":"https://careers.google.com/jobs/123","notes":""}'

# Test 2: Wait for scraping
sleep 10

# Test 3: Check Application (user input preserved)
curl /api/v1/applications/{app_id} | jq '.company_name'
# Expected: "Goggle" (unchanged)

# Test 4: Check JobPosting (scraped data)
curl /api/v1/applications/{app_id}/posting | jq '.company_name'
# Expected: "Google" (scraped correctly)
```

**UI Verification**:
1. Capture job with typo in company name
2. Wait for scraping
3. Open application details
4. Verify "You entered: Goggle" label shown
5. Verify "Scraped from job posting: Google" label shown
6. Verify user can choose to adopt scraped value

---

## 7️⃣ DATA CONSISTENCY

### Item 7.1: Validate Single Active Resume Enforcement
**File**: `backend/app/services/resume_service.py`

**(a) Static Assumption**:
- Multiple resumes can be marked `is_active = true`
- Job discovery uses random resume if multiple active

**(b) Real Replacement**:
- Already enforced (✅ line in resume service)
- Validate UI clearly indicates which resume is active

**(c) Verification**:
```bash
# Test 1: Upload first resume
RESUME1=$(curl -X POST /api/v1/resume/upload -F file=@resume1.pdf | jq -r '.id')
curl /api/v1/resumes/${RESUME1} | jq '.is_active'
# Expected: true

# Test 2: Upload second resume
RESUME2=$(curl -X POST /api/v1/resume/upload -F file=@resume2.pdf | jq -r '.id')
curl /api/v1/resumes/${RESUME1} | jq '.is_active'
# Expected: false (deactivated automatically)
curl /api/v1/resumes/${RESUME2} | jq '.is_active'
# Expected: true

# Test 3: Verify discovery uses resume2
curl /api/v1/jobs/discover | jq '.resume_id'
# Expected: RESUME2
```

**UI Verification**:
1. Upload resume → verify "Active" badge appears
2. Upload second resume → verify first loses "Active" badge
3. Verify job discovery uses most recent resume
4. Verify user can manually switch active resume

---

### Item 7.2: Validate Timeline Event Timestamps
**File**: `backend/app/db/models/timeline_event.py`

**(a) Static Assumption**:
- Event timestamps can be manipulated
- Events inserted out of chronological order

**(b) Real Replacement**:
- DB default: `occurred_at = NOW()` (✅ already exists)
- Validate API never accepts custom timestamps

**(c) Verification**:
```bash
# Test 1: Attempt to create event with custom timestamp
curl -X POST /api/v1/timeline -d '{"event_type":"custom","occurred_at":"2020-01-01T00:00:00Z"}'
# Expected: 404 Not Found (no POST endpoint exists) ✅

# Test 2: Verify events auto-timestamped
curl /api/v1/timeline/{app_id} | jq -r '.events[] | .occurred_at' | head -1
# Expected: Recent timestamp (not controllable by client)
```

**UI Verification**:
1. View timeline
2. Verify all events show "X minutes ago" or timestamp
3. Verify events sorted chronologically
4. Verify no gaps in timeline (all events captured)

---

## PHASE 2 ACCEPTANCE CRITERIA

### ✅ Phase 2 is COMPLETE when ALL of the following are true:

#### 🎯 Core Functionality (MUST PASS)
- [ ] **Job Discovery Returns Real Data**
  - Jobs page shows scraped jobs from browser extension
  - No hardcoded job listings visible
  - Empty state shows actionable message (not error)

- [ ] **Resume-Based Matching Works**
  - Jobs sorted by match percentage
  - Uploading different resume changes job order
  - Zero-match jobs excluded from results

- [ ] **Application Capture Requires No DB Edits**
  - Browser extension captures job → appears in UI immediately
  - No manual SQL needed to fix data
  - Validation errors surface in UI with clear messages

- [ ] **Analysis Runs Reliably**
  - Analysis completes within 60s for typical job
  - Race condition (analysis before scraping) handled gracefully
  - Analysis failures surface in UI with "Retry" button

- [ ] **State Transitions Work**
  - Status changes: applied → interviewed → offered → accepted (all work)
  - Timeline records all transitions
  - No silent failures or missing events

#### 🛡️ Error Visibility (MUST PASS)
- [ ] **Missing Data Shows in UI**
  - Incomplete resume extraction → warning banner
  - Failed scraping → error badge with retry option
  - Failed analysis → error message with reason

- [ ] **No Silent Failures**
  - All API errors return HTTP 4xx/5xx (not 200 with error in body)
  - Timeline events never return `null` silently
  - Validation errors show field-specific messages

- [ ] **Graceful Degradation**
  - Empty job discovery → helpful message (not crash)
  - Partial resume parse → warnings (not failure)
  - Analysis timeout → retry option (not stuck spinner)

#### 🔄 Integration Hardness (MUST PASS)
- [ ] **Greenhouse API Integration**
  - Greenhouse jobs scrape in <5s
  - Fallback to HTML scraping on API 404
  - Company slug extraction works for custom domains

- [ ] **Non-Greenhouse Scraping**
  - Lever jobs extract correctly
  - Workday jobs extract correctly
  - Custom job boards extract partial data + flag for review

- [ ] **Background Workers Stable**
  - Scraper queue processes jobs without crashing
  - Analysis queue retries transient failures
  - No infinite retry loops

#### 📊 Data Consistency (MUST PASS)
- [ ] **Timeline Integrity**
  - All events append-only (no edits/deletes)
  - Events sorted chronologically always
  - Event timestamps accurate (within 1s of action)

- [ ] **Resume Activation**
  - Only one resume active at a time
  - Job discovery always uses active resume
  - Switching resumes updates job matches

- [ ] **Application Lifecycle**
  - Status changes recorded in timeline
  - Deleted applications excluded from queries
  - Analysis results linked correctly to applications

#### 🧪 User Validation (MUST PASS - MANUAL TEST)
- [ ] **Daily Use Test (3 Days)**
  - Upload resume → capture 5 jobs → analyze all 5 → no crashes
  - Change application statuses → verify timeline updates
  - Upload new resume → verify job discovery refreshes

- [ ] **Error Recovery Test**
  - Trigger analysis on incomplete job → verify error message
  - Upload corrupt resume → verify parse error shown
  - Capture invalid URL → verify scraping failure surfaced

- [ ] **Browser Extension Test**
  - Capture Greenhouse job → verify scraping works
  - Capture Lever job → verify scraping works
  - Capture unknown ATS → verify partial extraction + review flag

---

## KNOWN LIMITATIONS (DEFERRED TO PHASE 3)

### ⏭️ Out of Scope for Phase 2

1. **Job Board Ingestion**
   - No automatic job discovery from APIs (Indeed, LinkedIn, etc.)
   - Jobs only captured via browser extension (manual)
   - **Rationale**: Phase 2 validates existing flows, not new features

2. **ATS Coverage Expansion**
   - Only Greenhouse has dedicated API integration
   - Lever, Workday, others use HTML scraping fallback
   - **Rationale**: Scraping works adequately for Phase 2 validation

3. **Advisory System Improvements**
   - Silent error suppression remains (by design per exploration)
   - No ML model tuning or quality improvements
   - **Rationale**: Advisory is read-only, doesn't block core flows

4. **Performance Optimization**
   - No pagination on jobs endpoint
   - No caching of analysis results
   - No database indexing tuning
   - **Rationale**: Scale not a concern for Phase 2 (testing with <100 jobs)

5. **UX Polish**
   - No loading state improvements beyond basic spinners
   - No empty state illustrations or onboarding
   - No mobile responsive design
   - **Rationale**: Phase 2 focuses on functionality, not aesthetics

6. **Authentication & Multi-User**
   - Single user assumed (no auth system)
   - No user management or permissions
   - **Rationale**: Not needed for validation testing

7. **Advanced Analytics**
   - No application funnel metrics
   - No match score trend analysis
   - No email alerts on status changes
   - **Rationale**: Phase 3 feature expansion

8. **Strict State Machine Enforcement**
   - All status transitions allowed (no FSM validation)
   - Unusual transitions (applied → accepted) logged but not blocked
   - **Rationale**: Adds complexity without clear hardening benefit

9. **Error Tracking/Observability**
   - No Sentry/Datadog integration
   - No request tracing IDs
   - No error aggregation dashboard
   - **Rationale**: Logging to console sufficient for Phase 2

10. **Resume Format Support**
    - PDF and DOCX only
    - No TXT, RTF, HTML resume support
    - **Rationale**: Covers 95% of use cases

---

## EXECUTION SEQUENCE

### Week 1: Replace Static Paths
1. Item 1.1: Remove hardcoded jobs (DAY 1-2)
2. Item 1.2: Validate resume-indexed discovery (DAY 2-3)
3. Item 1.3: Handle empty discovery (DAY 3)

### Week 2: Harden Analysis + Lifecycle
4. Item 2.1: Validate analysis reliability (DAY 4-5)
5. Item 2.2: Ensure deterministic ranking (DAY 5)
6. Item 3.1: Fix application capture validation (DAY 6)
7. Item 3.2: Validate state transitions (DAY 6)

### Week 3: Error Visibility + Integration
8. Item 4.1-4.4: Surface all errors in UI (DAY 7-8)
9. Item 5.1-5.2: Validate integrations (DAY 9-10)
10. Item 6.1-6.2: Race condition handling (DAY 10)

### Week 4: Data Consistency + Validation
11. Item 7.1-7.2: Data consistency checks (DAY 11)
12. Acceptance testing (DAY 12-14)
13. Bug fixes from testing (DAY 15+)

---

## SUCCESS METRICS

**Phase 2 is done when:**
1. ✅ Zero static data paths remain in production code
2. ✅ 3-day user test completes without developer intervention
3. ✅ All acceptance criteria pass
4. ✅ All error states visible in UI (no silent failures)
5. ✅ Timeline integrity validated (append-only, chronological)

**Phase 2 is NOT done if:**
- ❌ Hardcoded jobs still appear in discovery
- ❌ Analysis fails silently without UI indication
- ❌ Application capture requires manual DB edits
- ❌ Race conditions cause data corruption
- ❌ User encounters unhandled 500 errors

---

## NOTES

- **Advisory System**: Errors suppressed by design (read-only feature). No changes needed unless it blocks core flows.
- **Retries**: Smart retry logic already implemented in analysis worker. Validate it works end-to-end.
- **Timeline Events**: Already append-only at API level (no DELETE/UPDATE endpoints). DB-level constraint deferred to Phase 3.
- **Greenhouse Integration**: Already implemented and working. Validate with real URLs.
- **Browser Extension**: Assumed to be working (out of scope for backend hardening).

---

**REMINDER**: The goal is NOT perfection. The goal is stability and visibility. If it breaks, it must be loud.
