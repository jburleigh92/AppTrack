from datetime import datetime
from typing import Optional
from uuid import UUID as PyUUID, uuid4
from sqlalchemy import String, Integer, ForeignKey, Index, CheckConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class AnalysisResult(Base):
    __tablename__ = "analysis_results"
    
    id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    application_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False
    )
    resume_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("resumes.id", ondelete="CASCADE"),
        nullable=False
    )
    job_posting_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("job_postings.id", ondelete="CASCADE"),
        nullable=False
    )
    
    match_score: Mapped[int] = mapped_column(Integer, nullable=False)
    qualifications_met: Mapped[dict] = mapped_column(JSONB, default=list, nullable=False)
    qualifications_missing: Mapped[dict] = mapped_column(JSONB, default=list, nullable=False)
    suggestions: Mapped[dict] = mapped_column(JSONB, default=list, nullable=False)
    
    llm_provider: Mapped[str] = mapped_column(String(50), nullable=False)
    llm_model: Mapped[str] = mapped_column(String(100), nullable=False)
    analysis_metadata: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)
    
    application = relationship("Application", foreign_keys=[application_id])
    resume = relationship("Resume", back_populates="analyses")
    job_posting = relationship("JobPosting", back_populates="analyses")
    
    __table_args__ = (
        CheckConstraint(
            "match_score >= 0 AND match_score <= 100",
            name="chk_match_score"
        ),
        Index("idx_analysis_results_application_id", "application_id"),
        Index("idx_analysis_results_resume_id", "resume_id"),
        Index("idx_analysis_results_job_posting_id", "job_posting_id"),
        Index("idx_analysis_results_qualifications", "qualifications_met", "qualifications_missing", postgresql_using="gin"),
    )
