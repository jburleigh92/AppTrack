from datetime import date, datetime
from typing import Optional
from uuid import uuid4
from sqlalchemy import String, Text, Boolean, Date, ForeignKey, Index, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin, SoftDeleteMixin


class Application(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "applications"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    job_title: Mapped[str] = mapped_column(String(255), nullable=False)
    job_posting_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    application_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="applied", nullable=False)
    
    source: Mapped[str] = mapped_column(String(50), default="manual", nullable=False)
    job_board_source: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    analysis_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    posting_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("job_postings.id", ondelete="SET NULL"),
        nullable=True
    )
    analysis_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("analysis_results.id", ondelete="SET NULL"),
        nullable=True
    )
    
    posting = relationship("JobPosting", foreign_keys=[posting_id], back_populates="applications")
    analysis = relationship("AnalysisResult", foreign_keys=[analysis_id], back_populates="application_ref")
    timeline_events = relationship("TimelineEvent", back_populates="application", cascade="all, delete-orphan")
    scraper_jobs = relationship("ScraperQueue", back_populates="application", cascade="all, delete-orphan")
    analysis_jobs = relationship("AnalysisQueue", back_populates="application", cascade="all, delete-orphan")
    
    __table_args__ = (
        CheckConstraint(
            "status IN ('applied', 'screening', 'interview', 'offer', 'rejected', 'withdrawn')",
            name="chk_status"
        ),
        CheckConstraint(
            "source IN ('browser', 'email', 'manual')",
            name="chk_source"
        ),
        CheckConstraint(
            "length(notes) <= 10000",
            name="chk_notes_length"
        ),
        Index("idx_applications_posting_id", "posting_id"),
        Index("idx_applications_analysis_id", "analysis_id"),
        Index("idx_applications_status", "status", postgresql_where="is_deleted = false"),
        Index("idx_applications_created_at", "created_at", postgresql_ops={"created_at": "DESC"}, postgresql_where="is_deleted = false"),
        Index("idx_applications_company_name", "company_name", postgresql_where="is_deleted = false"),
        Index("idx_applications_needs_review", "needs_review", postgresql_where="needs_review = true AND is_deleted = false"),
    )
