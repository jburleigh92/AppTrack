"""
SerpAPI Google Jobs integration for job ingestion.

Fetches real, current job postings from Google Jobs via SerpAPI.
Provides global, cross-industry coverage with proper attribution.

Required: SERPAPI_API_KEY environment variable
"""
import logging
import os
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import time

logger = logging.getLogger(__name__)

# SerpAPI configuration
SERPAPI_ENDPOINT = "https://serpapi.com/search.json"
DEFAULT_LOCATION = "United States"
RESULTS_PER_PAGE = 100  # SerpAPI supports up to 100 results per request
REQUEST_DELAY = 1.0  # Seconds between requests to respect rate limits


def parse_serpapi_date(date_str: str) -> Optional[datetime]:
    """
    Parse SerpAPI date strings into datetime objects.

    SerpAPI returns dates in various formats:
    - "2 days ago"
    - "1 week ago"
    - "3 hours ago"
    - "2024-01-15" (ISO format)

    Args:
        date_str: Date string from SerpAPI

    Returns:
        datetime object or None if unparseable
    """
    if not date_str:
        return None

    date_str = date_str.lower().strip()
    now = datetime.utcnow()

    try:
        # Handle "X days/weeks/hours ago" format
        if "ago" in date_str:
            parts = date_str.replace("ago", "").strip().split()
            if len(parts) == 2:
                value = int(parts[0])
                unit = parts[1]

                if "hour" in unit:
                    return now - timedelta(hours=value)
                elif "day" in unit:
                    return now - timedelta(days=value)
                elif "week" in unit:
                    return now - timedelta(weeks=value)
                elif "month" in unit:
                    return now - timedelta(days=value * 30)  # Approximate

        # Handle ISO format
        if "-" in date_str and len(date_str) >= 8:
            return datetime.fromisoformat(date_str.replace("Z", ""))

    except (ValueError, IndexError) as e:
        logger.warning(f"Failed to parse date: {date_str} - {e}")

    return None


def fetch_google_jobs_serpapi(
    query: str,
    api_key: str,
    location: str = DEFAULT_LOCATION,
    num_results: int = 100
) -> List[Dict[str, Any]]:
    """
    Fetch jobs from Google Jobs via SerpAPI.

    Args:
        query: Search keyword (e.g., "software engineer", "warehouse associate")
        api_key: SerpAPI API key
        location: Location filter (default: "United States")
        num_results: Maximum number of results to fetch (default: 100)

    Returns:
        List of normalized job dictionaries

    Raises:
        Exception: If API request fails or API key is invalid
    """
    try:
        import requests
    except ImportError:
        raise Exception(
            "requests library not installed. Run: pip install requests"
        )

    if not api_key:
        raise Exception("SerpAPI API key is required")

    logger.info(f"Fetching Google Jobs for query='{query}', location='{location}'")

    params = {
        "engine": "google_jobs",
        "q": query,
        "location": location,
        "api_key": api_key,
        "num": min(num_results, RESULTS_PER_PAGE),  # Respect SerpAPI limits
        "hl": "en",  # English results
    }

    try:
        response = requests.get(SERPAPI_ENDPOINT, params=params, timeout=30)
        response.raise_for_status()

        data = response.json()

        # Check for API errors
        if "error" in data:
            raise Exception(f"SerpAPI error: {data['error']}")

        jobs = data.get("jobs_results", [])

        logger.info(f"Fetched {len(jobs)} jobs from SerpAPI for query='{query}'")
        return jobs

    except requests.exceptions.RequestException as e:
        logger.error(f"SerpAPI request failed: {e}")
        raise Exception(f"Failed to fetch jobs from SerpAPI: {e}")


def normalize_serpapi_job(
    job_data: Dict[str, Any],
    query: str,
    fetch_timestamp: datetime
) -> Dict[str, Any]:
    """
    Normalize SerpAPI Google Jobs response into JobPosting schema.

    Args:
        job_data: Raw job dict from SerpAPI
        query: Search query used to fetch this job
        fetch_timestamp: When this job was fetched

    Returns:
        Normalized job dict ready for JobPosting model, or None if validation fails
    """
    # Extract and validate required fields
    title = job_data.get("title", "").strip()
    company = job_data.get("company_name", "").strip()
    description = job_data.get("description", "").strip()
    apply_link = job_data.get("apply_link") or job_data.get("share_link", "")

    # Validate required fields
    if not title:
        logger.warning("Skipping job: missing title")
        return None

    if not company:
        logger.warning(f"Skipping job: missing company (title={title[:50]})")
        return None

    if not description:
        logger.warning(f"Skipping job: missing description (title={title[:50]})")
        return None

    if not apply_link:
        logger.warning(f"Skipping job: missing apply link (title={title[:50]})")
        return None

    # Parse posted date
    posted_via = job_data.get("detected_extensions", {}).get("posted_at")
    posted_at = parse_serpapi_date(posted_via) if posted_via else None

    # Extract location
    location = job_data.get("location", "Location not specified")

    # Extract employment type
    extensions = job_data.get("detected_extensions", {})
    employment_type = None
    if "schedule_type" in extensions:
        employment_type = extensions["schedule_type"]

    # Generate unique external ID
    # SerpAPI doesn't provide stable IDs, so we use a hash of title+company+location
    import hashlib
    id_string = f"{title}_{company}_{location}".encode('utf-8')
    external_id = f"serpapi_{hashlib.md5(id_string).hexdigest()}"

    return {
        "job_title": title,
        "company_name": company,
        "description": description,
        "location": location,
        "employment_type": employment_type,
        "external_url": apply_link,
        "external_id": external_id,
        "source": "serpapi_google_jobs",
        "source_query": query,
        "source_timestamp": fetch_timestamp,
        "posted_at": posted_at,
        "extraction_complete": True,
    }


def fetch_jobs_for_industry(
    api_key: str,
    query: str,
    location: str = DEFAULT_LOCATION,
    max_results: int = 100,
    delay: float = REQUEST_DELAY
) -> List[Dict[str, Any]]:
    """
    Fetch and normalize jobs for a specific industry query.

    Args:
        api_key: SerpAPI API key
        query: Search query (e.g., "warehouse associate", "software engineer")
        location: Location filter
        max_results: Maximum jobs to fetch
        delay: Delay between requests (rate limiting)

    Returns:
        List of normalized, validated job dicts
    """
    fetch_timestamp = datetime.utcnow()

    # Fetch raw jobs from SerpAPI
    raw_jobs = fetch_google_jobs_serpapi(
        query=query,
        api_key=api_key,
        location=location,
        num_results=max_results
    )

    # Normalize and validate each job
    normalized_jobs = []
    for raw_job in raw_jobs:
        normalized = normalize_serpapi_job(raw_job, query, fetch_timestamp)
        if normalized:  # Only include if validation passed
            normalized_jobs.append(normalized)

    logger.info(
        f"Normalized {len(normalized_jobs)}/{len(raw_jobs)} jobs for query='{query}'"
    )

    # Respect rate limits
    if delay > 0:
        time.sleep(delay)

    return normalized_jobs


def get_industry_queries() -> Dict[str, List[str]]:
    """
    Get search queries organized by industry.

    Returns comprehensive queries across multiple industries to ensure
    diverse job coverage beyond just tech roles.

    Returns:
        Dict mapping industry names to search queries
    """
    return {
        "Software / IT": [
            "software engineer",
            "frontend developer",
            "backend engineer",
            "full stack developer",
        ],
        "Data / Analytics / AI": [
            "data scientist",
            "data engineer",
            "machine learning engineer",
        ],
        "Sales / Marketing": [
            "account executive",
            "marketing manager",
            "sales representative",
        ],
        "Operations / Warehouse / Logistics": [
            "warehouse associate",
            "operations manager",
            "logistics coordinator",
        ],
        "Finance / Accounting": [
            "accountant",
            "financial analyst",
            "finance manager",
        ],
        "Healthcare / Medical": [
            "registered nurse",
            "medical assistant",
            "healthcare administrator",
        ],
        "Education / Training": [
            "teacher",
            "training specialist",
            "instructional designer",
        ],
        "Customer Support / Success": [
            "customer success manager",
            "technical support specialist",
        ],
    }


def test_serpapi_connection(api_key: str) -> bool:
    """
    Test SerpAPI connection with a simple query.

    Args:
        api_key: SerpAPI API key to test

    Returns:
        True if connection successful, False otherwise
    """
    try:
        jobs = fetch_google_jobs_serpapi(
            query="software engineer",
            api_key=api_key,
            num_results=1
        )
        return len(jobs) > 0
    except Exception as e:
        logger.error(f"SerpAPI connection test failed: {e}")
        return False
