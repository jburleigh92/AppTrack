import logging
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
from app.api.dependencies.database import get_db
from app.db.models.queue import ScraperQueue
from app.db.models.job_posting import JobPosting
from app.db.models.application import Application
from app.services.timeline_service import record_posting_scraped_event, record_scrape_failed_event

router = APIRouter(prefix="/internal", tags=["internal"])
logger = logging.getLogger(__name__)


class ScrapeCompleteRequest(BaseModel):
    job_id: UUID
    status: str
    job_posting_id: Optional[UUID] = None
    error_message: Optional[str] = None


@router.post("/scrape-complete", status_code=200)
def scrape_complete_callback(
    request: ScrapeCompleteRequest,
    db: Session = Depends(get_db)
):
    """
    Callback endpoint for worker to report scrape completion.
    """
    try:
        # Find scraper queue job
        scraper_job = db.query(ScraperQueue).filter(
            ScraperQueue.id == request.job_id
        ).first()
        
        if not scraper_job:
            raise HTTPException(status_code=404, detail="Scraper job not found")
        
        # Update job status
        scraper_job.status = request.status
        scraper_job.completed_at = datetime.utcnow()
        
        if request.error_message:
            scraper_job.error_message = request.error_message
        
        # Record timeline event if linked to application
        if scraper_job.application_id:
            if request.status == "complete" and request.job_posting_id:
                record_posting_scraped_event(
                    db=db,
                    application_id=scraper_job.application_id,
                    url=scraper_job.url,
                    partial=False
                )
            elif request.status == "failed":
                record_scrape_failed_event(
                    db=db,
                    application_id=scraper_job.application_id,
                    url=scraper_job.url,
                    error=request.error_message or "Unknown error"
                )
        
        db.commit()
        
        logger.info(
            f"Scrape job completed",
            extra={
                "job_id": str(request.job_id),
                "status": request.status
            }
        )
        
        return {"message": "Callback processed successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to process scrape callback: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Failed to process callback"
        )
