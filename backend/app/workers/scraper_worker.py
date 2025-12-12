import asyncio
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.db.models.job_posting import JobPosting, ScrapedPosting
from app.db.models.application import Application
from app.services.scraping import scrape_url, extract_job_data, enrich_job_data, normalize_url
from app.services.timeline_service import (
    log_scrape_started_sync,
    log_scrape_completed_sync,
    log_scrape_failed_sync,
    log_posting_linked
)

logger = logging.getLogger(__name__)


async def process_scrape_job(job_data: dict):
    """
    Process a scrape job from the queue.
    
    Args:
        job_data: Dict with 'job_posting_url' and optional 'application_id'
    """
    url = job_data.get('job_posting_url')
    application_id = job_data.get('application_id')
    
    logger.info(
        f"Processing scrape job",
        extra={
            "url": url,
            "application_id": application_id
        }
    )
    
    db = SessionLocal()
    
    try:
        # Log scrape started
        if application_id:
            log_scrape_started_sync(db=db, application_id=application_id, url=url)
            db.commit()
        
        # Step 1: Scrape URL
        scrape_result = await scrape_url(url)
        
        if scrape_result.status == "error":
            logger.error(
                f"Scrape failed: {scrape_result.error_reason}",
                extra={"url": url}
            )
            
            if application_id:
                log_scrape_failed_sync(
                    db=db,
                    application_id=application_id,
                    reason=scrape_result.error_reason,
                    url=url
                )
                db.commit()
            
            return
        
        # Step 2: Extract data
        extracted = extract_job_data(scrape_result.html, url)
        
        # Step 3: Enrich data
        enriched = enrich_job_data(extracted)
        
        # Step 4: Save scraped posting
        scraped_posting = ScrapedPosting(
            url=url,
            html_content=scrape_result.html[:1000000],  # Limit to 1MB
            http_status_code=scrape_result.http_status_code or 200,
            scraped_at=datetime.utcnow()
        )
        db.add(scraped_posting)
        db.flush()
        
        # Step 5: Create job posting
        normalized_url = normalize_url(scrape_result.redirect_url or url)
        
        job_posting = JobPosting(
            url=url,
            normalized_url=normalized_url,
            title=enriched.get('title'),
            company=enriched.get('company'),
            location=enriched.get('location'),
            description=enriched.get('description'),
            requirements=enriched.get('requirements'),
            employment_type=enriched.get('employment_type'),
            salary_range=enriched.get('salary'),
            source=enriched.get('source'),
            extraction_complete=not enriched.get('needs_review', False)
        )
        
        db.add(job_posting)
        db.flush()
        
        # Link scraped posting to job posting
        scraped_posting.job_posting_id = job_posting.id
        
        # Step 6: Link to application if provided
        if application_id:
            application = db.query(Application).filter(
                Application.id == application_id
            ).first()
            
            if application:
                application.posting_id = job_posting.id
                
                # Update missing fields
                if not application.company_name or application.company_name == "Unknown Company":
                    if job_posting.company:
                        application.company_name = job_posting.company
                
                if not application.job_title or application.job_title == "Unknown Position":
                    if job_posting.title:
                        application.job_title = job_posting.title
                
                # Clear needs_review if data is now complete
                if application.company_name and application.job_title:
                    if application.company_name != "Unknown Company" and application.job_title != "Unknown Position":
                        application.needs_review = False
                
                # Log events
                log_scrape_completed_sync(
                    db=db,
                    application_id=application_id,
                    url=url,
                    posting_id=job_posting.id
                )
        
        db.commit()
        
        logger.info(
            f"Scrape job completed successfully",
            extra={
                "url": url,
                "job_posting_id": str(job_posting.id),
                "application_id": application_id
            }
        )
    
    except Exception as e:
        logger.error(f"Error processing scrape job", exc_info=True)
        db.rollback()
        
        if application_id:
            log_scrape_failed_sync(
                db=db,
                application_id=application_id,
                reason=str(e),
                url=url
            )
            db.commit()
    
    finally:
        db.close()


def run_scraper_worker():
    """Run the scraper worker (polling mode for now)."""
    logger.info("Scraper worker started")
    
    # In a real implementation, this would poll a queue table
    # For now, this is a placeholder for the worker process
    while True:
        try:
            # Poll for pending scrape jobs
            # This would be replaced with actual queue polling
            asyncio.run(asyncio.sleep(5))
        except KeyboardInterrupt:
            logger.info("Scraper worker stopped")
            break
        except Exception as e:
            logger.error("Error in scraper worker", exc_info=True)
            asyncio.run(asyncio.sleep(5))


if __name__ == "__main__":
    run_scraper_worker()
