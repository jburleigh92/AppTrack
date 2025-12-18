import logging
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.dependencies.database import get_db
from app.db.models.resume import Resume, ResumeData

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/discover")
def discover_jobs(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    """
    Discover jobs based on active resume skills.

    Returns a list of job opportunities matched to the user's resume.
    Current implementation returns curated static jobs for v1.
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

    # Static job listings (v1 implementation)
    # In production, this would integrate with external APIs
    all_jobs = [
        {
            "title": "Senior Backend Engineer",
            "company": "TechCorp",
            "url": "https://jobs.techcorp.example/backend-engineer",
            "location": "Remote",
            "required_skills": ["Python", "FastAPI", "PostgreSQL", "Docker"],
            "description": "Build scalable backend services"
        },
        {
            "title": "Full Stack Developer",
            "company": "StartupXYZ",
            "url": "https://careers.startupxyz.example/fullstack",
            "location": "San Francisco, CA",
            "required_skills": ["Python", "React", "PostgreSQL", "AWS"],
            "description": "Work on both frontend and backend systems"
        },
        {
            "title": "DevOps Engineer",
            "company": "CloudSystems Inc",
            "url": "https://cloudsystems.example/careers/devops",
            "location": "Remote",
            "required_skills": ["Docker", "Kubernetes", "AWS", "CI/CD", "Python"],
            "description": "Manage cloud infrastructure and deployment pipelines"
        },
        {
            "title": "Data Engineer",
            "company": "DataFlow",
            "url": "https://dataflow.example/jobs/data-engineer",
            "location": "New York, NY",
            "required_skills": ["Python", "SQL", "PostgreSQL", "Airflow"],
            "description": "Build data pipelines and warehouses"
        },
        {
            "title": "Machine Learning Engineer",
            "company": "AI Innovations",
            "url": "https://aiinnovations.example/ml-engineer",
            "location": "Remote",
            "required_skills": ["Python", "Machine Learning", "TensorFlow", "PyTorch"],
            "description": "Develop and deploy ML models"
        },
        {
            "title": "Frontend Developer",
            "company": "DesignFirst",
            "url": "https://designfirst.example/frontend-dev",
            "location": "Austin, TX",
            "required_skills": ["JavaScript", "React", "TypeScript", "CSS"],
            "description": "Create beautiful user interfaces"
        },
        {
            "title": "API Developer",
            "company": "Integration Hub",
            "url": "https://integrationhub.example/api-dev",
            "location": "Remote",
            "required_skills": ["Python", "FastAPI", "REST", "GraphQL"],
            "description": "Design and implement RESTful APIs"
        },
        {
            "title": "Cloud Architect",
            "company": "Enterprise Solutions",
            "url": "https://enterprisesolutions.example/cloud-architect",
            "location": "Seattle, WA",
            "required_skills": ["AWS", "Azure", "GCP", "Terraform", "Docker"],
            "description": "Design cloud infrastructure for enterprise clients"
        }
    ]

    # Match jobs to user skills
    matched_jobs = []

    for job in all_jobs:
        # Calculate skill match
        job_skills = set(job["required_skills"])
        user_skills_set = set(user_skills)
        matched_skills = job_skills.intersection(user_skills_set)

        # Only include jobs with at least one skill match
        if matched_skills:
            match_count = len(matched_skills)
            match_percentage = int((match_count / len(job_skills)) * 100) if job_skills else 0

            matched_jobs.append({
                "title": job["title"],
                "company": job["company"],
                "url": job["url"],
                "location": job["location"],
                "match_reason": ", ".join(sorted(matched_skills)),
                "match_percentage": match_percentage,
                "match_count": match_count,
                "description": job["description"]
            })

    # Sort by match percentage (highest first)
    matched_jobs.sort(key=lambda x: (x["match_percentage"], x["match_count"]), reverse=True)

    logger.info(
        "Job discovery completed",
        extra={
            "resume_id": str(resume.id),
            "user_skills_count": len(user_skills),
            "matched_jobs_count": len(matched_jobs)
        }
    )

    return matched_jobs
