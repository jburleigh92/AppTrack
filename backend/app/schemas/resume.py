from datetime import datetime
from typing import Literal, Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel


class ResumeDataResponse(BaseModel):
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin_url: Optional[str] = None
    skills: List[str] = []
    experience: List[Dict[str, Any]] = []
    education: List[Dict[str, Any]] = []
    extraction_complete: bool

    class Config:
        from_attributes = True


class ResumeUploadResponse(BaseModel):
    resume_id: UUID
    status: Literal["parsed", "failed"]
    resume_data: Optional[ResumeDataResponse] = None
    error_message: Optional[str] = None
    warnings: List[str] = []


class ResumeResponse(BaseModel):
    id: UUID
    filename: str
    file_size_bytes: int
    mime_type: str
    status: str
    is_active: bool
    uploaded_at: datetime

    class Config:
        from_attributes = True
