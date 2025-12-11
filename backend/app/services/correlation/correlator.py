import logging
from datetime import timedelta
from difflib import SequenceMatcher
from typing import Tuple, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, or_
from app.db.models.application import Application
from app.db.models.email import ProcessedEmailUID
from app.schemas.email import EmailIngestRequest

logger = logging.getLogger(__name__)


class CorrelationStrategy:
    EXACT_URL = "exact_url"
    FUZZY_COMPANY_TITLE = "fuzzy_company_title"
    TITLE_DATE = "title_date"
    COMPANY_ONLY = "company_only"
    CREATED_NEW = "created_new"


def similarity_ratio(a: str, b: str) -> float:
    """Calculate similarity between two strings."""
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


def correlate_email(
    db: Session,
    email_request: EmailIngestRequest,
    email_uid_record: ProcessedEmailUID
) -> Tuple[Application, str]:
    """
    Correlate email with existing application or create new one.
    
    Returns:
        Tuple of (Application, strategy_used)
    """
    
    # Stage A: URL Match (Strongest)
    if email_request.job_posting_url:
        application = _match_by_url(db, email_request.job_posting_url)
        if application:
            _update_application_from_email(db, application, email_request, email_uid_record)
            logger.info(
                f"Correlated email via URL match",
                extra={
                    "message_id": email_request.message_id,
                    "application_id": str(application.id),
                    "strategy": CorrelationStrategy.EXACT_URL
                }
            )
            return application, CorrelationStrategy.EXACT_URL
    
    # Stage B: Company + Title (High Confidence)
    if email_request.company_name and email_request.job_title:
        application = _match_by_company_title(
            db,
            email_request.company_name,
            email_request.job_title
        )
        if application:
            _update_application_from_email(db, application, email_request, email_uid_record)
            logger.info(
                f"Correlated email via company+title match",
                extra={
                    "message_id": email_request.message_id,
                    "application_id": str(application.id),
                    "strategy": CorrelationStrategy.FUZZY_COMPANY_TITLE
                }
            )
            return application, CorrelationStrategy.FUZZY_COMPANY_TITLE
    
    # Stage C: Title + Date Window (Medium)
    if email_request.job_title and email_request.application_date:
        application = _match_by_title_date(
            db,
            email_request.job_title,
            email_request.application_date
        )
        if application:
            _update_application_from_email(db, application, email_request, email_uid_record)
            logger.info(
                f"Correlated email via title+date match",
                extra={
                    "message_id": email_request.message_id,
                    "application_id": str(application.id),
                    "strategy": CorrelationStrategy.TITLE_DATE
                }
            )
            return application, CorrelationStrategy.TITLE_DATE
    
    # Stage D: Company-only (Weak)
    if email_request.company_name:
        application = _match_by_company(db, email_request.company_name)
        if application:
            _update_application_from_email(db, application, email_request, email_uid_record)
            logger.info(
                f"Correlated email via company-only match",
                extra={
                    "message_id": email_request.message_id,
                    "application_id": str(application.id),
                    "strategy": CorrelationStrategy.COMPANY_ONLY
                }
            )
            return application, CorrelationStrategy.COMPANY_ONLY
    
    # Stage E: No Match - Create New Application
    from app.services.application_service import create_application_from_email
    
    application = create_application_from_email(db, email_request)
    email_uid_record.application_id = application.id
    db.commit()
    
    logger.info(
        f"Created new application from email (no correlation)",
        extra={
            "message_id": email_request.message_id,
            "application_id": str(application.id),
            "strategy": CorrelationStrategy.CREATED_NEW
        }
    )
    
    return application, CorrelationStrategy.CREATED_NEW


def _match_by_url(db: Session, url: str) -> Optional[Application]:
    """Match application by exact URL."""
    stmt = select(Application).where(
        and_(
            Application.job_posting_url == url,
            Application.is_deleted == False
        )
    ).limit(1)
    
    return db.execute(stmt).scalar_one_or_none()


def _match_by_company_title(
    db: Session,
    company_name: str,
    job_title: str
) -> Optional[Application]:
    """Match application by fuzzy company name and job title."""
    stmt = select(Application).where(
        Application.is_deleted == False
    )
    
    applications = db.execute(stmt).scalars().all()
    
    matches = []
    for app in applications:
        company_sim = similarity_ratio(company_name, app.company_name)
        title_sim = similarity_ratio(job_title, app.job_title)
        
        if company_sim >= 0.80 and title_sim >= 0.75:
            matches.append((app, company_sim + title_sim))
    
    if len(matches) == 1:
        return matches[0][0]
    
    return None


def _match_by_title_date(
    db: Session,
    job_title: str,
    application_date
) -> Optional[Application]:
    """Match application by job title within ±2 day window."""
    date_min = application_date - timedelta(days=2)
    date_max = application_date + timedelta(days=2)
    
    stmt = select(Application).where(
        and_(
            Application.application_date >= date_min,
            Application.application_date <= date_max,
            Application.is_deleted == False
        )
    )
    
    applications = db.execute(stmt).scalars().all()
    
    matches = []
    for app in applications:
        title_sim = similarity_ratio(job_title, app.job_title)
        if title_sim >= 0.75:
            matches.append(app)
    
    if len(matches) == 1:
        return matches[0]
    
    return None


def _match_by_company(db: Session, company_name: str) -> Optional[Application]:
    """Match application by company name only."""
    stmt = select(Application).where(
        Application.is_deleted == False
    )
    
    applications = db.execute(stmt).scalars().all()
    
    matches = []
    for app in applications:
        company_sim = similarity_ratio(company_name, app.company_name)
        if company_sim >= 0.80:
            matches.append(app)
    
    if len(matches) == 1:
        return matches[0]
    
    return None


def _update_application_from_email(
    db: Session,
    application: Application,
    email_request: EmailIngestRequest,
    email_uid_record: ProcessedEmailUID
):
    """Update application with email data and mark as correlated."""
    # Update missing fields
    if not application.company_name or application.company_name == "Unknown Company":
        if email_request.company_name:
            application.company_name = email_request.company_name
    
    if not application.job_title or application.job_title == "Unknown Position":
        if email_request.job_title:
            application.job_title = email_request.job_title
    
    if not application.job_posting_url:
        if email_request.job_posting_url:
            application.job_posting_url = email_request.job_posting_url
    
    # Update needs_review
    if application.company_name != "Unknown Company" and application.job_title != "Unknown Position":
        application.needs_review = False
    
    # Link email to application
    email_uid_record.application_id = application.id
    
    db.commit()
