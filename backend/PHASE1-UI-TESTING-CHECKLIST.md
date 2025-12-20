# Phase 1 UI Testing Checklist

## Setup Instructions

### Prerequisites
1. PostgreSQL database running on localhost:5432
2. Database named `jobtracker` created
3. Environment variables set in `.env`:
   ```bash
   DATABASE_URL=postgresql://user:password@localhost:5432/jobtracker
   ```
4. Run migrations:
   ```bash
   alembic upgrade heads
   ```
5. Start the server:
   ```bash
   uvicorn app.main:app --reload
   ```
6. Navigate to `http://localhost:8000` in your browser

---

## ✅ Pre-Apply Flow

### Screen 1: Resume Upload (`/`)

- [ ] **Page loads correctly**
  - [ ] Navigation bar shows: Resume | Jobs | Applications
  - [ ] Upload form is visible with file input
  - [ ] File input accepts .pdf and .docx only

- [ ] **File upload validation**
  - [ ] Cannot submit without selecting a file
  - [ ] Files larger than 10MB are rejected with error message
  - [ ] Non-PDF/DOCX files show appropriate error

- [ ] **Resume upload and parsing**
  - [ ] Upload a PDF resume → parsing starts
  - [ ] "Parsing resume..." loading message appears
  - [ ] Parsed data displays: Contact Info, Skills, Experience, Education
  - [ ] Skills appear as colored tags
  - [ ] Experience items show title, company, duration
  - [ ] Education items show degree, institution, year

- [ ] **Continue button behavior**
  - [ ] Button is disabled while parsing
  - [ ] Button enables when `extraction_complete = true`
  - [ ] Clicking "Continue to Jobs" navigates to `/jobs`

- [ ] **Returning user (already has resume)**
  - [ ] If active resume exists, it displays automatically
  - [ ] "Continue to Jobs" button is enabled immediately

---

### Screen 2: Job Recommendations (`/jobs`)

- [ ] **Navigation guard**
  - [ ] If no active resume: redirects to `/` with error message
  - [ ] If active resume exists: page loads successfully

- [ ] **Job list display**
  - [ ] Loading message appears initially
  - [ ] Jobs load from `/api/v1/jobs/discover`
  - [ ] Each job card shows:
    - [ ] Job title and company name
    - [ ] Location (if available)
    - [ ] Match percentage badge
    - [ ] "Why this match" reasoning

- [ ] **Missing skills section**
  - [ ] "Missing X skills" summary is clickable
  - [ ] Expanding shows red-tagged missing skills
  - [ ] Count is accurate

- [ ] **Apply button**
  - [ ] "Apply on Company Site" button opens job URL in new tab
  - [ ] URL opens correctly in external window

- [ ] **I Applied button**
  - [ ] Clicking "I Applied" navigates to `/applications`
  - [ ] URL includes query params: `?company=X&title=Y&url=Z`
  - [ ] Parameters are correctly encoded

- [ ] **Empty state**
  - [ ] If no jobs found: "No Job Recommendations" message displays

---

## ✅ Post-Apply Flow

### Screen 3: Applications Dashboard (`/applications`)

#### Application Capture Form

- [ ] **Pre-filled data from URL params**
  - [ ] Company name is pre-filled (if coming from Jobs page)
  - [ ] Job title is pre-filled
  - [ ] Job URL is pre-filled

- [ ] **Form validation**
  - [ ] Company name is required
  - [ ] Job title is required
  - [ ] Job URL is optional
  - [ ] Notes are optional
  - [ ] Form cannot submit without required fields

- [ ] **Form submission**
  - [ ] Submit calls `POST /api/v1/applications/capture`
  - [ ] Success shows green alert: "Application captured successfully!"
  - [ ] Form resets after successful submission
  - [ ] Application appears in list below immediately

#### Applications List

- [ ] **Initial load**
  - [ ] Loading message appears
  - [ ] Applications load from `GET /api/v1/applications`
  - [ ] Table shows: Company | Job Title | Status | Applied Date

- [ ] **Empty state**
  - [ ] If no applications: "No Applications Yet" message displays
  - [ ] Message prompts to capture first application

- [ ] **Status dropdown**
  - [ ] Each row has status dropdown with options:
    - [ ] Applied
    - [ ] Screening
    - [ ] Interview
    - [ ] Offer
    - [ ] Rejected
    - [ ] Withdrawn
  - [ ] Current status is selected
  - [ ] Changing status calls `PATCH /api/v1/applications/{id}`
  - [ ] Success shows alert: "Status updated successfully!"
  - [ ] List refreshes to show updated status

- [ ] **Expandable row**
  - [ ] Clicking row (not status dropdown) expands details
  - [ ] Details section toggles open/closed
  - [ ] Clicking again collapses details

#### Timeline Section (in expanded row)

- [ ] **Timeline loads**
  - [ ] Timeline fetches from `GET /api/v1/applications/{id}/timeline`
  - [ ] Events display in reverse chronological order
  - [ ] Each event shows:
    - [ ] Event type (formatted: "Application Captured", "Status Changed")
    - [ ] Timestamp (formatted as readable date/time)
    - [ ] Event data (if available)

- [ ] **Timeline events**
  - [ ] "Application Captured" event exists for all applications
  - [ ] Status changes create "Status Changed" events
  - [ ] Event data shows old → new status (if status changed)

- [ ] **Empty timeline**
  - [ ] If no events: "No timeline events" message displays

#### Analysis Section (in expanded row)

- [ ] **No analysis exists**
  - [ ] Shows "No analysis run yet"
  - [ ] "Run Analysis" button is visible
  - [ ] Button is enabled

- [ ] **Triggering analysis**
  - [ ] Click "Run Analysis" → calls `POST /api/v1/analysis/{id}/analysis/run`
  - [ ] Button disables and text changes to "Running Analysis..."
  - [ ] Info alert shows: "Analysis started! Refresh the page in a few seconds to see results."
  - [ ] Button text updates to "Analysis In Progress..."

- [ ] **Analysis results (after refresh)**
  - [ ] Refresh page or re-expand row
  - [ ] Analysis section shows:
    - [ ] Match score percentage (large, bold, green)
    - [ ] ✅ Qualifications Met (list with count)
    - [ ] ❌ Qualifications Missing (list with count)
    - [ ] 💡 Suggestions (list)
  - [ ] All data displays correctly from `GET /api/v1/analysis/{id}/analysis`

---

## ✅ End-to-End Flow Verification

### Complete User Journey (No Manual DB Intervention)

1. [ ] **Fresh start**
   - [ ] Navigate to `http://localhost:8000`
   - [ ] No active resume exists

2. [ ] **Upload resume**
   - [ ] Upload a PDF/DOCX resume
   - [ ] Wait for parsing to complete
   - [ ] Verify parsed data displays
   - [ ] Click "Continue to Jobs"

3. [ ] **Browse jobs**
   - [ ] See list of recommended jobs
   - [ ] Expand "Missing Skills" on one job
   - [ ] Click "Apply on Company Site" → external URL opens
   - [ ] Return to AppTrack
   - [ ] Click "I Applied" on the same job

4. [ ] **Capture application**
   - [ ] Verify form is pre-filled with job data
   - [ ] Add notes: "Applied via LinkedIn"
   - [ ] Submit form
   - [ ] See success message
   - [ ] Application appears in table

5. [ ] **Update status**
   - [ ] Change status from "Applied" to "Screening"
   - [ ] Verify success message
   - [ ] Status updates in table

6. [ ] **View timeline**
   - [ ] Click row to expand
   - [ ] See timeline events:
     - [ ] "Application Captured"
     - [ ] "Status Changed to screening"
   - [ ] Timestamps are correct

7. [ ] **Run analysis**
   - [ ] Click "Run Analysis"
   - [ ] See "Analysis in progress" message
   - [ ] Wait 5-10 seconds
   - [ ] Refresh page or re-expand row
   - [ ] Analysis results display with match score and recommendations

8. [ ] **Navigate back to resume**
   - [ ] Click "Resume" in nav
   - [ ] Active resume displays immediately
   - [ ] Can navigate to Jobs again without re-uploading

9. [ ] **Navigate to Applications**
   - [ ] Click "Applications" in nav
   - [ ] Previously captured application is visible
   - [ ] Status is still "Screening"

---

## ✅ Edge Cases & Error Handling

### Error Scenarios

- [ ] **No backend connection**
  - [ ] Stop backend server
  - [ ] Try to upload resume → shows error message
  - [ ] Try to load jobs → shows error message
  - [ ] Error messages are user-friendly

- [ ] **API errors**
  - [ ] Invalid resume file → error displayed
  - [ ] Duplicate application → (backend should handle or show error)
  - [ ] Analysis fails → error message displayed

- [ ] **Empty states**
  - [ ] No resume → redirects to `/`
  - [ ] No jobs → "No recommendations" message
  - [ ] No applications → "No applications yet" message
  - [ ] No timeline events → "No timeline events" message
  - [ ] No analysis → "No analysis run yet" message

### Browser Compatibility

- [ ] **Chrome/Edge**
  - [ ] All features work
  - [ ] No console errors

- [ ] **Firefox**
  - [ ] All features work
  - [ ] No console errors

- [ ] **Safari** (if available)
  - [ ] All features work
  - [ ] No console errors

---

## ✅ UI/UX Quality Checks

- [ ] **Visual consistency**
  - [ ] Navigation bar is consistent across all pages
  - [ ] Buttons use consistent styling
  - [ ] Forms are readable and aligned
  - [ ] Cards have consistent spacing

- [ ] **Responsive behavior** (optional for Phase 1)
  - [ ] Layout doesn't break on smaller screens
  - [ ] Tables are readable

- [ ] **Loading states**
  - [ ] Loading messages appear when fetching data
  - [ ] Loading messages disappear when data loads

- [ ] **Success/error feedback**
  - [ ] Success messages are green
  - [ ] Error messages are red
  - [ ] Messages auto-dismiss after 5 seconds

---

## ✅ API Integration Verification

### Endpoints Used (verify in Network tab)

- [ ] `POST /api/v1/resume/upload` - Resume upload
- [ ] `GET /api/v1/resume/active` - Get active resume
- [ ] `GET /api/v1/jobs/discover` - Get job recommendations
- [ ] `POST /api/v1/applications/capture` - Capture application
- [ ] `GET /api/v1/applications` - List applications
- [ ] `PATCH /api/v1/applications/{id}` - Update status
- [ ] `GET /api/v1/applications/{id}/timeline` - Get timeline
- [ ] `POST /api/v1/analysis/{id}/analysis/run` - Trigger analysis
- [ ] `GET /api/v1/analysis/{id}/analysis` - Get analysis results

### HTTP Status Codes

- [ ] 200 OK for successful GET requests
- [ ] 201 Created for successful POST requests
- [ ] 404 Not Found for missing resources (handled gracefully)
- [ ] 422 Validation Error for invalid input (shows user-friendly message)

---

## ✅ Phase 1 Completion Criteria

Phase 1 is complete when **ALL** of the following are true:

1. [ ] A real user can upload a resume without developer intervention
2. [ ] Resume parsing completes and displays parsed data
3. [ ] User can see a ranked list of jobs based on their resume
4. [ ] User can click out to apply on external job sites
5. [ ] User can manually capture applications back into AppTrack
6. [ ] Application lifecycle states can be updated (applied → screening → interview → offer → rejected/withdrawn)
7. [ ] Timeline accurately reflects state changes
8. [ ] Analysis can be triggered and results are visible
9. [ ] Analysis links the resume, job posting, and application
10. [ ] **Zero database scripts or developer intervention required** for the entire flow

---

## Notes

- **Phase 1 UI is intentionally minimal** - No fancy styling, no advanced features
- **Boring is better** - Explicit, functional, and reliable
- **Backend truth is surfaced** - Empty states and errors are clearly communicated
- **No premature optimization** - Refresh instead of polling is acceptable

---

## Issues Found During Testing

_Document any bugs or issues discovered:_

1. [Issue description]
   - **Expected:** [What should happen]
   - **Actual:** [What actually happens]
   - **Steps to reproduce:** [How to trigger the issue]

---

## Testing Completed By

- **Tester Name:**
- **Date:**
- **Environment:** (OS, Browser, Database version)
- **Result:** ✅ PASS / ❌ FAIL

---

**Phase 1 Status:** [READY FOR TESTING / IN PROGRESS / COMPLETE]
