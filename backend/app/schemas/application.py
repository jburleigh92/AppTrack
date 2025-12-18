from datetime import date, datetime
from typing import Optional, Literal
from uuid import UUID
from pydantic import BaseModel, Field, HttpUrl


class CaptureApplicationRequest(BaseModel):
    company_name: str = Field(..., min_length=1, max_length=255)
    job_title: str = Field(..., min_length=1, max_length=255)
    job_posting_url: Optional[str] = Field(None, max_length=2048)
    notes: Optional[str] = Field(None, max_length=10000)

    class Config:
        from_attributes = True


class UpdateApplicationRequest(BaseModel):
    status: Optional[Literal["applied", "screening", "interview", "offer", "rejected", "withdrawn"]] = None
    notes: Optional[str] = Field(None, max_length=10000)

    class Config:
        from_attributes = True


class ApplicationResponse(BaseModel):
    id: UUID
    company_name: str
    job_title: str
    job_posting_url: Optional[str]
    application_date: date
    status: str
    source: str
    job_board_source: Optional[str]
    notes: Optional[str]
    needs_review: bool
    analysis_completed: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
