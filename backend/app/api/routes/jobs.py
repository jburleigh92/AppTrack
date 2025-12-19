import logging
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.dependencies.database import get_db
from app.db.models.resume import Resume, ResumeData
from app.services.scraping.greenhouse_api import fetch_all_greenhouse_jobs

router = APIRouter()
logger = logging.getLogger(__name__)

# Target companies to fetch jobs from (Greenhouse job boards)
# These are popular tech companies with public Greenhouse boards
TARGET_COMPANIES = [
    "airbnb",
    "stripe",
    "shopify",
    "coinbase",
    "dropbox",
    "instacart",
    "robinhood",
    "doordash",
    "gitlab",
    "notion",
]


def _extract_skills_from_text(text: str, known_skills: List[str]) -> List[str]:
    """
    Extract skills from job description text by matching against known skills.
    Case-insensitive matching.
    """
    if not text:
        return []

    text_lower = text.lower()
    found_skills = []

    for skill in known_skills:
        if skill.lower() in text_lower:
            found_skills.append(skill)

    return found_skills


@router.get("/discover")
def discover_jobs(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    """
    Discover jobs from Greenhouse job boards based on active resume skills.

    Fetches available jobs from configured companies' Greenhouse boards
    and matches them against the user's resume.
    """
    # Get active resume
    resume = db.query(Resume).filter(Resume.is_active == True).first()

    if not resume:
        raise HTTPException(
            status_code=404,
            detail="No active resume found. Please upload a resume first."
        )

    # Get resume data
    resume_data = db.query(ResumeData).filter(
        ResumeData.resume_id == resume.id
    ).first()

    if not resume_data or not resume_data.extraction_complete:
        raise HTTPException(
            status_code=400,
            detail="Resume parsing not complete"
        )

    # Extract skills from resume
    user_skills = resume_data.skills if resume_data.skills else []
    user_skills_set = set(skill.lower() for skill in user_skills) if user_skills else set()

    # Fetch jobs from all target companies
    all_jobs = []
    for company_slug in TARGET_COMPANIES:
        company_jobs = fetch_all_greenhouse_jobs(company_slug)
        all_jobs.extend(company_jobs)

    logger.info(f"Fetched {len(all_jobs)} total jobs from {len(TARGET_COMPANIES)} companies")

    if not all_jobs:
        logger.info(
            "Job discovery returned no jobs from Greenhouse",
            extra={
                "resume_id": str(resume.id),
                "user_skills_count": len(user_skills),
                "companies_checked": len(TARGET_COMPANIES)
            }
        )
        return []

    # Match jobs to user skills
    matched_jobs = []

    for job in all_jobs:
        # Extract job details from Greenhouse API response
        job_id = job.get("id")
        job_title = job.get("title", "")
        company_name = job.get("company_name", "Unknown Company")
        location = job.get("location", {}).get("name", "Location not specified")
        absolute_url = job.get("absolute_url", "")

        # Get job content for skill matching
        job_content = job.get("content", "")

        # Calculate skill match
        if job_content and user_skills:
            job_skills = _extract_skills_from_text(job_content, user_skills)

            if job_skills:
                job_skills_set = set(skill.lower() for skill in job_skills)
                matched_skills = job_skills_set.intersection(user_skills_set)

                if matched_skills:
                    match_count = len(matched_skills)
                    match_percentage = int((match_count / len(user_skills_set)) * 100)
                    match_reason = ", ".join(sorted(skill.title() for skill in matched_skills))

                    # Only include jobs with at least one skill match
                    matched_jobs.append({
                        "id": str(job_id),
                        "title": job_title,
                        "company": company_name,
                        "url": absolute_url,
                        "location": location,
                        "match_reason": match_reason,
                        "match_percentage": match_percentage,
                        "description": job_content[:200] + "..." if len(job_content) > 200 else job_content,
                        "source": "greenhouse"
                    })

    # Sort by match percentage (highest first)
    matched_jobs.sort(key=lambda x: x["match_percentage"], reverse=True)

    logger.info(
        "Job discovery completed",
        extra={
            "resume_id": str(resume.id),
            "user_skills_count": len(user_skills),
            "total_greenhouse_jobs": len(all_jobs),
            "matched_jobs_count": len(matched_jobs)
        }
    )

    return matched_jobs
