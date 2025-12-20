"""
Industry classification for job postings.

Provides explicit, rule-based industry mapping based on job titles and descriptions.
NO silent defaults - jobs that can't be classified are marked as 'unknown'.
"""
import logging
from typing import Optional, Dict, Set
import re

logger = logging.getLogger(__name__)

# Industry classification rules - explicit keyword mappings
# Each industry has required keywords (any match) and optional exclusions
INDUSTRY_RULES = {
    "Software / IT": {
        "title_keywords": [
            "software engineer", "developer", "programmer", "swe", "sde",
            "frontend", "backend", "full stack", "fullstack", "devops",
            "site reliability", "sre", "platform engineer", "infrastructure engineer",
            "mobile engineer", "ios engineer", "android engineer",
            "web developer", "application developer", "systems engineer",
            "technical lead", "engineering manager", "principal engineer",
            "staff engineer", "architect", "qa engineer", "test engineer"
        ],
        "description_keywords": [
            "software development", "coding", "programming", "api development",
            "microservices", "cloud infrastructure", "ci/cd", "kubernetes",
            "docker", "rest api", "graphql", "react", "angular", "vue",
            "python", "java", "javascript", "typescript", "go", "rust"
        ],
    },

    "Data / Analytics / AI": {
        "title_keywords": [
            "data scientist", "data engineer", "data analyst", "analytics engineer",
            "ml engineer", "machine learning", "ai engineer", "research scientist",
            "data architect", "business intelligence", "bi analyst"
        ],
        "description_keywords": [
            "machine learning", "deep learning", "data pipeline", "etl",
            "spark", "hadoop", "airflow", "tensorflow", "pytorch", "scikit-learn",
            "data warehouse", "snowflake", "bigquery", "redshift",
            "predictive modeling", "statistical analysis", "a/b testing"
        ],
    },

    "Product / Design": {
        "title_keywords": [
            "product manager", "product owner", "product designer",
            "ux designer", "ui designer", "ux/ui", "interaction designer",
            "visual designer", "user researcher", "design lead"
        ],
        "description_keywords": [
            "product roadmap", "user research", "wireframes", "prototyping",
            "figma", "sketch", "user experience", "product strategy",
            "stakeholder management", "agile product", "feature prioritization"
        ],
    },

    "Sales / Marketing": {
        "title_keywords": [
            "account executive", "sales representative", "sales manager",
            "business development", "bdr", "sdr", "sales engineer",
            "marketing manager", "digital marketing", "growth marketing",
            "content marketing", "product marketing", "marketing operations",
            "marketing specialist", "marketing coordinator"
        ],
        "description_keywords": [
            "quota attainment", "pipeline generation", "lead generation",
            "salesforce", "crm", "outbound sales", "inbound sales",
            "marketing campaigns", "seo", "sem", "content strategy",
            "email marketing", "social media marketing", "brand awareness"
        ],
    },

    "Finance / Accounting": {
        "title_keywords": [
            "accountant", "financial analyst", "controller", "cfo",
            "finance manager", "accounting manager", "bookkeeper",
            "accounts payable", "accounts receivable", "payroll specialist",
            "tax specialist", "audit", "financial planner"
        ],
        "description_keywords": [
            "financial reporting", "gaap", "ifrs", "general ledger",
            "reconciliation", "budgeting", "forecasting", "variance analysis",
            "quickbooks", "netsuite", "financial statements", "sox compliance",
            "month-end close", "accounts payable", "accounts receivable"
        ],
    },

    "Operations / Warehouse / Logistics": {
        "title_keywords": [
            "warehouse associate", "warehouse manager", "operations manager",
            "logistics coordinator", "supply chain", "inventory manager",
            "fulfillment associate", "warehouse supervisor", "distribution center",
            "material handler", "forklift operator", "shipping receiving",
            "operations coordinator", "operations specialist"
        ],
        "description_keywords": [
            "warehouse operations", "inventory management", "shipping receiving",
            "fulfillment center", "logistics", "supply chain", "forklift",
            "picking packing", "order fulfillment", "inventory control",
            "distribution", "wms", "warehouse management", "freight"
        ],
    },

    "Healthcare / Medical": {
        "title_keywords": [
            "nurse", "physician", "medical assistant", "healthcare",
            "clinical", "pharmacist", "therapist", "medical technician",
            "registered nurse", "rn", "nurse practitioner", "physician assistant",
            "medical coder", "health informatics"
        ],
        "description_keywords": [
            "patient care", "clinical setting", "medical records", "hipaa",
            "healthcare facility", "hospital", "clinic", "medical software",
            "ehr", "electronic health records", "medical devices",
            "patient safety", "healthcare compliance"
        ],
    },

    "Education / Training": {
        "title_keywords": [
            "teacher", "instructor", "professor", "educator", "tutor",
            "curriculum developer", "instructional designer", "training specialist",
            "education coordinator", "academic advisor", "learning specialist"
        ],
        "description_keywords": [
            "curriculum development", "lesson planning", "student engagement",
            "educational technology", "classroom management", "pedagogy",
            "learning management system", "lms", "teaching", "training programs"
        ],
    },

    "Customer Support / Success": {
        "title_keywords": [
            "customer support", "customer success", "technical support",
            "support engineer", "support specialist", "customer service",
            "client success", "support manager", "help desk",
            "customer experience", "customer support representative"
        ],
        "description_keywords": [
            "customer satisfaction", "support tickets", "troubleshooting",
            "zendesk", "intercom", "customer inquiries", "issue resolution",
            "customer onboarding", "account management", "customer retention",
            "technical assistance", "live chat support"
        ],
    },

    "Security / Compliance": {
        "title_keywords": [
            "security engineer", "information security", "cybersecurity",
            "security analyst", "compliance officer", "security architect",
            "penetration tester", "security operations", "soc analyst"
        ],
        "description_keywords": [
            "security vulnerabilities", "penetration testing", "threat detection",
            "siem", "incident response", "security compliance", "iso 27001",
            "sox", "gdpr", "encryption", "firewall", "vulnerability assessment",
            "security protocols", "risk assessment"
        ],
    },
}


def classify_industry(job_title: str, job_description: str = "") -> str:
    """
    Classify job industry based on explicit rules.

    Uses keyword matching against job title (primary) and description (secondary).
    Returns 'unknown' if no clear classification can be made.

    Args:
        job_title: Job title (required)
        job_description: Job description (optional but recommended)

    Returns:
        Industry name or 'unknown'
    """
    if not job_title:
        logger.warning("Cannot classify job without title")
        return "unknown"

    title_lower = job_title.lower()
    desc_lower = job_description.lower() if job_description else ""

    # Track industry scores
    industry_scores: Dict[str, int] = {}

    for industry, rules in INDUSTRY_RULES.items():
        score = 0

        # Check title keywords (weighted higher)
        for keyword in rules.get("title_keywords", []):
            if keyword.lower() in title_lower:
                score += 10  # Strong signal from title
                break  # One title match is enough

        # Check description keywords (supporting evidence)
        desc_keywords = rules.get("description_keywords", [])
        if desc_keywords and desc_lower:
            matched_desc_keywords = sum(
                1 for keyword in desc_keywords
                if keyword.lower() in desc_lower
            )
            # Each description keyword adds 1 point, max 5
            score += min(matched_desc_keywords, 5)

        if score > 0:
            industry_scores[industry] = score

    # Return industry with highest score, or 'unknown' if no matches
    if not industry_scores:
        logger.info(f"No industry classification for: {job_title[:50]}")
        return "unknown"

    best_industry = max(industry_scores, key=industry_scores.get)
    best_score = industry_scores[best_industry]

    # Require minimum score threshold (at least one title match or strong desc evidence)
    if best_score < 10:
        logger.info(f"Industry classification uncertain for: {job_title[:50]} (score={best_score})")
        return "unknown"

    logger.debug(f"Classified '{job_title[:50]}' as '{best_industry}' (score={best_score})")
    return best_industry


def get_supported_industries() -> Set[str]:
    """
    Get list of industries that can be classified.

    Returns:
        Set of industry names
    """
    return set(INDUSTRY_RULES.keys())


def validate_industry(industry: Optional[str]) -> bool:
    """
    Validate that an industry is recognized.

    Args:
        industry: Industry string to validate

    Returns:
        True if valid (including 'unknown'), False otherwise
    """
    if not industry:
        return False

    return industry in INDUSTRY_RULES or industry == "unknown"
