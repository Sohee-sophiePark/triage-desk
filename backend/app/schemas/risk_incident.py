import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict

from app.models.risk_incident import IncidentSeverity, IncidentStatus, IncidentType


class RiskIncidentBase(BaseModel):
    customer_id: uuid.UUID
    incident_type: Optional[IncidentType] = None
    severity: Optional[IncidentSeverity] = None
    status: Optional[IncidentStatus] = None
    description: Optional[str] = None
    evidence_json: Optional[Dict[str, Any]] = None
    related_transaction_ids: Optional[List[str]] = None
    created_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None

class RiskIncidentCreate(RiskIncidentBase):
    pass

class RiskIncidentResponse(RiskIncidentBase):
    id: uuid.UUID

    model_config = ConfigDict(from_attributes=True)
