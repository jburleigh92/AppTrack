from datetime import date
from typing import Optional
from pydantic import BaseModel, Field


class ExportFilters(BaseModel):
    """Filters for export operations."""
    status: Optional[str] = Field(None, description="Filter by application status")
    company_name: Optional[str] = Field(None, description="Filter by company name (partial match)")
    date_from: Optional[date] = Field(None, description="Filter applications from this date")
    date_to: Optional[date] = Field(None, description="Filter applications until this date")
    
    class Config:
        from_attributes = True


class CSVExportResponse(BaseModel):
    """Response for CSV export (streaming, no download_url needed)."""
    message: str = "CSV export generated successfully"
    row_count: int


class SheetsSyncRequest(BaseModel):
    """Request to sync data to Google Sheets."""
    sheet_id: str = Field(..., description="Google Sheets spreadsheet ID")
    worksheet_name: Optional[str] = Field("Applications", description="Worksheet/tab name")
    filters: Optional[ExportFilters] = Field(default_factory=ExportFilters, description="Optional filters")
    
    class Config:
        from_attributes = True


class SheetsSyncResponse(BaseModel):
    """Response after syncing to Google Sheets."""
    success: bool
    message: str
    updated_rows: int
    sheet_url: Optional[str] = None
