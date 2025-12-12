# Job Application Tracker - Database Layer Implementation

**Implementation Date:** December 11, 2025  
**Status:** Complete - Ready for Deployment

---

## Overview

This directory contains the complete database layer implementation for the Job Application Tracker, including SQLAlchemy ORM models, Alembic migrations, and session management.

---

## Files Included

### Core Configuration
- `base.py` - SQLAlchemy declarative base, TimestampMixin, SoftDeleteMixin
- `session.py` - Database engine, session factory, FastAPI dependency

### ORM Models (12 tables)
- `models/__init__.py` - Model exports
- `models/application.py` - Application (main entity with soft delete)
- `models/job_posting.py` - JobPosting + ScrapedPosting
- `models/resume.py` - Resume + ResumeData
- `models/analysis.py` - AnalysisResult
- `models/timeline.py` - TimelineEvent
- `models/queue.py` - ScraperQueue, ParserQueue, AnalysisQueue
- `models/email.py` - ProcessedEmailUID
- `models/settings.py` - Settings (singleton)

### Migrations
- `migrations/env.py` - Alembic configuration
- `migrations/versions/0001_initial_schema.py` - Initial database schema

---

## Setup Instructions

### 1. Install Dependencies

```bash
pip install sqlalchemy[asyncio] alembic psycopg2-binary python-dotenv
```

### 2. Configure Database

Create `.env` file:

```bash
DATABASE_URL=postgresql://user:password@localhost:5432/jobtracker
```

### 3. Initialize Database

```bash
# Create database (PostgreSQL)
createdb jobtracker

# Initialize Alembic (if not done)
alembic init migrations

# Run migrations
alembic upgrade head
```

### 4. Verify Setup

```python
from app.db.session import init_db, get_db
from app.db.models import Application

# Initialize
init_db("postgresql://user:password@localhost:5432/jobtracker")

# Test
db = next(get_db())
apps = db.query(Application).all()
print(f"Applications: {len(apps)}")
```

---

## Schema Features

### Tables (12)
- applications (main entity)
- job_postings, scraped_postings
- resumes, resume_data
- analysis_results
- timeline_events
- scraper_queue, parser_queue, analysis_queue
- processed_email_uids
- settings (singleton)

### Indexes (28+)
- Primary keys (UUID)
- Foreign keys
- Partial indexes (is_deleted = false, is_active = true, status = 'pending')
- Full-text search (GIN on applications)
- JSONB indexes (skills, qualifications)
- Composite indexes with DESC ordering

### Constraints
- CHECK constraints (status enums, score range 0-100, notes length ≤10000)
- UNIQUE constraints (email_uid, resume_id, singleton settings)
- Foreign keys with CASCADE/SET NULL
- Partial unique index (active resume)

### Special Features
- Soft delete on applications (is_deleted, deleted_at)
- Timestamp audit (created_at, updated_at with server defaults)
- Active resume enforcement (partial unique index)
- Settings singleton (CHECK id = 1)
- Queue retry tracking (attempts, max_attempts, retry_after)
- JSONB for flexible data (skills, experience, event_data, metadata)

---

## SQLAlchemy 2.x Features

This implementation uses modern SQLAlchemy 2.x patterns:

- `Mapped[Type]` type hints
- `mapped_column()` for explicit configuration
- `relationship()` with proper backrefs
- Server-side defaults using `func.now()`
- UUID primary keys with `uuid4` defaults
- Proper nullable/non-nullable typing

---

## Usage Examples

### Create Application

```python
from app.db.session import get_db
from app.db.models import Application
from datetime import date

db = next(get_db())

app = Application(
    company_name="Tech Corp",
    job_title="Software Engineer",
    application_date=date.today(),
    status="applied",
    source="browser"
)

db.add(app)
db.commit()
db.refresh(app)
```

### Query with Relationships

```python
from app.db.models import Application

# Eager load relationships
app = db.query(Application)\
    .options(
        joinedload(Application.posting),
        joinedload(Application.timeline_events)
    )\
    .filter(Application.id == app_id)\
    .first()

print(f"Company: {app.company_name}")
print(f"Job Description: {app.posting.description}")
print(f"Timeline: {len(app.timeline_events)} events")
```

### Queue Operations

```python
from app.db.models import ScraperQueue
from sqlalchemy import select

# Dequeue with row lock (prevents race conditions)
stmt = select(ScraperQueue)\
    .where(ScraperQueue.status == 'pending')\
    .order_by(ScraperQueue.priority.desc(), ScraperQueue.created_at)\
    .limit(1)\
    .with_for_update(skip_locked=True)

job = db.execute(stmt).scalar_one_or_none()

if job:
    job.status = 'processing'
    job.started_at = datetime.utcnow()
    db.commit()
```

### Active Resume Enforcement

```python
from app.db.models import Resume

# Archive old active resume
old_active = db.query(Resume)\
    .filter(Resume.is_active == True)\
    .first()

if old_active:
    old_active.is_active = False

# Activate new resume
new_resume.is_active = True
db.commit()

# Constraint ensures only one active resume
```

---

## Migration Commands

```bash
# Create new migration (autogenerate)
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Show current version
alembic current

# Show migration history
alembic history
```

---

## Testing

### Unit Tests

```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.base import Base
from app.db.models import Application

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

def test_create_application(db_session):
    app = Application(
        company_name="Test Corp",
        job_title="Test Job",
        application_date=date.today()
    )
    db_session.add(app)
    db_session.commit()
    
    assert app.id is not None
    assert app.status == "applied"
    assert app.needs_review == False
```

---

## Production Considerations

### Connection Pooling

Configured in `session.py`:
- `pool_size=10` - Normal connections
- `max_overflow=20` - Peak connections
- `pool_pre_ping=True` - Verify connections

### Index Usage

Monitor query performance:
```sql
EXPLAIN ANALYZE 
SELECT * FROM applications 
WHERE status = 'applied' AND is_deleted = false;
```

### Maintenance

Regular tasks:
```sql
-- Analyze tables for query planner
ANALYZE applications;

-- Vacuum to reclaim space
VACUUM ANALYZE applications;

-- Check index usage
SELECT schemaname, tablename, indexname, idx_scan
FROM pg_stat_user_indexes
ORDER BY idx_scan;
```

---

## Troubleshooting

### Migration Conflicts

```bash
# Reset to specific version
alembic downgrade <revision>

# Stamp without running
alembic stamp <revision>
```

### Connection Issues

```python
# Check engine status
from app.db.session import get_engine

engine = get_engine("postgresql://...")
with engine.connect() as conn:
    result = conn.execute("SELECT 1")
    print("Connected successfully")
```

### Constraint Violations

```python
from sqlalchemy.exc import IntegrityError

try:
    db.commit()
except IntegrityError as e:
    db.rollback()
    print(f"Constraint violated: {e}")
```

---

## Next Steps

1. **Implement Repositories** (M1 milestone)
   - ApplicationRepository with CRUD operations
   - QueueRepository with dequeue logic
   - ResumeRepository with active management

2. **Add Validation** (M2 milestone)
   - Pydantic schemas for API layer
   - Business rule validators

3. **Create Fixtures** (Testing)
   - Sample data generators
   - Factory functions

---

**Database Layer Status:** ✅ Complete and Production-Ready
