import logging
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.api.dependencies.database import get_db
from app.db.models.application import Application
from app.schemas.application import CaptureApplicationRequest, ApplicationResponse, UpdateApplicationRequest
from app.services.application_service import create_application_from_capture
from app.services.timeline_service import create_event_sync

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("", response_model=List[ApplicationResponse])
def list_applications(
    status: Optional[str] = Query(None, description="Filter by status"),
    db: Session = Depends(get_db)
):
    """
    List all applications.

    Optionally filter by status.
    Returns all non-deleted applications ordered by creation date (newest first).
    """
    try:
        # Base query - exclude deleted applications
        query = db.query(Application).filter(Application.is_deleted == False)

        # Apply status filter if provided
        if status:
            query = query.filter(Application.status == status)

        # Order by created_at descending (newest first)
        query = query.order_by(Application.created_at.desc())

        applications = query.all()

        logger.info(
            "applications_listed",
            extra={
                "count": len(applications),
                "status_filter": status
            }
        )

        return applications

    except Exception as e:
        logger.error(f"Failed to list applications: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list applications")


@router.get("/{application_id}", response_model=ApplicationResponse)
def get_application(
    application_id: str,
    db: Session = Depends(get_db)
):
    """
    Get a single application by ID.

    Returns full application details including linked resources.
    """
    try:
        app_uuid = UUID(application_id)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid application ID format"
        )

    application = db.query(Application).filter(
        Application.id == app_uuid,
        Application.is_deleted == False
    ).first()

    if not application:
        raise HTTPException(
            status_code=404,
            detail="Application not found"
        )

    logger.info(
        "application_retrieved",
        extra={
            "application_id": str(application.id),
            "company_name": application.company_name
        }
    )

    return application


@router.patch("/{application_id}", response_model=ApplicationResponse)
def update_application(
    application_id: str,
    request: UpdateApplicationRequest,
    db: Session = Depends(get_db)
):
    """
    Update an application.

    Currently supports updating status and notes.
    Records timeline event when status changes.
    """
    try:
        app_uuid = UUID(application_id)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid application ID format"
        )

    # Get application
    application = db.query(Application).filter(
        Application.id == app_uuid,
        Application.is_deleted == False
    ).first()

    if not application:
        raise HTTPException(
            status_code=404,
            detail="Application not found"
        )

    # Track old status for timeline event
    old_status = application.status

    # Update fields
    if request.status is not None:
        application.status = request.status

    if request.notes is not None:
        application.notes = request.notes

    db.commit()
    db.refresh(application)

    # Log timeline event if status changed
    if request.status is not None and old_status != request.status:
        create_event_sync(
            db=db,
            application_id=application.id,
            event_type="status_changed",
            event_data={
                "old_status": old_status,
                "new_status": request.status
            }
        )
        db.commit()

    logger.info(
        "application_updated",
        extra={
            "application_id": str(application.id),
            "status_changed": old_status != request.status,
            "old_status": old_status,
            "new_status": application.status
        }
    )

    return application


@router.delete("/{application_id}", status_code=204)
def delete_application(
    application_id: str,
    db: Session = Depends(get_db)
):
    """
    Delete an application (soft delete).

    Marks the application as deleted rather than permanently removing it.
    This preserves data integrity and allows for potential recovery.
    """
    try:
        app_uuid = UUID(application_id)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid application ID format"
        )

    # Get application
    application = db.query(Application).filter(
        Application.id == app_uuid,
        Application.is_deleted == False
    ).first()

    if not application:
        raise HTTPException(
            status_code=404,
            detail="Application not found"
        )

    # Soft delete
    application.is_deleted = True
    db.commit()

    logger.info(
        "application_deleted",
        extra={
            "application_id": str(application.id),
            "company_name": application.company_name,
            "job_title": application.job_title
        }
    )

    return None


@router.post("/capture", response_model=ApplicationResponse, status_code=201)
def capture_application(
    request: CaptureApplicationRequest,
    db: Session = Depends(get_db)
):
    """Capture application submission from browser extension."""
    try:
        # This already logs the timeline event internally
        application = create_application_from_capture(db, request)

        db.commit()

        logger.info(
            "application_captured_browser",
            extra={
                "company_name": application.company_name,
                "job_title": application.job_title,
                "job_posting_url": application.job_posting_url
            }
        )

        return application
    except Exception as e:
        logger.error(f"Failed to capture application: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to capture application")
