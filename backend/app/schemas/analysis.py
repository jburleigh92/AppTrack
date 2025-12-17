from datetime import datetime
from typing import Optional, List, Dict, Any, Literal
from uuid import UUID
from pydantic import BaseModel, Field, conint

from app.schemas.advisory import AdvisoryEnvelope


class AnalysisBase(BaseModel):
    match_score: conint(ge=0, le=100) = Field(..., description="Match score from 0-100")
    qualifications_met: List[str] = Field(default_factory=list, description="Qualifications candidate meets")
    qualifications_missing: List[str] = Field(default_factory=list, description="Qualifications candidate lacks")
    suggestions: List[str] = Field(default_factory=list, description="Skill suggestions for candidate")
    llm_provider: str = Field(..., description="LLM provider used")
    llm_model: str = Field(..., description="LLM model used")
    analysis_metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class AnalysisResponse(AnalysisBase):
    id: UUID
    application_id: UUID
    resume_id: UUID
    job_posting_id: UUID
    created_at: datetime
    advisory: Optional[AdvisoryEnvelope] = Field(
        default=None,
        description="Optional, non-authoritative advisory data (WS5)",
    )
    
    class Config:
        from_attributes = True


class AnalysisJobEnqueueRequest(BaseModel):
    application_id: UUID


class AnalysisJobEnqueueResponse(BaseModel):
    job_id: UUID
    status: Literal["queued"] = "queued"
