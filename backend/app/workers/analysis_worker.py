print(">>> analysis_worker module loaded <<<")


import asyncio
import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.db.session import SessionLocal
from app.db.models.queue import AnalysisQueue
from app.services.analysis import AnalysisService, MissingDataError, LLMError, LLMClient, LLMSettings
from app.services.advisory import AdvisoryPopulator, NoOpAdvisoryComputer
from app.services.timeline_service import (
    log_analysis_started_sync,
    log_analysis_completed_sync,
    log_analysis_failed_sync
)
from app.core.config import get_settings

logger = logging.getLogger(__name__)


async def process_analysis_job(job: AnalysisQueue):
    """
    Process a single analysis job from the queue.
    
    Args:
        job: AnalysisQueue job to process
    """
    db = SessionLocal()
    settings = get_settings()
    
    try:
        job = db.merge(job)

        # Mark job as processing
        job.status = "processing"
        job.started_at = datetime.utcnow()
        job.attempts += 1
        db.commit()
        
        # Log analysis started
        log_analysis_started_sync(db=db, application_id=job.application_id)
        db.commit()
        
        # Initialize LLM client
        llm_settings = LLMSettings(
            provider=settings.llm_config.get("provider", "openai"),
            model=settings.llm_config.get("model", "gpt-4"),
            temperature=settings.llm_config.get("temperature", 0.2),
            max_tokens=settings.llm_config.get("max_tokens", 1500),
            api_key=settings.llm_config.get("api_key") or settings.OPENAI_API_KEY or settings.ANTHROPIC_API_KEY
        )
        
        llm_client = LLMClient(llm_settings)
        analysis_service = AnalysisService(llm_client)
        
        # Run analysis
        analysis = await analysis_service.run_analysis_for_application(
            db=db,
            application_id=job.application_id
        )

        # Mark job complete
        job.status = "complete"
        job.completed_at = datetime.utcnow()
        job.error_message = None

        db.commit()

        AdvisoryPopulator(NoOpAdvisoryComputer()).populate_from_analysis(
            db=db,
            analysis_result=analysis,
        )

        logger.info(
            f"Analysis job completed successfully",
            extra={
                "job_id": str(job.id),
                "application_id": str(job.application_id),
                "analysis_id": str(analysis.id)
            }
        )
    
    except MissingDataError as e:
        error_msg = str(e).lower()

        # Check if this is a transient race condition (scraping in progress)
        # vs permanent missing data (truly doesn't exist)
        is_race_condition = any([
            "has no linked job posting" in error_msg,
            "job posting not found" in error_msg,
            "has no description" in error_msg,
        ])

        if is_race_condition and job.attempts < job.max_attempts:
            # Transient failure - scrape may still be in progress
            # Retry with aggressive backoff: 10s, 30s, 2min
            backoff_seconds = [10, 30, 120]
            backoff_index = min(job.attempts - 1, len(backoff_seconds) - 1)
            retry_delay = timedelta(seconds=backoff_seconds[backoff_index])

            job.status = "pending"
            job.retry_after = datetime.utcnow() + retry_delay
            job.error_message = f"Waiting for scrape completion (attempt {job.attempts}): {str(e)}"

            logger.info(
                f"Analysis job waiting for scrape completion - will retry in {backoff_seconds[backoff_index]}s",
                extra={
                    "job_id": str(job.id),
                    "application_id": str(job.application_id),
                    "attempt": job.attempts,
                    "error": str(e)
                }
            )

            db.commit()
        else:
            # Permanent failure - data truly missing or max attempts exceeded
            reason = "max_retries_exceeded" if job.attempts >= job.max_attempts else "missing_data"

            logger.warning(
                f"Analysis job failed due to missing data: {str(e)}",
                extra={
                    "job_id": str(job.id),
                    "application_id": str(job.application_id),
                    "attempts": job.attempts,
                    "reason": reason
                }
            )

            job.status = "failed"
            job.completed_at = datetime.utcnow()
            job.error_message = f"Missing data: {str(e)}"

            log_analysis_failed_sync(
                db=db,
                application_id=job.application_id,
                reason=reason,
                details=str(e)
            )

            db.commit()
    
    except LLMError as e:
        logger.error(f"Analysis job failed due to LLM error: {str(e)}")
        
        # Transient failure - retry if attempts remaining
        if job.attempts >= job.max_attempts:
            job.status = "failed"
            job.completed_at = datetime.utcnow()
            job.error_message = f"LLM error after {job.attempts} attempts: {str(e)}"
            
            log_analysis_failed_sync(
                db=db,
                application_id=job.application_id,
                reason="llm_error",
                details=str(e)
            )
        else:
            # Set retry backoff: 1min, 5min, 15min
            backoff_minutes = [1, 5, 15]
            backoff_index = min(job.attempts - 1, len(backoff_minutes) - 1)
            retry_delay = timedelta(minutes=backoff_minutes[backoff_index])
            
            job.status = "pending"
            job.retry_after = datetime.utcnow() + retry_delay
            job.error_message = f"LLM error (attempt {job.attempts}): {str(e)}"
            
            logger.info(f"Analysis job will retry in {backoff_minutes[backoff_index]} minutes")
        
        db.commit()
    
    except Exception as e:
        logger.error(f"Unexpected error in analysis job", exc_info=True)
        
        # Treat as transient and retry
        if job.attempts >= job.max_attempts:
            job.status = "failed"
            job.completed_at = datetime.utcnow()
            job.error_message = f"Unexpected error after {job.attempts} attempts: {str(e)}"
            
            log_analysis_failed_sync(
                db=db,
                application_id=job.application_id,
                reason="unexpected_error",
                details=str(e)
            )
        else:
            backoff_minutes = [1, 5, 15]
            backoff_index = min(job.attempts - 1, len(backoff_minutes) - 1)
            retry_delay = timedelta(minutes=backoff_minutes[backoff_index])
            
            job.status = "pending"
            job.retry_after = datetime.utcnow() + retry_delay
            job.error_message = f"Error (attempt {job.attempts}): {str(e)}"
        
        db.commit()
    
    finally:
        db.close()


async def poll_analysis_queue():
    """Poll for pending analysis jobs."""
    db = SessionLocal()
    
    try:
        # Find next pending job
        now = datetime.utcnow()
        
        stmt = select(AnalysisQueue).where(
            AnalysisQueue.status == "pending",
            (AnalysisQueue.retry_after == None) | (AnalysisQueue.retry_after <= now)
        ).order_by(
            AnalysisQueue.priority.desc(),
            AnalysisQueue.created_at
        ).limit(1)
        
        job = db.execute(stmt).scalar_one_or_none()
        
        if job:
            await process_analysis_job(job)
            return True
        
        return False
    
    except Exception as e:
        logger.error("Error polling analysis queue", exc_info=True)
        return False
    
    finally:
        db.close()


def run_analysis_worker():
    print(">>> ENTERED run_analysis_worker <<<", flush=True)
    """Run the analysis worker (polling mode)."""
    logger.info("Analysis worker started")
    
    while True:
        try:
            logger.info(">>> ANALYSIS WORKER POLLING <<<")
            # Poll for jobs
            has_job = asyncio.run(poll_analysis_queue())
            
            # If no job found, wait before polling again
            if not has_job:
                asyncio.run(asyncio.sleep(5))
        
        except KeyboardInterrupt:
            logger.info("Analysis worker stopped")
            break
        
        except Exception as e:
            logger.error("Error in analysis worker", exc_info=True)
            asyncio.run(asyncio.sleep(5))


if __name__ == "__main__":
    run_analysis_worker()
