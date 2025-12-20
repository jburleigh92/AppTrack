from datetime import datetime
from typing import Optional
from uuid import uuid4
from sqlalchemy import String, Text, Integer, Boolean, ForeignKey, Index, CheckConstraint, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin


class Resume(Base, TimestampMixin):
    __tablename__ = "resumes"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    
    status: Mapped[str] = mapped_column(String(50), default="uploaded", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    uploaded_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)
    
    resume_data = relationship("ResumeData", back_populates="resume", uselist=False, cascade="all, delete-orphan")
    parser_jobs = relationship("ParserQueue", back_populates="resume", cascade="all, delete-orphan")
    analyses = relationship("AnalysisResult", back_populates="resume")
    
    __table_args__ = (
        CheckConstraint(
            "status IN ('uploaded', 'processing', 'parsed', 'failed')",
            name="chk_resume_status"
        ),
        Index("idx_resumes_active", "is_active", unique=True, postgresql_where="is_active = true"),
    )


class ResumeData(Base, TimestampMixin):
    __tablename__ = "resume_data"

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
    
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    linkedin_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    skills: Mapped[dict] = mapped_column(JSONB, default=list, nullable=False)
    experience: Mapped[dict] = mapped_column(JSONB, default=list, nullable=False)
    education: Mapped[dict] = mapped_column(JSONB, default=list, nullable=False)
    certifications: Mapped[dict] = mapped_column(JSONB, default=list, nullable=False)
    
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    raw_text_other: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Career intent profile for job matching
    intent_profile: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    extraction_complete: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    resume = relationship("Resume", back_populates="resume_data")
    
    __table_args__ = (
        UniqueConstraint("resume_id", name="uq_resume_id"),
        Index("idx_resume_data_resume_id", "resume_id"),
        Index("idx_resume_data_skills", "skills", postgresql_using="gin"),
    )
