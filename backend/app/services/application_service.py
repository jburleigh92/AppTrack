from datetime import date, datetime, timezone
from sqlalchemy.orm import Session
from app.db.models.application import Application
from app.db.models.resume import Resume
from app.schemas.application import CaptureApplicationRequest
from app.schemas.email import EmailIngestRequest
from app.services.timeline_service import record_application_created_event
from logging import Logger


def create_application_from_capture(
    db: Session,
    request: CaptureApplicationRequest
) -> Application:
    """Create application record from browser extension capture."""

    # Semantic validation - check for meaningful data, not specific strings
    if not request.company_name or len(request.company_name.strip()) < 2:
        raise ValueError("Company name must be at least 2 characters")

    company_lower = request.company_name.strip().lower()
    if company_lower in ["unknown", "n/a", "none", "null", "undefined", "test"]:
        raise ValueError("Please provide a valid company name")

    if not request.job_title or len(request.job_title.strip()) < 2:
        raise ValueError("Job title must be at least 2 characters")

    job_title_lower = request.job_title.strip().lower()
    if job_title_lower in ["unknown", "n/a", "none", "null", "undefined", "test"]:
        raise ValueError("Please provide a valid job title")

    if not request.job_posting_url or len(request.job_posting_url.strip()) < 10:
        raise ValueError("Job posting URL must be at least 10 characters")

    url_lower = request.job_posting_url.strip().lower()
    if not (url_lower.startswith("http://") or url_lower.startswith("https://")):
        raise ValueError("Job posting URL must start with http:// or https://")

    if url_lower in ["http://example.com", "https://example.com", "http://localhost", "https://localhost"]:
        raise ValueError("Please provide a real job posting URL")

    # Notes can be empty or any value (optional field)

    # Get active resume
    active_resume = db.query(Resume).filter(Resume.is_active == True).first()

    application = Application(
        company_name=request.company_name,
        job_title=request.job_title,
        job_posting_url=request.job_posting_url or "",
        application_date=date.today(),
        status="applied",
        source="browser",
        notes=request.notes,
        needs_review=False,
        analysis_completed=False,
        resume_id=active_resume.id if active_resume else None
    )

    db.add(application)
    db.flush()

    # Record timeline event
    record_application_created_event(
        db=db,
        application_id=application.id,
        source="browser"
    )
    
    return application

def create_application_from_email(
    db: Session,
    request: EmailIngestRequest
) -> Application:
    """Create application record from email ingestion."""
    # Get active resume
    active_resume = db.query(Resume).filter(Resume.is_active == True).first()

    application = Application(
        company_name=request.company_name or "Unknown Company",
        job_title=request.job_title or "Unknown Position",
        job_posting_url=request.job_posting_url or "",
        application_date=request.application_date,
        status="applied",
        source="email",
        notes=f"From: {request.from_email}\nSubject: {request.subject}\n\n{request.body_snippet}",
        needs_review=True if not request.company_name or not request.job_title else False,
        analysis_completed=False,
        resume_id=active_resume.id if active_resume else None
    )

    db.add(application)
    db.flush()

    # Record timeline event
    record_application_created_event(
        db=db,
        application_id=application.id,
        source="email"
    )

    return application

def update_application_fields(
    db: Session,
    application: Application,
    **fields
) -> Application:
    """Update application fields."""
    for key, value in fields.items():
        if hasattr(application, key) and value is not None:
            setattr(application, key, value)
    
    db.commit()
    db.refresh(application)
    
    return application
