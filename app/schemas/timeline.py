from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID
from pydantic import BaseModel


class TimelineEventBase(BaseModel):
    """Base schema for timeline events."""
    event_type: str
    event_data: Dict[str, Any] = {}
    occurred_at: datetime = None
    
    class Config:
        from_attributes = True


class TimelineEventResponse(BaseModel):
    id: UUID
    application_id: UUID
    event_type: str
    event_data: Dict[str, Any]
    occurred_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class TimelineEventListResponse(BaseModel):
    """Response for listing timeline events."""
    events: List[TimelineEventResponse]
    total: int
    
    class Config:
        from_attributes = True


class TimelineEventCreate(BaseModel):
    application_id: UUID
    event_type: str
    description: Optional[str] = None
    event_data: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True
