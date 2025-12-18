import logging
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.api.dependencies.database import get_db
from app.db.models.resume import Resume, ResumeData
from app.db.models.application import Application
from app.db.models.job_posting import JobPosting
from app.db.models.analysis import AnalysisResult

router = APIRouter()
logger = logging.getLogger(__name__)


def _extract_skills_from_text(text: str, known_skills: List[str]) -> List[str]:
    """
    Extract skills from job requirements text by matching against known skills.
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
def discover_jobs(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Discover jobs based on active resume skills.

    Returns a list of job opportunities matched to the user's resume.
    Jobs are sourced from captured applications with scraped job postings.
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

    # Query all applications with extracted job postings
    # Join with JobPosting where extraction is complete
    # Left join with AnalysisResult to get match scores if available
    applications_with_postings = (
        db.query(Application, JobPosting, AnalysisResult)
        .join(JobPosting, Application.posting_id == JobPosting.id)
        .outerjoin(AnalysisResult, Application.analysis_id == AnalysisResult.id)
        .filter(
            and_(
                Application.is_deleted == False,
                JobPosting.extraction_complete == True
            )
        )
        .all()
    )

    # If no jobs found, return empty result with helpful message
    if not applications_with_postings:
        total_applications = db.query(Application).filter(Application.is_deleted == False).count()

        if total_applications == 0:
            message = "No jobs found. Capture job postings using the browser extension to see them here."
        else:
            message = f"{total_applications} job(s) captured but not yet scraped. Wait for scraping to complete."

        logger.info(
            "Job discovery returned empty results",
            extra={
                "resume_id": str(resume.id),
                "user_skills_count": len(user_skills),
                "total_applications": total_applications,
                "reason": "no_extracted_postings"
            }
        )

        return {
            "jobs": [],
            "message": message,
            "diagnostics": {
                "resume_skills_count": len(user_skills),
                "total_jobs_in_system": total_applications,
                "extracted_jobs_count": 0
            }
        }

    # Build matched jobs list
    matched_jobs = []

    for app, posting, analysis in applications_with_postings:
        # Prefer analysis match_score if available, otherwise calculate basic skill match
        if analysis and analysis.match_score is not None:
            match_percentage = analysis.match_score
            # Extract matched skills from qualifications_met
            matched_skills_list = analysis.qualifications_met if isinstance(analysis.qualifications_met, list) else []
            match_reason = ", ".join(matched_skills_list[:5]) if matched_skills_list else "LLM analysis"
        else:
            # Fallback: Calculate basic skill match from requirements text
            job_skills = _extract_skills_from_text(
                posting.requirements or posting.description or "",
                user_skills
            )

            if not job_skills or not user_skills:
                # No skills to match - include with 0% match but don't exclude
                match_percentage = 0
                match_reason = "No skills detected"
            else:
                job_skills_set = set(skill.lower() for skill in job_skills)
                matched_skills = job_skills_set.intersection(user_skills_set)

                if matched_skills:
                    match_percentage = int((len(matched_skills) / len(job_skills_set)) * 100)
                    # Capitalize matched skills for display
                    match_reason = ", ".join(sorted(skill.title() for skill in matched_skills))
                else:
                    match_percentage = 0
                    match_reason = "No matching skills"

        # Include all jobs (even 0% match) so users can see what they captured
        matched_jobs.append({
            "id": str(app.id),
            "title": posting.job_title or app.job_title,
            "company": posting.company_name or app.company_name,
            "url": app.job_posting_url,
            "location": posting.location or "Location not specified",
            "match_reason": match_reason,
            "match_percentage": match_percentage,
            "description": (posting.description[:200] + "...") if posting.description and len(posting.description) > 200 else (posting.description or "No description available"),
            "has_analysis": analysis is not None,
            "extraction_complete": posting.extraction_complete,
            "application_status": app.status
        })

    # Sort by match percentage (highest first), then by created_at (newest first)
    matched_jobs.sort(
        key=lambda x: (x["match_percentage"], x.get("id", "")),
        reverse=True
    )

    # Prepare diagnostic message
    if not matched_jobs:
        message = "No jobs match your resume skills."
    elif not user_skills:
        message = f"{len(matched_jobs)} job(s) found, but no skills detected in resume. Upload a resume with skills for better matching."
    else:
        high_match_count = len([j for j in matched_jobs if j["match_percentage"] >= 60])
        if high_match_count > 0:
            message = f"Found {high_match_count} high-match job(s) (60%+ match)"
        else:
            message = f"Found {len(matched_jobs)} job(s) with varying match levels"

    logger.info(
        "Job discovery completed",
        extra={
            "resume_id": str(resume.id),
            "user_skills_count": len(user_skills),
            "matched_jobs_count": len(matched_jobs),
            "jobs_with_analysis": len([j for j in matched_jobs if j["has_analysis"]])
        }
    )

    return {
        "jobs": matched_jobs,
        "message": message,
        "diagnostics": {
            "resume_skills_count": len(user_skills),
            "total_jobs_in_system": len(applications_with_postings),
            "extracted_jobs_count": len(applications_with_postings)
        }
    }
