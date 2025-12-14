import logging
import re
from typing import Optional, Dict, Any
from bs4 import BeautifulSoup
from datetime import datetime

logger = logging.getLogger(__name__)


class ExtractedData:
    def __init__(
        self,
        title: Optional[str] = None,
        company: Optional[str] = None,
        location: Optional[str] = None,
        employment_type: Optional[str] = None,
        salary: Optional[str] = None,
        description_html: Optional[str] = None,
        requirements_html: Optional[str] = None,
        posted_date: Optional[str] = None,
        source: Optional[str] = None,
        needs_review: bool = False
    ):
        self.title = title
        self.company = company
        self.location = location
        self.employment_type = employment_type
        self.salary = salary
        self.description_html = description_html
        self.requirements_html = requirements_html
        self.posted_date = posted_date
        self.source = source
        self.needs_review = needs_review


def extract_job_data(html: str, url: str) -> ExtractedData:
    """
    Extract structured job posting data from HTML.
    
    Args:
        html: Raw HTML content
        url: Original URL for ATS detection
        
    Returns:
        ExtractedData with parsed fields
    """
    soup = BeautifulSoup(html, 'html.parser')
    
    # Detect ATS source
    source = _detect_ats(url, soup)
    
    # Extract fields
    title = _extract_title(soup, source)
    company = _extract_company(soup, source)
    location = _extract_location(soup, source)
    employment_type = _extract_employment_type(soup)
    salary = _extract_salary(soup)
    description_html = _extract_description(soup, source)
    requirements_html = _extract_requirements(soup)
    posted_date = _extract_posted_date(soup)
    
    # Determine if needs review
    needs_review = not all([title, company, description_html])
    
    logger.info(
        "Extracted job data",
        extra={
            "url": url,
            "source": source,
            "has_title": bool(title),
            "has_company": bool(company),
            "has_description": bool(description_html),
            "needs_review": needs_review
        }
    )
    
    return ExtractedData(
        title=title,
        company=company,
        location=location,
        employment_type=employment_type,
        salary=salary,
        description_html=description_html,
        requirements_html=requirements_html,
        posted_date=posted_date,
        source=source,
        needs_review=needs_review
    )


def _detect_ats(url: str, soup: BeautifulSoup) -> str:
    """Detect ATS platform from URL and HTML markers."""
    url_lower = url.lower()
    
    if 'greenhouse.io' in url_lower or 'boards.greenhouse.io' in url_lower:
        return 'greenhouse'
    elif 'lever.co' in url_lower or 'jobs.lever.co' in url_lower:
        return 'lever'
    elif 'myworkdayjobs.com' in url_lower:
        return 'workday'
    elif 'careers-page.com' in url_lower:
        return 'careers-page'
    elif 'ashbyhq.com' in url_lower:
        return 'ashby'
    elif 'jobs.smartrecruiters.com' in url_lower:
        return 'smartrecruiters'
    elif 'linkedin.com/jobs' in url_lower:
        return 'linkedin'
    elif 'indeed.com' in url_lower:
        return 'indeed'
    
    # Check HTML meta tags
    meta_generator = soup.find('meta', attrs={'name': 'generator'})
    if meta_generator:
        content = meta_generator.get('content', '').lower()
        if 'greenhouse' in content:
            return 'greenhouse'
        elif 'lever' in content:
            return 'lever'
    
    return 'unknown'


def _extract_title(soup: BeautifulSoup, source: str) -> Optional[str]:
    """Extract job title."""
    # Try source-specific selectors
    if source == 'greenhouse':
        title_elem = soup.select_one('.app-title')
        if title_elem:
            return title_elem.get_text(strip=True)
    
    elif source == 'lever':
        title_elem = soup.select_one('.posting-headline h2')
        if title_elem:
            return title_elem.get_text(strip=True)
    
    elif source == 'workday':
        title_elem = soup.select_one('[data-automation-id="jobPostingHeader"]')
        if title_elem:
            return title_elem.get_text(strip=True)
    
    # Generic fallback
    selectors = [
        'h1.job-title', 'h1[itemprop="title"]', '.job-title',
        'h1', '[class*="job-title"]', '[class*="position-title"]'
    ]
    
    for selector in selectors:
        elem = soup.select_one(selector)
        if elem:
            text = elem.get_text(strip=True)
            if len(text) > 5 and len(text) < 200:
                return text
    
    # Try page title as last resort
    title_tag = soup.find('title')
    if title_tag:
        text = title_tag.get_text(strip=True)
        # Remove common suffixes
        for suffix in [' - Careers', ' | Jobs', ' - Job Board']:
            text = text.replace(suffix, '')
        if len(text) > 5 and len(text) < 200:
            return text
    
    return None


def _extract_company(soup: BeautifulSoup, source: str) -> Optional[str]:
    """Extract company name."""
    if source == 'greenhouse':
        company_elem = soup.select_one('.company-name')
        if company_elem:
            return company_elem.get_text(strip=True)
    
    elif source == 'lever':
        company_elem = soup.select_one('.main-header-text a')
        if company_elem:
            return company_elem.get_text(strip=True)
    
    # Generic fallback
    selectors = [
        '[itemprop="hiringOrganization"]', '.company-name',
        '[class*="company"]', 'meta[property="og:site_name"]'
    ]
    
    for selector in selectors:
        elem = soup.select_one(selector)
        if elem:
            if elem.name == 'meta':
                text = elem.get('content', '')
            else:
                text = elem.get_text(strip=True)
            
            if len(text) > 1 and len(text) < 100:
                return text
    
    return None


def _extract_location(soup: BeautifulSoup, source: str) -> Optional[str]:
    """Extract job location."""
    if source == 'greenhouse':
        location_elem = soup.select_one('.location')
        if location_elem:
            return location_elem.get_text(strip=True)
    
    elif source == 'lever':
        location_elem = soup.select_one('.posting-categories .location')
        if location_elem:
            return location_elem.get_text(strip=True)
    
    # Generic fallback
    selectors = [
        '[itemprop="jobLocation"]', '.location',
        '[class*="location"]', 'meta[property="og:location"]'
    ]
    
    for selector in selectors:
        elem = soup.select_one(selector)
        if elem:
            if elem.name == 'meta':
                text = elem.get('content', '')
            else:
                text = elem.get_text(strip=True)
            
            if len(text) > 2 and len(text) < 200:
                return text
    
    return None


def _extract_employment_type(soup: BeautifulSoup) -> Optional[str]:
    """Extract employment type (Full-time, Part-time, etc)."""
    selectors = [
        '[itemprop="employmentType"]',
        '.employment-type',
        '[class*="employment"]'
    ]
    
    for selector in selectors:
        elem = soup.select_one(selector)
        if elem:
            text = elem.get_text(strip=True).lower()
            
            if 'full' in text or 'full-time' in text:
                return 'Full-time'
            elif 'part' in text or 'part-time' in text:
                return 'Part-time'
            elif 'contract' in text:
                return 'Contract'
            elif 'intern' in text:
                return 'Internship'
    
    return None


def _extract_salary(soup: BeautifulSoup) -> Optional[str]:
    """Extract salary information."""
    selectors = [
        '[itemprop="baseSalary"]',
        '.salary',
        '[class*="salary"]',
        '[class*="compensation"]'
    ]
    
    for selector in selectors:
        elem = soup.select_one(selector)
        if elem:
            text = elem.get_text(strip=True)
            # Check if looks like salary (contains numbers and $)
            if '$' in text or re.search(r'\d{2,}', text):
                return text
    
    return None


def _extract_description(soup: BeautifulSoup, source: str) -> Optional[str]:
    """Extract job description HTML."""
    if source == 'greenhouse':
        desc_elem = soup.select_one('#content .content')
        if desc_elem:
            return str(desc_elem)
    
    elif source == 'lever':
        desc_elem = soup.select_one('.section-wrapper .section:first-of-type')
        if desc_elem:
            return str(desc_elem)
    
    # Generic fallback
    selectors = [
        '[itemprop="description"]',
        '.job-description',
        '[class*="description"]',
        '.content'
    ]
    
    for selector in selectors:
        elem = soup.select_one(selector)
        if elem and len(elem.get_text(strip=True)) > 100:
            return str(elem)
    
    return None


def _extract_requirements(soup: BeautifulSoup) -> Optional[str]:
    """Extract job requirements HTML."""
    selectors = [
        '.requirements',
        '[class*="requirements"]',
        '[class*="qualifications"]'
    ]
    
    for selector in selectors:
        elem = soup.select_one(selector)
        if elem and len(elem.get_text(strip=True)) > 50:
            return str(elem)
    
    return None


def _extract_posted_date(soup: BeautifulSoup) -> Optional[str]:
    """Extract posting date."""
    selectors = [
        '[itemprop="datePosted"]',
        '.posted-date',
        '[class*="posted"]'
    ]
    
    for selector in selectors:
        elem = soup.select_one(selector)
        if elem:
            if elem.name == 'meta':
                return elem.get('content', '')
            else:
                return elem.get_text(strip=True)
    
    return None
