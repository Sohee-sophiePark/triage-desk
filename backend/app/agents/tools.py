"""Read-only, case-bound tools: every number the agents see is a Metric computed here."""
import statistics
import uuid
from datetime import timedelta
from typing import Literal

from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.customer import Customer
from app.models.risk_incident import RiskIncident
from app.models.transaction import Transaction

WINDOW_DAYS = 30
NEAR_THRESHOLD = (9000.0, 10000.0)  # just under the cash-reporting threshold
MAX_EVIDENCE = 8


class Metric(BaseModel):
    key: str
    value: float | str
    unit: Literal["count", "ratio", "usd", "score", "text"]
    label: str
    source: str


# Which metrics each specialist sees (isolated context).
SLICES = {
    "transactions": ["txn_count_30d", "txn_monthly_avg_prior", "velocity_ratio", "max_amount_30d",
                     "median_amount_prior", "amount_outlier_ratio", "flagged_txn_count_30d"],
    "customer": ["credit_score", "kyc_status", "segment", "account_count", "prior_incident_count",
                 "incident_type", "incident_severity"],
    "compliance": ["kyc_status", "near_threshold_count_30d", "flagged_txn_count_30d", "max_amount_30d",
                   "incident_type"],
}


def _m(key, value, unit, label, source) -> tuple[str, Metric]:
    return key, Metric(key=key, value=value, unit=unit, label=label, source=source)


async def transaction_metrics(db: AsyncSession, customer_id: uuid.UUID) -> tuple[dict[str, Metric], dict[str, dict]]:
    """Velocity, outliers, near-threshold activity over the last 30 days vs the prior baseline; plus evidence refs."""
    rows = (await db.execute(
        select(Transaction).join(Account, Transaction.account_id == Account.id)
        .where(Account.customer_id == customer_id).order_by(Transaction.timestamp)
    )).scalars().all()
    src = "transaction_metrics"
    if not rows:
        zero = [("txn_count_30d", "count", "Transactions in the last 30 days"),
                ("txn_monthly_avg_prior", "count", "Average transactions per month before that"),
                ("velocity_ratio", "ratio", "Recent volume vs baseline"),
                ("max_amount_30d", "usd", "Largest transaction in the last 30 days"),
                ("median_amount_prior", "usd", "Median transaction before that"),
                ("amount_outlier_ratio", "ratio", "Largest recent vs median baseline"),
                ("near_threshold_count_30d", "count", "Recent transactions just under $10,000"),
                ("flagged_txn_count_30d", "count", "Recent transactions flagged by rules")]
        return dict(_m(k, 0.0, u, lbl, src) for k, u, lbl in zero), {}

    anchor = rows[-1].timestamp
    cutoff = anchor - timedelta(days=WINDOW_DAYS)
    recent = [t for t in rows if t.timestamp > cutoff]
    prior = [t for t in rows if t.timestamp <= cutoff]
    prior_months = max((cutoff - rows[0].timestamp).days / WINDOW_DAYS, 1.0) if prior else 1.0
    prior_avg = len(prior) / prior_months
    max_recent = max(float(t.amount) for t in recent)
    median_prior = statistics.median(float(t.amount) for t in prior) if prior else 0.0
    near = [t for t in recent if NEAR_THRESHOLD[0] <= float(t.amount) < NEAR_THRESHOLD[1]]
    flagged = [t for t in recent if t.risk_flag]

    metrics = dict([
        _m("txn_count_30d", float(len(recent)), "count", "Transactions in the last 30 days", src),
        _m("txn_monthly_avg_prior", round(prior_avg, 1), "count", "Average transactions per month before that", src),
        _m("velocity_ratio", round(len(recent) / max(prior_avg, 1.0), 2), "ratio", "Recent volume vs baseline", src),
        _m("max_amount_30d", round(max_recent, 2), "usd", "Largest transaction in the last 30 days", src),
        _m("median_amount_prior", round(median_prior, 2), "usd", "Median transaction before that", src),
        _m("amount_outlier_ratio", round(max_recent / median_prior, 2) if median_prior else 0.0, "ratio",
           "Largest recent vs median baseline", src),
        _m("near_threshold_count_30d", float(len(near)), "count", "Recent transactions just under $10,000", src),
        _m("flagged_txn_count_30d", float(len(flagged)), "count", "Recent transactions flagged by rules", src),
    ])

    picked = sorted({*flagged, *near, max(recent, key=lambda t: float(t.amount))},
                    key=lambda t: (-float(t.amount), str(t.id)))[:MAX_EVIDENCE]
    evidence = {
        f"T{i}": {"id": str(t.id), "amount": float(t.amount), "date": t.timestamp.date().isoformat(),
                  "merchant": t.merchant, "channel": t.channel.value if t.channel else None,
                  "flagged": bool(t.risk_flag)}
        for i, t in enumerate(picked, 1)
    }
    return metrics, evidence


async def customer_metrics(db: AsyncSession, incident: RiskIncident) -> dict[str, Metric]:
    """Profile, KYC and incident context; no names or contact details."""
    c = (await db.execute(select(Customer).where(Customer.id == incident.customer_id))).scalar_one_or_none()
    accounts = (await db.execute(select(func.count(Account.id)).where(Account.customer_id == incident.customer_id))).scalar() or 0
    prior = (await db.execute(select(func.count(RiskIncident.id)).where(
        RiskIncident.customer_id == incident.customer_id, RiskIncident.id != incident.id))).scalar() or 0
    src = "customer_metrics"
    return dict([
        _m("credit_score", float(c.credit_score or 0) if c else 0.0, "score", "Credit score", src),
        _m("kyc_status", c.kyc_status.value if c and c.kyc_status else "unknown", "text", "KYC status", src),
        _m("segment", c.segment.value if c and c.segment else "unknown", "text", "Customer segment", src),
        _m("account_count", float(accounts), "count", "Open accounts", src),
        _m("prior_incident_count", float(prior), "count", "Other incidents on file", src),
        _m("incident_type", incident.incident_type.value if incident.incident_type else "unknown", "text",
           "Incident type", src),
        _m("incident_severity", incident.severity.value if incident.severity else "unknown", "text",
           "Severity reported by the alert", src),
    ])
