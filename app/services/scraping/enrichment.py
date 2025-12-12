import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def enrich_job_data(extracted_data) -> dict:
    """
    Apply enrichment and cleanup to extracted job data.
    
    Args:
        extracted_data: ExtractedData object
        
    Returns:
        Dict with enriched fields
    """
    enriched = {
        'title': _clean_text(extracted_data.title),
        'company': _clean_text(extracted_data.company),
        'location': _clean_text(extracted_data.location),
        'employment_type': _clean_text(extracted_data.employment_type),
        'salary': _normalize_salary(extracted_data.salary),
        'description': _clean_html(extracted_data.description_html),
        'requirements': _clean_html(extracted_data.requirements_html),
        'posted_date': extracted_data.posted_date,
        'source': extracted_data.source,
        'needs_review': extracted_data.needs_review
    }
    
    logger.info(
        f"Enriched job data",
        extra={
            "source": enriched['source'],
            "has_salary": bool(enriched['salary'])
        }
    )
    
    return enriched


def _clean_text(text: Optional[str]) -> Optional[str]:
    """Remove extra whitespace and normalize text."""
    if not text:
        return None
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    
    # Remove zero-width characters
    text = re.sub(r'[\u200b-\u200f\ufeff]', '', text)
    
    return text if text else None


def _clean_html(html: Optional[str]) -> Optional[str]:
    """Clean and normalize HTML content."""
    if not html:
        return None
    
    # Remove script and style tags
    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
    
    # Normalize whitespace
    html = re.sub(r'\s+', ' ', html)
    
    return html.strip() if html else None


def _normalize_salary(salary: Optional[str]) -> Optional[str]:
    """Normalize salary format."""
    if not salary:
        return None
    
    # Clean whitespace
    salary = re.sub(r'\s+', ' ', salary).strip()
    
    # Normalize common formats
    salary = salary.replace('$', '$')
    salary = salary.replace('k', 'K')
    
    # Extract numeric range if present
    match = re.search(r'\$[\d,]+\s*-\s*\$[\d,]+', salary)
    if match:
        return match.group(0)
    
    # Extract single number
    match = re.search(r'\$[\d,]+[Kk]?', salary)
    if match:
        return match.group(0)
    
    return salary
