from datetime import date
from typing import Optional
from pydantic import BaseModel, Field


class EmailIngestRequest(BaseModel):
    message_id: str = Field(..., min_length=1, max_length=255)
    from_email: str = Field(..., description="Email address")
    subject: str
    body_snippet: str
    application_date: date
    company_name: Optional[str] = Field(None, max_length=255)
    job_title: Optional[str] = Field(None, max_length=255)
    job_posting_url: Optional[str] = Field(None, max_length=2048)

    class Config:
        from_attributes = True


class EmailIngestResponse(BaseModel):
    status: str
    duplicate: bool = False
    strategy: Optional[str] = None
    application_id: Optional[str] = None

    class Config:
        from_attributes = True
