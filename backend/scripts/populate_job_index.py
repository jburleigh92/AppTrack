#!/usr/bin/env python3
"""
Job index population script - ensures job_postings has data.

This script:
1. Checks if job_postings table is empty
2. Populates it with seed data (fast, reliable)
3. Optionally ingests from Greenhouse (slow, requires API access)
4. Shows index statistics

Usage:
    # Use seed data (fast, always works):
    python scripts/populate_job_index.py

    # Use seed data + Greenhouse (slow, comprehensive):
    python scripts/populate_job_index.py --greenhouse

    # Force re-ingest even if table has data:
    python scripts/populate_job_index.py --force
"""
import sys
import os
import argparse

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db.session import SessionLocal
from app.services.job_ingestion import (
    ingest_seed_jobs,
    ingest_greenhouse_jobs,
    get_ingestion_stats
)
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Populate job index with data."""
    parser = argparse.ArgumentParser(description='Populate job_postings index')
    parser.add_argument(
        '--greenhouse',
        action='store_true',
        help='Also fetch from Greenhouse boards (slow)'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force re-ingestion even if table has data'
    )
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("Job Index Population Script")
    logger.info("=" * 60)

    db = SessionLocal()

    try:
        # Step 1: Check current state
        logger.info("\n[1/4] Checking current index state...")
        stats_before = get_ingestion_stats(db)
        logger.info(f"Current state: {stats_before}")

        total_jobs = stats_before.get('total_jobs', 0)

        if total_jobs > 0 and not args.force:
            logger.info(f"✓ Index already has {total_jobs} jobs")
            logger.info("  Use --force to re-ingest anyway")
            return

        # Step 2: Ingest seed data (always fast and reliable)
        logger.info("\n[2/4] Ingesting seed data...")
        seed_stats = ingest_seed_jobs(db)
        logger.info(f"Seed ingestion result: {seed_stats}")

        # Step 3: Optionally ingest from Greenhouse
        if args.greenhouse:
            logger.info("\n[3/4] Ingesting from Greenhouse (this may take 1-2 minutes)...")
            greenhouse_companies = [
                "airbnb", "stripe", "shopify", "coinbase", "dropbox",
                "gitlab", "notion", "figma", "databricks", "snowflake",
            ]
            greenhouse_stats = ingest_greenhouse_jobs(db, greenhouse_companies)
            logger.info(f"Greenhouse ingestion result: {greenhouse_stats}")
        else:
            logger.info("\n[3/4] Skipping Greenhouse ingestion (use --greenhouse to enable)")

        # Step 4: Show final statistics
        logger.info("\n[4/4] Final index state:")
        stats_after = get_ingestion_stats(db)
        logger.info(f"Total jobs: {stats_after.get('total_jobs', 0)}")
        logger.info(f"Jobs by source: {stats_after.get('jobs_by_source', {})}")
        logger.info(f"Latest update: {stats_after.get('latest_update', 'N/A')}")

        logger.info("\n" + "=" * 60)
        logger.info("✓ Job index population complete!")
        logger.info("=" * 60)
        logger.info("\nYou can now test the search:")
        logger.info("  GET /api/v1/jobs/search?keyword=engineer")
        logger.info("  GET /api/v1/jobs/search?location=remote")
        logger.info("  GET /api/v1/jobs/search?company=stripe")

    except Exception as e:
        logger.error(f"Job index population failed: {str(e)}", exc_info=True)
        sys.exit(1)

    finally:
        db.close()


if __name__ == "__main__":
    main()
