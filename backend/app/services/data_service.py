import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.audit_trail import AuditTrail
from app.models.customer import Customer
from app.models.holding import ProductHolding
from app.models.risk_incident import RiskIncident
from app.models.transaction import Transaction


class DataService:
    """Agent-facing async query helpers.

    Provides read-only access to DB entities for use inside LangGraph agent nodes.
    Not intended for direct use by API endpoint handlers — use SQLAlchemy queries there.
    All methods accept a live AsyncSession and return plain dicts suitable for JSON serialisation.
    """
    @staticmethod
    async def get_customer_360(db: AsyncSession, customer_id: uuid.UUID) -> dict:
        """Customer summary + accounts + holdings count + recent incident count."""
        result = await db.execute(select(Customer).where(Customer.id == customer_id))
        customer = result.scalar_one_or_none()
        if not customer:
            return {}

        account_result = await db.execute(
            select(func.count(Account.id)).where(Account.customer_id == customer_id)
        )
        account_count = account_result.scalar() or 0

        holding_result = await db.execute(
            select(func.count(ProductHolding.id)).where(ProductHolding.customer_id == customer_id)
        )
        holding_count = holding_result.scalar() or 0

        incident_result = await db.execute(
            select(func.count(RiskIncident.id)).where(RiskIncident.customer_id == customer_id)
        )
        incident_count = incident_result.scalar() or 0

        return {
            "customer_id": str(customer.id),
            "external_id": customer.external_id,
            "segment": customer.segment.value if customer.segment else None,
            "income_bracket": customer.income_bracket.value if customer.income_bracket else None,
            "credit_score": customer.credit_score,
            "risk_tolerance": customer.risk_tolerance.value if customer.risk_tolerance else None,
            "kyc_status": customer.kyc_status.value if customer.kyc_status else None,
            "account_count": account_count,
            "holding_count": holding_count,
            "incident_count": incident_count,
        }

    @staticmethod
    async def get_flagged_transactions(
        db: AsyncSession, customer_id: uuid.UUID, limit: int = 20
    ) -> list[dict]:
        """Transactions with risk_flag=True for a customer (via accounts join)."""
        account_result = await db.execute(
            select(Account.id).where(Account.customer_id == customer_id)
        )
        account_ids = [row[0] for row in account_result.fetchall()]
        if not account_ids:
            return []

        txn_result = await db.execute(
            select(Transaction)
            .where(
                Transaction.account_id.in_(account_ids),
                Transaction.risk_flag == True,  # noqa: E712
            )
            .order_by(Transaction.timestamp.desc())
            .limit(limit)
        )
        transactions = txn_result.scalars().all()

        return [
            {
                "id": str(t.id),
                "amount": float(t.amount),
                "category": t.category,
                "merchant": t.merchant,
                "channel": t.channel.value if t.channel else None,
                "status": t.status.value if t.status else None,
                "risk_flag": t.risk_flag,
                "timestamp": t.timestamp.isoformat() if t.timestamp else None,
            }
            for t in transactions
        ]

    @staticmethod
    async def get_recent_transactions(
        db: AsyncSession, customer_id: uuid.UUID, limit: int = 20
    ) -> list[dict]:
        """Most recent transactions for a customer (via accounts join)."""
        account_result = await db.execute(
            select(Account.id).where(Account.customer_id == customer_id)
        )
        account_ids = [row[0] for row in account_result.fetchall()]
        if not account_ids:
            return []

        txn_result = await db.execute(
            select(Transaction)
            .where(Transaction.account_id.in_(account_ids))
            .order_by(Transaction.timestamp.desc())
            .limit(limit)
        )
        transactions = txn_result.scalars().all()

        return [
            {
                "id": str(t.id),
                "amount": float(t.amount),
                "category": t.category,
                "merchant": t.merchant,
                "channel": t.channel.value if t.channel else None,
                "status": t.status.value if t.status else None,
                "risk_flag": t.risk_flag,
                "timestamp": t.timestamp.isoformat() if t.timestamp else None,
            }
            for t in transactions
        ]

    @staticmethod
    async def get_case_audit(db: AsyncSession, case_id: uuid.UUID) -> list[dict]:
        """All AuditTrail rows for a case, ordered by created_at."""
        result = await db.execute(
            select(AuditTrail)
            .where(
                AuditTrail.entity_type == "WorkflowCase",
                AuditTrail.entity_id == str(case_id),
            )
            .order_by(AuditTrail.created_at.asc())
        )
        rows = result.scalars().all()
        return [
            {
                "id": str(r.id),
                "action": r.action,
                "actor_id": r.actor_id,
                "changes": r.changes,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]
