"""
Production job ingestion service with validation and audit logging.

Ensures every ingested job is traceable, recent, and complete.
Provides detailed audit logs for data quality assurance.
"""
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from app.db.models.job_posting import JobPosting
from app.services.serpapi_jobs import (
    fetch_jobs_for_industry,
    get_industry_queries,
    test_serpapi_connection
)
from app.services.industry_classifier import classify_industry, validate_industry

logger = logging.getLogger(__name__)

# Validation configuration
MAX_JOB_AGE_DAYS = 30  # Only ingest jobs posted within last 30 days
MIN_DESCRIPTION_LENGTH = 50  # Minimum characters in description
REQUIRED_FIELDS = ["job_title", "company_name", "description", "external_url"]


class IngestionAuditLog:
    """
    Audit log for tracking ingestion quality and statistics.
    """

    def __init__(self):
        self.jobs_fetched = 0
        self.jobs_inserted = 0
        self.jobs_updated = 0
        self.jobs_dropped_missing_fields = 0
        self.jobs_dropped_outdated = 0
        self.jobs_dropped_duplicate = 0
        self.jobs_dropped_no_industry = 0
        self.jobs_by_industry: Dict[str, int] = {}
        self.jobs_by_query: Dict[str, int] = {}
        self.oldest_posted_at: Optional[datetime] = None
        self.newest_posted_at: Optional[datetime] = None
        self.errors: List[str] = []

    def record_job_fetched(self):
        """Record that a job was fetched from source."""
        self.jobs_fetched += 1

    def record_job_inserted(self, industry: str, query: str, posted_at: Optional[datetime]):
        """Record successful job insertion."""
        self.jobs_inserted += 1
        self.jobs_by_industry[industry] = self.jobs_by_industry.get(industry, 0) + 1
        self.jobs_by_query[query] = self.jobs_by_query.get(query, 0) + 1

        if posted_at:
            if not self.oldest_posted_at or posted_at < self.oldest_posted_at:
                self.oldest_posted_at = posted_at
            if not self.newest_posted_at or posted_at > self.newest_posted_at:
                self.newest_posted_at = posted_at

    def record_job_updated(self):
        """Record that an existing job was updated."""
        self.jobs_updated += 1

    def record_drop_missing_fields(self, reason: str):
        """Record job dropped due to missing required fields."""
        self.jobs_dropped_missing_fields += 1
        self.errors.append(f"Missing fields: {reason}")

    def record_drop_outdated(self, posted_date: Optional[datetime]):
        """Record job dropped due to being too old."""
        self.jobs_dropped_outdated += 1
        if posted_date:
            self.errors.append(f"Outdated: posted {posted_date.date()}")

    def record_drop_duplicate(self):
        """Record job skipped as duplicate."""
        self.jobs_dropped_duplicate += 1

    def record_drop_no_industry(self):
        """Record job dropped due to unclassifiable industry."""
        self.jobs_dropped_no_industry += 1

    def record_error(self, error: str):
        """Record a general error."""
        self.errors.append(error)

    def to_dict(self) -> Dict[str, Any]:
        """
        Export audit log as dictionary.

        Returns:
            Complete audit log with all statistics
        """
        return {
            "summary": {
                "jobs_fetched": self.jobs_fetched,
                "jobs_inserted": self.jobs_inserted,
                "jobs_updated": self.jobs_updated,
                "jobs_dropped_total": (
                    self.jobs_dropped_missing_fields +
                    self.jobs_dropped_outdated +
                    self.jobs_dropped_duplicate +
                    self.jobs_dropped_no_industry
                ),
            },
            "drops_breakdown": {
                "missing_required_fields": self.jobs_dropped_missing_fields,
                "outdated_posting_date": self.jobs_dropped_outdated,
                "duplicate_external_id": self.jobs_dropped_duplicate,
                "unclassifiable_industry": self.jobs_dropped_no_industry,
            },
            "jobs_by_industry": self.jobs_by_industry,
            "jobs_by_query": self.jobs_by_query,
            "date_range": {
                "oldest_posted_at": self.oldest_posted_at.isoformat() if self.oldest_posted_at else None,
                "newest_posted_at": self.newest_posted_at.isoformat() if self.newest_posted_at else None,
            },
            "errors": self.errors[:20],  # Limit to first 20 errors for readability
            "total_errors": len(self.errors),
        }

    def log_summary(self):
        """Log a human-readable summary of the ingestion."""
        logger.info("=" * 70)
        logger.info("INGESTION AUDIT LOG")
        logger.info("=" * 70)
        logger.info(f"Jobs fetched:     {self.jobs_fetched}")
        logger.info(f"Jobs inserted:    {self.jobs_inserted}")
        logger.info(f"Jobs updated:     {self.jobs_updated}")
        logger.info(f"Jobs dropped:     {self.jobs_dropped_missing_fields + self.jobs_dropped_outdated + self.jobs_dropped_duplicate + self.jobs_dropped_no_industry}")
        logger.info("")
        logger.info("Drop reasons:")
        logger.info(f"  - Missing fields:     {self.jobs_dropped_missing_fields}")
        logger.info(f"  - Outdated:           {self.jobs_dropped_outdated}")
        logger.info(f"  - Duplicate:          {self.jobs_dropped_duplicate}")
        logger.info(f"  - No industry:        {self.jobs_dropped_no_industry}")
        logger.info("")
        logger.info("Jobs by industry:")
        for industry, count in sorted(self.jobs_by_industry.items(), key=lambda x: x[1], reverse=True):
            logger.info(f"  - {industry:30s}: {count:3d}")
        logger.info("")
        if self.oldest_posted_at and self.newest_posted_at:
            logger.info(f"Date range: {self.oldest_posted_at.date()} to {self.newest_posted_at.date()}")
        logger.info("=" * 70)


def validate_job_data(job_data: Dict[str, Any], audit: IngestionAuditLog) -> bool:
    """
    Validate that job has all required fields and meets quality criteria.

    Args:
        job_data: Normalized job dictionary
        audit: Audit log to record validation failures

    Returns:
        True if valid, False if should be dropped
    """
    # Check required fields
    for field in REQUIRED_FIELDS:
        if not job_data.get(field):
            audit.record_drop_missing_fields(f"{field} is empty")
            return False

    # Check description length
    description = job_data.get("description", "")
    if len(description) < MIN_DESCRIPTION_LENGTH:
        audit.record_drop_missing_fields(f"description too short ({len(description)} chars)")
        return False

    # Check posted date (must be within last 30 days)
    posted_at = job_data.get("posted_at")
    if posted_at:
        age_days = (datetime.utcnow() - posted_at).days
        if age_days > MAX_JOB_AGE_DAYS:
            audit.record_drop_outdated(posted_at)
            return False
    else:
        # If no posted_at, we can't verify age - log but allow
        logger.warning(f"Job missing posted_at: {job_data.get('job_title', '')[:50]}")

    return True


def ingest_validated_jobs(
    db: Session,
    api_key: str,
    queries_per_industry: int = 2,
    max_jobs_per_query: int = 50
) -> IngestionAuditLog:
    """
    Ingest jobs with strict validation and industry classification.

    This is the MAIN production ingestion function. It:
    - Fetches real jobs from SerpAPI Google Jobs
    - Validates every field
    - Classifies industry
    - Filters by date
    - Deduplicates
    - Provides comprehensive audit logs

    Args:
        db: Database session
        api_key: SerpAPI API key
        queries_per_industry: Number of queries to run per industry (default: 2)
        max_jobs_per_query: Maximum jobs to fetch per query (default: 50)

    Returns:
        IngestionAuditLog with complete statistics

    Raises:
        Exception: If SerpAPI is unavailable or API key is invalid
    """
    audit = IngestionAuditLog()

    logger.info("=" * 70)
    logger.info("Starting validated job ingestion from SerpAPI Google Jobs")
    logger.info("=" * 70)

    # Test SerpAPI connection first
    logger.info("Testing SerpAPI connection...")
    if not test_serpapi_connection(api_key):
        raise Exception("SerpAPI connection failed. Check API key and network.")

    logger.info("✓ SerpAPI connection successful")

    # Get industry queries
    industry_queries = get_industry_queries()

    # Fetch jobs for each industry
    for industry, queries in industry_queries.items():
        logger.info(f"\nFetching jobs for industry: {industry}")

        # Limit queries per industry
        for query in queries[:queries_per_industry]:
            logger.info(f"  Query: '{query}'")

            try:
                # Fetch jobs from SerpAPI
                jobs = fetch_jobs_for_industry(
                    api_key=api_key,
                    query=query,
                    max_results=max_jobs_per_query
                )

                # Process each fetched job
                for job_data in jobs:
                    audit.record_job_fetched()

                    # Validate job data
                    if not validate_job_data(job_data, audit):
                        continue  # Skip invalid jobs

                    # Classify industry
                    classified_industry = classify_industry(
                        job_title=job_data["job_title"],
                        job_description=job_data["description"]
                    )

                    # Drop jobs we can't classify (data quality requirement)
                    if classified_industry == "unknown":
                        audit.record_drop_no_industry()
                        logger.debug(f"Dropped unclassifiable job: {job_data['job_title'][:50]}")
                        continue

                    # Add industry to job data
                    job_data["industry"] = classified_industry

                    # Check for duplicates
                    existing = db.query(JobPosting).filter(
                        and_(
                            JobPosting.external_id == job_data["external_id"],
                            JobPosting.source == "serpapi_google_jobs"
                        )
                    ).first()

                    if existing:
                        # Update existing job
                        for key, value in job_data.items():
                            setattr(existing, key, value)
                        existing.updated_at = datetime.utcnow()
                        audit.record_job_updated()
                    else:
                        # Insert new job
                        job_posting = JobPosting(**job_data)
                        db.add(job_posting)
                        audit.record_job_inserted(
                            classified_industry,
                            query,
                            job_data.get("posted_at")
                        )

                # Commit after each query to avoid losing progress
                db.commit()
                logger.info(f"  ✓ Processed {len(jobs)} jobs")

            except Exception as e:
                error_msg = f"Error processing query '{query}': {str(e)}"
                logger.error(error_msg, exc_info=True)
                audit.record_error(error_msg)
                db.rollback()
                continue

    # Log final audit summary
    audit.log_summary()

    return audit


def get_index_health(db: Session) -> Dict[str, Any]:
    """
    Get comprehensive index health statistics.

    Returns:
        Dict with index health metrics including traceability stats
    """
    total_jobs = db.query(func.count(JobPosting.id)).scalar()

    # Jobs by source
    jobs_by_source = dict(
        db.query(JobPosting.source, func.count(JobPosting.id))
        .group_by(JobPosting.source)
        .all()
    )

    # Jobs by industry
    jobs_by_industry = dict(
        db.query(JobPosting.industry, func.count(JobPosting.id))
        .group_by(JobPosting.industry)
        .all()
    )

    # Date range
    oldest_posted = db.query(func.min(JobPosting.posted_at)).scalar()
    newest_posted = db.query(func.max(JobPosting.posted_at)).scalar()

    # Traceability metrics
    jobs_with_query = db.query(func.count(JobPosting.id)).filter(
        JobPosting.source_query.isnot(None)
    ).scalar()

    jobs_with_posted_date = db.query(func.count(JobPosting.id)).filter(
        JobPosting.posted_at.isnot(None)
    ).scalar()

    jobs_with_industry = db.query(func.count(JobPosting.id)).filter(
        JobPosting.industry.isnot(None),
        JobPosting.industry != "unknown"
    ).scalar()

    return {
        "total_jobs": total_jobs,
        "jobs_by_source": jobs_by_source,
        "jobs_by_industry": jobs_by_industry,
        "date_range": {
            "oldest_posted_at": oldest_posted.isoformat() if oldest_posted else None,
            "newest_posted_at": newest_posted.isoformat() if newest_posted else None,
        },
        "traceability": {
            "jobs_with_source_query": jobs_with_query,
            "jobs_with_posted_date": jobs_with_posted_date,
            "jobs_with_classified_industry": jobs_with_industry,
            "traceability_percentage": round((jobs_with_query / total_jobs * 100), 2) if total_jobs > 0 else 0,
        },
    }
