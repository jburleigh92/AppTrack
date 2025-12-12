from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4
from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, Index, String, Text, ForeignKey, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class Application(Base):
    __tablename__ = "applications"
    
    id: Mapped[uuid4] = mapped_column(Uuid, primary_key=True, default=uuid4)
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
    
    posting_id: Mapped[Optional[uuid4]] = mapped_column(
        Uuid,
        ForeignKey("job_postings.id", ondelete="SET NULL"),
        nullable=True
    )
    
    analysis_id: Mapped[Optional[uuid4]] = mapped_column(
        Uuid,
        ForeignKey("analysis_results.id", ondelete="SET NULL"),
        nullable=True
    )
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    
    posting = relationship("JobPosting", foreign_keys=[posting_id], back_populates="applications")
    analysis = relationship("AnalysisResult", foreign_keys=[analysis_id], uselist=False)
    timeline_events = relationship("TimelineEvent", back_populates="application", cascade="all, delete-orphan")
    scraper_jobs = relationship("ScraperQueue", back_populates="application", cascade="all, delete-orphan")
    analysis_jobs = relationship("AnalysisQueue", back_populates="application", cascade="all, delete-orphan")
