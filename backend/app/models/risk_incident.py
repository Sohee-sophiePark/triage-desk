import enum
import uuid

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin


class IncidentType(str, enum.Enum):
    fraud_alert = "fraud_alert"
    aml_flag = "aml_flag"
    credit_breach = "credit_breach"
    suspicious_txn = "suspicious_txn"
    identity_theft = "identity_theft"

class IncidentSeverity(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"

class IncidentStatus(str, enum.Enum):
    open = "open"
    investigating = "investigating"
    resolved = "resolved"
    dismissed = "dismissed"
    escalated = "escalated"

class RiskIncident(Base, UUIDMixin):
    __tablename__ = "risk_incidents"

    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customers.id"), index=True)
    incident_type: Mapped[IncidentType] = mapped_column(Enum(IncidentType), nullable=True)
    severity: Mapped[IncidentSeverity] = mapped_column(Enum(IncidentSeverity), nullable=True)
    status: Mapped[IncidentStatus] = mapped_column(Enum(IncidentStatus), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    evidence_json: Mapped[dict] = mapped_column(JSON, nullable=True)
    related_transaction_ids: Mapped[list] = mapped_column(JSON, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime, nullable=True)
    resolved_at: Mapped[DateTime] = mapped_column(DateTime, nullable=True)
    resolution_notes: Mapped[str] = mapped_column(Text, nullable=True)

    customer = relationship("Customer", back_populates="risk_incidents")
