from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel


class ResumeUploadResponse(BaseModel):
    resume_id: UUID
    parser_job_id: UUID
    status: Literal["enqueued"] = "enqueued"
    message: str = "Resume uploaded and queued for parsing"


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
