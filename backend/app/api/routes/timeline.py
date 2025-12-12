import logging
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.dependencies.database import get_db
from app.schemas.timeline import (
    TimelineEventBase,
    TimelineEventResponse,
    TimelineEventListResponse
)
from app.services.timeline_service import (
    create_event_sync,
    list_events_for_application_sync
)
from app.db.models.application import Application

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/{application_id}/timeline", response_model=TimelineEventListResponse)
def get_application_timeline(
    application_id: UUID,
    limit: Optional[int] = 100,
    db: Session = Depends(get_db)
):
    """
    Get timeline events for an application.
    
    Returns events in chronological order (oldest first).
    """
    # Verify application exists
    application = db.query(Application).filter(
        Application.id == application_id,
        Application.is_deleted == False
    ).first()
    
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    
    # Get timeline events
    events = list_events_for_application_sync(db, application_id, limit=limit)
    
    return TimelineEventListResponse(
        events=events,
        total=len(events)
    )

@router.post("/{application_id}/timeline", response_model=TimelineEventResponse, status_code=201)
def create_timeline_event(
    application_id: UUID,
    event: TimelineEventBase,
    db: Session = Depends(get_db)
):
    """
    Create a timeline event manually (for internal/admin use).
    
    Most timeline events are created automatically by the system,
    but this endpoint allows manual event creation.
    """
    # Verify application exists
    application = db.query(Application).filter(
        Application.id == application_id,
        Application.is_deleted == False
    ).first()
    
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    
    # Create event
    created_event = create_event_sync(
        db=db,
        application_id=application_id,
        event_type=event.event_type,
        event_data=event.event_data,
        occurred_at=event.occurred_at
    )
    
    if not created_event:
        raise HTTPException(
            status_code=500,
            detail="Failed to create timeline event"
        )
    
    return created_event
