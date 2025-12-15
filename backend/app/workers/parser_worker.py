import asyncio
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.db.session import SessionLocal
from app.db.models.queue import ParserQueue
from app.db.models.resume import Resume, ResumeData
from app.services.resume_parser import extract_text_from_resume, parse_resume_fields

logger = logging.getLogger(__name__)


async def process_parser_job(job: ParserQueue):
    """
    Process a single parser job from the queue.

    Args:
        job: ParserQueue job to process
    """
    db = SessionLocal()

    try:
        job = db.merge(job)

        # Mark job as processing
        job.status = "processing"
        job.started_at = datetime.utcnow()
        job.attempts += 1
        db.commit()

        # Get associated resume
        resume = db.query(Resume).filter(Resume.id == job.resume_id).first()

        if not resume:
            raise ValueError(f"Resume not found: {job.resume_id}")

        # Update resume status to processing
        resume.status = "processing"
        db.commit()

        logger.info(
            "Starting resume parsing",
            extra={
                "job_id": str(job.id),
                "resume_id": str(resume.id),
                "filename": resume.filename
            }
        )

        # Extract text from resume file
        text = extract_text_from_resume(job.file_path, resume.mime_type)

        if not text or len(text.strip()) == 0:
            raise ValueError("No text extracted from resume")

        # Parse resume fields
        parsed_fields = parse_resume_fields(text)

        # Check if resume_data already exists
        existing_data = db.query(ResumeData).filter(
            ResumeData.resume_id == resume.id
        ).first()

        if existing_data:
            # Update existing record
            existing_data.email = parsed_fields.get("email")
            existing_data.phone = parsed_fields.get("phone")
            existing_data.linkedin_url = parsed_fields.get("linkedin_url")
            existing_data.skills = parsed_fields.get("skills", [])
            existing_data.experience = parsed_fields.get("experience", [])
            existing_data.education = parsed_fields.get("education", [])
            existing_data.raw_text_other = parsed_fields.get("raw_text_other")
            existing_data.extraction_complete = True

            resume_data = existing_data
        else:
            # Create new resume_data record
            resume_data = ResumeData(
                resume_id=resume.id,
                email=parsed_fields.get("email"),
                phone=parsed_fields.get("phone"),
                linkedin_url=parsed_fields.get("linkedin_url"),
                skills=parsed_fields.get("skills", []),
                experience=parsed_fields.get("experience", []),
                education=parsed_fields.get("education", []),
                certifications=[],
                raw_text_other=parsed_fields.get("raw_text_other"),
                extraction_complete=True
            )

            db.add(resume_data)

        # Update resume status to parsed
        resume.status = "parsed"
        resume.error_message = None

        # Mark job complete
        job.status = "complete"
        job.completed_at = datetime.utcnow()
        job.error_message = None

        db.commit()

        logger.info(
            "Resume parsing completed successfully",
            extra={
                "job_id": str(job.id),
                "resume_id": str(resume.id),
                "skills_count": len(parsed_fields.get("skills", [])),
                "has_email": parsed_fields.get("email") is not None,
                "has_phone": parsed_fields.get("phone") is not None
            }
        )

    except ValueError as e:
        logger.error(f"Parser job failed due to validation error: {str(e)}")

        # Permanent failure - don't retry
        job.status = "failed"
        job.completed_at = datetime.utcnow()
        job.error_message = str(e)

        # Update resume status
        resume = db.query(Resume).filter(Resume.id == job.resume_id).first()
        if resume:
            resume.status = "failed"
            resume.error_message = str(e)

        db.commit()

    except Exception as e:
        logger.error(f"Unexpected error in parser job", exc_info=True)

        # Permanent failure for parsing (max_attempts = 1 by default)
        job.status = "failed"
        job.completed_at = datetime.utcnow()
        job.error_message = f"Parse error: {str(e)}"

        # Update resume status
        resume = db.query(Resume).filter(Resume.id == job.resume_id).first()
        if resume:
            resume.status = "failed"
            resume.error_message = str(e)

        db.commit()

    finally:
        db.close()


async def poll_parser_queue():
    """Poll for pending parser jobs."""
    db = SessionLocal()

    try:
        # Find next pending job
        stmt = select(ParserQueue).where(
            ParserQueue.status == "pending"
        ).order_by(
            ParserQueue.priority.desc(),
            ParserQueue.created_at
        ).limit(1)

        job = db.execute(stmt).scalar_one_or_none()

        if job:
            await process_parser_job(job)
            return True

        return False

    except Exception as e:
        logger.error("Error polling parser queue", exc_info=True)
        return False

    finally:
        db.close()


def run_parser_worker():
    """Run the parser worker (polling mode)."""
    logger.info("Parser worker started")

    while True:
        try:
            # Poll for jobs
            has_job = asyncio.run(poll_parser_queue())

            # If no job found, wait before polling again
            if not has_job:
                asyncio.run(asyncio.sleep(5))

        except KeyboardInterrupt:
            logger.info("Parser worker stopped")
            break

        except Exception as e:
            logger.error("Error in parser worker", exc_info=True)
            asyncio.run(asyncio.sleep(5))


if __name__ == "__main__":
    run_parser_worker()
