from datetime import date, datetime
from decimal import Decimal
from uuid import UUID as PyUUID
from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, Integer, Numeric, Text, UniqueConstraint, Index, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from app.db.base import Base


class P3AdvisorySignal(Base):
    __tablename__ = "p3_advisory_signal"

    id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    resume_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    job_posting_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    signal_type: Mapped[str] = mapped_column(Text, nullable=False)
    signal_payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    confidence_score: Mapped[Decimal] = mapped_column(
        Numeric(5, 4),
        CheckConstraint("confidence_score BETWEEN 0 AND 1"),
        nullable=False,
    )
    model_version: Mapped[str] = mapped_column(Text, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        Index("idx_p3_signal_resume_job", "resume_id", "job_posting_id"),
        Index("idx_p3_signal_active", "is_active"),
    )


class P3AdvisoryBudget(Base):
    __tablename__ = "p3_advisory_budget"

    id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    resume_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    budget_day: Mapped[date] = mapped_column(Date, nullable=False)
    max_advisories: Mapped[int] = mapped_column(Integer, nullable=False)
    used_advisories: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("resume_id", "budget_day"),
        Index("idx_p3_budget_day", "budget_day"),
    )


class P3AdvisoryCache(Base):
    __tablename__ = "p3_advisory_cache"

    id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    cache_key: Mapped[str] = mapped_column(Text, nullable=False)
    signal_id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("cache_key"),
        Index("idx_p3_cache_signal", "signal_id"),
    )


class P3FeatureState(Base):
    __tablename__ = "p3_feature_state"

    feature_name: Mapped[str] = mapped_column(Text, primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    rollout_percent: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint("rollout_percent BETWEEN 0 AND 100"),
    )
