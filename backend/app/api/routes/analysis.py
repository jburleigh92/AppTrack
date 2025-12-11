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
    """
    try:
        # Validate application exists
        application = db.query(Application).filter(
            Application.id == application_id,
            Application.is_deleted == False
        ).first()
        
        if not application:
            raise HTTPException(status_code=404, detail="Application not found")
        
        # Check if job posting exists
        if not application.posting_id:
            raise HTTPException(
                status_code=400,
                detail="Application has no linked job posting. Scrape the posting first."
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
            created_at=analysis.created_at
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get analysis: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve analysis"
        )
