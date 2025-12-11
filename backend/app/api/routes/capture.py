import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.dependencies.database import get_db
from app.schemas.application import CaptureApplicationRequest, ApplicationResponse
from app.services.application_service import create_application_from_capture
from app.services.timeline_service import log_browser_capture_sync

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/capture", response_model=ApplicationResponse, status_code=201)
def capture_application(
    request: CaptureApplicationRequest,
    db: Session = Depends(get_db)
):
    """Capture application submission from browser extension."""
    try:
        application = create_application_from_capture(db, request)
        
        # Log browser capture event
        log_browser_capture_sync(
            db=db,
            application_id=application.id,
            url=application.job_posting_url
        )
        
        db.commit()
        
        logger.info(
            "application_captured_browser",
            extra={
                "company_name": application.company_name,
                "job_title": application.job_title,
                "job_posting_url": application.job_posting_url
            }
        )
        
        return application
    except Exception as e:
        logger.error(f"Failed to capture application: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to capture application")
