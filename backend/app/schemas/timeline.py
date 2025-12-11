from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel


class TimelineEventResponse(BaseModel):
    id: UUID
    application_id: UUID
    event_type: str
    event_data: Dict[str, Any]
    occurred_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class TimelineEventCreate(BaseModel):
    application_id: UUID
    event_type: str
    description: Optional[str] = None
    event_data: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True
