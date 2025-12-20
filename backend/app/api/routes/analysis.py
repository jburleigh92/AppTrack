import logging
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.dependencies.database import get_db
from app.db.models.application import Application
from app.db.models.analysis import AnalysisResult
from app.db.models.queue import AnalysisQueue
from app.schemas.analysis import (
    AnalysisResponse,
    AnalysisJobEnqueueRequest,
    AnalysisJobEnqueueResponse
)
from app.services.advisory.exposure import get_advisory_envelope

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/{application_id}/analysis/run", response_model=AnalysisJobEnqueueResponse, status_code=202)
def trigger_analysis(
    application_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Trigger AI analysis for an application.

    Enqueues the analysis job for background processing.
    Validates all prerequisites before enqueuing.
    """
    try:
        # Validate application exists
        application = db.query(Application).filter(
            Application.id == application_id,
            Application.is_deleted == False
        ).first()

        if not application:
            raise HTTPException(status_code=404, detail="Application not found")

        # Check if application needs manual review
        if application.needs_review:
            raise HTTPException(
                status_code=422,
                detail="Cannot analyze: application marked for review. Complete manual review first, then retry analysis."
            )

        # Check if job posting exists
        if not application.posting_id:
            raise HTTPException(
                status_code=422,
                detail="Cannot analyze: job posting not linked. Wait for scraping to complete, then try again."
            )

        # Validate job posting extraction is complete
        from app.db.models.job_posting import JobPosting
        from app.db.models.resume import Resume, ResumeData

        job_posting = db.query(JobPosting).filter(
            JobPosting.id == application.posting_id
        ).first()

        if not job_posting:
            raise HTTPException(
                status_code=422,
                detail="Cannot analyze: job posting not found. Wait for scraping to complete, then try again."
            )

        if not job_posting.extraction_complete:
            raise HTTPException(
                status_code=422,
                detail="Cannot analyze: job posting still being scraped. Wait a moment and try again."
            )

        # Validate job description exists and is substantial
        if not job_posting.description or len(job_posting.description.strip()) < 50:
            raise HTTPException(
                status_code=422,
                detail="Cannot analyze: job description too short or missing. Job posting may need manual review."
            )

        # Validate active resume exists
        active_resume = db.query(Resume).filter(Resume.is_active == True).first()
        if not active_resume:
            raise HTTPException(
                status_code=422,
                detail="Cannot analyze: no active resume found. Upload a resume first."
            )

        # Validate resume data exists and has skills
        resume_data = db.query(ResumeData).filter(
            ResumeData.resume_id == active_resume.id
        ).first()

        if not resume_data or not resume_data.extraction_complete:
            raise HTTPException(
                status_code=422,
                detail="Cannot analyze: resume parsing not complete. Wait for resume processing to finish."
            )

        if not resume_data.skills or len(resume_data.skills) == 0:
            raise HTTPException(
                status_code=422,
                detail="Cannot analyze: no skills found in resume. Upload a resume with skills listed, or add skills manually."
            )

        # Create analysis queue job
        analysis_job = AnalysisQueue(
            application_id=application_id,
            priority=0,
            status="pending",
            attempts=0,
            max_attempts=3
        )
        
        db.add(analysis_job)
        db.commit()
        db.refresh(analysis_job)
        
        logger.info(
            f"Analysis job enqueued",
            extra={
                "job_id": str(analysis_job.id),
                "application_id": str(application_id)
            }
        )
        
        return AnalysisJobEnqueueResponse(
            job_id=analysis_job.id,
            status="queued"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to enqueue analysis job: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Failed to enqueue analysis job"
        )


@router.get("/{application_id}/analysis", response_model=AnalysisResponse)
def get_analysis(
    application_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get the latest analysis result for an application.
    """
    try:
        # Validate application exists
        application = db.query(Application).filter(
            Application.id == application_id,
            Application.is_deleted == False
        ).first()
        
        if not application:
            raise HTTPException(status_code=404, detail="Application not found")
        
        # Get analysis via analysis_id
        if not application.analysis_id:
            raise HTTPException(
                status_code=404,
                detail="No analysis found for this application"
            )
        
        analysis = db.query(AnalysisResult).filter(
            AnalysisResult.id == application.analysis_id
        ).first()
        
        if not analysis:
            raise HTTPException(
                status_code=404,
                detail="Analysis record not found"
            )
        
        advisory_payload = None
        try:
            advisory_payload = get_advisory_envelope(
                db,
                resume_id=analysis.resume_id,
                job_posting_id=analysis.job_posting_id,
            )
        except Exception:
            logger.debug(
                "WS5: advisory retrieval failed; continuing without advisory",
                exc_info=True,
            )

        return AnalysisResponse(
            id=analysis.id,
            application_id=analysis.application_id,
            resume_id=analysis.resume_id,
            job_posting_id=analysis.job_posting_id,
            match_score=analysis.match_score,
            qualifications_met=analysis.qualifications_met if isinstance(analysis.qualifications_met, list) else [],
            qualifications_missing=analysis.qualifications_missing if isinstance(analysis.qualifications_missing, list) else [],
            suggestions=analysis.suggestions if isinstance(analysis.suggestions, list) else [],
            llm_provider=analysis.llm_provider,
            llm_model=analysis.llm_model,
            analysis_metadata=analysis.analysis_metadata,
            created_at=analysis.created_at,
            advisory=advisory_payload,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get analysis: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve analysis"
        )
