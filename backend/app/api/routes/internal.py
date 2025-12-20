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
    source: str = "seed",
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Manually trigger job ingestion.

    Args:
        source: Data source - "seed" (fast), "greenhouse" (slow), or "all"

    Returns:
        Ingestion statistics

    Example:
        POST /internal/jobs/ingest?source=seed
        POST /internal/jobs/ingest?source=greenhouse
        POST /internal/jobs/ingest?source=all
    """
    logger.info(f"Manual job ingestion triggered: source={source}")

    results = {}

    try:
        if source == "seed":
            # Ingest seed data only (fast)
            stats = ingest_seed_jobs(db)
            results["seed"] = stats

        elif source == "greenhouse":
            # Ingest from Greenhouse (slow)
            greenhouse_companies = [
                "airbnb", "stripe", "shopify", "coinbase", "dropbox",
                "gitlab", "notion", "figma", "databricks", "snowflake",
            ]
            stats = ingest_greenhouse_jobs(db, greenhouse_companies)
            results["greenhouse"] = stats

        elif source == "all":
            # Ingest from all sources
            seed_stats = ingest_seed_jobs(db)
            results["seed"] = seed_stats

            greenhouse_companies = [
                "airbnb", "stripe", "shopify", "coinbase", "dropbox",
                "gitlab", "notion", "figma", "databricks", "snowflake",
            ]
            greenhouse_stats = ingest_greenhouse_jobs(db, greenhouse_companies)
            results["greenhouse"] = greenhouse_stats

        else:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid source: {source}. Use 'seed', 'greenhouse', or 'all'"
            )

        # Get final index stats
        index_stats = get_ingestion_stats(db)
        results["index_stats"] = index_stats

        logger.info(f"Job ingestion complete: {results}")
        return {
            "status": "success",
            "results": results
        }

    except Exception as e:
        logger.error(f"Job ingestion failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Ingestion failed: {str(e)}"
        )


@router.get("/jobs/stats")
def get_job_index_stats(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Get current job index statistics.

    Returns:
        Total jobs, jobs by source, latest update time
    """
    try:
        stats = get_ingestion_stats(db)
        return {
            "status": "success",
            "stats": stats
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
