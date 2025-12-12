from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.db.models.email import ProcessedEmailUID


def check_email_exists(db: Session, message_id: str) -> bool:
    """Check if email message ID has already been processed."""
    stmt = select(ProcessedEmailUID).where(ProcessedEmailUID.email_uid == message_id)
    result = db.execute(stmt).scalar_one_or_none()
    return result is not None


def store_email_uid(db: Session, message_id: str) -> ProcessedEmailUID:
    """Store email UID to prevent duplicate processing."""
    email_uid = ProcessedEmailUID(
        email_uid=message_id,
        email_account="default",
        processed_at=datetime.utcnow()
    )
    
    db.add(email_uid)
    db.commit()
    db.refresh(email_uid)
    
    return email_uid
