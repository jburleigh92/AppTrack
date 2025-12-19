import logging
import httpx
import time
from typing import Optional, List, Dict, Any
from urllib.parse import urlparse, parse_qs
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def fetch_all_greenhouse_jobs(company_slug: str, max_retries: int = 3) -> List[Dict[str, Any]]:
    """
    Fetch all available jobs from a Greenhouse company board.

    Args:
        company_slug: Company identifier (e.g., 'airbnb', 'stripe', 'shopify')
        max_retries: Maximum number of retry attempts for rate limiting

    Returns:
        List of job dictionaries with fields: id, title, location, departments, etc.
    """
    url = f"https://boards-api.greenhouse.io/v1/boards/{company_slug}/jobs"
    backoff_delays = [1, 2, 4]

    for attempt in range(max_retries):
        try:
            with httpx.Client(
                timeout=10.0,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Accept": "application/json",
                }
            ) as client:
                response = client.get(url)

                if response.status_code == 200:
                    data = response.json()
                    jobs = data.get("jobs", [])
                    logger.info(f"Fetched {len(jobs)} jobs from Greenhouse for {company_slug}")
                    return jobs

                elif response.status_code == 404:
                    logger.info(f"Greenhouse board not found for company: {company_slug}")
                    return []

                elif response.status_code == 429:
                    if attempt < max_retries - 1:
                        delay = backoff_delays[attempt]
                        logger.warning(f"Rate limited fetching {company_slug} jobs. Retrying in {delay}s...")
                        time.sleep(delay)
                        continue
                    else:
                        logger.error(f"Rate limit exceeded for {company_slug}")
                        return []

                else:
                    logger.warning(f"Greenhouse API returned {response.status_code} for {company_slug}")
                    return []

        except Exception as e:
            logger.warning(f"Error fetching jobs for {company_slug}: {str(e)}")
            return []

    return []


def fetch_greenhouse_job(company_slug: str, job_id: str, max_retries: int = 3) -> Optional[dict]:
    """
    Fetch job data from Greenhouse Boards API with retry logic.

    Args:
        company_slug: Company identifier (e.g., 'company-name')
        job_id: Greenhouse job ID (numeric string)
        max_retries: Maximum number of retry attempts for rate limiting

    Returns:
        Parsed JSON dict if successful, None otherwise
    """
    url = f"https://boards-api.greenhouse.io/v1/boards/{company_slug}/jobs/{job_id}"
    backoff_delays = [1, 2, 4]  # Exponential backoff: 1s, 2s, 4s

    for attempt in range(max_retries):
        try:
            with httpx.Client(
                timeout=10.0,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Accept": "application/json",
                }
            ) as client:
                response = client.get(url)

                if response.status_code == 200:
                    logger.info(
                        f"Greenhouse Boards API success for {company_slug}/{job_id}"
                    )
                    return response.json()

                elif response.status_code == 404:
                    logger.info(
                        f"Greenhouse Boards API returned 404 — job not publicly available: {company_slug}/{job_id}"
                    )
                    return None  # Don't retry 404s

                elif response.status_code == 429:
                    # Rate limited - retry with backoff
                    if attempt < max_retries - 1:
                        delay = backoff_delays[attempt]
                        logger.warning(
                            f"Greenhouse API rate limited (429) for {company_slug}/{job_id}. "
                            f"Retrying in {delay}s (attempt {attempt + 1}/{max_retries})..."
                        )
                        time.sleep(delay)
                        continue
                    else:
                        logger.error(
                            f"Greenhouse API rate limit exceeded after {max_retries} attempts for {company_slug}/{job_id}"
                        )
                        return None

                else:
                    logger.warning(
                        f"Greenhouse Boards API returned {response.status_code} for {company_slug}/{job_id}"
                    )
                    return None  # Don't retry other status codes

        except httpx.TimeoutException:
            logger.warning(f"Greenhouse Boards API timeout for {company_slug}/{job_id}")
            return None

        except httpx.ConnectError:
            logger.warning(f"Greenhouse Boards API connection error for {company_slug}/{job_id}")
            return None

        except Exception as e:
            logger.warning(
                f"Greenhouse Boards API error for {company_slug}/{job_id}: {str(e)}"
            )
            return None

    return None  # Fallback if all retries exhausted


def extract_company_slug(url: str, html: Optional[str] = None) -> Optional[str]:
    """
    Extract Greenhouse company slug from URL or HTML.

    Args:
        url: Job posting URL
        html: Optional HTML content for fallback extraction

    Returns:
        Company slug if found, None otherwise
    """
    # Try URL hostname first
    parsed = urlparse(url)
    hostname = parsed.netloc.lower()

    # Direct boards.greenhouse.io URL: https://boards.greenhouse.io/company-name/jobs/123
    if 'boards.greenhouse.io' in hostname:
        path_parts = parsed.path.strip('/').split('/')
        if len(path_parts) >= 1:
            return path_parts[0]

    # Custom domain with gh_jid (e.g., stripe.com/jobs/search?gh_jid=123)
    # Extract company name from hostname
    if hostname:
        # Remove common prefixes
        hostname = hostname.replace('www.', '')
        hostname = hostname.replace('jobs.', '')
        hostname = hostname.replace('careers.', '')

        # Extract base company name from domain
        # e.g., stripe.com -> stripe, anthropic.com -> anthropic
        parts = hostname.split('.')
        if len(parts) >= 2:
            company_slug = parts[0]
            # Validate it looks reasonable (alphanumeric, hyphens)
            if company_slug and len(company_slug) > 1:
                return company_slug

    # Embedded Greenhouse (custom domain): try HTML fallback
    if html:
        try:
            soup = BeautifulSoup(html, 'html.parser')

            # Look for Greenhouse API calls in script tags
            scripts = soup.find_all('script')
            for script in scripts:
                if script.string and 'boards-api.greenhouse.io' in script.string:
                    # Try to extract company slug from API URL
                    import re
                    match = re.search(r'boards-api\.greenhouse\.io/v1/boards/([^/\'"]+)', script.string)
                    if match:
                        return match.group(1)

            # Look for greenhouse board token meta tag
            meta = soup.find('meta', attrs={'name': 'greenhouse-board-token'})
            if meta:
                token = meta.get('content')
                if token:
                    return token

        except Exception as e:
            logger.debug(f"Failed to parse HTML for company slug: {e}")

    return None


def extract_job_id(url: str) -> Optional[str]:
    """
    Extract Greenhouse job ID from URL query parameters.

    Args:
        url: Job posting URL

    Returns:
        Job ID if found, None otherwise
    """
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)

    # Check for gh_jid parameter
    if "gh_jid" in qs:
        return qs["gh_jid"][0]

    # Check URL path for job ID: /jobs/123 or /jobs/123456789
    path_parts = parsed.path.strip('/').split('/')
    if 'jobs' in path_parts:
        job_idx = path_parts.index('jobs')
        if job_idx + 1 < len(path_parts):
            potential_id = path_parts[job_idx + 1]
            # Greenhouse job IDs are numeric
            if potential_id.isdigit():
                return potential_id

    return None
