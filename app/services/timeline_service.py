"""
Timeline event logging service.

Provides functions for recording application lifecycle events.
All functions have both async and sync variants for compatibility.
"""
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.timeline import TimelineEvent
from uuid import UUID
from typing import Optional, List

logger = logging.getLogger(__name__)


# Core event creation functions

async def create_event(
    db: AsyncSession,
    application_id: UUID,
    event_type: str,
    event_data: dict,
    occurred_at: Optional[datetime] = None
) -> Optional[TimelineEvent]:
    """Create a timeline event (async version)."""
    try:
        event = TimelineEvent(
            application_id=application_id,
            event_type=event_type,
            event_data=event_data or {},
            occurred_at=occurred_at or datetime.utcnow()
        )
        db.add(event)
        await db.flush()
        return event
    except Exception as e:
        logger.error(f"Failed to create timeline event", exc_info=True, extra={
            "application_id": str(application_id),
            "event_type": event_type
        })
        return None


def create_event_sync(
    db: Session,
    application_id: UUID,
    event_type: str,
    event_data: dict,
    occurred_at: Optional[datetime] = None
) -> Optional[TimelineEvent]:
    """Create a timeline event (sync version)."""
    try:
        event = TimelineEvent(
            application_id=application_id,
            event_type=event_type,
            event_data=event_data or {},
            occurred_at=occurred_at or datetime.utcnow()
        )
        db.add(event)
        db.flush()
        return event
    except Exception as e:
        logger.error(f"Failed to create timeline event", exc_info=True, extra={
            "application_id": str(application_id),
            "event_type": event_type
        })
        return None


# Application events

async def log_application_created(
    db: AsyncSession,
    application_id: UUID,
    source: str
) -> Optional[TimelineEvent]:
    """Log application creation event (async)."""
    return await create_event(
        db=db,
        application_id=application_id,
        event_type="application_created",
        event_data={"source": source}
    )


def log_application_created_sync(
    db: Session,
    application_id: UUID,
    source: str
) -> Optional[TimelineEvent]:
    """Log application creation event (sync)."""
    return create_event_sync(
        db=db,
        application_id=application_id,
        event_type="application_created",
        event_data={"source": source}
    )


def record_application_created_event(
    db: Session,
    application_id: UUID,
    source: str
) -> Optional[TimelineEvent]:
    """Alias for log_application_created_sync."""
    return log_application_created_sync(db, application_id, source)


# Browser capture events

async def log_browser_capture(
    db: AsyncSession,
    application_id: UUID,
    url: str
) -> Optional[TimelineEvent]:
    """Log browser capture event (async)."""
    return await create_event(
        db=db,
        application_id=application_id,
        event_type="browser_capture",
        event_data={"url": url}
    )


def log_browser_capture_sync(
    db: Session,
    application_id: UUID,
    url: str
) -> Optional[TimelineEvent]:
    """Log browser capture event (sync)."""
    return create_event_sync(
        db=db,
        application_id=application_id,
        event_type="browser_capture",
        event_data={"url": url}
    )


# Email correlation events

async def log_email_correlated(
    db: AsyncSession,
    application_id: UUID,
    message_id: str,
    strategy: str
) -> Optional[TimelineEvent]:
    """Log email correlation event (async)."""
    return await create_event(
        db=db,
        application_id=application_id,
        event_type="email_correlated",
        event_data={
            "message_id": message_id,
            "correlation_strategy": strategy
        }
    )


def log_email_correlated_sync(
    db: Session,
    application_id: UUID,
    message_id: str,
    strategy: str
) -> Optional[TimelineEvent]:
    """Log email correlation event (sync)."""
    return create_event_sync(
        db=db,
        application_id=application_id,
        event_type="email_correlated",
        event_data={
            "message_id": message_id,
            "correlation_strategy": strategy
        }
    )


def record_correlation_event(
    db: Session,
    application_id: UUID,
    message_id: str,
    strategy: str
) -> Optional[TimelineEvent]:
    """Alias for log_email_correlated_sync."""
    return log_email_correlated_sync(db, application_id, message_id, strategy)


# Scraping events

async def log_scrape_started(
    db: AsyncSession,
    application_id: UUID,
    url: str
) -> Optional[TimelineEvent]:
    """Log scrape start event (async)."""
    return await create_event(
        db=db,
        application_id=application_id,
        event_type="scrape_started",
        event_data={"url": url}
    )


def log_scrape_started_sync(
    db: Session,
    application_id: UUID,
    url: str
) -> Optional[TimelineEvent]:
    """Log scrape start event (sync)."""
    return create_event_sync(
        db=db,
        application_id=application_id,
        event_type="scrape_started",
        event_data={"url": url}
    )


async def log_scrape_completed(
    db: AsyncSession,
    application_id: UUID,
    url: str,
    posting_id: Optional[UUID] = None
) -> Optional[TimelineEvent]:
    """Log scrape completion event (async)."""
    event_data = {"url": url}
    if posting_id:
        event_data["posting_id"] = str(posting_id)
    
    return await create_event(
        db=db,
        application_id=application_id,
        event_type="scrape_completed",
        event_data=event_data
    )


def log_scrape_completed_sync(
    db: Session,
    application_id: UUID,
    url: str,
    posting_id: Optional[UUID] = None
) -> Optional[TimelineEvent]:
    """Log scrape completion event (sync)."""
    event_data = {"url": url}
    if posting_id:
        event_data["posting_id"] = str(posting_id)
    
    return create_event_sync(
        db=db,
        application_id=application_id,
        event_type="scrape_completed",
        event_data=event_data
    )


def record_posting_scraped_event(
    db: Session,
    application_id: UUID,
    url: str,
    partial: bool = False
) -> Optional[TimelineEvent]:
    """Record job posting scrape event."""
    event_type = "scrape_partial_data" if partial else "posting_scraped"
    return create_event_sync(
        db=db,
        application_id=application_id,
        event_type=event_type,
        event_data={
            "url": url,
            "partial": partial
        }
    )


async def log_scrape_failed(
    db: AsyncSession,
    application_id: UUID,
    url: str,
    reason: str
) -> Optional[TimelineEvent]:
    """Log scrape failure event (async)."""
    return await create_event(
        db=db,
        application_id=application_id,
        event_type="scrape_failed",
        event_data={
            "url": url,
            "reason": reason
        }
    )


def log_scrape_failed_sync(
    db: Session,
    application_id: UUID,
    url: str,
    reason: str
) -> Optional[TimelineEvent]:
    """Log scrape failure event (sync)."""
    return create_event_sync(
        db=db,
        application_id=application_id,
        event_type="scrape_failed",
        event_data={
            "url": url,
            "reason": reason
        }
    )


def record_scrape_failed_event(
    db: Session,
    application_id: UUID,
    url: str,
    error: str
) -> Optional[TimelineEvent]:
    """Alias for log_scrape_failed_sync."""
    return log_scrape_failed_sync(db, application_id, url, error)


# Analysis events

async def log_analysis_started(
    db: AsyncSession,
    application_id: UUID
) -> Optional[TimelineEvent]:
    """Log analysis start event (async)."""
    return await create_event(
        db=db,
        application_id=application_id,
        event_type="analysis_started",
        event_data={}
    )


def log_analysis_started_sync(
    db: Session,
    application_id: UUID
) -> Optional[TimelineEvent]:
    """Log analysis start event (sync)."""
    return create_event_sync(
        db=db,
        application_id=application_id,
        event_type="analysis_started",
        event_data={}
    )


async def log_analysis_completed(
    db: AsyncSession,
    application_id: UUID,
    analysis_id: UUID,
    match_score: int
) -> Optional[TimelineEvent]:
    """Log analysis completion event (async)."""
    return await create_event(
        db=db,
        application_id=application_id,
        event_type="analysis_completed",
        event_data={
            "analysis_id": str(analysis_id),
            "match_score": match_score
        }
    )


def log_analysis_completed_sync(
    db: Session,
    application_id: UUID,
    analysis_id: UUID,
    match_score: int
) -> Optional[TimelineEvent]:
    """Log analysis completion event (sync)."""
    return create_event_sync(
        db=db,
        application_id=application_id,
        event_type="analysis_completed",
        event_data={
            "analysis_id": str(analysis_id),
            "match_score": match_score
        }
    )


async def log_analysis_failed(
    db: AsyncSession,
    application_id: UUID,
    reason: str,
    details: Optional[str] = None
) -> Optional[TimelineEvent]:
    """Log analysis failure event (async)."""
    event_data = {"reason": reason}
    if details:
        event_data["details"] = details
    
    return await create_event(
        db=db,
        application_id=application_id,
        event_type="analysis_failed",
        event_data=event_data
    )


def log_analysis_failed_sync(
    db: Session,
    application_id: UUID,
    reason: str,
    details: Optional[str] = None
) -> Optional[TimelineEvent]:
    """Log analysis failure event (sync)."""
    event_data = {"reason": reason}
    if details:
        event_data["details"] = details
    
    return create_event_sync(
        db=db,
        application_id=application_id,
        event_type="analysis_failed",
        event_data=event_data
    )


# Query functions

async def list_events_for_application(
    db: AsyncSession,
    application_id: UUID,
    limit: int = 100
) -> List[TimelineEvent]:
    """List timeline events for an application (async)."""
    from sqlalchemy import select
    
    stmt = select(TimelineEvent).where(
        TimelineEvent.application_id == application_id
    ).order_by(
        TimelineEvent.created_at.asc()
    ).limit(limit)
    
    result = await db.execute(stmt)
    return list(result.scalars().all())


def list_events_for_application_sync(
    db: Session,
    application_id: UUID,
    limit: int = 100
) -> List[TimelineEvent]:
    """List timeline events for an application (sync)."""
    return db.query(TimelineEvent).filter(
        TimelineEvent.application_id == application_id
    ).order_by(
        TimelineEvent.created_at.asc()
    ).limit(limit).all()
