from datetime import datetime
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AdvisorySignal(BaseModel):
    """Representation of a single advisory signal."""

    model_config = ConfigDict(protected_namespaces=())

    type: str = Field(..., description="Type of advisory signal")
    confidence: Optional[float] = Field(
        None, description="Confidence score for this advisory signal"
    )
    summary: Optional[str] = Field(
        None, description="Short, advisory-only summary if available"
    )
    details: Optional[Dict[str, Any]] = Field(
        None, description="Opaque payload with advisory context"
    )
    model_version: str = Field(..., description="Model version used to compute signal")
    computed_at: Optional[datetime] = Field(
        None, description="Timestamp when the advisory signal was computed"
    )


class AdvisoryEnvelope(BaseModel):
    """Container for advisory data exposed via WS5."""

    model_config = ConfigDict(protected_namespaces=())

    resume_id: UUID
    job_posting_id: UUID
    advisory_only: bool = Field(
        True, description="Indicates this payload is advisory-only and non-authoritative"
    )
    generated_at: Optional[datetime] = Field(
        None, description="Timestamp of the most recent advisory signal"
    )
    signals: List[AdvisorySignal] = Field(
        default_factory=list, description="List of advisory signals"
    )
