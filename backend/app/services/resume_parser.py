import logging
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
from PyPDF2 import PdfReader
from docx import Document
from sqlalchemy.orm import Session
from app.db.models.resume import Resume, ResumeData

logger = logging.getLogger(__name__)


def extract_text_from_pdf(file_path: str) -> str:
    """Extract text from a PDF file."""
    try:
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text.strip()
    except Exception as e:
        logger.error(f"Failed to extract text from PDF: {str(e)}", exc_info=True)
        raise


def extract_text_from_docx(file_path: str) -> str:
    """Extract text from a DOCX file."""
    try:
        doc = Document(file_path)
        text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
        return text.strip()
    except Exception as e:
        logger.error(f"Failed to extract text from DOCX: {str(e)}", exc_info=True)
        raise


def extract_text_from_resume(file_path: str, mime_type: str) -> str:
    """
    Extract text from a resume file based on its MIME type.

    Args:
        file_path: Path to the resume file
        mime_type: MIME type of the file

    Returns:
        Extracted text content

    Raises:
        ValueError: If file type is not supported
    """
    if mime_type == "application/pdf":
        return extract_text_from_pdf(file_path)
    elif mime_type in [
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ]:
        return extract_text_from_docx(file_path)
    else:
        raise ValueError(f"Unsupported file type: {mime_type}")


def extract_email(text: str) -> Optional[str]:
    """Extract email address from text."""
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    match = re.search(email_pattern, text)
    return match.group(0) if match else None


def extract_phone(text: str) -> Optional[str]:
    """Extract phone number from text."""
    # Match various phone formats
    phone_patterns = [
        r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',  # 123-456-7890 or 1234567890
        r'\(\d{3}\)\s*\d{3}[-.]?\d{4}',     # (123) 456-7890
        r'\+\d{1,3}\s*\d{3}[-.]?\d{3}[-.]?\d{4}'  # +1 123-456-7890
    ]

    for pattern in phone_patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(0)

    return None


def extract_linkedin_url(text: str) -> Optional[str]:
    """Extract LinkedIn URL from text."""
    linkedin_pattern = r'(?:https?://)?(?:www\.)?linkedin\.com/in/[\w-]+'
    match = re.search(linkedin_pattern, text, re.IGNORECASE)
    return match.group(0) if match else None


def extract_skills(text: str) -> List[str]:
    """
    Extract skills from resume text.

    This is a simple implementation that looks for common skill keywords.
    A more sophisticated implementation could use NLP or ML.
    """
    # Common technical skills
    common_skills = [
        "Python", "Java", "JavaScript", "TypeScript", "C++", "C#", "Go", "Rust", "Ruby",
        "React", "Angular", "Vue", "Node.js", "Django", "Flask", "FastAPI", "Spring",
        "SQL", "PostgreSQL", "MySQL", "MongoDB", "Redis", "Elasticsearch",
        "AWS", "Azure", "GCP", "Docker", "Kubernetes", "CI/CD", "Git",
        "REST", "GraphQL", "API", "Microservices", "Agile", "Scrum",
        "Machine Learning", "Deep Learning", "TensorFlow", "PyTorch",
        "HTML", "CSS", "SASS", "Tailwind", "Bootstrap",
        "Linux", "Unix", "Bash", "Shell", "DevOps", "Terraform"
    ]

    found_skills = []
    text_lower = text.lower()

    for skill in common_skills:
        # Use word boundaries to avoid partial matches
        pattern = r'\b' + re.escape(skill.lower()) + r'\b'
        if re.search(pattern, text_lower):
            found_skills.append(skill)

    return found_skills


def extract_experience_section(text: str) -> List[Dict[str, str]]:
    """
    Extract experience section from resume.

    This is a simplified implementation that looks for common experience patterns.
    Returns a list of experience entries as dictionaries.
    """
    experiences = []

    # Look for experience section
    experience_pattern = r'(?i)(experience|work history|employment)(.*?)(?=education|skills|projects|$)'
    match = re.search(experience_pattern, text, re.DOTALL)

    if match:
        experience_text = match.group(2)

        # Split by common delimiters (company entries often have dates)
        # Look for patterns like "Company Name | 2020-2023"
        entries = re.split(r'\n(?=\S)', experience_text)

        for entry in entries:
            if entry.strip():
                experiences.append({
                    "raw_text": entry.strip()
                })

    return experiences


def extract_education_section(text: str) -> List[Dict[str, str]]:
    """
    Extract education section from resume.

    This is a simplified implementation that looks for common education patterns.
    Returns a list of education entries as dictionaries.
    """
    education = []

    # Look for education section
    education_pattern = r'(?i)(education|academic background)(.*?)(?=experience|skills|projects|$)'
    match = re.search(education_pattern, text, re.DOTALL)

    if match:
        education_text = match.group(2)

        # Split by line breaks for education entries
        entries = re.split(r'\n(?=\S)', education_text)

        for entry in entries:
            if entry.strip():
                education.append({
                    "raw_text": entry.strip()
                })

    return education


def parse_resume_fields(text: str) -> Dict[str, Any]:
    """
    Parse structured fields from resume text.

    Args:
        text: Raw text extracted from resume

    Returns:
        Dictionary containing parsed resume fields
    """
    return {
        "email": extract_email(text),
        "phone": extract_phone(text),
        "linkedin_url": extract_linkedin_url(text),
        "skills": extract_skills(text),
        "experience": extract_experience_section(text),
        "education": extract_education_section(text),
        "raw_text_other": text
    }


def parse_resume_sync(resume_id: str, db: Session) -> ResumeData:
    """
    Synchronously parse a resume file and persist results.

    Args:
        resume_id: ID of the resume to parse
        db: Database session

    Returns:
        ResumeData object with parsed fields

    Raises:
        ValueError: If resume not found or parsing fails
        Exception: For any unexpected errors
    """
    # Get resume record
    resume = db.query(Resume).filter(Resume.id == resume_id).first()

    if not resume:
        raise ValueError(f"Resume not found: {resume_id}")

    try:
        # Update resume status to processing
        resume.status = "processing"
        db.commit()

        #logger.info(
            #"Starting synchronous resume parsing",
            #extra={
                #"resume_id": str(resume.id),
                #"filename": resume.filename
            #}
        #)

        # Extract text from resume file
        text = extract_text_from_resume(resume.file_path, resume.mime_type)

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

        db.commit()
        db.refresh(resume_data)

        logger.info(
            "Resume parsing completed successfully",
            extra={
                "resume_id": str(resume.id),
                "skills_count": len(parsed_fields.get("skills", [])),
                "has_email": parsed_fields.get("email") is not None,
                "has_phone": parsed_fields.get("phone") is not None
            }
        )

        return resume_data

    except ValueError as e:
        logger.error(f"Resume parsing failed due to validation error: {str(e)}")

        # Update resume status to failed
        resume.status = "failed"
        resume.error_message = str(e)
        db.commit()

        raise

    except Exception as e:
        logger.error(f"Unexpected error in resume parsing", exc_info=True)

        # Update resume status to failed
        resume.status = "failed"
        resume.error_message = str(e)
        db.commit()

        raise
