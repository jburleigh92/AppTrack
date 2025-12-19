import logging
from uuid import UUID
from typing import Optional
from sqlalchemy.orm import Session
from datetime import datetime
from app.db.models.application import Application
from app.db.models.job_posting import JobPosting
from app.db.models.resume import Resume, ResumeData
from app.db.models.analysis import AnalysisResult
from app.services.analysis.llm_client import LLMClient
from app.services.timeline_service import log_analysis_completed_sync, log_analysis_failed_sync

logger = logging.getLogger(__name__)


class AnalysisError(Exception):
    """Base exception for analysis errors."""
    pass


class MissingDataError(AnalysisError):
    """Raised when required data is missing."""
    pass


class LLMError(AnalysisError):
    """Raised when LLM call fails."""
    pass


class AnalysisService:
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client
    
    async def run_analysis_for_application(
        self,
        db: Session,
        application_id: UUID
    ) -> AnalysisResult:
        """
        Run AI analysis for an application.
        
        Steps:
        1. Load application
        2. Validate job posting exists
        3. Load active resume
        4. Call LLM
        5. Persist results
        6. Update application
        7. Emit timeline event
        
        Raises:
            MissingDataError: If required data is missing
            LLMError: If LLM call fails
        """
        
        # Step 1: Load application
        application = db.query(Application).filter(
            Application.id == application_id,
            Application.is_deleted == False
        ).first()
        
        if not application:
            raise MissingDataError(f"Application {application_id} not found")
        
        # Step 2: Validate job posting
        if not application.posting_id:
            raise MissingDataError("Application has no linked job posting")
        
        job_posting = db.query(JobPosting).filter(
            JobPosting.id == application.posting_id
        ).first()
        
        if not job_posting:
            raise MissingDataError("Job posting not found")
        
        if not job_posting.description:
            raise MissingDataError("Job posting has no description")
        
        # Step 3: Load active resume
        active_resume = db.query(Resume).filter(
            Resume.is_active == True
        ).first()
        
        if not active_resume:
            raise MissingDataError("No active resume found")
        
        resume_data = db.query(ResumeData).filter(
            ResumeData.resume_id == active_resume.id
        ).first()
        
        if not resume_data:
            raise MissingDataError("Resume data not found")

        # Get intent profile for context-aware analysis
        intent_profile_data = None
        if hasattr(resume_data, 'intent_profile') and resume_data.intent_profile:
            intent_profile_data = resume_data.intent_profile

        # Step 4: Call LLM
        logger.info(
            f"Running analysis for application {application_id}",
            extra={
                "application_id": str(application_id),
                "job_posting_id": str(job_posting.id),
                "resume_id": str(active_resume.id),
                "has_intent_profile": intent_profile_data is not None
            }
        )

        try:
            result = await self.llm_client.analyze_job_vs_resume(
                job_description=job_posting.description,
                job_requirements=job_posting.requirements,
                resume_summary=resume_data.summary,
                resume_skills=resume_data.skills if isinstance(resume_data.skills, list) else [],
                resume_experience=resume_data.experience if isinstance(resume_data.experience, list) else [],
                resume_education=resume_data.education if isinstance(resume_data.education, list) else [],
                intent_profile=intent_profile_data
            )
        except Exception as e:
            logger.error(f"LLM call failed for application {application_id}", exc_info=True)
            raise LLMError(f"LLM analysis failed: {str(e)}")
        
        # Step 5: Persist results
        analysis = AnalysisResult(
            application_id=application_id,
            resume_id=active_resume.id,
            job_posting_id=job_posting.id,
            match_score=result["match_score"],
            qualifications_met=result["matched_qualifications"],
            qualifications_missing=result["missing_qualifications"],
            suggestions=result["skill_suggestions"],
            llm_provider=self.llm_client.provider,
            llm_model=result["model_used"],
            analysis_metadata={
                "tokens_used": result.get("tokens_used")
            }
        )
        
        db.add(analysis)
        db.flush()
        
        # Step 6: Update application
        application.analysis_id = analysis.id
        application.analysis_completed = True
        
        # Step 7: Emit timeline event
        log_analysis_completed_sync(
            db=db,
            application_id=application_id,
            analysis_id=analysis.id,
            match_score=result["match_score"]
        )
        
        db.commit()
        db.refresh(analysis)
        
        logger.info(
            f"Analysis completed for application {application_id}",
            extra={
                "application_id": str(application_id),
                "analysis_id": str(analysis.id),
                "match_score": result["match_score"]
            }
        )
        
        return analysis
