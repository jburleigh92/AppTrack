from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, HttpUrl


class JobPostingBase(BaseModel):
    url: str
    normalized_url: Optional[str] = None
    title: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None
    requirements: Optional[str] = None
    employment_type: Optional[str] = None
    salary_range: Optional[str] = None
    source: Optional[str] = None


class JobPostingCreate(JobPostingBase):
    pass


class JobPostingResponse(JobPostingBase):
    id: UUID
    extraction_complete: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ScrapedPostingResponse(BaseModel):
    id: UUID
    url: str
    http_status_code: int
    scraped_at: datetime
    job_posting_id: Optional[UUID] = None
    
    class Config:
        from_attributes = True
