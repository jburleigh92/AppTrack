
# Job Index Ingestion Guide

## Overview

The AppTrack job index uses **production-quality ingestion** with full traceability and validation. Every job in the index can answer:

- **Where did this come from?** (`source`, `source_query`)
- **When was it posted?** (`posted_at`)
- **When was it fetched?** (`source_timestamp`)
- **What industry is it?** (`industry`)

## Required Fields

Every ingested job **must** have:

1. **Core Data:**
   - `job_title` (non-empty)
   - `company_name` (non-empty)
   - `description` (≥50 characters)
   - `external_url` (apply link)

2. **Traceability:**
   - `source` (e.g., `serpapi_google_jobs`)
   - `source_query` (keyword used to fetch it)
   - `source_timestamp` (when fetched)
   - `posted_at` (original posting date)
   - `industry` (classified industry)

Jobs missing any required field are **dropped** and logged in the audit.

## Data Sources

### SerpAPI Google Jobs (Production)

**Preferred** - Fetches real, current jobs from Google Jobs aggregator.

**Requirements:**
- SerpAPI API key (get from [serpapi.com](https://serpapi.com/))
- `requests` Python library: `pip install requests`

**Features:**
- Global coverage (all industries, all companies)
- Real-time data (jobs posted within last 30 days)
- Structured data (title, company, description, posted date)
- Legal and documented API

### Seed Data (Development/Testing)

Synthetic jobs for bootstrapping demos. **Not for production use.**

## Usage

### Option 1: Command Line (Recommended)

```bash
# Set API key
export SERPAPI_API_KEY="your_key_here"

# Run production ingestion
python scripts/ingest_production_jobs.py

# With custom settings
python scripts/ingest_production_jobs.py --queries-per-industry 3 --max-per-query 100

# Export audit log to file
python scripts/ingest_production_jobs.py --export-audit audit.json
```

### Option 2: HTTP API

```bash
# Production ingestion
POST /internal/jobs/ingest?source=production

# With custom parameters
POST /internal/jobs/ingest?source=production&queries_per_industry=3&max_per_query=100

# Seed data (testing only)
POST /internal/jobs/ingest?source=seed

# Check index health
GET /internal/jobs/stats
```

### Option 3: Python Code

```python
from app.db.session import SessionLocal
from app.services.validated_ingestion import ingest_validated_jobs, get_index_health
import os

db = SessionLocal()
api_key = os.environ.get("SERPAPI_API_KEY")

# Run ingestion
audit = ingest_validated_jobs(
    db=db,
    api_key=api_key,
    queries_per_industry=2,
    max_jobs_per_query=50
)

# Check results
audit.log_summary()
health = get_index_health(db)
print(health)

db.close()
```

## Industry Coverage

Ingestion **deliberately covers multiple industries**, not just tech:

- **Software / IT** - `software engineer`, `frontend developer`, `devops engineer`
- **Data / Analytics / AI** - `data scientist`, `data engineer`, `ml engineer`
- **Sales / Marketing** - `account executive`, `marketing manager`
- **Operations / Warehouse** - `warehouse associate`, `operations manager`
- **Finance / Accounting** - `accountant`, `financial analyst`
- **Healthcare / Medical** - `registered nurse`, `medical assistant`
- **Education / Training** - `teacher`, `training specialist`
- **Customer Support** - `customer success manager`, `technical support`

Industry is **classified automatically** based on job title and description using explicit rules (no ML, no guessing).

## Validation Rules

Jobs are dropped if:

1. **Missing required fields** - Any of: title, company, description, external_url
2. **Description too short** - Less than 50 characters
3. **Posted too long ago** - More than 30 days old (configurable)
4. **Unclassifiable industry** - Cannot determine industry from title/description
5. **Duplicate** - Same `external_id` already exists

All drops are **logged in the audit** with reasons.

## Audit Logging

Every ingestion run produces a comprehensive audit log:

```json
{
  "summary": {
    "jobs_fetched": 500,
    "jobs_inserted": 387,
    "jobs_updated": 12,
    "jobs_dropped_total": 101
  },
  "drops_breakdown": {
    "missing_required_fields": 23,
    "outdated_posting_date": 45,
    "duplicate_external_id": 12,
    "unclassifiable_industry": 21
  },
  "jobs_by_industry": {
    "Software / IT": 156,
    "Operations / Warehouse / Logistics": 89,
    "Sales / Marketing": 67,
    "Finance / Accounting": 42,
    "Healthcare / Medical": 33
  },
  "jobs_by_query": {
    "software engineer": 89,
    "warehouse associate": 67,
    "marketing manager": 45
  },
  "date_range": {
    "oldest_posted_at": "2024-11-20T00:00:00",
    "newest_posted_at": "2024-12-20T00:00:00"
  },
  "errors": ["...", "..."],
  "total_errors": 101
}
```

## Verification

After ingestion, verify the index is working:

```bash
# Search for tech jobs
GET /api/v1/jobs/search?keyword=engineer

# Search for non-tech jobs
GET /api/v1/jobs/search?keyword=warehouse
GET /api/v1/jobs/search?keyword=marketing
GET /api/v1/jobs/search?keyword=nurse

# Check index health
GET /internal/jobs/stats
```

Expected results:
- Jobs have recent `posted_at` dates (within 30 days)
- Jobs have correct `industry` classification
- Jobs have `source_query` matching search terms
- Multiple industries represented (not just tech)

## Troubleshooting

### Zero jobs inserted

**Possible causes:**
1. SerpAPI API key invalid or expired
2. SerpAPI quota exceeded
3. All jobs failed validation (check `drops_breakdown`)
4. All jobs were duplicates (re-running without clearing)

**Fix:**
- Check API key: `echo $SERPAPI_API_KEY`
- Check SerpAPI dashboard for quota/errors
- Review audit log for drop reasons
- Clear duplicates if re-testing: `DELETE FROM job_postings`

### All jobs classified as "unknown"

**Cause:** Industry classifier rules don't match job titles/descriptions

**Fix:** Update `backend/app/services/industry_classifier.py` with better keywords for your target industries

### SerpAPI rate limit errors

**Cause:** Too many requests too fast

**Fix:**
- Reduce `queries_per_industry` parameter
- Reduce `max_per_query` parameter
- Add delays between runs
- Upgrade SerpAPI plan

### Jobs too old (all dropped as outdated)

**Cause:** SerpAPI returned jobs older than 30 days

**Fix:**
- This is working as designed (validation is strict)
- Check if SerpAPI is returning stale data
- Adjust `MAX_JOB_AGE_DAYS` in `validated_ingestion.py` if needed

## Database Schema

Jobs are stored in the `job_postings` table with:

```sql
-- Core data
job_title VARCHAR(255) NOT NULL
company_name VARCHAR(255) NOT NULL
description TEXT
location VARCHAR(255)
employment_type VARCHAR(50)

-- Traceability (required for production)
source VARCHAR(50)                  -- 'serpapi_google_jobs'
source_query VARCHAR(200)           -- 'software engineer'
source_timestamp TIMESTAMP          -- When fetched
posted_at TIMESTAMP                 -- Original posting date
industry VARCHAR(100)               -- 'Software / IT'

-- Ingestion metadata
external_url TEXT                   -- Apply link
external_id VARCHAR(200)            -- Deduplication ID
extraction_complete BOOLEAN

-- Standard timestamps
created_at TIMESTAMP
updated_at TIMESTAMP
```

**Indexes:**
- `(source, external_id)` - UNIQUE (deduplication)
- `source_query` - For audit queries
- `posted_at` - For freshness checks
- `industry` - For coverage analysis

## Maintenance

### Regular ingestion schedule

Run ingestion **daily or weekly** to keep index fresh:

```bash
# Cron example (daily at 2 AM)
0 2 * * * cd /path/to/backend && SERPAPI_API_KEY=xxx python scripts/ingest_production_jobs.py
```

### Cleanup old jobs

Remove jobs older than 60 days:

```bash
POST /internal/jobs/cleanup?days_old=60
```

### Monitor index health

```bash
GET /internal/jobs/stats
```

Check:
- `traceability_percentage` should be >90%
- `jobs_by_industry` should show diversity
- `newest_posted_at` should be recent

## Cost Estimates

**SerpAPI pricing** (as of Dec 2024):
- Free plan: 100 searches/month
- Starter: $50/month - 5,000 searches
- Production: $250/month - 30,000 searches

**Ingestion costs:**
- Default settings: 16 queries (8 industries × 2 queries each)
- Conservative run: ~16 searches = $0.08 (production plan)
- Daily ingestion: ~$2.40/month
- Weekly ingestion: ~$0.60/month

**Recommendation:** Start with weekly ingestion on Starter plan.

## Architecture

```
┌─────────────────┐
│   SerpAPI       │  Fetch real jobs
│  Google Jobs    │  from Google Jobs
└────────┬────────┘
         │
         v
┌─────────────────┐
│  Industry       │  Classify industry
│  Classifier     │  based on rules
└────────┬────────┘
         │
         v
┌─────────────────┐
│  Validation     │  Enforce required
│  Pipeline       │  fields and dates
└────────┬────────┘
         │
         v
┌─────────────────┐
│  Deduplication  │  Check external_id
│                 │  for uniqueness
└────────┬────────┘
         │
         v
┌─────────────────┐
│  job_postings   │  Indexed, searchable
│  Database       │  local storage
└─────────────────┘
```

Search queries **never touch external APIs** - only query the local database.
