import logging
import csv
import io
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.api.dependencies.database import get_db
from app.schemas.export import (
    ExportFilters,
    CSVExportResponse,
    SheetsSyncRequest,
    SheetsSyncResponse
)
from app.services.export_service import (
    generate_export_rows,
    sync_to_google_sheets,
    ExportError
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/csv")
def export_to_csv(
    filters: ExportFilters,
    db: Session = Depends(get_db)
):
    """
    Export applications to CSV with optional filters.
    
    Returns a streaming CSV file download.
    Handles empty results gracefully (returns headers with no data rows).
    """
    try:
        # Generate export data
        headers, rows = generate_export_rows(db, filters)
        
        # Create CSV in memory
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=headers)
        
        # Write headers
        writer.writeheader()
        
        # Write data rows
        for row in rows:
            writer.writerow(row)
        
        # Get CSV content
        csv_content = output.getvalue()
        output.close()
        
        # Generate filename with timestamp
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_filename = f"applications_export_{timestamp}.csv"
        
        logger.info(
            f"CSV export generated: {export_filename}, rows: {len(rows)}"
        )
        
        # Return streaming response
        return StreamingResponse(
            io.BytesIO(csv_content.encode('utf-8')),
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="{export_filename}"'
            }
        )
    
    except Exception as e:
        logger.error(f"CSV export failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate CSV export: {str(e)}"
        )


@router.post("/sheets", response_model=SheetsSyncResponse)
def sync_to_sheets(
    request: SheetsSyncRequest,
    db: Session = Depends(get_db)
):
    """
    Sync applications to Google Sheets with optional filters.
    
    Requires:
    - GOOGLE_SERVICE_ACCOUNT_JSON environment variable pointing to service account JSON
    - Service account must have edit access to the target spreadsheet
    
    The worksheet will be cleared and rewritten with current data.
    """
    try:
        # Generate export data
        filters = request.filters or ExportFilters()
        headers, rows = generate_export_rows(db, filters)
        
        # Sync to Google Sheets
        result = sync_to_google_sheets(
            headers=headers,
            rows=rows,
            sheet_id=request.sheet_id,
            worksheet_name=request.worksheet_name or "Applications"
        )
        
        logger.info(
            f"Google Sheets sync completed: {request.sheet_id}, rows: {result['updated_rows']}"
        )
        
        return SheetsSyncResponse(
            success=result['success'],
            message=result['message'],
            updated_rows=result['updated_rows'],
            sheet_url=result.get('sheet_url')
        )
    
    except ExportError as e:
        logger.error(f"Google Sheets sync failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
    
    except Exception as e:
        logger.error(f"Unexpected error in Sheets sync: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to sync to Google Sheets: {str(e)}"
        )
