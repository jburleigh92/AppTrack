from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Base event model used for event creation via API
# ---------------------------------------------------------------------------
class TimelineEventBase(BaseModel):
    event_type: str
    event_data: Optional[Dict[str, Any]] = None
    occurred_at: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Response model for a single event
# ---------------------------------------------------------------------------
class TimelineEventResponse(BaseModel):
    id: UUID
    application_id: UUID
    event_type: str
    event_data: Dict[str, Any]
    occurred_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Wrapper response used by GET /{id}/timeline
# ---------------------------------------------------------------------------
class TimelineEventListResponse(BaseModel):
    events: List[TimelineEventResponse]
    total: int
