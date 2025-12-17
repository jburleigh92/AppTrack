from datetime import datetime
from uuid import UUID as PyUUID, uuid4
from sqlalchemy import DateTime, String, ForeignKey, Index, desc
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.db.base import Base


class TimelineEvent(Base):
    __tablename__ = "timeline_events"

    id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    
    application_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False
    )
    
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    event_data: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    
    application = relationship("Application", back_populates="timeline_events")
    
    __table_args__ = (
        Index("idx_timeline_events_application_id", "application_id"),
        Index("idx_timeline_events_occurred_at", desc("occurred_at")),
        Index("idx_timeline_events_type", "event_type"),
    )
