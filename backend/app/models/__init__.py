from app.models.account import Account as Account
from app.models.audit_trail import AuditTrail as AuditTrail
from app.models.base import Base as Base
from app.models.customer import Customer as Customer
from app.models.holding import ProductHolding as ProductHolding
from app.models.product_catalog import ProductCatalog as ProductCatalog
from app.models.risk_incident import RiskIncident as RiskIncident
from app.models.transaction import Transaction as Transaction
from app.models.user import User as User
from app.models.workflow_case import WorkflowCase as WorkflowCase

target_metadata = Base.metadata
