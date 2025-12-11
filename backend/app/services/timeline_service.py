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
