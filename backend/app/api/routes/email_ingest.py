import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.dependencies.database import get_db
from app.schemas.email import EmailIngestRequest, EmailIngestResponse
from app.services.email_service import store_email_uid, check_email_exists
from app.services.correlation import correlate_email
from app.services.timeline_service import create_event_sync

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/ingest", response_model=EmailIngestResponse, status_code=200)
def ingest_email(
    request: EmailIngestRequest,
    db: Session = Depends(get_db)
):
    """Ingest parsed email event from Gmail polling/webhook worker."""
    try:
        # Check for duplicate
        if check_email_exists(db, request.message_id):
            logger.info(
                "email_already_processed",
                extra={"message_id": request.message_id}
            )
            return EmailIngestResponse(
                status="processed",
                duplicate=True,
                strategy=None,
                application_id=None
            )
        
        # Store email UID
        email_uid_record = store_email_uid(db, request.message_id)
        
        # Correlate with existing application or create new
        application, strategy = correlate_email(db, request, email_uid_record)
        
        # Record correlation timeline event if matched
        if strategy != "created_new":
            create_event_sync(
                db=db,
                application_id=application.id,
                event_type="email_correlated",
                event_data={
                    "message_id": request.message_id,
                    "correlation_strategy": strategy
                }
            )
        
        db.commit()
        
        logger.info(
            "email_ingested",
            extra={
                "message_id": request.message_id,
                "application_id": str(application.id),
                "strategy": strategy
            }
        )
        
        return EmailIngestResponse(
            status="processed",
            duplicate=False,
            strategy=strategy,
            application_id=str(application.id)
        )
    except Exception as e:
        logger.error(f"Failed to ingest email: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to ingest email")
