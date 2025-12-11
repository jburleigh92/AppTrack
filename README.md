# Job Application Tracker

A local-first, privacy-preserving automation system that captures job applications from browser activity, email confirmations, and manual entries. The system enriches postings through scraping, analyzes fit using AI, and provides a unified dashboard for managing the entire job search lifecycle.

---

## Table of Contents
- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Repository Structure](#repository-structure)
- [Setup](#setup)
- [Development](#development)
- [Documentation](#documentation)
- [Roadmap](#roadmap)
- [License](#license)

---

## Overview
The Job Application Tracker automates the ingestion, enrichment, and analysis of your job search pipeline. It consolidates applications from multiple sources and provides actionable insights with zero cloud dependency.

---

## Features
- Browser extension capture for application submissions
- Email ingestion for confirmation messages
- Job posting scraping + structured extraction
- AI-driven resume-job fit scoring
- Unified dashboard with timeline and status tracking
- Local PostgreSQL database (SQLite fallback)
- CSV export for analysis

---

## Architecture
- **Frontend:** Browser extension + local web dashboard  
- **Backend:** FastAPI service  
- **Workers:** Celery / RQ for scraping, parsing, and AI analysis  
- **Database:** PostgreSQL 14+  
- **AI:** OpenAI / Anthropic API integration  

See full architecture docs in `docs/02-architecture`.

---

## Tech Stack
| Layer | Technology |
|-------|------------|
| API Backend | FastAPI |
| Workers | Celery or RQ |
| Database | PostgreSQL |
| ORM | SQLAlchemy |
| Queue Broker | Redis |
| Frontend | Browser Extension + minimal web UI |
| AI | OpenAI / Anthropic |
| Scraping | Playwright or Requests+BS4 |

---

## Repository Structure

```
AppTrack/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── routes/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── applications.py
│   │   │   │   ├── job_postings.py
│   │   │   │   ├── resumes.py
│   │   │   │   ├── analysis.py
│   │   │   │   ├── timeline.py
│   │   │   │   ├── queue.py
│   │   │   │   ├── settings.py
│   │   │   │   ├── capture.py
│   │   │   │   └── internal.py
│   │   │   ├── dependencies/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── auth.py
│   │   │   │   └── database.py
│   │   │   └── error_handlers/
│   │   │       ├── __init__.py
│   │   │       └── handlers.py
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── config.py
│   │   │   ├── security.py
│   │   │   └── logging.py
│   │   ├── db/
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   ├── session.py
│   │   │   ├── models/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── application.py
│   │   │   │   ├── job_posting.py
│   │   │   │   ├── resume.py
│   │   │   │   ├── analysis.py
│   │   │   │   ├── timeline.py
│   │   │   │   ├── queue.py
│   │   │   │   ├── email.py
│   │   │   │   └── settings.py
│   │   │   └── migrations/
│   │   │       ├── env.py
│   │   │       └── versions/
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── application.py
│   │   │   ├── job_posting.py
│   │   │   ├── resume.py
│   │   │   ├── analysis.py
│   │   │   ├── timeline.py
│   │   │   ├── queue.py
│   │   │   ├── settings.py
│   │   │   └── common.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── application_service.py
│   │   │   ├── scraping/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── scraper.py
│   │   │   │   └── extractor.py
│   │   │   ├── parsing/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── pdf_parser.py
│   │   │   │   ├── docx_parser.py
│   │   │   │   └── text_parser.py
│   │   │   └── analysis/
│   │   │       ├── __init__.py
│   │   │       ├── llm_client.py
│   │   │       └── analyzer.py
│   │   └── workers/
│   │       ├── __init__.py
│   │       ├── scraper_worker.py
│   │       ├── parser_worker.py
│   │       └── analysis_worker.py
│   ├── alembic.ini
│   ├── pyproject.toml
│   ├── .env.example
│   └── README.md
│
├── extension/
│   └── (browser extension source)
└── docs/
    └── (documentation set: product, architecture, system design, APIs, schemas, modules, implementation plan, testing, observability, operations, prompts)


````

Full documentation is in the `/docs` directory.

---

## Setup
```bash
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git
cd YOUR_REPO
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
````

---

## Development

Run backend:

```bash
uvicorn backend.main:app --reload
```

Run workers:

```bash
celery -A backend.workers worker --loglevel=info
```

---

## Documentation

Full engineering documentation lives in:

```
docs/
  01-product/
  02-architecture/
  03-system-design/
  04-api-contracts/
  05-schemas/
  06-modules/
  07-implementation-plan/
  08-testing/
  09-observability/
  10-operations/
  11-prompts/
```

---

## Roadmap

* Dashboard UI
* AI-powered resume tailoring
* Interview prep module
* ATS integration support

---

## License

MIT License
