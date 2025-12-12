import logging
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, HttpUrl
from typing import Optional
from app.api.dependencies.database import get_db
from app.db.models.queue import ScraperQueue
from app.db.models.application import Application

router = APIRouter()
logger = logging.getLogger(__name__)


class ScrapeRequest(BaseModel):
    url: HttpUrl
    application_id: Optional[UUID] = None


class ScrapeResponse(BaseModel):
    job_id: UUID
    status: str
    message: str


@router.post("/scrape", response_model=ScrapeResponse, status_code=202)
def trigger_scrape(
    request: ScrapeRequest,
    db: Session = Depends(get_db)
):
    """
    Trigger a job posting scrape.
    
    Enqueues the URL for background scraping.
    """
    try:
        # Validate application if provided
        if request.application_id:
            application = db.query(Application).filter(
                Application.id == request.application_id
            ).first()
            
            if not application:
                raise HTTPException(
                    status_code=404,
                    detail="Application not found"
                )
        
        # Create scraper queue job
        scraper_job = ScraperQueue(
            application_id=request.application_id,
            url=str(request.url),
            priority=0,
            status="pending",
            attempts=0,
            max_attempts=3
        )
        
        db.add(scraper_job)
        db.commit()
        db.refresh(scraper_job)
        
        logger.info(
            f"Scrape job enqueued",
            extra={
                "job_id": str(scraper_job.id),
                "url": str(request.url),
                "application_id": str(request.application_id) if request.application_id else None
            }
        )
        
        return ScrapeResponse(
            job_id=scraper_job.id,
            status="enqueued",
            message="Scrape job has been enqueued for processing"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to enqueue scrape job: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Failed to enqueue scrape job"
        )
