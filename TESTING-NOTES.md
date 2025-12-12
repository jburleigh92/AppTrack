# AppTrack Testing Notes

## Test Environment
- **Platform**: GitHub Codespaces (Ubuntu)
- **Database**: PostgreSQL 16
- **Python**: 3.12.1
- **Framework**: FastAPI with Uvicorn

## Phase 1-4: Core Backend Testing ✅ COMPLETE

### Repository & Deployment
- ✅ Repository structure organized (backend/, docs/)
- ✅ GitHub integration and version control
- ✅ Codespaces deployment successful

### Database
- ✅ PostgreSQL 16 installed and configured
- ✅ All Alembic migrations applied successfully
- ✅ 12 tables created with proper relationships
- ✅ Connection pooling and session management working

### API Server
- ✅ FastAPI server running on port 8000
- ✅ Swagger UI accessible at /docs
- ✅ CORS middleware configured
- ✅ All route modules loaded successfully

### Health Checks
- ✅ GET /api/v1/health/health/live → 200 OK
- ✅ GET /api/v1/health/health/ready → 200 OK with database connection verified

### Application Ingestion
- ✅ POST /api/v1/applications/capture (browser source)
  - Created test application: Test Corp - Software Engineer
  - Status: applied, Source: browser
- ✅ POST /api/v1/emails/ingest (email source)
  - Created test application: Acme Corp - Senior Developer
  - Status: applied, Source: email
  - Correlation strategy: created_new

### Timeline Events
- ✅ GET /api/v1/timeline/{application_id}/timeline
  - Returns chronological event list
  - Tracks application_created events
  - 6 total timeline events recorded

### Export Functionality
- ✅ POST /api/v1/exports/csv
  - Successfully generated CSV with 2 applications
  - Includes all fields: company, title, status, dates, notes
  - Proper formatting and headers

## Phase 5: Scraper Service Testing 🔄 IN PROGRESS

### Scraper Queue System
- ✅ POST /api/v1/scraper/scrape endpoint functional
- ✅ Jobs enqueued successfully to scraper_queue table
- ✅ Queue records include: id, application_id, url, status, timestamps

### Background Worker
- ✅ Scraper worker implemented with queue polling
- ✅ Job status transitions: pending → processing → completed/failed
- ✅ Worker processes jobs asynchronously
- ✅ Error handling for HTTP errors (404, timeouts, etc.)
- ✅ Database updates on completion/failure

### Test Results
- **Test 1**: Lever.co test URL (non-existent)
  - Status: failed (404)
  - Error message: "URL not found (404)"
  - Completed at: 2025-12-12 21:58:16
- **Test 2**: Anthropic jobs page
  - Status: failed (404)
  - Worker successfully detected and logged error

### Known Issues
- Test URLs return 404 (expected for non-existent pages)
- Need to test with actual live job posting URLs
- Worker uses deprecated datetime.utcnow() (warning logged)

## Test Data Summary

### Applications Table (2 records)
| ID | Company | Title | Source | Date |
|----|---------|-------|--------|------|
| 5fa2837d... | Test Corp | Software Engineer | browser | 2025-12-12 |
| 573e7096... | Acme Corp | Senior Developer | email | 2025-12-10 |

### Scraper Queue (2 jobs)
| ID | Status | URL | Error |
|----|--------|-----|-------|
| be6e08e1... | failed | lever.co/example/... | URL not found (404) |
| 8a37ab58... | failed | lever.co/anthropic | URL not found (404) |

### Timeline Events (6 events)
- 2x application_created (browser)
- 2x application_created (email)
- 2x scrape_started
- (scrape_failed events expected but may be recorded)

## Outstanding Work

### Phase 5 (Scraper) - Remaining
- [ ] Test with real, live job posting URLs
- [ ] Verify HTML extraction logic
- [ ] Test ATS platform detection (Greenhouse, Lever, Workday, etc.)
- [ ] Validate job_postings table population
- [ ] Test application-to-posting linking

### Phase 6 (AI Analysis)
- [ ] Implement analysis worker
- [ ] Test LLM integration (OpenAI/Anthropic)
- [ ] Verify resume-job matching logic
- [ ] Test analysis_results table population

### Phase 7 (Additional Features)
- [ ] Google Sheets sync functionality
- [ ] End-to-end workflow testing
- [ ] Performance testing with multiple concurrent jobs
- [ ] Error recovery and retry logic

## Commands for Testing

### Start API Server
```bash
cd /workspaces/AppTrack/backend
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Start Scraper Worker
```bash
cd /workspaces/AppTrack/backend
source venv/bin/activate
python -m app.workers.scraper_worker
```

### Database Queries
```bash
# Check applications
PGPASSWORD=postgres psql -h localhost -U postgres -d jobtracker -c "SELECT * FROM applications;"

# Check scraper queue
PGPASSWORD=postgres psql -h localhost -U postgres -d jobtracker -c "SELECT * FROM scraper_queue;"

# Check timeline events
PGPASSWORD=postgres psql -h localhost -U postgres -d jobtracker -c "SELECT * FROM timeline_events ORDER BY created_at;"
```

### API Test Commands
```bash
# Health check
curl http://localhost:8000/api/v1/health/health/ready

# Create application
curl -X POST http://localhost:8000/api/v1/applications/capture \
  -H "Content-Type: application/json" \
  -d '{"company_name": "Example Corp", "job_title": "Engineer", "job_posting_url": "https://example.com/job"}'

# Trigger scrape
curl -X POST http://localhost:8000/api/v1/scraper/scrape \
  -H "Content-Type: application/json" \
  -d '{"application_id": "UUID", "url": "https://jobs.lever.co/..."}'

# Export CSV
curl -X POST http://localhost:8000/api/v1/exports/csv \
  -H "Content-Type: application/json" \
  -d '{}' -o export.csv
```

## Notes
- All timestamps are in UTC
- Database connection uses connection pooling (pool_size=10, max_overflow=20)
- API server auto-reloads on code changes in development mode
- Worker runs in continuous polling mode (5 second intervals)
- All changes committed to GitHub after each successful test phase
