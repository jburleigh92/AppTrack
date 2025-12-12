from datetime import datetime
from typing import Optional
from uuid import uuid4
from sqlalchemy import String, Text, Boolean, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin


class JobPosting(Base, TimestampMixin):
    __tablename__ = "job_postings"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    
    url: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    company: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    requirements: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    salary_range: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    employment_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    source: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    extraction_complete: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    applications = relationship("Application", foreign_keys="Application.posting_id", back_populates="posting")
    scraped_posting = relationship("ScrapedPosting", back_populates="job_posting", uselist=False)
    analyses = relationship("AnalysisResult", back_populates="job_posting")


class ScrapedPosting(Base, TimestampMixin):
    __tablename__ = "scraped_postings"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    
    url: Mapped[str] = mapped_column(Text, nullable=False)
    html_content: Mapped[str] = mapped_column(Text, nullable=False)
    http_status_code: Mapped[int] = mapped_column(nullable=False)
    
    job_posting_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("job_postings.id", ondelete="CASCADE"),
        nullable=True
    )
    
    scraped_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)
    
    job_posting = relationship("JobPosting", back_populates="scraped_posting")
    
    __table_args__ = (
        Index("idx_scraped_postings_job_posting_id", "job_posting_id"),
    )
