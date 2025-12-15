from datetime import datetime
from typing import Optional
from uuid import uuid4
from sqlalchemy import String, Text, Integer, ForeignKey, Index, CheckConstraint, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin


class ScraperQueue(Base, TimestampMixin):
    __tablename__ = "scraper_queue"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )

    application_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=True
    )
    
    url: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
    
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    retry_after: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    processing_metadata: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    application = relationship("Application", back_populates="scraper_jobs")
    
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'processing', 'completed', 'failed')",
            name="chk_scraper_status"
        ),
        CheckConstraint(
            "attempts >= 0",
            name="chk_scraper_attempts"
        ),
        Index("idx_scraper_queue_application_id", "application_id"),
        Index("idx_scraper_queue_pending", "priority", "created_at", postgresql_ops={"priority": "DESC"}, postgresql_where="status = 'pending'"),
        Index("idx_scraper_queue_stuck", "started_at", postgresql_where="status = 'processing'"),
    )


class ParserQueue(Base, TimestampMixin):
    __tablename__ = "parser_queue"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    
    resume_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("resumes.id", ondelete="CASCADE"),
        nullable=False
    )
    
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
    
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    processing_metadata: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    resume = relationship("Resume", back_populates="parser_jobs")
    
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'processing', 'complete', 'failed')",
            name="chk_parser_status"
        ),
        CheckConstraint(
            "attempts >= 0",
            name="chk_parser_attempts"
        ),
        Index("idx_parser_queue_resume_id", "resume_id"),
        Index("idx_parser_queue_pending", "created_at", postgresql_where="status = 'pending'"),
        Index("idx_parser_queue_stuck", "started_at", postgresql_where="status = 'processing'"),
    )


class AnalysisQueue(Base, TimestampMixin):
    __tablename__ = "analysis_queue"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    
    application_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False
    )
    
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
    
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    retry_after: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    processing_metadata: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    application = relationship("Application", back_populates="analysis_jobs")
    
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'processing', 'complete', 'failed')",
            name="chk_analysis_status"
        ),
        CheckConstraint(
            "attempts >= 0",
            name="chk_analysis_attempts"
        ),
        Index("idx_analysis_queue_application_id", "application_id"),
        Index("idx_analysis_queue_pending", "priority", "created_at", postgresql_ops={"priority": "DESC"}, postgresql_where="status = 'pending'"),
        Index("idx_analysis_queue_stuck", "started_at", postgresql_where="status = 'processing'"),
    )
