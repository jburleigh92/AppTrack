import logging
import os
from pathlib import Path
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import update
from app.api.dependencies.database import get_db
from app.db.models.resume import Resume
from app.schemas.resume import ResumeUploadResponse, ResumeResponse, ResumeDataResponse
from app.core.config import settings
from app.services.resume_parser import parse_resume_sync

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/upload", response_model=ResumeUploadResponse, status_code=200)
async def upload_resume(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload a resume file (PDF or DOCX) and parse it synchronously.

    The file will be stored on disk and parsed immediately.
    Only one resume can be active at a time - uploading a new resume
    will automatically deactivate the previous active resume.
    """
    file_path = None

    try:
        # Validate file type
        if file.content_type not in settings.ALLOWED_RESUME_MIME_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Allowed types: PDF, DOC, DOCX"
            )

        # Read file content to validate and get size
        file_content = await file.read()
        file_size = len(file_content)

        # Validate file size
        max_size_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        if file_size > max_size_bytes:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size: {settings.MAX_UPLOAD_SIZE_MB}MB"
            )

        if file_size == 0:
            raise HTTPException(
                status_code=400,
                detail="Empty file"
            )

        # Create upload directory if it doesn't exist
        upload_dir = Path(settings.RESUME_UPLOAD_DIR)
        upload_dir.mkdir(parents=True, exist_ok=True)

        # Generate unique filename
        file_extension = Path(file.filename).suffix
        unique_filename = f"{uuid4()}{file_extension}"
        file_path = upload_dir / unique_filename

        # Write file to disk
        with open(file_path, "wb") as f:
            f.write(file_content)

        # Deactivate any previously active resume
        db.execute(
            update(Resume)
            .where(Resume.is_active == True)
            .values(is_active=False)
        )

        # Create resume record
        resume = Resume(
            filename=file.filename,
            file_path=str(file_path),
            file_size_bytes=file_size,
            mime_type=file.content_type,
            status="uploaded",
            is_active=True
        )

        db.add(resume)
        db.commit()
        db.refresh(resume)

        logger.info(
            "Resume uploaded, starting synchronous parsing",
            extra={
                "resume_id": str(resume.id),
                "uploaded_filename": file.filename,
                "file_size": file_size,
                "mime_type": file.content_type
            }
        )

        # Parse resume synchronously
        try:
            resume_data = parse_resume_sync(resume.id, db)

            return ResumeUploadResponse(
                resume_id=resume.id,
                status="parsed",
                resume_data=ResumeDataResponse.from_orm(resume_data),
                error_message=None
            )

        except ValueError as parse_error:
            # Parsing failed due to validation error
            logger.error(f"Resume parsing failed: {str(parse_error)}")

            return ResumeUploadResponse(
                resume_id=resume.id,
                status="failed",
                resume_data=None,
                error_message=str(parse_error)
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to upload resume: {str(e)}", exc_info=True)
        db.rollback()

        # Clean up file if it was written
        if file_path is not None and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception as cleanup_error:
                logger.error(f"Failed to clean up file: {str(cleanup_error)}")

        raise HTTPException(
            status_code=500,
            detail="Failed to upload resume"
        )


@router.get("/active", response_model=ResumeResponse)
def get_active_resume(db: Session = Depends(get_db)):
    """
    Get the currently active resume.
    """
    resume = db.query(Resume).filter(Resume.is_active == True).first()

    if not resume:
        raise HTTPException(
            status_code=404,
            detail="No active resume found"
        )

    return resume


@router.get("/{resume_id}/data", response_model=ResumeDataResponse)
def get_resume_data(resume_id: str, db: Session = Depends(get_db)):
    """
    Get parsed resume data for a specific resume.
    """
    from app.db.models.resume import ResumeData
    from uuid import UUID

    try:
        resume_uuid = UUID(resume_id)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid resume ID format"
        )

    resume_data = db.query(ResumeData).filter(
        ResumeData.resume_id == resume_uuid
    ).first()

    if not resume_data:
        raise HTTPException(
            status_code=404,
            detail="Resume data not found. Resume may not have been parsed yet."
        )

    return resume_data
