from datetime import datetime
from typing import Optional
from uuid import uuid4
from sqlalchemy import String, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class TimelineEvent(Base):
    __tablename__ = "timeline_events"

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
    
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    event_data: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)
    
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=datetime.utcnow)
    
    application = relationship("Application", back_populates="timeline_events")
    
    __table_args__ = (
        Index("idx_timeline_events_application_id", "application_id"),
        Index("idx_timeline_events_occurred_at", "occurred_at", postgresql_ops={"occurred_at": "DESC"}),
        Index("idx_timeline_events_type", "event_type"),
    )
