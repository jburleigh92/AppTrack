#!/usr/bin/env python3
"""
Job ingestion script - populates the job_postings index.

Usage:
    python scripts/ingest_jobs.py

This script:
1. Fetches jobs from Greenhouse company boards
2. Normalizes and stores them in job_postings table
3. Provides stats on ingestion progress

This should be run periodically (cron/scheduled task) to keep the index fresh.
NOT run during search requests.
"""
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db.session import SessionLocal
from app.services.job_ingestion import ingest_greenhouse_jobs, get_ingestion_stats, clean_expired_jobs
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Curated list of Greenhouse company boards to index
# This is a subset of high-quality boards for initial seeding
# Can be expanded over time
GREENHOUSE_COMPANIES = [
    # High-volume tech companies
    "airbnb", "stripe", "shopify", "coinbase", "dropbox",
    "gitlab", "notion", "figma", "databricks", "snowflake",

    # Add more as capacity allows
    # See backend/app/api/routes/jobs.py TARGET_COMPANIES for full list
]


def main():
    """Run job ingestion process."""
    logger.info("Starting job ingestion process")

    db = SessionLocal()

    try:
        # Step 1: Ingest Greenhouse jobs
        logger.info(f"Ingesting from {len(GREENHOUSE_COMPANIES)} Greenhouse boards")
        stats = ingest_greenhouse_jobs(db, GREENHOUSE_COMPANIES)

        logger.info(f"Ingestion complete: {stats}")

        # Step 2: Clean old jobs (optional)
        # Uncomment to enable automatic cleanup
        # deleted = clean_expired_jobs(db, days_old=60)
        # logger.info(f"Cleaned {deleted} expired jobs")

        # Step 3: Show current index stats
        index_stats = get_ingestion_stats(db)
        logger.info(f"Index stats: {index_stats}")

        logger.info("Job ingestion completed successfully")

    except Exception as e:
        logger.error(f"Job ingestion failed: {str(e)}", exc_info=True)
        sys.exit(1)

    finally:
        db.close()


if __name__ == "__main__":
    main()
