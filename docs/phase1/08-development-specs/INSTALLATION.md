# Job Application Tracker - Installation Guide

**Quick Start Guide for Backend API**

---

## Prerequisites

- Python 3.11+
- PostgreSQL 15+
- pip (Python package manager)
- Git (optional)

---

## Installation Steps

### 1. Extract the Archive

```bash
unzip job-tracker-backend-complete.zip
cd backend_complete
```

### 2. Create Python Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate it
# On macOS/Linux:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Set Up PostgreSQL Database

```bash
# Create database (using psql)
psql -U postgres -c "CREATE DATABASE jobtracker;"

# Or using createdb
createdb jobtracker
```

### 5. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your settings
nano .env  # or use your preferred editor
```

**Required Settings:**
```bash
DATABASE_URL=postgresql://user:password@localhost:5432/jobtracker
```

**Optional Settings (for full functionality):**
```bash
# For AI Analysis (M6)
OPENAI_API_KEY=sk-...
# OR
ANTHROPIC_API_KEY=sk-ant-...

# For Google Sheets Export (M8)
GOOGLE_SERVICE_ACCOUNT_JSON=/path/to/service-account.json
```

### 6. Run Database Migrations

```bash
# Check current migration status
alembic current

# Run all migrations
alembic upgrade head

# Verify migrations applied
alembic current
```

### 7. Start the API Server

```bash
# Development mode (with auto-reload)
uvicorn app.main:app --reload

# Production mode
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 8. Verify Installation

Open your browser and go to:
```
http://localhost:8000/docs
```

You should see the interactive API documentation (Swagger UI).

**Test the health endpoint:**
```bash
curl http://localhost:8000/api/v1/health/live
# Should return: {"status": "ok"}

curl http://localhost:8000/api/v1/health/ready
# Should return: {"status": "ok", "database": "connected"}
```

---

## Optional: Start Background Workers

For full functionality, start the worker processes:

### Scraper Worker (M5)

```bash
# In a new terminal (with venv activated)
python -m app.workers.scraper_worker
```

### Analysis Worker (M6)

```bash
# In another new terminal (with venv activated)
python -m app.workers.analysis_worker
```

**Note:** Workers require their respective configurations:
- Scraper Worker: Just needs DATABASE_URL
- Analysis Worker: Needs DATABASE_URL + LLM API key (OPENAI_API_KEY or ANTHROPIC_API_KEY)

---

## Configuration Details

### Database URL Format

```
postgresql://[user]:[password]@[host]:[port]/[database]
```

**Examples:**
```bash
# Local PostgreSQL
DATABASE_URL=postgresql://postgres:mypassword@localhost:5432/jobtracker

# Docker PostgreSQL
DATABASE_URL=postgresql://postgres:postgres@db:5432/jobtracker

# Cloud PostgreSQL (with SSL)
DATABASE_URL=postgresql://user:pass@host.amazonaws.com:5432/jobtracker?sslmode=require
```

### LLM Configuration

Choose one LLM provider:

**OpenAI (recommended for GPT-4):**
```bash
OPENAI_API_KEY=sk-proj-...
```

**Anthropic (for Claude):**
```bash
ANTHROPIC_API_KEY=sk-ant-...
```

Configure model in `app/core/config.py`:
```python
llm_config = {
    "provider": "openai",     # or "anthropic"
    "model": "gpt-4",         # or "claude-3-opus-20240229"
    "temperature": 0.2,
    "max_tokens": 1500
}
```

### Google Sheets Configuration

1. **Create Google Cloud Project**
   - Go to https://console.cloud.google.com
   - Create new project
   - Enable Google Sheets API

2. **Create Service Account**
   - IAM & Admin → Service Accounts
   - Create service account
   - Download JSON key file

3. **Configure Application**
   ```bash
   GOOGLE_SERVICE_ACCOUNT_JSON=/path/to/service-account.json
   ```

4. **Share Spreadsheet**
   - Open your Google Sheet
   - Share with service account email (from JSON file)
   - Give "Editor" permission

**See:** `README-EXPORT-LAYER.md` for detailed setup instructions

---

## Troubleshooting

### Database Connection Failed

**Problem:** `sqlalchemy.exc.OperationalError: could not connect to server`

**Solutions:**
1. Verify PostgreSQL is running: `pg_isready`
2. Check DATABASE_URL is correct
3. Verify database exists: `psql -l | grep jobtracker`
4. Check PostgreSQL logs: `tail -f /var/log/postgresql/postgresql-15-main.log`

### Migration Failed

**Problem:** `alembic.util.exc.CommandError`

**Solutions:**
1. Check database connection: `psql $DATABASE_URL`
2. Reset to initial state: `alembic downgrade base && alembic upgrade head`
3. Check for conflicting migrations: `alembic history`

### Import Errors

**Problem:** `ModuleNotFoundError: No module named 'app'`

**Solutions:**
1. Verify you're in the `backend_complete` directory
2. Activate virtual environment: `source venv/bin/activate`
3. Install dependencies: `pip install -r requirements.txt`
4. Set PYTHONPATH: `export PYTHONPATH=$PYTHONPATH:$(pwd)`

### Worker Not Processing

**Problem:** Jobs stuck in queue

**Solutions:**
1. Check worker is running: `ps aux | grep worker`
2. Check worker logs for errors
3. Verify queue table has pending jobs:
   ```sql
   SELECT * FROM scraper_queue WHERE status = 'pending';
   SELECT * FROM analysis_queue WHERE status = 'pending';
   ```
4. Restart worker: `python -m app.workers.scraper_worker`

### API Key Errors

**Problem:** `401 Unauthorized` from LLM providers

**Solutions:**
1. Verify API key is set: `echo $OPENAI_API_KEY`
2. Check key format (should start with `sk-`)
3. Test key with curl:
   ```bash
   curl https://api.openai.com/v1/models \
     -H "Authorization: Bearer $OPENAI_API_KEY"
   ```
4. Restart server after setting new key

---

## Development Setup

For active development:

### 1. Install Development Dependencies

```bash
pip install -r requirements.txt
pip install pytest pytest-asyncio pytest-cov black isort mypy
```

### 2. Set Up Pre-commit Hooks

```bash
# Format code
black app/
isort app/

# Type checking
mypy app/

# Run tests
pytest tests/ -v
```

### 3. Database Development

```bash
# Create new migration
alembic revision -m "description"

# Edit migration file in app/db/migrations/versions/

# Apply migration
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

---

## Docker Setup (Alternative)

### Using Docker Compose

Create `docker-compose.yml`:
```yaml
version: '3.8'

services:
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: jobtracker
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://postgres:postgres@db:5432/jobtracker
      OPENAI_API_KEY: ${OPENAI_API_KEY}
    depends_on:
      - db
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000

volumes:
  postgres_data:
```

Run with:
```bash
docker-compose up -d
```

---

## Next Steps

After successful installation:

1. **Read the Documentation**
   - Start with `README.md` for overview
   - Check milestone-specific READMEs for details

2. **Test the API**
   - Use Swagger UI: http://localhost:8000/docs
   - Try creating an application via `/api/v1/applications/capture`

3. **Configure Integrations**
   - Set up Gmail integration (README-INGESTION-PIPELINES.md)
   - Configure LLM provider (README-AI-ANALYSIS-ENGINE.md)
   - Set up Google Sheets (README-EXPORT-LAYER.md)

4. **Start Workers**
   - Launch scraper worker for job posting extraction
   - Launch analysis worker for AI-powered analysis

5. **Monitor Logs**
   - Check application logs for errors
   - Monitor worker processing
   - Review timeline events

---

## Support

For issues and questions:

- **Documentation:** See `README-*.md` files
- **API Docs:** http://localhost:8000/docs
- **Logs:** Check console output or log files
- **Database:** Use psql or pgAdmin to inspect data

---

**Installation Complete!** 🎉

You now have a fully functional Job Application Tracker backend API.

**Quick Test:**
```bash
# Create an application
curl -X POST http://localhost:8000/api/v1/applications/capture \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://jobs.example.com/123",
    "company_name": "Acme Corp",
    "job_title": "Software Engineer",
    "source": "browser"
  }'

# Export to CSV
curl -X POST http://localhost:8000/api/v1/exports/csv \
  -H "Content-Type: application/json" \
  -d '{}' \
  --output applications.csv
```
