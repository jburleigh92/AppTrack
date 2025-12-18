"""FastAPI application entry point"""
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.api.routes import (
    health,
    capture,
    email_ingest,
    scraper,
    analysis,
    timeline,
    exports,
    internal,
    resume,
    advisory,
    jobs,
)
from app.core.config import settings
from app.core.logging import setup_logging

# Setup logging
setup_logging()

# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="Job Application Tracker Backend API",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix=f"{settings.API_V1_PREFIX}/health", tags=["health"])
app.include_router(capture.router, prefix=f"{settings.API_V1_PREFIX}/applications", tags=["applications"])
app.include_router(email_ingest.router, prefix=f"{settings.API_V1_PREFIX}/emails", tags=["emails"])
app.include_router(scraper.router, prefix=f"{settings.API_V1_PREFIX}/scraper", tags=["scraper"])
app.include_router(advisory.router, prefix=f"{settings.API_V1_PREFIX}/advisory", tags=["advisory"])
app.include_router(analysis.router, prefix=f"{settings.API_V1_PREFIX}/analysis", tags=["analysis"])
app.include_router(timeline.router, prefix=f"{settings.API_V1_PREFIX}/timeline", tags=["timeline"])
app.include_router(exports.router, prefix=f"{settings.API_V1_PREFIX}/exports", tags=["exports"])
app.include_router(internal.router, prefix=f"{settings.API_V1_PREFIX}/internal", tags=["internal"])
app.include_router(resume.router, prefix=f"{settings.API_V1_PREFIX}/resume", tags=["resume"])
app.include_router(jobs.router, prefix=f"{settings.API_V1_PREFIX}/jobs", tags=["jobs"])

@app.get("/")
async def root():
    """Serve the web UI"""
    static_dir = Path(__file__).parent.parent / "static"
    index_path = static_dir / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    else:
        return {
            "message": "Job Application Tracker API",
            "version": "1.0.0",
            "docs": "/docs",
        }
