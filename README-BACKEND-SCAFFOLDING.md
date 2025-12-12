# Job Application Tracker - Core Backend Scaffolding

**Implementation Date:** December 11, 2025  
**Status:** Complete - Production-Ready FastAPI Application

---

## Overview

This directory contains the core backend scaffolding for the Job Application Tracker, including FastAPI application setup, configuration management, structured logging, error handling, and health check endpoints.

---

## Files Implemented

### Core Configuration
- `app/__init__.py` - Application root package
- `app/main.py` - FastAPI application entrypoint with factory pattern
- `app/core/config.py` - Pydantic settings management with environment variables
- `app/core/logging.py` - Structured logging configuration

### API Layer
- `app/api/__init__.py` - API module
- `app/api/routes/__init__.py` - API router aggregation
- `app/api/routes/health.py` - Health check endpoints (liveness/readiness)
- `app/api/dependencies/database.py` - Database session dependency
- `app/api/error_handlers/__init__.py` - Error handler registration
- `app/api/error_handlers/handlers.py` - HTTP and general exception handlers

---

## Quick Start

### 1. Install Dependencies

```bash
pip install fastapi uvicorn[standard] pydantic-settings python-dotenv
```

### 2. Create Environment File

Create `.env` in the `backend/` directory:

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/jobtracker

# Environment
ENV=local
DEBUG=true
LOG_LEVEL=INFO

# API Keys (optional for now)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

### 3. Run Database Migrations

```bash
cd backend
alembic upgrade head
```

### 4. Start the Application

```bash
cd backend
uvicorn app.main:app --reload
```

The application will start on `http://localhost:8000`

### 5. Test Health Endpoints

```bash
# Liveness check
curl http://localhost:8000/api/v1/health/live

# Readiness check (requires database)
curl http://localhost:8000/api/v1/health/ready
```

### 6. Access API Documentation

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## Architecture

### Application Factory Pattern

The application uses a factory pattern (`create_app()`) for better testability and configuration management:

```python
def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings)
    init_db(settings.DATABASE_URL)
    
    app = FastAPI(...)
    # Configure middleware, error handlers, routes
    return app

app = create_app()
```

### Configuration Management

Settings are managed using Pydantic BaseSettings with environment variable support:

```python
from app.core.config import get_settings

settings = get_settings()  # Cached singleton
print(settings.DATABASE_URL)
print(settings.DEBUG)
```

**Available Settings:**
- `ENV` - Environment (local/dev/staging/production)
- `DEBUG` - Debug mode (auto-enabled for local/dev)
- `APP_NAME` - Application name
- `API_V1_PREFIX` - API version prefix (/api/v1)
- `DATABASE_URL` - PostgreSQL connection string
- `OPENAI_API_KEY` - OpenAI API key (optional)
- `ANTHROPIC_API_KEY` - Anthropic API key (optional)
- `LOG_LEVEL` - Logging level (INFO/DEBUG/WARNING/ERROR)

### Structured Logging

Logging is configured with structured output format:

```
2025-12-11 10:30:45 | INFO     | app.main | Application started
2025-12-11 10:30:46 | ERROR    | app.api.routes.health | Database connection failed
```

Usage in code:

```python
import logging

logger = logging.getLogger(__name__)
logger.info("Processing request")
logger.error("Failed to process", exc_info=True)
```

### Database Dependency

FastAPI dependency injection for database sessions:

```python
from fastapi import Depends
from sqlalchemy.orm import Session
from app.api.dependencies.database import get_db

@router.get("/applications")
def list_applications(db: Session = Depends(get_db)):
    apps = db.query(Application).all()
    return apps
```

### Error Handling

Global error handlers provide consistent error responses:

**HTTP Exceptions:**
```json
{
  "error": {
    "code": 404,
    "message": "Resource not found"
  }
}
```

**Unexpected Exceptions:**
```json
{
  "error": {
    "code": 500,
    "message": "Internal server error"
  }
}
```

### CORS Configuration

CORS is pre-configured for local development:
- Origins: localhost:3000, localhost:8000, 127.0.0.1:3000, 127.0.0.1:8000
- Methods: All
- Headers: All
- Credentials: Enabled

---

## API Endpoints

### Health Checks

#### Liveness Probe
```http
GET /api/v1/health/live
```

**Response:**
```json
{
  "status": "ok"
}
```

**Purpose:** Verifies the application process is running. Used by container orchestrators (Kubernetes, Docker Compose) to determine if the process should be restarted.

#### Readiness Probe
```http
GET /api/v1/health/ready
```

**Response (Success):**
```json
{
  "status": "ok"
}
```

**Response (Failure - 503):**
```json
{
  "detail": {
    "status": "error",
    "message": "Database unavailable"
  }
}
```

**Purpose:** Verifies the application can serve requests (database connection is healthy). Used by load balancers to determine if traffic should be routed to this instance.

---

## Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                        # FastAPI entrypoint
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py                  # Settings management
│   │   └── logging.py                 # Logging configuration
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes/
│   │   │   ├── __init__.py           # Router aggregation
│   │   │   └── health.py             # Health check routes
│   │   ├── dependencies/
│   │   │   ├── __init__.py
│   │   │   └── database.py           # DB dependency
│   │   └── error_handlers/
│   │       ├── __init__.py           # Handler registration
│   │       └── handlers.py           # Exception handlers
│   └── db/
│       ├── base.py
│       ├── session.py
│       ├── models/
│       └── migrations/
├── .env                               # Environment variables
├── alembic.ini                        # Alembic configuration
└── requirements.txt                   # Python dependencies
```

---

## Testing

### Manual Testing

```bash
# Start application
uvicorn app.main:app --reload

# Test liveness
curl http://localhost:8000/api/v1/health/live

# Test readiness (requires DB)
curl http://localhost:8000/api/v1/health/ready

# Test with database stopped (should return 503)
docker stop postgres
curl http://localhost:8000/api/v1/health/ready
```

### Unit Testing

```python
import pytest
from fastapi.testclient import TestClient
from app.main import create_app

@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)

def test_liveness(client):
    response = client.get("/api/v1/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_readiness_success(client):
    response = client.get("/api/v1/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

---

## Configuration Examples

### Local Development
```bash
ENV=local
DEBUG=true
DATABASE_URL=postgresql://user:pass@localhost:5432/jobtracker_dev
LOG_LEVEL=DEBUG
```

### Staging
```bash
ENV=staging
DEBUG=false
DATABASE_URL=postgresql://user:pass@staging-db:5432/jobtracker
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

### Production
```bash
ENV=production
DEBUG=false
DATABASE_URL=postgresql://user:pass@prod-db:5432/jobtracker
LOG_LEVEL=WARNING
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

---

## Adding New Routes

### 1. Create Route Module

```python
# app/api/routes/applications.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api.dependencies.database import get_db

router = APIRouter(prefix="/applications", tags=["applications"])

@router.get("/")
def list_applications(db: Session = Depends(get_db)):
    # Implementation here
    return []
```

### 2. Register Route

```python
# app/api/routes/__init__.py
from fastapi import APIRouter
from app.api.routes import health, applications

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(applications.router)  # Add this line
```

---

## Deployment

### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker Compose

```yaml
version: '3.8'

services:
  api:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/jobtracker
      - ENV=production
    depends_on:
      - db
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health/ready"]
      interval: 30s
      timeout: 10s
      retries: 3

  db:
    image: postgres:14
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
      - POSTGRES_DB=jobtracker
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: jobtracker-api
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: api
        image: jobtracker-api:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-credentials
              key: url
        livenessProbe:
          httpGet:
            path: /api/v1/health/live
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /api/v1/health/ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 10
```

---

## Troubleshooting

### Database Connection Issues

**Error:** `Database unavailable`

**Solutions:**
1. Verify DATABASE_URL is correct
2. Check PostgreSQL is running: `pg_isready -h localhost`
3. Test connection: `psql $DATABASE_URL`
4. Check network connectivity
5. Verify credentials

### Import Errors

**Error:** `ModuleNotFoundError: No module named 'app'`

**Solutions:**
1. Ensure you're in the `backend/` directory
2. Run with: `python -m uvicorn app.main:app --reload`
3. Check PYTHONPATH includes backend directory

### Port Already in Use

**Error:** `Error: [Errno 48] Address already in use`

**Solutions:**
1. Kill existing process: `lsof -ti:8000 | xargs kill`
2. Use different port: `uvicorn app.main:app --port 8001`

---

## Next Steps

1. **Implement Application Routes** (M2 milestone)
   - POST /applications
   - GET /applications
   - GET /applications/{id}
   - PATCH /applications/{id}
   - DELETE /applications/{id}

2. **Add Pydantic Schemas** (M2 milestone)
   - ApplicationCreate
   - ApplicationResponse
   - ApplicationUpdate
   - Validation rules

3. **Implement Repositories** (M2 milestone)
   - ApplicationRepository
   - CRUD operations
   - Query builders

4. **Add Authentication** (Future)
   - Internal API token for workers
   - JWT tokens for users (if needed)

---

## References

- FastAPI Documentation: https://fastapi.tiangolo.com/
- Pydantic Settings: https://docs.pydantic.dev/latest/concepts/pydantic_settings/
- SQLAlchemy 2.0: https://docs.sqlalchemy.org/en/20/
- Python Logging: https://docs.python.org/3/library/logging.html

---

**Backend Scaffolding Status:** ✅ Complete and Ready for Application Development
