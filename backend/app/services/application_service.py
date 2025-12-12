from datetime import date, datetime, timezone
from sqlalchemy.orm import Session
from app.db.models.application import Application
from app.schemas.application import CaptureApplicationRequest
from app.schemas.email import EmailIngestRequest
from app.services.timeline_service import record_application_created_event

def create_application_from_capture(
    db: Session,
    request: CaptureApplicationRequest
) -> Application:
    """Create application record from browser extension capture."""
    application = Application(
        company_name=request.company_name,
        job_title=request.job_title,
        job_posting_url=request.job_posting_url or "",
        application_date=date.today(),
        status="applied",
        source="browser",
        notes=request.notes,
        needs_review=False,
        analysis_completed=False
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
    application = Application(
        company_name=request.company_name or "Unknown Company",
        job_title=request.job_title or "Unknown Position",
        job_posting_url=request.job_posting_url or "",
        application_date=request.application_date,
        status="applied",
        source="email",
        notes=f"From: {request.from_email}\nSubject: {request.subject}\n\n{request.body_snippet}",
        needs_review=True if not request.company_name or not request.job_title else False,
        analysis_completed=False
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
