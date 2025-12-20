#!/usr/bin/env python3
"""
Production job ingestion script with validation and audit logging.

This script fetches REAL, CURRENT job postings from SerpAPI Google Jobs
with full traceability and validation.

Requirements:
- SERPAPI_API_KEY environment variable must be set
- Database must be migrated to latest schema

Usage:
    export SERPAPI_API_KEY="your_key_here"
    python scripts/ingest_production_jobs.py

    # With custom settings:
    python scripts/ingest_production_jobs.py --queries-per-industry 3 --max-per-query 100

Success Criteria:
- Jobs have source, source_query, source_timestamp, posted_at, industry
- All jobs are within MAX_JOB_AGE_DAYS (30 days)
- Industry classification covers tech AND non-tech roles
- Audit log proves data quality

Exit Codes:
    0 - Success (jobs ingested)
    1 - Fatal error (API failure, DB error)
    2 - Validation failure (0 jobs ingested)
"""
import sys
import os
import argparse
import json

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db.session import SessionLocal
from app.services.validated_ingestion import ingest_validated_jobs, get_index_health
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Run production job ingestion with validation."""
    parser = argparse.ArgumentParser(
        description='Ingest jobs from SerpAPI Google Jobs with validation'
    )
    parser.add_argument(
        '--queries-per-industry',
        type=int,
        default=2,
        help='Number of search queries to run per industry (default: 2)'
    )
    parser.add_argument(
        '--max-per-query',
        type=int,
        default=50,
        help='Maximum jobs to fetch per query (default: 50)'
    )
    parser.add_argument(
        '--export-audit',
        type=str,
        help='Export audit log to JSON file'
    )
    args = parser.parse_args()

    logger.info("=" * 80)
    logger.info("PRODUCTION JOB INGESTION")
    logger.info("=" * 80)
    logger.info("")
    logger.info("This script fetches REAL, CURRENT jobs from SerpAPI Google Jobs.")
    logger.info("Every job will be validated and classified.")
    logger.info("")
    logger.info("Settings:")
    logger.info(f"  - Queries per industry: {args.queries_per_industry}")
    logger.info(f"  - Max jobs per query:   {args.max_per_query}")
    logger.info("")

    # Get API key from environment
    api_key = os.environ.get("SERPAPI_API_KEY")
    if not api_key:
        logger.error("ERROR: SERPAPI_API_KEY environment variable not set")
        logger.error("")
        logger.error("To fix:")
        logger.error("  1. Get API key from https://serpapi.com/")
        logger.error("  2. export SERPAPI_API_KEY='your_key_here'")
        logger.error("  3. Run this script again")
        sys.exit(1)

    logger.info("✓ SerpAPI API key found")

    # Initialize database
    db = SessionLocal()

    try:
        # Show index state before ingestion
        logger.info("\n" + "=" * 80)
        logger.info("INDEX STATE - BEFORE")
        logger.info("=" * 80)
        health_before = get_index_health(db)
        logger.info(json.dumps(health_before, indent=2))

        # Run validated ingestion
        logger.info("\n" + "=" * 80)
        logger.info("RUNNING INGESTION")
        logger.info("=" * 80)

        audit = ingest_validated_jobs(
            db=db,
            api_key=api_key,
            queries_per_industry=args.queries_per_industry,
            max_jobs_per_query=args.max_per_query
        )

        # Export audit log if requested
        if args.export_audit:
            audit_dict = audit.to_dict()
            with open(args.export_audit, 'w') as f:
                json.dump(audit_dict, f, indent=2)
            logger.info(f"\n✓ Audit log exported to: {args.export_audit}")

        # Show index state after ingestion
        logger.info("\n" + "=" * 80)
        logger.info("INDEX STATE - AFTER")
        logger.info("=" * 80)
        health_after = get_index_health(db)
        logger.info(json.dumps(health_after, indent=2))

        # Validate ingestion success
        logger.info("\n" + "=" * 80)
        logger.info("VALIDATION")
        logger.info("=" * 80)

        if audit.jobs_inserted == 0:
            logger.error("✗ FAILURE: Zero jobs were inserted")
            logger.error("")
            logger.error("Possible reasons:")
            logger.error(f"  - All jobs failed validation (check drops_breakdown above)")
            logger.error(f"  - SerpAPI returned no results (check your API key and quota)")
            logger.error(f"  - All jobs were duplicates (jobs_dropped_duplicate > 0)")
            logger.error("")
            logger.error("Review the audit log above for details.")
            sys.exit(2)

        # Check industry diversity
        industries_covered = len(audit.jobs_by_industry)
        if industries_covered < 3:
            logger.warning(f"⚠ WARNING: Only {industries_covered} industries covered")
            logger.warning("  Expected: Multiple industries (tech AND non-tech)")
        else:
            logger.info(f"✓ Industry diversity: {industries_covered} industries covered")

        # Check date freshness
        if audit.oldest_posted_at:
            oldest_age_days = (audit.newest_posted_at - audit.oldest_posted_at).days
            logger.info(f"✓ Date range: {oldest_age_days} days")
        else:
            logger.warning("⚠ WARNING: No posted_at dates found")

        # Check traceability
        traceability_pct = health_after["traceability"]["traceability_percentage"]
        if traceability_pct < 90:
            logger.warning(f"⚠ WARNING: Traceability at {traceability_pct}%")
            logger.warning("  Expected: >90% of jobs with source_query")
        else:
            logger.info(f"✓ Traceability: {traceability_pct}%")

        logger.info("")
        logger.info("=" * 80)
        logger.info("✓ INGESTION COMPLETE")
        logger.info("=" * 80)
        logger.info("")
        logger.info("You can now test search:")
        logger.info("  GET /api/v1/jobs/search?keyword=engineer")
        logger.info("  GET /api/v1/jobs/search?keyword=warehouse")
        logger.info("  GET /api/v1/jobs/search?keyword=marketing")
        logger.info("")

    except Exception as e:
        logger.error(f"\n✗ FATAL ERROR: {str(e)}", exc_info=True)
        sys.exit(1)

    finally:
        db.close()


if __name__ == "__main__":
    main()
