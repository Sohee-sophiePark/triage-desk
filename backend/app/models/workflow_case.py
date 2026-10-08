import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDMixin


class CaseType(str, enum.Enum):
    fraud = "fraud"
    risk = "risk"
    compliance = "compliance"

class CaseStatus(str, enum.Enum):
    created = "created"
    ai_processing = "ai_processing"
    ai_evaluated = "ai_evaluated"
    pending_review = "pending_review"
    in_review = "in_review"
    human_decided = "human_decided"
    escalated = "escalated"
    closed = "closed"

class WorkflowCase(Base, UUIDMixin):
    __tablename__ = "workflow_cases"

    case_type: Mapped[CaseType] = mapped_column(Enum(CaseType), nullable=True)
    status: Mapped[CaseStatus] = mapped_column(Enum(CaseStatus), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    # Phase 4 additions
    incident_id: Mapped[uuid.UUID] = mapped_column(nullable=True)
    assigned_to: Mapped[uuid.UUID] = mapped_column(nullable=True)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=True)
    ai_evaluation: Mapped[dict] = mapped_column(JSON, nullable=True)
    human_decision: Mapped[dict] = mapped_column(JSON, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
