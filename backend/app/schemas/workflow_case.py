from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.workflow_case import CaseStatus, CaseType


class WorkflowCaseResponse(BaseModel):
    """API response schema for a workflow case, including the full AI evaluation snapshot."""

    id: UUID
    case_type: Optional[CaseType]
    status: Optional[CaseStatus]
    incident_id: Optional[UUID]
    assigned_to: Optional[UUID]
    confidence_score: Optional[float]
    ai_evaluation: Optional[dict]
    human_decision: Optional[dict]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


class HumanDecisionRequest(BaseModel):
    """Request body for POST /cases/{id}/decide. Reasoning is mandatory (PRD EV-06)."""

    decision: Literal["approve", "reject", "escalate"]
    reasoning: str = Field(..., min_length=10)
