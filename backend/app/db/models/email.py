from datetime import datetime
from typing import Optional
from uuid import uuid4
from sqlalchemy import String, ForeignKey, Index, UniqueConstraint, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class ProcessedEmailUID(Base):
    __tablename__ = "processed_email_uids"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    
    email_uid: Mapped[str] = mapped_column(String(255), nullable=False)
    email_account: Mapped[str] = mapped_column(String(255), nullable=False)
    
    application_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("applications.id", ondelete="SET NULL"),
        nullable=True
    )
    
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint("email_uid", name="uq_email_uid"),
        Index("idx_processed_email_uids_application_id", "application_id"),
        Index("idx_processed_email_uids_processed_at", "processed_at"),
    )
