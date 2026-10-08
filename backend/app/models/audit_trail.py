from sqlalchemy import Column, String
from sqlalchemy.dialects.sqlite import JSON

from .base import Base, TimestampMixin, UUIDMixin


class AuditTrail(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "audit_trails"

    entity_type = Column(String(50), nullable=False) # e.g 'Transaction', 'Customer'
    entity_id = Column(String(36), nullable=False)
    action = Column(String(50), nullable=False) # e.g 'UPDATE', 'DELETE'
    actor_id = Column(String(36), nullable=False) # ID of user or AI agent
    changes = Column(JSON, nullable=True) # The diff payload
