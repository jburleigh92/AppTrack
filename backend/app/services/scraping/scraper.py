import logging
import httpx
from typing import Optional
from datetime import datetime
from urllib.parse import urlparse, parse_qs, urlencode

logger = logging.getLogger(__name__)


class ScrapeResult:
    def __init__(
        self,
        status: str,
        url: str,
        html: Optional[str] = None,
        redirect_url: Optional[str] = None,
        error_reason: Optional[str] = None,
        http_status_code: Optional[int] = None
    ):
        self.status = status
        self.url = url
        self.html = html
        self.redirect_url = redirect_url
        self.error_reason = error_reason
        self.http_status_code = http_status_code


async def scrape_url(url: str) -> ScrapeResult:
    """
    Fetch HTML content from a job posting URL.

    Returns:
        ScrapeResult with status, html, and metadata
    """
    try:
        async with httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            }
        ) as client:
            response = await client.get(url)
            
            if response.status_code == 200:
                final_url = str(response.url) if response.url != url else None

                logger.info(
                    f"Fetched HTML length: {len(response.text)}"
                )
                
                logger.info(
                    "Successfully scraped URL",
                    extra={
                        "url": url,
                        "status_code": response.status_code,
                        "redirect_url": final_url
                    }
                )
                
                return ScrapeResult(
                    status="success",
                    url=url,
                    html=response.text,
                    redirect_url=final_url,
                    http_status_code=response.status_code
                )
            
            elif response.status_code == 403:
                logger.warning(f"Access forbidden (403) for URL: {url}")
                return ScrapeResult(
                    status="error",
                    url=url,
                    error_reason="Access forbidden (403) - possible bot protection",
                    http_status_code=response.status_code
                )
            
            elif response.status_code == 404:
                logger.warning(f"URL not found (404): {url}")
                return ScrapeResult(
                    status="error",
                    url=url,
                    error_reason="URL not found (404)",
                    http_status_code=response.status_code
                )
            
            else:
                logger.warning(f"Unexpected status code {response.status_code} for URL: {url}")
                return ScrapeResult(
                    status="error",
                    url=url,
                    error_reason=f"HTTP {response.status_code}",
                    http_status_code=response.status_code
                )
    
    except httpx.TimeoutException:
        logger.error(f"Timeout while scraping URL: {url}")
        return ScrapeResult(
            status="error",
            url=url,
            error_reason="Request timeout"
        )
    
    except httpx.ConnectError:
        logger.error(f"Connection error while scraping URL: {url}")
        return ScrapeResult(
            status="error",
            url=url,
            error_reason="Connection error"
        )
    
    except Exception as e:
        logger.error(f"Unexpected error while scraping URL: {url}", exc_info=True)
        return ScrapeResult(
            status="error",
            url=url,
            error_reason=f"Unexpected error: {str(e)}"
        )


def normalize_url(url: str) -> str:
    """Normalize URL while preserving Greenhouse embedded job URLs."""
    parsed = urlparse(url)
    query_params = parse_qs(parsed.query)

    # If this is a Greenhouse embedded job, KEEP it intact
    if "gh_jid" in query_params:
        return url

    tracking_params = {
        'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
        'ref', 'source', 'trk', 'referrer', 'fbclid', 'gclid'
    }

    cleaned_params = {
        k: v for k, v in query_params.items()
        if k not in tracking_params
    }

    cleaned_query = urlencode(cleaned_params, doseq=True)

    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}" + (
        f"?{cleaned_query}" if cleaned_query else ""
    )
