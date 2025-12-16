print(">>> scraper_worker module loaded <<<")

import asyncio
import logging
import time
from datetime import datetime
from sqlalchemy.orm import Session
from app.core.config import settings
from app.db.session import SessionLocal
from app.db.models.job_posting import JobPosting, ScrapedPosting
from app.db.models.application import Application
from app.db.models.queue import ScraperQueue
from app.services.scraping import scrape_url, extract_job_data, enrich_job_data, normalize_url
from app.services.scraping.extractor import ExtractedData
from app.services.scraping.greenhouse_api import (
    fetch_greenhouse_job,
    extract_company_slug,
    extract_job_id
)
from app.services.timeline_service import (
    log_scrape_started_sync,
    log_scrape_completed_sync,
    log_scrape_failed_sync,
)

logger = logging.getLogger(__name__)

async def process_scrape_job(job: ScraperQueue, db: Session):
    print(f">>> WORKER PICKED UP JOB {job.id}")
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
        
        # FIX: normalize URL BEFORE scraping and extraction
        norm_url = normalize_url(url)

        # Initialize processing metadata
        processing_metadata = {}
        extracted = None
        scrape_result = None

        # Step 1: Try Greenhouse Boards API first (before HTTP scrape)
        # Detect by gh_jid parameter, not by hostname
        # This is source-agnostic: works for direct scrapes AND browser-captured applications
        job_id = extract_job_id(norm_url)
        greenhouse_retry_with_html = False

        if job_id:
            # Try to get company_slug from URL (works for any domain)
            company_slug = extract_company_slug(norm_url, html=None)

            if company_slug:
                logger.info(
                    f"Attempting Greenhouse Boards API for {company_slug}/{job_id}"
                )
                processing_metadata['greenhouse_api_attempted'] = True

                api_data = fetch_greenhouse_job(company_slug, job_id)

                if api_data:
                    # API success - short-circuit, skip HTTP scrape
                    processing_metadata['greenhouse_api_result'] = 'success'
                    logger.info(
                        f"Greenhouse Boards API success — skipping HTTP scrape for {company_slug}/{job_id}"
                    )

                    # Map API response to ExtractedData
                    extracted = ExtractedData(
                        title=api_data.get('title'),
                        company=company_slug.replace('-', ' ').title(),  # Best-effort company name
                        location=api_data.get('location', {}).get('name') if isinstance(api_data.get('location'), dict) else None,
                        description_html=api_data.get('content'),
                        source='greenhouse',
                        needs_review=not bool(api_data.get('content'))
                    )
                else:
                    # API returned None (404 or error)
                    # Retry with HTML to extract correct company_slug
                    processing_metadata['greenhouse_api_result'] = 'not_found_url_slug'
                    greenhouse_retry_with_html = True
                    logger.info(
                        f"Greenhouse Boards API returned 404 for URL-derived slug '{company_slug}' — will retry with HTML-extracted slug"
                    )
            else:
                # Could not determine company_slug from URL - try with HTML
                greenhouse_retry_with_html = True
                logger.info(
                    f"Could not extract company_slug from URL for job_id {job_id} — will try HTML extraction"
                )

        # Step 2: HTTP scrape (only if API didn't provide data)
        if extracted is None:
            scrape_result = await scrape_url(norm_url)

            if scrape_result.status == "error":
                logger.error(f"Scrape failed: {scrape_result.error_reason}")
                job.status = "failed"
                job.error_message = scrape_result.error_reason
                job.completed_at = datetime.utcnow()
                job.processing_metadata = processing_metadata if processing_metadata else None
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

            # Step 2b: Retry Greenhouse API with HTML-extracted company_slug
            # This handles cases where:
            # 1. Company slug couldn't be extracted from URL alone
            # 2. URL-derived slug didn't match actual Greenhouse boards slug
            # This ensures gh_jid URLs ALWAYS try Greenhouse API (source-agnostic)
            if greenhouse_retry_with_html and job_id and scrape_result:
                company_slug_from_html = extract_company_slug(norm_url, html=scrape_result.html)

                if company_slug_from_html:
                    logger.info(
                        f"Retrying Greenhouse Boards API with HTML-extracted slug: {company_slug_from_html}/{job_id}"
                    )
                    processing_metadata['greenhouse_api_retry_with_html'] = True

                    api_data = fetch_greenhouse_job(company_slug_from_html, job_id)

                    if api_data:
                        # API success - skip HTML extraction
                        processing_metadata['greenhouse_api_result'] = 'success_html_slug'
                        logger.info(
                            f"Greenhouse Boards API success with HTML-extracted slug — skipping HTML extraction"
                        )

                        # Map API response to ExtractedData
                        extracted = ExtractedData(
                            title=api_data.get('title'),
                            company=company_slug_from_html.replace('-', ' ').title(),
                            location=api_data.get('location', {}).get('name') if isinstance(api_data.get('location'), dict) else None,
                            description_html=api_data.get('content'),
                            source='greenhouse',
                            needs_review=not bool(api_data.get('content'))
                        )
                    else:
                        processing_metadata['greenhouse_api_result'] = 'not_found_html_slug'
                        logger.info(
                            f"Greenhouse Boards API returned 404 with HTML-extracted slug — falling back to HTML extraction"
                        )
                else:
                    logger.info(
                        f"Could not extract company_slug from HTML for job_id {job_id} — falling back to HTML extraction"
                    )

        # Step 3: Extract job data from HTML (if API didn't provide data)
        if extracted is None and scrape_result:
            extracted = extract_job_data(scrape_result.html, norm_url)

        # Step 4: Enrich data
        enriched = enrich_job_data(extracted)
        # Determine whether extraction produced meaningful data
        description = enriched.get("description") or ""
        has_meaningful_data = len(description.strip()) >= settings.HEADLESS_MIN_DESCRIPTION_LENGTH


        # Step 5: Save to database
        extraction_complete = bool(enriched.get("description"))
        job_posting = JobPosting(
            job_title=enriched.get("title", "Unknown"),
            company_name=enriched.get("company", "Unknown"),
            description=enriched.get("description"),
            requirements=enriched.get("requirements"),
            salary_range=enriched.get("salary"),
            location=enriched.get("location"),
            employment_type=enriched.get("employment_type"),
            extraction_complete=extraction_complete
        )

        db.add(job_posting)
        db.flush()

        # Link to application ONLY if extraction completed successfully
        # This enforces the invariant: incomplete job_postings cannot trigger analysis
        if application_id and extraction_complete:
            application = db.query(Application).filter(Application.id == application_id).first()
            if application:
                application.posting_id = job_posting.id
                application.scraping_attempted = True
                application.scraping_successful = True
        elif application_id and not extraction_complete:
            # Mark scraping as attempted but not successful for incomplete extraction
            application = db.query(Application).filter(Application.id == application_id).first()
            if application:
                application.scraping_attempted = True
                application.scraping_successful = False
        
        # Update queue job
        if has_meaningful_data:
            job.status = "completed"
        else:
            job.status = "failed"
            job.error_message = "Extraction completed but no meaningful job description found"

        job.completed_at = datetime.utcnow()
        job.processing_metadata = processing_metadata if processing_metadata else None
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
    print(">>> Scraper worker started <<<")
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
