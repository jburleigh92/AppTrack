# Job Application Tracker - Backend API

**Complete Implementation**  
**Version:** 1.0.0  
**Date:** December 11, 2025

A comprehensive backend API for tracking job applications with AI-powered analysis, email ingestion, web scraping, and export capabilities.

---

## 🚀 Quick Start

```bash
# 1. Clone and navigate
cd backend

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env with your database URL and API keys

# 4. Run migrations
alembic upgrade head

# 5. Start server
uvicorn app.main:app --reload

# 6. Access API docs
# Open http://localhost:8000/docs
```

---

## 📋 Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Milestones Completed](#milestones-completed)
- [API Endpoints](#api-endpoints)
- [Configuration](#configuration)
- [Database Schema](#database-schema)
- [Worker Processes](#worker-processes)
- [Documentation](#documentation)
- [Testing](#testing)
- [Deployment](#deployment)

---

## ✨ Features

### Core Functionality
- **Application Management**: Create, track, and manage job applications
- **Multi-Source Ingestion**: Browser captures and Gmail integration
- **Intelligent Correlation**: 5-stage fuzzy matching engine
- **Web Scraping**: ATS-aware job posting extraction (8+ platforms)
- **AI Analysis**: LLM-powered job-resume matching (OpenAI/Anthropic)
- **Timeline Tracking**: Comprehensive audit trail for all events
- **Data Export**: CSV downloads and Google Sheets sync

### Technical Highlights
- **FastAPI**: Modern async Python web framework
- **SQLAlchemy 2.x**: ORM with full type safety
- **PostgreSQL**: Robust relational database with JSONB support
- **Queue-Based Workers**: Async background job processing
- **Production-Ready**: Comprehensive error handling and logging
- **API-First Design**: OpenAPI/Swagger documentation

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        FastAPI Server                        │
│                      (app/main.py)                           │
└───────────┬─────────────────────────────────────┬───────────┘
            │                                     │
    ┌───────▼────────┐                   ┌────────▼────────┐
    │   API Routes   │                   │  Worker Processes│
    │   /api/v1/*    │                   │  - Scraper      │
    └───────┬────────┘                   │  - Analysis     │
            │                            └────────┬────────┘
    ┌───────▼────────┐                           │
    │   Services     │◄──────────────────────────┘
    │   - Application│
    │   - Correlation│
    │   - Scraping   │
    │   - Analysis   │
    │   - Export     │
    │   - Timeline   │
    └───────┬────────┘
            │
    ┌───────▼────────┐
    │   Database     │
    │   PostgreSQL   │
    │   - 12 Tables  │
    │   - 28+ Indexes│
    └────────────────┘
```

### Layers

1. **API Layer** (`app/api/`): FastAPI routes, dependencies, error handlers
2. **Service Layer** (`app/services/`): Business logic, external integrations
3. **Data Layer** (`app/db/`): SQLAlchemy models, migrations, session management
4. **Worker Layer** (`app/workers/`): Background job processors
5. **Core Layer** (`app/core/`): Configuration, logging, utilities

---

## 📁 Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI application entry point
│   │
│   ├── api/                       # API layer
│   │   ├── __init__.py
│   │   ├── dependencies/          # Dependency injection
│   │   │   ├── __init__.py
│   │   │   └── database.py        # DB session dependency
│   │   ├── error_handlers/        # Global error handling
│   │   │   ├── __init__.py
│   │   │   └── handlers.py
│   │   └── routes/                # API endpoints
│   │       ├── __init__.py
│   │       ├── health.py          # Health check endpoints
│   │       ├── capture.py         # Browser capture API
│   │       ├── email_ingest.py    # Email ingestion API
│   │       ├── scraper.py         # Scraper control API
│   │       ├── analysis.py        # AI analysis API
│   │       ├── timeline.py        # Timeline events API
│   │       ├── exports.py         # Export/sync API
│   │       └── internal.py        # Internal callbacks
│   │
│   ├── core/                      # Core configuration
│   │   ├── __init__.py
│   │   ├── config.py              # Settings management
│   │   └── logging.py             # Logging configuration
│   │
│   ├── db/                        # Database layer
│   │   ├── __init__.py
│   │   ├── base.py                # SQLAlchemy base
│   │   ├── session.py             # Session factory
│   │   ├── models/                # SQLAlchemy models
│   │   │   ├── __init__.py
│   │   │   ├── application.py
│   │   │   ├── job_posting.py
│   │   │   ├── resume.py
│   │   │   ├── analysis.py
│   │   │   ├── timeline.py
│   │   │   ├── email.py
│   │   │   ├── queue.py
│   │   │   └── settings.py
│   │   └── migrations/            # Alembic migrations
│   │       ├── env.py
│   │       └── versions/
│   │           └── 0001_initial_schema.py
│   │
│   ├── schemas/                   # Pydantic schemas
│   │   ├── __init__.py
│   │   ├── application.py
│   │   ├── job_posting.py
│   │   ├── analysis.py
│   │   ├── timeline.py
│   │   ├── email.py
│   │   └── export.py
│   │
│   ├── services/                  # Business logic
│   │   ├── __init__.py
│   │   ├── application_service.py # Application CRUD
│   │   ├── email_service.py       # Email handling
│   │   ├── timeline_service.py    # Timeline logging
│   │   ├── export_service.py      # CSV/Sheets export
│   │   ├── correlation/           # Email correlation
│   │   │   ├── __init__.py
│   │   │   └── correlator.py
│   │   ├── scraping/              # Web scraping
│   │   │   ├── __init__.py
│   │   │   ├── scraper.py         # HTML fetching
│   │   │   ├── extractor.py       # ATS detection
│   │   │   └── enrichment.py      # Data parsing
│   │   └── analysis/              # AI analysis
│   │       ├── __init__.py
│   │       ├── llm_client.py      # LLM integration
│   │       └── analyzer.py        # Analysis orchestration
│   │
│   └── workers/                   # Background workers
│       ├── __init__.py
│       ├── scraper_worker.py      # Scraping queue processor
│       └── analysis_worker.py     # Analysis queue processor
│
├── alembic.ini                    # Alembic configuration
├── requirements.txt               # Python dependencies
├── .env.example                   # Environment template
│
└── README*.md                     # Documentation
    ├── README.md                  # This file
    ├── README-DATABASE.md
    ├── README-BACKEND-SCAFFOLDING.md
    ├── README-INGESTION-PIPELINES.md
    ├── README-CORRELATION-ENGINE.md
    ├── README-SCRAPER-SERVICE.md
    ├── README-AI-ANALYSIS-ENGINE.md
    ├── README-TIMELINE-EVENTS.md
    └── README-EXPORT-LAYER.md
```

---

## 🎯 Milestones Completed

### ✅ M1: Database Schema & Migrations
- 12 tables with proper relationships
- 28+ indexes for optimal performance
- Full Alembic migration system
- JSONB support for flexible data

### ✅ M2: Core Backend Scaffolding
- FastAPI application setup
- Settings management with Pydantic
- Structured logging
- Health check endpoints
- Global error handling

### ✅ M3: Ingestion Pipelines
- Browser capture API
- Gmail integration with IMAP
- Application creation from captures
- Email UID tracking

### ✅ M4: Correlation Engine
- 5-stage fuzzy matching
- Email-to-application linking
- Company name normalization
- Job title similarity scoring

### ✅ M5: Scraper Service
- HTML fetching with retry logic
- 8+ ATS platform detection
- Job posting extraction
- Queue-based processing
- Scraper worker daemon

### ✅ M6: AI Analysis Engine
- OpenAI & Anthropic integration
- Job-resume matching
- Structured analysis output
- Analysis queue processing
- Analysis worker daemon

### ✅ M7: Timeline Events System
- Universal event logging
- Never-crash error handling
- 17 event types
- Query API for event history

### ✅ M8: Export Layer
- CSV export with streaming
- Google Sheets sync
- Flexible filtering
- Service account authentication

---

## 🔌 API Endpoints

### Health & Status
```
GET  /api/v1/health/live       # Liveness probe
GET  /api/v1/health/ready      # Readiness probe (DB check)
```

### Application Capture
```
POST /api/v1/applications/capture    # Create from browser extension
```

### Email Ingestion
```
POST /api/v1/emails/ingest           # Process Gmail messages
```

### Scraping
```
POST /api/v1/scraper/scrape          # Enqueue scraping job
POST /api/v1/internal/scrape-complete # Worker callback (internal)
```

### AI Analysis
```
POST /api/v1/applications/{id}/analysis/run  # Enqueue analysis
GET  /api/v1/applications/{id}/analysis      # Get analysis results
```

### Timeline
```
GET  /api/v1/applications/{id}/timeline      # Get event history
POST /api/v1/applications/{id}/timeline      # Create manual event
```

### Export
```
POST /api/v1/exports/csv                     # Download CSV
POST /api/v1/exports/sheets                  # Sync to Google Sheets
```

**Interactive API Docs:** `http://localhost:8000/docs`

---

## ⚙️ Configuration

### Environment Variables

```bash
# Application
ENV=local                        # local | staging | production
DEBUG=true
APP_NAME=Job Application Tracker

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/jobtracker

# LLM Providers (at least one required for AI analysis)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Google Sheets (optional, for export)
GOOGLE_SERVICE_ACCOUNT_JSON=/path/to/service-account.json

# Logging
LOG_LEVEL=INFO                   # DEBUG | INFO | WARNING | ERROR
```

### LLM Configuration

Configure in `core/config.py` or via environment:

```python
llm_config = {
    "provider": "openai",        # openai | anthropic
    "model": "gpt-4",            # gpt-4 | claude-3-opus | etc
    "temperature": 0.2,
    "max_tokens": 1500
}
```

---

## 🗄️ Database Schema

### Core Tables

**applications** - Job application records
- Primary tracking entity
- Links to job_postings, resumes, analysis_results
- Status workflow tracking

**job_postings** - Scraped job details
- Company, title, description, requirements
- Location, salary, employment type
- ATS platform detection

**resumes** - User resumes
- Parsed content (skills, experience, education)
- Active/inactive status
- Used for AI analysis

**analysis_results** - AI analysis output
- Match score (0-100)
- Qualifications met/missing
- Skill suggestions
- LLM provider/model metadata

**timeline_events** - Audit trail
- Every significant action logged
- 17 event types
- JSONB event data

### Queue Tables

**scraper_queue** - Scraping jobs
**analysis_queue** - Analysis jobs

### Supporting Tables

**email_uids** - Gmail message tracking
**settings** - User configuration

**See:** `README-DATABASE.md` for full schema details

---

## 🔄 Worker Processes

### Scraper Worker

```bash
python -m app.workers.scraper_worker
```

**Responsibilities:**
- Poll `scraper_queue` for pending jobs
- Fetch job posting HTML
- Detect ATS platform
- Extract structured data
- Link to applications
- Log timeline events

**Retry Logic:** 1min, 5min, 15min exponential backoff

### Analysis Worker

```bash
python -m app.workers.analysis_worker
```

**Responsibilities:**
- Poll `analysis_queue` for pending jobs
- Load application, job posting, resume
- Call LLM API for analysis
- Parse structured response
- Persist results
- Update application
- Log timeline events

**Retry Logic:** 1min, 5min, 15min exponential backoff

---

## 📚 Documentation

Comprehensive documentation in dedicated README files:

- **`README-DATABASE.md`** - Database schema, migrations, models
- **`README-BACKEND-SCAFFOLDING.md`** - FastAPI setup, config, logging
- **`README-INGESTION-PIPELINES.md`** - Browser/email capture
- **`README-CORRELATION-ENGINE.md`** - Email matching algorithms
- **`README-SCRAPER-SERVICE.md`** - Web scraping system
- **`README-AI-ANALYSIS-ENGINE.md`** - LLM integration
- **`README-TIMELINE-EVENTS.md`** - Event logging system
- **`README-EXPORT-LAYER.md`** - CSV/Sheets export

Each README includes:
- Architecture overview
- API reference
- Usage examples
- Error handling
- Testing strategies
- Troubleshooting guides

---

## 🧪 Testing

### Unit Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_correlation.py
```

### Manual Testing

```bash
# Test health check
curl http://localhost:8000/api/v1/health/live

# Test browser capture
curl -X POST http://localhost:8000/api/v1/applications/capture \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://jobs.example.com/123",
    "company_name": "Acme Corp",
    "job_title": "Software Engineer"
  }'

# Test CSV export
curl -X POST http://localhost:8000/api/v1/exports/csv \
  -H "Content-Type: application/json" \
  -d '{}' \
  --output export.csv
```

### API Documentation

Interactive testing via Swagger UI:
```
http://localhost:8000/docs
```

---

## 🚢 Deployment

### Docker (Recommended)

```dockerfile
# Dockerfile example
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY alembic.ini .

# Run migrations
RUN alembic upgrade head

# Start server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker Compose

```yaml
version: '3.8'

services:
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: jobtracker
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data

  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://user:password@db:5432/jobtracker
      OPENAI_API_KEY: ${OPENAI_API_KEY}
    depends_on:
      - db

  scraper_worker:
    build: .
    command: python -m app.workers.scraper_worker
    environment:
      DATABASE_URL: postgresql://user:password@db:5432/jobtracker
    depends_on:
      - db

  analysis_worker:
    build: .
    command: python -m app.workers.analysis_worker
    environment:
      DATABASE_URL: postgresql://user:password@db:5432/jobtracker
      OPENAI_API_KEY: ${OPENAI_API_KEY}
    depends_on:
      - db

volumes:
  postgres_data:
```

### Production Checklist

- [ ] Set `ENV=production` and `DEBUG=false`
- [ ] Use strong database password
- [ ] Configure SSL/TLS for database connections
- [ ] Set up proper logging aggregation
- [ ] Configure rate limiting
- [ ] Set up monitoring (Prometheus/Grafana)
- [ ] Enable CORS appropriately
- [ ] Secure API keys in secrets manager
- [ ] Set up automated backups
- [ ] Configure horizontal scaling for workers

---

## 🔒 Security

### API Keys
- Store in environment variables
- Use secrets manager in production
- Never commit to version control

### Database
- Use connection pooling
- Enable SSL for connections
- Regular security updates

### Google Service Account
- Restrict to Sheets API only
- Store JSON outside repository
- Rotate keys periodically

---

## 🐛 Troubleshooting

### Database Connection Issues

```bash
# Test connection
psql $DATABASE_URL

# Check migrations
alembic current
alembic history
```

### Worker Not Processing Jobs

```bash
# Check queue tables
psql $DATABASE_URL -c "SELECT * FROM scraper_queue WHERE status = 'pending';"
psql $DATABASE_URL -c "SELECT * FROM analysis_queue WHERE status = 'pending';"

# Check worker logs
python -m app.workers.scraper_worker  # Should show polling messages
```

### Google Sheets Sync Fails

```bash
# Verify credentials
echo $GOOGLE_SERVICE_ACCOUNT_JSON
cat $GOOGLE_SERVICE_ACCOUNT_JSON | jq .client_email

# Check API enabled
# Go to https://console.cloud.google.com
# Enable Google Sheets API

# Verify sheet permissions
# Share spreadsheet with service account email
```

---

## 📝 License

[Your License Here]

---

## 👥 Contributors

[Your Name/Team]

---

## 📞 Support

For issues and questions:
- GitHub Issues: [Your Repo]
- Email: [Your Email]
- Documentation: See README-*.md files

---

**Last Updated:** December 11, 2025  
**Status:** ✅ Production Ready
