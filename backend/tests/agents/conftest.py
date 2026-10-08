"""Factory for case data with a controlled transaction history (fixed anchor date, synthetic values only)."""
import uuid
from datetime import date, datetime, timedelta

import pytest

from app.models.account import Account, AccountType
from app.models.customer import Customer, IncomeBracket, KYCStatus, RiskTolerance, Segment
from app.models.risk_incident import IncidentSeverity, IncidentStatus, IncidentType, RiskIncident
from app.models.transaction import Transaction, TransactionChannel

ANCHOR = datetime(2026, 3, 31, 12, 0)


@pytest.fixture
def make_incident(db):
    async def _make(recent=(100.0,) * 10, prior=(100.0,) * 50, flagged_recent=0, kyc="verified", credit=700,
                    description="Unusual account activity reported by monitoring.",
                    incident_type=IncidentType.fraud_alert) -> RiskIncident:
        tag = uuid.uuid4().hex[:8]
        customer = Customer(
            id=uuid.uuid4(), external_id=f"AG-{tag}", first_name="Agent", last_name="Test",
            date_of_birth=date(1980, 1, 1), email=f"agent-{tag}@test.com", income_bracket=IncomeBracket.medium,
            credit_score=credit, risk_tolerance=RiskTolerance.moderate, segment=Segment.mass,
            kyc_status=KYCStatus(kyc),
        )
        account = Account(id=uuid.uuid4(), customer_id=customer.id, account_number=f"ACT-{tag}",
                          account_type=AccountType.checking, opened_date=date(2020, 1, 1))
        db.add_all([customer, account])
        # prior: spread evenly over the five months before the 30-day window
        for i, amount in enumerate(prior):
            ts = ANCHOR - timedelta(days=31 + i * (150 / max(len(prior), 1)))
            db.add(Transaction(id=uuid.uuid4(), account_id=account.id, amount=amount, merchant=f"Shop {i}",
                               channel=TransactionChannel.online, timestamp=ts))
        for i, amount in enumerate(recent):
            db.add(Transaction(id=uuid.uuid4(), account_id=account.id, amount=amount, merchant=f"Recent {i}",
                               channel=TransactionChannel.mobile, timestamp=ANCHOR - timedelta(days=i % 29),
                               risk_flag=i < flagged_recent))
        incident = RiskIncident(id=uuid.uuid4(), customer_id=customer.id, incident_type=incident_type,
                                severity=IncidentSeverity.medium, status=IncidentStatus.open,
                                description=description, created_at=ANCHOR)
        db.add(incident)
        await db.commit()
        return incident
    return _make
