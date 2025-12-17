import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies.database import get_db
from app.schemas.advisory import AdvisoryEnvelope
from app.services.advisory.exposure import get_advisory_envelope

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("", response_model=AdvisoryEnvelope, responses={204: {"description": "No advisory available"}})
def get_advisory(
    resume_id: UUID,
    job_posting_id: UUID,
    db: Session = Depends(get_db),
):
    """Return advisory data if available, otherwise 204 with no content."""

    try:
        advisory_payload = get_advisory_envelope(
            db, resume_id=resume_id, job_posting_id=job_posting_id
        )
    except Exception:
        logger.debug("WS5: advisory fetch failed; returning no content", exc_info=True)
        advisory_payload = None

    if not advisory_payload:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return advisory_payload
