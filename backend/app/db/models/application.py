from datetime import datetime
from typing import Optional
from uuid import UUID as PyUUID, uuid4
from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, Index, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func, text, desc
from app.db.base import Base

class Application(Base):
    __tablename__ = "applications"
    
    id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    job_title: Mapped[str] = mapped_column(String(255), nullable=False)
    job_posting_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    application_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="applied", nullable=False)
    job_board_source: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    analysis_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    posting_id: Mapped[Optional[PyUUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("job_postings.id", ondelete="SET NULL"),
        nullable=True
    )

    analysis_id: Mapped[Optional[PyUUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("analysis_results.id", ondelete="SET NULL"),
        nullable=True
    )

    resume_id: Mapped[Optional[PyUUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("resumes.id", ondelete="SET NULL"),
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    
    posting = relationship("JobPosting", foreign_keys=[posting_id], back_populates="applications")
    analysis = relationship("AnalysisResult", foreign_keys=[analysis_id], uselist=False)
    resume = relationship("Resume", foreign_keys=[resume_id])
    timeline_events = relationship("TimelineEvent", back_populates="application", cascade="all, delete-orphan")
    scraper_jobs = relationship("ScraperQueue", back_populates="application", cascade="all, delete-orphan")
    analysis_jobs = relationship("AnalysisQueue", back_populates="application", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_applications_analysis_id", "analysis_id"),
        Index("idx_applications_resume_id", "resume_id"),
        Index("idx_applications_company_name", "company_name", postgresql_where=text("is_deleted = false")),
        Index(
            "idx_applications_created_at",
            desc("created_at"),
            postgresql_where=text("is_deleted = false"),
        ),
        Index(
            "idx_applications_needs_review",
            "needs_review",
            postgresql_where=text("needs_review = true AND is_deleted = false"),
        ),
        Index("idx_applications_posting_id", "posting_id"),
        Index("idx_applications_status", "status", postgresql_where=text("is_deleted = false")),
        Index(
            "idx_applications_search_gin",
            text("to_tsvector('english', company_name || ' ' || job_title || ' ' || COALESCE(notes, ''))"),
            postgresql_using="gin",
        ),
    )
