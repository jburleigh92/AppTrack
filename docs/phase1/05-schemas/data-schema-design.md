# Job Application Tracker - Database Schema Specification

**Document Version:** 1.0  
**Last Updated:** December 10, 2025  
**Status:** Final Database Design

---

## Table of Contents

1. [Overview](#1-overview)
2. [Entity Relationship Diagram](#2-entity-relationship-diagram)
3. [Table Specifications](#3-table-specifications)
4. [Indexes](#4-indexes)
5. [Constraints](#5-constraints)
6. [Migrations](#6-migrations)

---

## 1. Overview

### Database Technology
- **RDBMS:** PostgreSQL 14+
- **ORM:** SQLAlchemy 2.0+
- **Migrations:** Alembic

### Design Principles
- **Normalization:** 3NF where practical
- **Soft deletes:** Applications use is_deleted flag
- **Audit trails:** All tables have created_at, updated_at
- **JSONB for flexibility:** Semi-structured data in JSONB columns
- **Foreign key cascades:** Clean deletion of related records

### Schema Statistics
- **Tables:** 12
- **Indexes:** 28+
- **Foreign Keys:** 11
- **Check Constraints:** 8
- **Unique Constraints:** 5

---

## 2. Entity Relationship Diagram

```
┌─────────────────────┐
│    applications     │
│  (main entity)      │
│                     │
│ PK: id              │
│ FK: posting_id      │──┐
│ FK: analysis_id     │  │
└─────────────────────┘  │
         │               │
         │ 1:N           │
         ▼               │ 1:1
┌─────────────────────┐  │
│  timeline_events    │  │
│  (audit trail)      │  │
│                     │  │
│ PK: id              │  │
│ FK: application_id  │  │
└─────────────────────┘  │
                         │
         ┌───────────────┘
         │ 1:1
         ▼
┌─────────────────────┐
│   job_postings      │
│  (structured data)  │
│                     │
│ PK: id              │
└─────────────────────┘
         ▲
         │ 1:1
┌─────────────────────┐
│  scraped_postings   │
│   (raw HTML)        │
│                     │
│ PK: id              │
│ FK: job_posting_id  │
└─────────────────────┘


┌─────────────────────┐
│      resumes        │
│  (metadata)         │
│                     │
│ PK: id              │
└─────────────────────┘
         │ 1:1
         ▼
┌─────────────────────┐
│   resume_data       │
│ (structured data)   │
│                     │
│ PK: id              │
│ FK: resume_id       │
└─────────────────────┘


┌─────────────────────┐
│  analysis_results   │
│  (AI analysis)      │
│                     │
│ PK: id              │
│ FK: application_id  │
│ FK: resume_id       │
│ FK: job_posting_id  │
└─────────────────────┘


┌─────────────────────┐
│   scraper_queue     │
│   parser_queue      │
│   analysis_queue    │
│  (job queues)       │
│                     │
│ PK: id              │
│ FK: application_id  │
│     (or resume_id)  │
└─────────────────────┘


┌─────────────────────┐
│processed_email_uids │
│  (idempotency)      │
│                     │
│ PK: id              │
│ UQ: email_uid       │
└─────────────────────┘


┌─────────────────────┐
│      settings       │
│   (singleton)       │
│                     │
│ PK: id (always 1)   │
└─────────────────────┘
```

---

## 3. Table Specifications

### 3.1 applications

**Purpose:** Main entity tracking job applications

```sql
CREATE TABLE applications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Core fields
    company_name VARCHAR(255) NOT NULL,
    job_title VARCHAR(255) NOT NULL,
    job_posting_url TEXT,
    application_date DATE NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'applied',
    
    -- Source tracking
    source VARCHAR(50) NOT NULL DEFAULT 'manual',
    job_board_source VARCHAR(100),
    
    -- Metadata
    notes TEXT,
    needs_review BOOLEAN NOT NULL DEFAULT false,
    analysis_completed BOOLEAN NOT NULL DEFAULT false,
    
    -- Relations
    posting_id UUID REFERENCES job_postings(id) ON DELETE SET NULL,
    analysis_id UUID REFERENCES analysis_results(id) ON DELETE SET NULL,
    
    -- Soft delete
    is_deleted BOOLEAN NOT NULL DEFAULT false,
    deleted_at TIMESTAMP WITH TIME ZONE,
    
    -- Audit
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
```

**Fields:**
- `id`: UUID primary key
- `company_name`: Required, max 255 chars
- `job_title`: Required, max 255 chars
- `job_posting_url`: Optional, full URL
- `application_date`: Required, date only (no time)
- `status`: Enum: applied, screening, interview, offer, rejected, withdrawn
- `source`: Enum: browser, email, manual
- `job_board_source`: Optional, e.g., "LinkedIn", "Indeed"
- `notes`: Optional, markdown-supported, max 10K chars
- `needs_review`: Flag for incomplete/uncertain data
- `analysis_completed`: Flag for analysis completion
- `posting_id`: FK to job_postings (nullable, SET NULL on delete)
- `analysis_id`: FK to analysis_results (nullable, SET NULL on delete)
- `is_deleted`: Soft delete flag
- `deleted_at`: Timestamp when soft deleted

**Constraints:**
- `status` CHECK constraint (valid enum values)
- `source` CHECK constraint (valid enum values)
- `notes` CHECK length <= 10000

---

### 3.2 job_postings

**Purpose:** Structured job posting data extracted from HTML

```sql
CREATE TABLE job_postings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Core fields
    job_title VARCHAR(255) NOT NULL,
    company_name VARCHAR(255) NOT NULL,
    description TEXT,
    requirements TEXT,
    salary_range VARCHAR(100),
    location VARCHAR(255),
    employment_type VARCHAR(50),
    
    -- Metadata
    extraction_complete BOOLEAN NOT NULL DEFAULT false,
    
    -- Audit
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
```

**Fields:**
- `description`: Full job description text
- `requirements`: Qualifications/requirements
- `salary_range`: E.g., "$80K-$120K"
- `location`: E.g., "San Francisco, CA"
- `employment_type`: E.g., "Full-time", "Contract"
- `extraction_complete`: true if extraction succeeded

---

### 3.3 scraped_postings

**Purpose:** Raw HTML storage from web scraping

```sql
CREATE TABLE scraped_postings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Core fields
    url TEXT NOT NULL,
    html_content TEXT NOT NULL,
    http_status_code INTEGER NOT NULL,
    
    -- Relations
    job_posting_id UUID REFERENCES job_postings(id) ON DELETE CASCADE,
    
    -- Audit
    scraped_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
```

**Fields:**
- `url`: Original URL scraped
- `html_content`: Full HTML response (can be large)
- `http_status_code`: E.g., 200, 301
- `job_posting_id`: FK to job_postings (CASCADE delete)
- `scraped_at`: Timestamp when scraped

**Notes:**
- Stores raw HTML for re-parsing if needed
- Large table (HTML can be 100KB-1MB per row)

---

### 3.4 resumes

**Purpose:** Resume file metadata

```sql
CREATE TABLE resumes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Core fields
    filename VARCHAR(255) NOT NULL,
    file_path TEXT NOT NULL,
    file_size_bytes INTEGER NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    
    -- Status
    status VARCHAR(50) NOT NULL DEFAULT 'uploaded',
    is_active BOOLEAN NOT NULL DEFAULT false,
    error_message TEXT,
    
    -- Audit
    uploaded_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
```

**Fields:**
- `filename`: Original filename (e.g., "resume.pdf")
- `file_path`: Absolute path on disk
- `file_size_bytes`: File size in bytes
- `mime_type`: E.g., "application/pdf"
- `status`: Enum: uploaded, processing, parsed, failed
- `is_active`: Only one resume can be active
- `error_message`: Populated on parsing failure

**Constraints:**
- Partial unique index: `UNIQUE (is_active) WHERE is_active = true`
- `status` CHECK constraint

---

### 3.5 resume_data

**Purpose:** Structured data extracted from resume

```sql
CREATE TABLE resume_data (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Relations
    resume_id UUID NOT NULL REFERENCES resumes(id) ON DELETE CASCADE,
    
    -- Contact info
    email VARCHAR(255),
    phone VARCHAR(50),
    linkedin_url TEXT,
    
    -- Structured data (JSONB)
    skills JSONB NOT NULL DEFAULT '[]',
    experience JSONB NOT NULL DEFAULT '[]',
    education JSONB NOT NULL DEFAULT '[]',
    certifications JSONB NOT NULL DEFAULT '[]',
    
    -- Text sections
    summary TEXT,
    raw_text_other TEXT,
    
    -- Metadata
    extraction_complete BOOLEAN NOT NULL DEFAULT false,
    
    -- Audit
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    UNIQUE(resume_id)
);
```

**JSONB Schemas:**

**skills:** Array of strings
```json
["Python", "FastAPI", "PostgreSQL"]
```

**experience:** Array of objects
```json
[
  {
    "title": "Software Engineer",
    "company": "Tech Corp",
    "start_date": "2020-01",
    "end_date": "2023-05",
    "description": "Built APIs..."
  }
]
```

**education:** Array of objects
```json
[
  {
    "degree": "BS Computer Science",
    "institution": "State University",
    "graduation_date": "2019-05"
  }
]
```

**certifications:** Array of objects
```json
[
  {
    "name": "AWS Solutions Architect",
    "issuer": "Amazon",
    "date": "2022-03"
  }
]
```

---

### 3.6 analysis_results

**Purpose:** AI-generated resume-job match analysis

```sql
CREATE TABLE analysis_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Relations
    application_id UUID NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    resume_id UUID NOT NULL REFERENCES resumes(id) ON DELETE CASCADE,
    job_posting_id UUID NOT NULL REFERENCES job_postings(id) ON DELETE CASCADE,
    
    -- Analysis data
    match_score INTEGER NOT NULL,
    qualifications_met JSONB NOT NULL DEFAULT '[]',
    qualifications_missing JSONB NOT NULL DEFAULT '[]',
    suggestions JSONB NOT NULL DEFAULT '[]',
    
    -- Metadata
    llm_provider VARCHAR(50) NOT NULL,
    llm_model VARCHAR(100) NOT NULL,
    analysis_metadata JSONB,
    
    -- Audit
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
```

**Fields:**
- `match_score`: Integer 0-100 (percentage)
- `qualifications_met`: Array of strings
- `qualifications_missing`: Array of strings
- `suggestions`: Array of strings
- `llm_provider`: E.g., "openai", "anthropic"
- `llm_model`: E.g., "gpt-4", "claude-3-opus"
- `analysis_metadata`: Additional context (prompt version, tokens used)

**Constraints:**
- `match_score` CHECK (match_score >= 0 AND match_score <= 100)

---

### 3.7 timeline_events

**Purpose:** Audit trail of application lifecycle events

```sql
CREATE TABLE timeline_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Relations
    application_id UUID NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    
    -- Event data
    event_type VARCHAR(100) NOT NULL,
    event_data JSONB NOT NULL DEFAULT '{}',
    occurred_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    -- Audit
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
```

**event_type Values:**
- `application_submitted`
- `status_changed`
- `note_updated`
- `job_scraped`
- `job_scraped_failed`
- `analysis_completed`
- `analysis_failed`
- `email_received`
- `manual_*` (user-created events)

**event_data Schemas by Type:**

**application_submitted:**
```json
{
  "source": "browser",
  "job_board_source": "LinkedIn"
}
```

**status_changed:**
```json
{
  "old_status": "applied",
  "new_status": "interview"
}
```

**job_scraped:**
```json
{
  "scrape_duration_seconds": 2.5,
  "extraction_complete": true
}
```

**analysis_completed:**
```json
{
  "match_score": 85,
  "llm_provider": "openai"
}
```

---

### 3.8 scraper_queue

**Purpose:** Job queue for web scraping tasks

```sql
CREATE TABLE scraper_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Relations
    application_id UUID NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    
    -- Job data
    url TEXT NOT NULL,
    priority INTEGER NOT NULL DEFAULT 0,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    
    -- Retry tracking
    attempts INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 3,
    retry_after TIMESTAMP WITH TIME ZONE,
    
    -- Result tracking
    error_message TEXT,
    processing_metadata JSONB,
    
    -- Audit
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE
);
```

**Fields:**
- `priority`: Higher = sooner (manual=100, browser=50, email=25, auto=0)
- `status`: Enum: pending, processing, complete, failed
- `attempts`: Current attempt count (0-indexed)
- `max_attempts`: Maximum retries allowed
- `retry_after`: Timestamp when next retry allowed
- `error_message`: Last error message
- `processing_metadata`: Worker info, backoff delays

**Constraints:**
- `status` CHECK constraint
- `attempts` CHECK (attempts >= 0)

---

### 3.9 parser_queue

**Purpose:** Job queue for resume parsing tasks

```sql
CREATE TABLE parser_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Relations
    resume_id UUID NOT NULL REFERENCES resumes(id) ON DELETE CASCADE,
    
    -- Job data
    file_path TEXT NOT NULL,
    priority INTEGER NOT NULL DEFAULT 0,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    
    -- Retry tracking (no retry for parser)
    attempts INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 1,
    
    -- Result tracking
    error_message TEXT,
    processing_metadata JSONB,
    
    -- Audit
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE
);
```

**Notes:**
- Similar to scraper_queue
- `max_attempts = 1` (no retry for parsing failures)

---

### 3.10 analysis_queue

**Purpose:** Job queue for AI analysis tasks

```sql
CREATE TABLE analysis_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Relations
    application_id UUID NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    
    -- Job data
    priority INTEGER NOT NULL DEFAULT 0,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    
    -- Retry tracking
    attempts INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 3,
    retry_after TIMESTAMP WITH TIME ZONE,
    
    -- Result tracking
    error_message TEXT,
    processing_metadata JSONB,
    
    -- Audit
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE
);
```

**Notes:**
- Similar to scraper_queue
- Triggers after scraping completes (if auto_analyze=true)
- Manual triggers have priority=100

---

### 3.11 processed_email_uids

**Purpose:** Track processed email UIDs for idempotency

```sql
CREATE TABLE processed_email_uids (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Core fields
    email_uid VARCHAR(255) NOT NULL UNIQUE,
    email_account VARCHAR(255) NOT NULL,
    
    -- Relations
    application_id UUID REFERENCES applications(id) ON DELETE SET NULL,
    
    -- Audit
    processed_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
```

**Fields:**
- `email_uid`: IMAP message UID (unique per account)
- `email_account`: Email address being monitored
- `application_id`: Link to created application (nullable)
- `processed_at`: When email was processed

**Constraints:**
- `UNIQUE (email_uid)` - prevents duplicate processing

---

### 3.12 settings

**Purpose:** Singleton table for application settings

```sql
CREATE TABLE settings (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    
    -- Email configuration
    email_config JSONB NOT NULL DEFAULT '{}',
    
    -- LLM configuration
    llm_config JSONB NOT NULL DEFAULT '{}',
    
    -- Feature flags
    auto_analyze BOOLEAN NOT NULL DEFAULT false,
    
    -- Audit
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
```

**email_config Schema:**
```json
{
  "enabled": true,
  "imap_server": "imap.gmail.com",
  "imap_port": 993,
  "username": "user@gmail.com",
  "folder": "INBOX",
  "polling_interval_seconds": 300
}
```

**llm_config Schema:**
```json
{
  "provider": "openai",
  "model": "gpt-4",
  "temperature": 0.7,
  "max_tokens": 2000
}
```

**Constraints:**
- `CHECK (id = 1)` - enforces singleton
- Default row inserted in migration

---

## 4. Indexes

### 4.1 Primary Key Indexes
All tables have UUID primary keys with automatic indexes.

### 4.2 Foreign Key Indexes
```sql
-- applications
CREATE INDEX idx_applications_posting_id ON applications(posting_id);
CREATE INDEX idx_applications_analysis_id ON applications(analysis_id);

-- scraped_postings
CREATE INDEX idx_scraped_postings_job_posting_id ON scraped_postings(job_posting_id);

-- resume_data
CREATE INDEX idx_resume_data_resume_id ON resume_data(resume_id);

-- analysis_results
CREATE INDEX idx_analysis_results_application_id ON analysis_results(application_id);
CREATE INDEX idx_analysis_results_resume_id ON analysis_results(resume_id);
CREATE INDEX idx_analysis_results_job_posting_id ON analysis_results(job_posting_id);

-- timeline_events
CREATE INDEX idx_timeline_events_application_id ON timeline_events(application_id);

-- Queue tables
CREATE INDEX idx_scraper_queue_application_id ON scraper_queue(application_id);
CREATE INDEX idx_parser_queue_resume_id ON parser_queue(resume_id);
CREATE INDEX idx_analysis_queue_application_id ON analysis_queue(application_id);

-- processed_email_uids
CREATE INDEX idx_processed_email_uids_application_id ON processed_email_uids(application_id);
```

### 4.3 Query Optimization Indexes

**applications - listing queries:**
```sql
CREATE INDEX idx_applications_status ON applications(status) WHERE is_deleted = false;
CREATE INDEX idx_applications_created_at ON applications(created_at DESC) WHERE is_deleted = false;
CREATE INDEX idx_applications_company_name ON applications(company_name) WHERE is_deleted = false;
CREATE INDEX idx_applications_needs_review ON applications(needs_review) WHERE needs_review = true AND is_deleted = false;
```

**applications - full-text search:**
```sql
CREATE INDEX idx_applications_search_gin ON applications 
USING gin(to_tsvector('english', company_name || ' ' || job_title || ' ' || COALESCE(notes, '')));
```

**timeline_events - queries:**
```sql
CREATE INDEX idx_timeline_events_occurred_at ON timeline_events(occurred_at DESC);
CREATE INDEX idx_timeline_events_type ON timeline_events(event_type);
```

**Queue tables - worker polling:**
```sql
CREATE INDEX idx_scraper_queue_pending ON scraper_queue(priority DESC, created_at) 
WHERE status = 'pending';

CREATE INDEX idx_parser_queue_pending ON parser_queue(created_at) 
WHERE status = 'pending';

CREATE INDEX idx_analysis_queue_pending ON analysis_queue(priority DESC, created_at) 
WHERE status = 'pending';

CREATE INDEX idx_scraper_queue_stuck ON scraper_queue(started_at) 
WHERE status = 'processing';

CREATE INDEX idx_parser_queue_stuck ON parser_queue(started_at) 
WHERE status = 'processing';

CREATE INDEX idx_analysis_queue_stuck ON analysis_queue(started_at) 
WHERE status = 'processing';
```

**resumes - active resume:**
```sql
CREATE UNIQUE INDEX idx_resumes_active ON resumes(is_active) WHERE is_active = true;
```

**processed_email_uids - cleanup:**
```sql
CREATE INDEX idx_processed_email_uids_processed_at ON processed_email_uids(processed_at);
```

### 4.4 JSONB Indexes

```sql
-- resume_data skills search
CREATE INDEX idx_resume_data_skills ON resume_data USING gin(skills);

-- analysis_results qualifications
CREATE INDEX idx_analysis_results_qualifications ON analysis_results 
USING gin(qualifications_met, qualifications_missing);
```

---

## 5. Constraints

### 5.1 Check Constraints

```sql
-- applications
ALTER TABLE applications ADD CONSTRAINT chk_status 
CHECK (status IN ('applied', 'screening', 'interview', 'offer', 'rejected', 'withdrawn'));

ALTER TABLE applications ADD CONSTRAINT chk_source 
CHECK (source IN ('browser', 'email', 'manual'));

ALTER TABLE applications ADD CONSTRAINT chk_notes_length 
CHECK (length(notes) <= 10000);

-- resumes
ALTER TABLE resumes ADD CONSTRAINT chk_resume_status 
CHECK (status IN ('uploaded', 'processing', 'parsed', 'failed'));

-- Queue tables
ALTER TABLE scraper_queue ADD CONSTRAINT chk_scraper_status 
CHECK (status IN ('pending', 'processing', 'complete', 'failed'));

ALTER TABLE parser_queue ADD CONSTRAINT chk_parser_status 
CHECK (status IN ('pending', 'processing', 'complete', 'failed'));

ALTER TABLE analysis_queue ADD CONSTRAINT chk_analysis_status 
CHECK (status IN ('pending', 'processing', 'complete', 'failed'));

-- analysis_results
ALTER TABLE analysis_results ADD CONSTRAINT chk_match_score 
CHECK (match_score >= 0 AND match_score <= 100);
```

### 5.2 Unique Constraints

```sql
-- Singleton settings
ALTER TABLE settings ADD CONSTRAINT chk_singleton CHECK (id = 1);

-- Active resume (partial unique)
CREATE UNIQUE INDEX idx_resumes_active ON resumes(is_active) WHERE is_active = true;

-- Email UID (prevents duplicates)
ALTER TABLE processed_email_uids ADD CONSTRAINT uq_email_uid UNIQUE (email_uid);

-- Resume data (1:1)
ALTER TABLE resume_data ADD CONSTRAINT uq_resume_id UNIQUE (resume_id);
```

### 5.3 Foreign Key Constraints

All foreign keys use appropriate ON DELETE actions:
- **CASCADE:** Delete related records (timeline_events, queue jobs, resume_data)
- **SET NULL:** Preserve parent, nullify reference (applications.posting_id)
- **RESTRICT:** Prevent deletion if referenced (default, rare)

---

## 6. Migrations

### 6.1 Initial Migration

```python
"""Initial schema

Revision ID: 001_initial
"""

def upgrade():
    # Create ENUM types
    op.execute("CREATE TYPE application_status AS ENUM ('applied', 'screening', 'interview', 'offer', 'rejected', 'withdrawn')")
    op.execute("CREATE TYPE application_source AS ENUM ('browser', 'email', 'manual')")
    op.execute("CREATE TYPE resume_status AS ENUM ('uploaded', 'processing', 'parsed', 'failed')")
    op.execute("CREATE TYPE queue_status AS ENUM ('pending', 'processing', 'complete', 'failed')")
    
    # Create tables (applications, job_postings, etc.)
    # ... (full SQL from above)
    
    # Create indexes
    # ... (all indexes from above)
    
    # Insert default settings row
    op.execute("""
        INSERT INTO settings (id, email_config, llm_config, auto_analyze)
        VALUES (1, '{}', '{}', false)
    """)

def downgrade():
    # Drop tables in reverse order
    # Drop ENUM types
    pass
```

### 6.2 Migration Best Practices

1. **Always include down migration**
2. **Test forward and backward**
3. **Use transactions**
4. **Create indexes concurrently in production:**
   ```sql
   CREATE INDEX CONCURRENTLY idx_name ON table(column);
   ```
5. **Add columns with defaults carefully:**
   ```sql
   ALTER TABLE table ADD COLUMN col TYPE DEFAULT value;
   -- In separate migration:
   ALTER TABLE table ALTER COLUMN col DROP DEFAULT;
   ```

---

**End of Database Schema Specification**
