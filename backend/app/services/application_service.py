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
    
    # Validation
    if request.company_name == "string":
        raise ValueError("string is not an accepted company name")
    if request.company_name is None:
        raise ValueError("NONE is not an accepted company name")
    if request.job_title == "string":
        raise ValueError("string is not an accepted job title")
    if request.job_title is None:
        raise ValueError("NONE is not an accepted job title")
    if request.job_posting_url == "string":
        raise ValueError("string is not an accepted URL")
    if request.job_posting_url is None:
        raise ValueError("NONE is not an accepted URL")
    if request.notes == "string":
        raise ValueError("string is not an accepted note")
    if request.notes is None:
        raise ValueError("NONE is not an accepted note")
    

    """Create application record from browser extension capture."""
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
