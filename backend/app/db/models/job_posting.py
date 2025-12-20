from datetime import datetime
from typing import Optional
from uuid import UUID as PyUUID, uuid4
from sqlalchemy import String, Text, Boolean, ForeignKey, Index, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.db.base import Base

class JobPosting(Base):
    __tablename__ = "job_postings"

    id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Core job details
    job_title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    requirements: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    salary_range: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    employment_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Ingestion metadata (for indexed jobs from Greenhouse, SerpAPI, etc.)
    source: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)  # 'greenhouse', 'serpapi', 'manual'
    external_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Apply link
    external_id: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, index=True)  # Source-specific ID for deduplication

    # Status flags
    extraction_complete: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships (for application tracking)
    applications = relationship("Application", foreign_keys="Application.posting_id", back_populates="posting")
    scraped_posting = relationship("ScrapedPosting", back_populates="job_posting", uselist=False)
    analyses = relationship("AnalysisResult", back_populates="job_posting")

    # Indexes for search performance
    __table_args__ = (
        Index("idx_job_postings_title_company", "job_title", "company_name"),
        Index("idx_job_postings_source_external_id", "source", "external_id", unique=True),
    )


class ScrapedPosting(Base):
    __tablename__ = "scraped_postings"

    id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    url: Mapped[str] = mapped_column(Text, nullable=False)
    html_content: Mapped[str] = mapped_column(Text, nullable=False)
    http_status_code: Mapped[int] = mapped_column(nullable=False)
    
    job_posting_id: Mapped[Optional[PyUUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("job_postings.id", ondelete="CASCADE"),
        nullable=True
    )

    scraped_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    
    job_posting = relationship("JobPosting", back_populates="scraped_posting")
    
    __table_args__ = (
        Index("idx_scraped_postings_job_posting_id", "job_posting_id"),
    )
