import asyncio
import logging
import time
from datetime import datetime
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.db.models.job_posting import JobPosting, ScrapedPosting
from app.db.models.application import Application
from app.db.models.queue import ScraperQueue
from app.services.scraping import scrape_url, extract_job_data, enrich_job_data, normalize_url
from app.services.timeline_service import (
    log_scrape_started_sync,
    log_scrape_completed_sync,
    log_scrape_failed_sync,
)

logger = logging.getLogger(__name__)

async def process_scrape_job(job: ScraperQueue, db: Session):
    """
    Process a scrape job from the queue.
    """
    url = job.url
    application_id = job.application_id
    
    logger.info(f"Processing scrape job: {url} for application {application_id}")
    
    try:
        # Update status to processing
        job.status = "processing"
        job.started_at = datetime.utcnow()
        db.commit()
        
        # Log scrape started
        if application_id:
            log_scrape_started_sync(db=db, application_id=application_id, url=url)
            db.commit()
        
        # Step 1: Scrape URL
        scrape_result = await scrape_url(url)
        
        if scrape_result.status == "error":
            logger.error(f"Scrape failed: {scrape_result.error_reason}")
            job.status = "failed"
            job.error_message = scrape_result.error_reason
            job.completed_at = datetime.utcnow()
            db.commit()
            
            if application_id:
                log_scrape_failed_sync(
                    db=db,
                    application_id=application_id,
                    reason=scrape_result.error_reason,
                    url=url
                )
                db.commit()
            return
        
        # Step 2: Extract job data
        extracted = extract_job_data(scrape_result.html, url)
        
        # Step 3: Enrich data
        enriched = enrich_job_data(extracted)
        
        # Step 4: Save to database
        norm_url = normalize_url(url)
        
        job_posting = JobPosting(
            job_title=enriched.get("title", "Unknown"),
            company_name=enriched.get("company", "Unknown"),
            description=enriched.get("description"),
            requirements=enriched.get("requirements"),
            salary_range=enriched.get("salary_range"),
            location=enriched.get("location"),
            employment_type=enriched.get("employment_type"),
            extraction_complete=not enriched.get("needs_review", False)
        )
        
        db.add(job_posting)
        db.flush()
        
        # Link to application
        if application_id:
            application = db.query(Application).filter(Application.id == application_id).first()
            if application:
                application.posting_id = job_posting.id
                application.scraping_attempted = True
                application.scraping_successful = True
        
        # Update queue job
        job.status = "completed"
        job.completed_at = datetime.utcnow()
        job.result_data = {"job_posting_id": str(job_posting.id)}
        
        db.commit()
        
        if application_id:
            log_scrape_completed_sync(
                db=db,
                application_id=application_id,
                job_posting_id=job_posting.id,
                url=url
            )
            db.commit()
        
        logger.info(f"Scrape job completed successfully: {job_posting.id}")
    
    except Exception as e:
        logger.error(f"Error processing scrape job", exc_info=True)
        db.rollback()
        
        job.status = "failed"
        job.error_message = str(e)
        job.completed_at = datetime.utcnow()
        db.commit()
        
        if application_id:
            log_scrape_failed_sync(
                db=db,
                application_id=application_id,
                reason=str(e),
                url=url
            )
            db.commit()

def run_scraper_worker():
    """Run the scraper worker (polling mode)."""
    logger.info("Scraper worker started")
    
    while True:
        db = SessionLocal()
        try:
            # Poll for pending scrape jobs
            pending_job = db.query(ScraperQueue).filter(
                ScraperQueue.status == "pending"
            ).order_by(ScraperQueue.created_at).first()
            
            if pending_job:
                logger.info(f"Found pending job: {pending_job.id}")
                asyncio.run(process_scrape_job(pending_job, db))
            else:
                # No jobs, sleep for a bit
                time.sleep(5)
        
        except KeyboardInterrupt:
            logger.info("Scraper worker stopped")
            db.close()
            break
        except Exception as e:
            logger.error("Error in scraper worker", exc_info=True)
            time.sleep(5)
        finally:
            db.close()

if __name__ == "__main__":
    run_scraper_worker()
