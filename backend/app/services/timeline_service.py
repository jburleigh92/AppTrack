from datetime import datetime
from sqlalchemy.orm import Session
from app.db.models.timeline import TimelineEvent
from uuid import UUID
from typing import Optional


def record_event(
    db: Session,
    application_id: UUID,
    event_type: str,
    description: str,
    event_data: dict = None
) -> TimelineEvent:
    """Record a timeline event for an application."""
    event = TimelineEvent(
        application_id=application_id,
        event_type=event_type,
        event_data=event_data or {},
        occurred_at=datetime.utcnow()
    )
    
    db.add(event)
    db.commit()
    db.refresh(event)
    
    return event


def record_correlation_event(
    db: Session,
    application_id: UUID,
    message_id: str,
    strategy: str
):
    """Record email correlation event."""
    return record_event(
        db=db,
        application_id=application_id,
        event_type="email_correlated",
        description=f"Email {message_id} correlated using {strategy}",
        event_data={
            "message_id": message_id,
            "correlation_strategy": strategy
        }
    )


def record_application_created_event(
    db: Session,
    application_id: UUID,
    source: str
):
    """Record application creation event."""
    return record_event(
        db=db,
        application_id=application_id,
        event_type="application_created",
        description=f"Application created from {source}",
        event_data={
            "source": source
        }
    )


def record_posting_scraped_event(
    db: Session,
    application_id: UUID,
    url: str,
    partial: bool = False
):
    """Record job posting scrape event."""
    event_type = "scrape_partial_data" if partial else "posting_scraped"
    description = f"Job posting scraped from {url}"
    if partial:
        description += " (partial data)"
    
    return record_event(
        db=db,
        application_id=application_id,
        event_type=event_type,
        description=description,
        event_data={
            "url": url,
            "partial": partial
        }
    )


def record_scrape_failed_event(
    db: Session,
    application_id: UUID,
    url: str,
    error: str
):
    """Record scrape failure event."""
    return record_event(
        db=db,
        application_id=application_id,
        event_type="scrape_failed",
        description=f"Failed to scrape {url}: {error}",
        event_data={
            "url": url,
            "error": error
        }
    )


def log_analysis_completed(
    db: Session,
    application_id: UUID,
    analysis_id: UUID,
    match_score: int
):
    """Record analysis completion event."""
    return record_event(
        db=db,
        application_id=application_id,
        event_type="analysis_completed",
        description=f"AI analysis completed with match score {match_score}",
        event_data={
            "analysis_id": str(analysis_id),
            "match_score": match_score
        }
    )


def log_analysis_failed(
    db: Session,
    application_id: UUID,
    reason: str,
    details: Optional[str] = None
):
    """Record analysis failure event."""
    description = f"AI analysis failed: {reason}"
    if details:
        description += f" - {details}"
    
    return record_event(
        db=db,
        application_id=application_id,
        event_type="analysis_failed",
        description=description,
        event_data={
            "reason": reason,
            "details": details
        }
    )

# Backward compatibility wrapper
def log_application_created_sync(db: Session, application_id: UUID, source: str):
    return record_application_created_event(db, application_id, source)

def log_browser_capture_sync(db: Session, application_id: UUID, url: str):
    """Backward-compatibility wrapper for browser capture."""
    return record_event(
        db=db,
        application_id=application_id,
        event_type="application_captured_browser",
        description=f"Application captured from browser: {url}",
        event_data={"url": url}
    )
def create_event_sync(
    db: Session,
    application_id: UUID,
    event_type: str,
    description: str,
    event_data: Optional[dict] = None
):
    """Backward-compatibility wrapper for generic event creation."""
    return record_event(
        db=db,
        application_id=application_id,
        event_type=event_type,
        description=description,
        event_data=event_data or {}
    )

# ---------------------------------------------------------------------------
# Functions expected by timeline routes
# ---------------------------------------------------------------------------

async def create_event(
    db: Session,
    application_id: UUID,
    event_type: str,
    event_data: Optional[dict] = None,
    occurred_at: Optional[datetime] = None
):
    """Create a timeline event (async API route handler)."""
    event = TimelineEvent(
        application_id=application_id,
        event_type=event_type,
        event_data=event_data or {},
        occurred_at=occurred_at or datetime.utcnow()
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def list_events_for_application(
    db: Session,
    application_id: UUID,
    limit: int = 100
):
    """Return timeline events for an application in chronological order."""
    return (
        db.query(TimelineEvent)
        .filter(TimelineEvent.application_id == application_id)
        .order_by(TimelineEvent.occurred_at.asc())
        .limit(limit)
        .all()
    )
