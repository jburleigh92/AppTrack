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
from app.services.job_ingestion import (
    ingest_seed_jobs,
    ingest_greenhouse_jobs,
    get_ingestion_stats,
    clean_expired_jobs
)
from app.services.validated_ingestion import ingest_validated_jobs, get_index_health
import os

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


@router.post("/jobs/ingest")
def trigger_job_ingestion(
    source: str = "production",
    queries_per_industry: int = 2,
    max_per_query: int = 50,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Manually trigger job ingestion.

    Args:
        source: Data source - "production" (SerpAPI with validation), "seed" (demo data)
        queries_per_industry: For production - queries per industry (default: 2)
        max_per_query: For production - max jobs per query (default: 50)

    Returns:
        Ingestion statistics and audit log

    Example:
        POST /internal/jobs/ingest?source=production
        POST /internal/jobs/ingest?source=seed
        POST /internal/jobs/ingest?source=production&queries_per_industry=3&max_per_query=100
    """
    logger.info(f"Manual job ingestion triggered: source={source}")

    try:
        if source == "production":
            # Production ingestion with SerpAPI and validation
            api_key = os.environ.get("SERPAPI_API_KEY")
            if not api_key:
                raise HTTPException(
                    status_code=400,
                    detail="SERPAPI_API_KEY environment variable not set. Cannot run production ingestion."
                )

            audit = ingest_validated_jobs(
                db=db,
                api_key=api_key,
                queries_per_industry=queries_per_industry,
                max_jobs_per_query=max_per_query
            )

            # Get index health
            index_health = get_index_health(db)

            return {
                "status": "success",
                "audit": audit.to_dict(),
                "index_health": index_health
            }

        elif source == "seed":
            # Ingest seed data only (for testing/demos)
            stats = ingest_seed_jobs(db)
            index_stats = get_ingestion_stats(db)

            return {
                "status": "success",
                "results": {
                    "seed": stats,
                    "index_stats": index_stats
                }
            }

        else:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid source: {source}. Use 'production' or 'seed'"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Job ingestion failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Ingestion failed: {str(e)}"
        )


@router.get("/jobs/stats")
def get_job_index_stats(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Get comprehensive job index health statistics.

    Returns:
        Total jobs, jobs by source/industry, traceability metrics, date ranges
    """
    try:
        health = get_index_health(db)
        return {
            "status": "success",
            "health": health
        }
    except Exception as e:
        logger.error(f"Failed to get stats: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get stats: {str(e)}"
        )


@router.post("/jobs/cleanup")
def cleanup_expired_jobs_endpoint(
    days_old: int = 30,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Remove jobs older than specified days.

    Args:
        days_old: Remove jobs older than this many days (default: 30)

    Returns:
        Number of jobs deleted
    """
    try:
        deleted = clean_expired_jobs(db, days_old=days_old)
        return {
            "status": "success",
            "deleted": deleted,
            "days_old": days_old
        }
    except Exception as e:
        logger.error(f"Cleanup failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Cleanup failed: {str(e)}"
        )
