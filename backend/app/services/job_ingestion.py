"""
Job ingestion service for populating the job_postings index.

This service fetches jobs from various sources and normalizes them into our local index.
Designed to run as a background task, NOT during search requests.

Sources:
- SerpAPI Google Jobs (primary - global coverage)
- Greenhouse company boards (secondary - curated tech companies)
- Adzuna (optional - additional coverage)

Usage:
    python scripts/ingest_jobs.py
    OR
    Scheduled via cron/Celery/etc.
"""
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.db.models.job_posting import JobPosting
from app.services.scraping.greenhouse_api import fetch_all_greenhouse_jobs
from app.services.seed_data import generate_seed_jobs
import uuid

logger = logging.getLogger(__name__)


def normalize_greenhouse_job(job_data: Dict[str, Any], company_slug: str) -> Dict[str, Any]:
    """
    Normalize Greenhouse job data into standard format.

    Args:
        job_data: Raw job dict from Greenhouse API
        company_slug: Company identifier used in API call

    Returns:
        Normalized job dict ready for insertion into JobPosting model
    """
    return {
        "job_title": job_data.get("title", "Unknown Title"),
        "company_name": job_data.get("company_name", company_slug.replace("-", " ").title()),
        "location": job_data.get("location", {}).get("name", "Location not specified"),
        "description": job_data.get("content", ""),
        "source": "greenhouse",
        "external_url": job_data.get("absolute_url", ""),
        "external_id": f"greenhouse_{company_slug}_{job_data.get('id')}",
        "extraction_complete": True,  # Greenhouse jobs come complete
    }


def ingest_greenhouse_jobs(db: Session, company_slugs: List[str]) -> Dict[str, int]:
    """
    Ingest jobs from Greenhouse company boards.

    This is a BACKGROUND operation, not called during search.

    Args:
        db: Database session
        company_slugs: List of Greenhouse board slugs to query

    Returns:
        Dict with ingestion stats: {inserted, updated, skipped, errors}
    """
    stats = {"inserted": 0, "updated": 0, "skipped": 0, "errors": 0}

    logger.info(f"Starting Greenhouse ingestion for {len(company_slugs)} companies")

    for company_slug in company_slugs:
        try:
            # Fetch jobs from Greenhouse (this is OK here - it's ingestion time)
            jobs = fetch_all_greenhouse_jobs(company_slug)

            for job_data in jobs:
                try:
                    normalized = normalize_greenhouse_job(job_data, company_slug)

                    # Check if job already exists (deduplication)
                    existing = db.query(JobPosting).filter(
                        and_(
                            JobPosting.external_id == normalized["external_id"],
                            JobPosting.source == "greenhouse"
                        )
                    ).first()

                    if existing:
                        # Update existing job
                        for key, value in normalized.items():
                            setattr(existing, key, value)
                        existing.updated_at = datetime.utcnow()
                        stats["updated"] += 1
                    else:
                        # Insert new job
                        job_posting = JobPosting(**normalized)
                        db.add(job_posting)
                        stats["inserted"] += 1

                except Exception as e:
                    logger.error(f"Error normalizing job from {company_slug}: {str(e)}")
                    stats["errors"] += 1
                    continue

            # Commit after each company to avoid losing progress
            db.commit()
            logger.info(f"Ingested {len(jobs)} jobs from {company_slug}")

        except Exception as e:
            logger.error(f"Error fetching jobs from {company_slug}: {str(e)}")
            stats["errors"] += 1
            continue

    logger.info(f"Greenhouse ingestion complete: {stats}")
    return stats


def ingest_seed_jobs(db: Session) -> Dict[str, int]:
    """
    Ingest seed job data for testing and demos.

    Use this when external APIs are unavailable or for initial bootstrap.

    Args:
        db: Database session

    Returns:
        Dict with ingestion stats: {inserted, updated, skipped, errors}
    """
    stats = {"inserted": 0, "updated": 0, "skipped": 0, "errors": 0}

    logger.info("Starting seed data ingestion")

    seed_jobs = generate_seed_jobs()

    for job_data in seed_jobs:
        try:
            # Check if job already exists (deduplication)
            existing = db.query(JobPosting).filter(
                and_(
                    JobPosting.external_id == job_data["external_id"],
                    JobPosting.source == "seed"
                )
            ).first()

            if existing:
                # Update existing job
                for key, value in job_data.items():
                    setattr(existing, key, value)
                existing.updated_at = datetime.utcnow()
                stats["updated"] += 1
            else:
                # Insert new job
                job_posting = JobPosting(**job_data)
                db.add(job_posting)
                stats["inserted"] += 1

        except Exception as e:
            logger.error(f"Error inserting seed job: {str(e)}")
            stats["errors"] += 1
            continue

    # Commit all seed jobs at once
    db.commit()

    logger.info(f"Seed data ingestion complete: {stats}")
    return stats


def ingest_serpapi_jobs(db: Session, keywords: List[str], api_key: str) -> Dict[str, int]:
    """
    Ingest jobs from SerpAPI Google Jobs.

    This provides global, cross-industry coverage.

    Args:
        db: Database session
        keywords: List of search terms to fetch (e.g., ["engineer", "manager", "specialist"])
        api_key: SerpAPI key

    Returns:
        Dict with ingestion stats

    Note:
        Requires SerpAPI subscription. This is a PAID service but provides:
        - Global job coverage
        - Cross-industry results
        - Single API for all job boards
        - ~10,000 results per keyword

        Alternative: Use Adzuna API (free tier available)
    """
    stats = {"inserted": 0, "updated": 0, "skipped": 0, "errors": 0}

    # TODO: Implement SerpAPI integration
    # This requires:
    # 1. pip install google-search-results
    # 2. SerpAPI account + API key
    # 3. Normalize SerpAPI response format

    logger.warning("SerpAPI ingestion not yet implemented. Use Greenhouse for now.")
    return stats


def clean_expired_jobs(db: Session, days_old: int = 30) -> int:
    """
    Remove jobs older than specified days.

    Greenhouse jobs don't have expiration dates, so we use created_at.

    Args:
        db: Database session
        days_old: Remove jobs older than this many days

    Returns:
        Number of jobs deleted
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days_old)

    deleted = db.query(JobPosting).filter(
        JobPosting.created_at < cutoff_date
    ).delete()

    db.commit()
    logger.info(f"Cleaned {deleted} expired jobs (older than {days_old} days)")

    return deleted


def get_ingestion_stats(db: Session) -> Dict[str, Any]:
    """
    Get current index statistics.

    Returns:
        Dict with total jobs, jobs by source, latest update, etc.
    """
    from sqlalchemy import func

    total_jobs = db.query(func.count(JobPosting.id)).scalar()

    jobs_by_source = db.query(
        JobPosting.source,
        func.count(JobPosting.id)
    ).group_by(JobPosting.source).all()

    latest_update = db.query(func.max(JobPosting.updated_at)).scalar()

    return {
        "total_jobs": total_jobs,
        "jobs_by_source": dict(jobs_by_source),
        "latest_update": latest_update.isoformat() if latest_update else None,
    }
