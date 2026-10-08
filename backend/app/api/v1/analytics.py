from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.database import get_db
from app.models.customer import Customer
from app.models.holding import ProductHolding
from app.models.product_catalog import ProductCatalog
from app.models.risk_incident import RiskIncident
from app.models.transaction import Transaction
from app.models.user import User
from app.models.workflow_case import WorkflowCase
from app.schemas.common import APIResponse

router = APIRouter()


def _enum_key(val: object) -> str:
    return val.value if hasattr(val, "value") else str(val)


@router.get("/summary")
async def get_analytics_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    # ── Headline KPIs ────────────────────────────────────────────────────────

    total_customers = await db.scalar(select(func.count(Customer.id))) or 0
    total_aum = float(await db.scalar(select(func.sum(ProductHolding.current_value))) or 0)
    estimated_revenue = float(
        await db.scalar(
            select(func.sum(ProductHolding.current_value * ProductCatalog.fee_pct / 100)).join(
                ProductCatalog, ProductHolding.product_id == ProductCatalog.id
            )
        )
        or 0
    )
    avg_credit_score = round(
        float(await db.scalar(select(func.avg(Customer.credit_score))) or 0), 1
    )
    total_incidents = await db.scalar(select(func.count(RiskIncident.id))) or 0
    pending_review_cases = (
        await db.scalar(
            select(func.count(WorkflowCase.id)).where(WorkflowCase.status == "pending_review")
        )
        or 0
    )
    escalated_cases = (
        await db.scalar(
            select(func.count(WorkflowCase.id)).where(WorkflowCase.status == "escalated")
        )
        or 0
    )

    # ── Customer distributions ───────────────────────────────────────────────

    credit_bin = case(
        (Customer.credit_score < 500, "300-499"),
        (Customer.credit_score < 600, "500-599"),
        (Customer.credit_score < 700, "600-699"),
        (Customer.credit_score < 750, "700-749"),
        (Customer.credit_score < 800, "750-799"),
        else_="800+",
    )
    credit_rows = (
        await db.execute(
            select(credit_bin.label("range"), func.count(Customer.id).label("count")).group_by(
                credit_bin
            )
        )
    ).all()
    order = ["300-499", "500-599", "600-699", "700-749", "750-799", "800+"]
    credit_map = {r.range: r.count for r in credit_rows}
    credit_score_distribution = [
        {"range": b, "count": credit_map.get(b, 0)} for b in order
    ]

    seg_rows = (
        await db.execute(
            select(Customer.segment, func.count(Customer.id).label("count")).group_by(
                Customer.segment
            )
        )
    ).all()
    segment_distribution = {_enum_key(r.segment): r.count for r in seg_rows}

    kyc_rows = (
        await db.execute(
            select(Customer.kyc_status, func.count(Customer.id).label("count")).group_by(
                Customer.kyc_status
            )
        )
    ).all()
    kyc_status_distribution = {_enum_key(r.kyc_status): r.count for r in kyc_rows}

    # ── AUM breakdowns ───────────────────────────────────────────────────────

    aum_seg_rows = (
        await db.execute(
            select(
                Customer.segment,
                func.sum(ProductHolding.current_value).label("aum"),
            )
            .join(ProductHolding, ProductHolding.customer_id == Customer.id)
            .group_by(Customer.segment)
        )
    ).all()
    aum_by_segment = {_enum_key(r.segment): float(r.aum or 0) for r in aum_seg_rows}

    pt_rows = (
        await db.execute(
            select(
                ProductHolding.product_type,
                func.sum(ProductHolding.current_value).label("aum"),
            )
            .group_by(ProductHolding.product_type)
            .order_by(func.sum(ProductHolding.current_value).desc())
        )
    ).all()
    product_type_distribution = {
        _enum_key(r.product_type): float(r.aum or 0) for r in pt_rows
    }

    # ── Incident distributions ───────────────────────────────────────────────

    inc_type_rows = (
        await db.execute(
            select(RiskIncident.incident_type, func.count(RiskIncident.id).label("count")).group_by(
                RiskIncident.incident_type
            )
        )
    ).all()
    incident_type_distribution = {_enum_key(r.incident_type): r.count for r in inc_type_rows}

    inc_sev_rows = (
        await db.execute(
            select(RiskIncident.severity, func.count(RiskIncident.id).label("count")).group_by(
                RiskIncident.severity
            )
        )
    ).all()
    incident_severity_distribution = {_enum_key(r.severity): r.count for r in inc_sev_rows}

    # ── Case distributions ───────────────────────────────────────────────────

    case_type_rows = (
        await db.execute(
            select(WorkflowCase.case_type, func.count(WorkflowCase.id).label("count")).group_by(
                WorkflowCase.case_type
            )
        )
    ).all()
    cases_by_type = {_enum_key(r.case_type): r.count for r in case_type_rows}

    case_status_rows = (
        await db.execute(
            select(WorkflowCase.status, func.count(WorkflowCase.id).label("count")).group_by(
                WorkflowCase.status
            )
        )
    ).all()
    cases_by_status = {_enum_key(r.status): r.count for r in case_status_rows}

    # ── Time series ──────────────────────────────────────────────────────────

    tx_rows = (
        await db.execute(
            select(
                func.strftime("%Y-%m", Transaction.timestamp).label("month"),
                func.sum(Transaction.amount).label("volume"),
            )
            .group_by(func.strftime("%Y-%m", Transaction.timestamp))
            .order_by(func.strftime("%Y-%m", Transaction.timestamp))
        )
    ).all()
    monthly_transaction_volume = [
        {"month": r.month, "volume": float(r.volume or 0)} for r in tx_rows
    ]

    case_month_rows = (
        await db.execute(
            select(
                func.strftime("%Y-%m", WorkflowCase.created_at).label("month"),
                func.count(WorkflowCase.id).label("count"),
            )
            .group_by(func.strftime("%Y-%m", WorkflowCase.created_at))
            .order_by(func.strftime("%Y-%m", WorkflowCase.created_at))
        )
    ).all()
    monthly_cases = [{"month": r.month, "count": r.count} for r in case_month_rows]

    aum_month_rows = (
        await db.execute(
            select(
                func.strftime("%Y-%m", ProductHolding.acquisition_date).label("month"),
                func.sum(ProductHolding.current_value).label("aum"),
            )
            .group_by(func.strftime("%Y-%m", ProductHolding.acquisition_date))
            .order_by(func.strftime("%Y-%m", ProductHolding.acquisition_date))
        )
    ).all()
    cumulative = 0.0
    monthly_aum: list[dict] = []
    for row in aum_month_rows:
        cumulative += float(row.aum or 0)
        monthly_aum.append({"month": row.month, "aum": cumulative})

    return APIResponse(
        status="success",
        data={
            "total_customers": total_customers,
            "total_aum": total_aum,
            "estimated_revenue": estimated_revenue,
            "avg_credit_score": avg_credit_score,
            "total_incidents": total_incidents,
            "pending_review_cases": pending_review_cases,
            "escalated_cases": escalated_cases,
            "credit_score_distribution": credit_score_distribution,
            "segment_distribution": segment_distribution,
            "kyc_status_distribution": kyc_status_distribution,
            "aum_by_segment": aum_by_segment,
            "product_type_distribution": product_type_distribution,
            "incident_type_distribution": incident_type_distribution,
            "incident_severity_distribution": incident_severity_distribution,
            "cases_by_type": cases_by_type,
            "cases_by_status": cases_by_status,
            "monthly_transaction_volume": monthly_transaction_volume,
            "monthly_cases": monthly_cases,
            "monthly_aum": monthly_aum,
        },
        meta={"timestamp": datetime.now(timezone.utc).isoformat()},
    )
