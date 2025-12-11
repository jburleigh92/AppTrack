import logging
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_
from app.db.models.application import Application
from app.db.models.job_posting import JobPosting
from app.db.models.analysis import AnalysisResult
from app.db.models.timeline import TimelineEvent
from app.schemas.export import ExportFilters

logger = logging.getLogger(__name__)


class ExportError(Exception):
    """Base exception for export operations."""
    pass


def generate_export_rows(
    db: Session,
    filters: ExportFilters
) -> Tuple[List[str], List[Dict]]:
    """
    Generate export data with optional filters.
    
    Args:
        db: Database session
        filters: Export filters (status, company, date range)
        
    Returns:
        Tuple of (headers, rows) where:
        - headers: List of column names
        - rows: List of dicts, each representing one application
        
    Note: Adjust field mappings in _build_export_row() if schema changes.
    """
    
    # Build query with joins (outer joins to handle missing related data)
    query = select(
        Application,
        JobPosting,
        AnalysisResult
    ).select_from(Application).outerjoin(
        JobPosting,
        Application.posting_id == JobPosting.id
    ).outerjoin(
        AnalysisResult,
        Application.analysis_id == AnalysisResult.id
    ).where(
        Application.is_deleted == False
    )
    
    # Apply filters
    conditions = []
    
    if filters.status:
        conditions.append(Application.status == filters.status)
    
    if filters.company_name:
        # Partial match, case-insensitive
        conditions.append(
            Application.company_name.ilike(f"%{filters.company_name}%")
        )
    
    if filters.date_from:
        conditions.append(Application.application_date >= filters.date_from)
    
    if filters.date_to:
        conditions.append(Application.application_date <= filters.date_to)
    
    if conditions:
        query = query.where(and_(*conditions))
    
    # Order by application date (newest first)
    query = query.order_by(Application.application_date.desc())
    
    # Execute query
    results = db.execute(query).all()
    
    # Get timeline data for each application (most recent event)
    application_ids = [row[0].id for row in results]
    timeline_data = _get_timeline_summary(db, application_ids)
    
    # Define column headers (stable order)
    headers = [
        "Application ID",
        "Company Name",
        "Job Title",
        "Status",
        "Application Date",
        "Source",
        "Job Location",
        "Job URL",
        "Employment Type",
        "Salary Range",
        "Analysis Match Score",
        "Qualifications Met",
        "Qualifications Missing",
        "Skills Suggestions",
        "Last Event Type",
        "Last Event Date",
        "Notes"
    ]
    
    # Build export rows
    rows = []
    for application, job_posting, analysis in results:
        row_data = _build_export_row(
            application,
            job_posting,
            analysis,
            timeline_data.get(application.id)
        )
        rows.append(row_data)
    
    logger.info(
        f"Generated export with {len(rows)} rows",
        extra={
            "filters": filters.dict(exclude_none=True),
            "row_count": len(rows)
        }
    )
    
    return headers, rows


def _get_timeline_summary(
    db: Session,
    application_ids: List
) -> Dict:
    """
    Get most recent timeline event for each application.
    
    Returns:
        Dict mapping application_id -> {event_type, occurred_at}
    """
    if not application_ids:
        return {}
    
    # Subquery to get most recent event per application
    subq = select(
        TimelineEvent.application_id,
        func.max(TimelineEvent.occurred_at).label('max_occurred_at')
    ).where(
        TimelineEvent.application_id.in_(application_ids)
    ).group_by(
        TimelineEvent.application_id
    ).subquery()
    
    # Get the actual events
    query = select(TimelineEvent).join(
        subq,
        and_(
            TimelineEvent.application_id == subq.c.application_id,
            TimelineEvent.occurred_at == subq.c.max_occurred_at
        )
    )
    
    events = db.execute(query).scalars().all()
    
    return {
        event.application_id: {
            'event_type': event.event_type,
            'occurred_at': event.occurred_at
        }
        for event in events
    }


def _build_export_row(
    application: Application,
    job_posting: Optional[JobPosting],
    analysis: Optional[AnalysisResult],
    timeline_summary: Optional[Dict]
) -> Dict:
    """
    Build a flat dictionary for one application row.
    
    Note: Adjust these field mappings if your schema changes:
    - Application fields: company_name, job_title, status, etc.
    - JobPosting fields: location, salary_range, employment_type
    - AnalysisResult fields: match_score, qualifications_met, etc.
    """
    
    # Format qualifications as comma-separated strings
    qualifications_met = ""
    qualifications_missing = ""
    suggestions = ""
    
    if analysis:
        if isinstance(analysis.qualifications_met, list):
            qualifications_met = ", ".join(analysis.qualifications_met)
        if isinstance(analysis.qualifications_missing, list):
            qualifications_missing = ", ".join(analysis.qualifications_missing)
        if isinstance(analysis.suggestions, list):
            suggestions = ", ".join(analysis.suggestions)
    
    # Build the row
    row = {
        "Application ID": str(application.id),
        "Company Name": application.company_name or "",
        "Job Title": application.job_title or "",
        "Status": application.status or "",
        "Application Date": application.application_date.isoformat() if application.application_date else "",
        "Source": application.source or "",
        "Job Location": job_posting.location if job_posting else "",
        "Job URL": application.job_posting_url or "",
        "Employment Type": job_posting.employment_type if job_posting else "",
        "Salary Range": job_posting.salary_range if job_posting else "",
        "Analysis Match Score": analysis.match_score if analysis else "",
        "Qualifications Met": qualifications_met,
        "Qualifications Missing": qualifications_missing,
        "Skills Suggestions": suggestions,
        "Last Event Type": timeline_summary.get('event_type', '') if timeline_summary else "",
        "Last Event Date": timeline_summary.get('occurred_at').isoformat() if timeline_summary and timeline_summary.get('occurred_at') else "",
        "Notes": application.notes or ""
    }
    
    return row


def sync_to_google_sheets(
    headers: List[str],
    rows: List[Dict],
    sheet_id: str,
    worksheet_name: str = "Applications",
    credentials_path: Optional[str] = None
) -> Dict:
    """
    Sync export data to Google Sheets.
    
    Args:
        headers: Column headers
        rows: Data rows (list of dicts)
        sheet_id: Google Sheets spreadsheet ID
        worksheet_name: Worksheet/tab name
        credentials_path: Path to service account JSON (optional, uses env var if None)
        
    Returns:
        Dict with sync results: {success, message, updated_rows}
        
    Raises:
        ExportError: If Google Sheets sync fails
        
    Note: Requires google-api-python-client installed and service account credentials.
    Strategy: Clears existing data in worksheet, then writes headers + all rows.
    """
    
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        from googleapiclient.errors import HttpError
    except ImportError:
        raise ExportError(
            "Google API client not installed. "
            "Install with: pip install google-api-python-client google-auth"
        )
    
    # Get credentials
    if credentials_path is None:
        import os
        credentials_path = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
        
        if not credentials_path:
            raise ExportError(
                "Google service account credentials not configured. "
                "Set GOOGLE_SERVICE_ACCOUNT_JSON environment variable or pass credentials_path."
            )
    
    try:
        # Load service account credentials
        SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
        credentials = service_account.Credentials.from_service_account_file(
            credentials_path,
            scopes=SCOPES
        )
        
        # Build Sheets API service
        service = build('sheets', 'v4', credentials=credentials)
        
        # Prepare data: headers + rows
        # Convert row dicts to lists in same order as headers
        data_rows = [[row.get(header, "") for header in headers] for row in rows]
        all_data = [headers] + data_rows
        
        # Clear existing data in worksheet
        clear_range = f"{worksheet_name}!A:Z"  # Adjust if you need more columns
        
        try:
            service.spreadsheets().values().clear(
                spreadsheetId=sheet_id,
                range=clear_range
            ).execute()
        except HttpError as e:
            # If worksheet doesn't exist, try to create it
            if e.resp.status == 400:
                try:
                    service.spreadsheets().batchUpdate(
                        spreadsheetId=sheet_id,
                        body={
                            'requests': [{
                                'addSheet': {
                                    'properties': {
                                        'title': worksheet_name
                                    }
                                }
                            }]
                        }
                    ).execute()
                except HttpError:
                    # Worksheet might already exist, continue
                    pass
        
        # Write data to worksheet
        update_range = f"{worksheet_name}!A1"
        body = {
            'values': all_data,
            'majorDimension': 'ROWS'
        }
        
        result = service.spreadsheets().values().update(
            spreadsheetId=sheet_id,
            range=update_range,
            valueInputOption='RAW',
            body=body
        ).execute()
        
        updated_cells = result.get('updatedCells', 0)
        updated_rows = len(data_rows)
        
        logger.info(
            f"Successfully synced to Google Sheets",
            extra={
                "sheet_id": sheet_id,
                "worksheet": worksheet_name,
                "rows": updated_rows,
                "cells": updated_cells
            }
        )
        
        return {
            'success': True,
            'message': f'Successfully synced {updated_rows} rows to Google Sheets',
            'updated_rows': updated_rows,
            'sheet_url': f'https://docs.google.com/spreadsheets/d/{sheet_id}'
        }
    
    except FileNotFoundError:
        raise ExportError(f"Service account credentials file not found: {credentials_path}")
    
    except HttpError as e:
        logger.error(f"Google Sheets API error: {str(e)}", exc_info=True)
        raise ExportError(f"Google Sheets sync failed: {str(e)}")
    
    except Exception as e:
        logger.error(f"Unexpected error in Google Sheets sync: {str(e)}", exc_info=True)
        raise ExportError(f"Failed to sync to Google Sheets: {str(e)}")
