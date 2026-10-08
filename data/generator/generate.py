import argparse
import asyncio
import logging
import os
import random
import uuid
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.base import Base
from app.models.account import Account, AccountType
from app.models.customer import Customer, IncomeBracket, KYCStatus, RiskTolerance, Segment
from app.models.holding import ProductHolding, ProductCategory
from app.models.product_catalog import CatalogCategory, ProductCatalog, ProductRiskLevel
from app.models.risk_incident import IncidentSeverity, IncidentStatus, IncidentType, RiskIncident
from app.models.transaction import Transaction, TransactionChannel, TransactionStatus, TransactionType

from distributions import generate_income, generate_age, determine_segment
from correlations import (
    accounts_per_customer,
    derive_risk_tolerance,
    generate_correlated_credit_score,
    txn_amount_distribution,
    txns_per_account_monthly,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

FIRST_NAMES = [
    "James", "Mary", "Robert", "Patricia", "John", "Jennifer", "Michael",
    "Linda", "David", "Elizabeth", "William", "Barbara", "Richard", "Susan",
    "Joseph", "Jessica", "Thomas", "Sarah", "Charles", "Karen",
]
LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
    "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Wilson",
    "Anderson", "Taylor", "Thomas", "Moore", "Jackson",
]
MERCHANTS = [
    "Amazon", "Walmart", "Target", "Costco", "Whole Foods", "Starbucks",
    "Shell", "BP", "Delta Airlines", "Marriott", "Apple Store", "Netflix",
    "Uber", "Lyft", "CVS", "Walgreens", "Home Depot", "Best Buy",
    "Nordstrom", "Trader Joe's", "Southwest Airlines", "Hilton",
]
CATEGORIES = [
    "groceries", "utilities", "travel", "dining", "entertainment",
    "investment", "transfer", "insurance", "medical", "retail",
]

# ── Income bracket mapping ────────────────────────────────────────────────────

def _income_bracket(income: float) -> IncomeBracket:
    if income < 40000:
        return IncomeBracket.low
    if income < 100000:
        return IncomeBracket.medium
    if income < 300000:
        return IncomeBracket.high
    return IncomeBracket.very_high


# ── Product catalog (~15 products across all categories) ────────────────────

def create_catalog(session: AsyncSession) -> dict[str, list[uuid.UUID]]:
    """Returns mapping of product_type → list of product_ids."""
    products = [
        # Deposits
        ("Premium Checking",          CatalogCategory.deposit, ProductRiskLevel.low,    100,    0.5,  0.0),
        ("High-Yield Savings",       CatalogCategory.deposit, ProductRiskLevel.low,    500,    4.5,  0.0),
        ("12-Month CD",             CatalogCategory.deposit, ProductRiskLevel.low,   1000,    5.1,  0.0),
        # Equities
        ("US Large Cap Equity Fund",  CatalogCategory.equity,  ProductRiskLevel.high,  1000,   10.2,  0.5),
        ("Emerging Markets ETF",      CatalogCategory.equity,  ProductRiskLevel.high,   500,   12.5,  0.3),
        ("Dividend Growth Fund",      CatalogCategory.equity,  ProductRiskLevel.medium, 2500,    7.8,  0.4),
        # Bonds
        ("US Treasury Bond Fund",     CatalogCategory.bond,    ProductRiskLevel.low,    500,    3.8,  0.2),
        ("Corporate Bond Portfolio",  CatalogCategory.bond,    ProductRiskLevel.medium, 2500,    5.2,  0.3),
        ("Municipal Bond Fund",       CatalogCategory.bond,    ProductRiskLevel.low,   1000,    3.2,  0.2),
        # Mutual funds / ETFs
        ("Balanced Growth Fund",      CatalogCategory.fund,    ProductRiskLevel.medium, 1000,    8.1,  0.6),
        ("S&P 500 Index ETF",         CatalogCategory.fund,    ProductRiskLevel.medium,  100,    9.5,  0.1),
        # Insurance
        ("Term Life Insurance",       CatalogCategory.insurance, ProductRiskLevel.low, 1200,    0.0,  0.0),
        ("Wealth Protection Plan",    CatalogCategory.insurance, ProductRiskLevel.low, 5000,    0.0,  0.0),
        # Loans
        ("Personal Loan",             CatalogCategory.loan,    ProductRiskLevel.medium, 5000,   -8.5,  2.0),
        ("Mortgage",                  CatalogCategory.loan,    ProductRiskLevel.medium,50000,   -6.5,  1.5),
    ]

    by_category: dict[str, list[uuid.UUID]] = {}
    for name, cat, risk, min_inv, ret, fee in products:
        pid = uuid.uuid4()
        p = ProductCatalog(
            id=pid,
            name=name,
            category=cat,
            risk_level=risk,
            min_investment=float(min_inv),
            expected_return_pct=float(ret),
            fee_pct=float(fee),
            description=f"{name} — auto-generated product.",
        )
        session.add(p)
        by_category.setdefault(cat.value, []).append(pid)

    return by_category


# ── Holdings: correlated with risk_tolerance ─────────────────────────────────

_RISK_PRODUCT_WEIGHTS: dict[str, dict[str, float]] = {
    "conservative": {"deposit": 0.50, "bond": 0.30, "fund": 0.10, "insurance": 0.10, "equity": 0.0,  "loan": 0.0},
    "moderate":     {"deposit": 0.25, "bond": 0.20, "fund": 0.25, "insurance": 0.10, "equity": 0.15, "loan": 0.05},
    "aggressive":   {"deposit": 0.10, "bond": 0.05, "fund": 0.20, "insurance": 0.05, "equity": 0.50, "loan": 0.10},
}

def _generate_holdings(
    customer_id: uuid.UUID,
    risk_tolerance: str,
    income: float,
    catalog: dict[str, list[uuid.UUID]],
) -> list[ProductHolding]:
    weights = _RISK_PRODUCT_WEIGHTS.get(risk_tolerance, _RISK_PRODUCT_WEIGHTS["moderate"])
    categories = [c for c, w in weights.items() if w > 0 and catalog.get(c)]
    cat_weights = [weights[c] for c in categories]

    # 1-4 holdings per customer
    n_holdings = random.randint(1, 4)
    chosen_cats = random.choices(categories, weights=cat_weights, k=n_holdings)

    holdings = []
    base_value = income * random.uniform(0.5, 3.0)
    for cat in chosen_cats:
        product_ids = catalog.get(cat, [])
        if not product_ids:
            continue
        pid = random.choice(product_ids)
        current_value = round(base_value * random.uniform(0.1, 0.6), 2)
        acquisition_price = round(current_value * random.uniform(0.7, 1.1), 2)
        qty = round(current_value / max(acquisition_price, 1), 4)
        acq_date = datetime.now().date() - timedelta(days=random.randint(30, 1500))
        holdings.append(ProductHolding(
            id=uuid.uuid4(),
            customer_id=customer_id,
            product_id=pid,
            product_type=ProductCategory(cat) if cat in ProductCategory.__members__ else ProductCategory.deposit,
            quantity=qty,
            current_value=current_value,
            acquisition_price=acquisition_price,
            acquisition_date=acq_date,
        ))
    return holdings


# ── Transactions: 6 months, temporal patterns, fraud injection ───────────────

_FRAUD_TXN_TYPES = [TransactionType.debit, TransactionType.withdrawal]
_NORMAL_TXN_TYPES = list(TransactionType)
_CHANNELS = list(TransactionChannel)

def _generate_transactions(
    account_id: uuid.UUID,
    segment: str,
    is_fraud_customer: bool,
    months: int = 6,
) -> list[Transaction]:
    txns = []
    now = datetime.now()
    start = now - timedelta(days=30 * months)

    monthly_counts = [txns_per_account_monthly(segment) for _ in range(months)]

    for month_idx in range(months):
        count = monthly_counts[month_idx]
        month_start = start + timedelta(days=30 * month_idx)

        # Fraud pattern: velocity spike — inject 3-5x normal volume in one month
        if is_fraud_customer and month_idx == months - 1:
            count = count * random.randint(3, 5)

        for _ in range(count):
            days_offset = random.randint(0, 29)
            hours_offset = random.randint(0, 23)
            ts = month_start + timedelta(days=days_offset, hours=hours_offset)

            amount = txn_amount_distribution(segment)

            # Fraud pattern: amount outlier (3σ) — spike amount 10-50x
            if is_fraud_customer and random.random() < 0.05:
                amount = amount * random.uniform(10, 50)

            risk_flag = is_fraud_customer and (amount > txn_amount_distribution(segment) * 8)

            txns.append(Transaction(
                id=uuid.uuid4(),
                account_id=account_id,
                amount=round(amount, 2),
                transaction_type=random.choice(_FRAUD_TXN_TYPES if is_fraud_customer else _NORMAL_TXN_TYPES),
                category=random.choice(CATEGORIES),
                merchant=random.choice(MERCHANTS),
                channel=random.choice(_CHANNELS),
                status=TransactionStatus.completed,
                risk_flag=risk_flag,
                timestamp=ts,
                description=f"{'[FLAGGED] ' if risk_flag else ''}Synthetic transaction",
            ))

    return txns


# ── Risk incident: linked to flagged transactions ─────────────────────────────

_SEV_BY_INCOME: dict[str, IncidentSeverity] = {
    "uhnw": IncidentSeverity.critical,
    "hnw": IncidentSeverity.high,
    "affluent": IncidentSeverity.medium,
    "mass": IncidentSeverity.low,
}

def _generate_incident(
    customer_id: uuid.UUID,
    segment: str,
    flagged_txn_ids: list[uuid.UUID],
) -> RiskIncident:
    incident_type = random.choice([
        IncidentType.fraud_alert,
        IncidentType.suspicious_txn,
        IncidentType.aml_flag,
        IncidentType.identity_theft,
        IncidentType.credit_breach,
    ])
    severity = _SEV_BY_INCOME.get(segment, IncidentSeverity.medium)
    evidence = {
        "triggered_rule": f"rule_{incident_type.value}_{random.randint(1, 99)}",
        "risk_score": round(random.uniform(60, 95), 1),
        "flagged_transactions": [str(tid) for tid in flagged_txn_ids[:5]],
        "pattern": random.choice(["velocity_spike", "amount_outlier", "geo_anomaly"]),
    }
    return RiskIncident(
        id=uuid.uuid4(),
        customer_id=customer_id,
        incident_type=incident_type,
        severity=severity,
        status=IncidentStatus.open,
        description=(
            f"Synthetic {incident_type.value.replace('_', ' ')} detected. "
            f"Pattern: {evidence['pattern']}. Risk score: {evidence['risk_score']}."
        ),
        evidence_json=evidence,
        related_transaction_ids=[str(tid) for tid in flagged_txn_ids[:5]],
    )


# ── Main generation loop ──────────────────────────────────────────────────────

async def generate(customers: int, output_path: str, seed: int | None = None) -> None:
    if seed is not None:
        random.seed(seed)

    logger.info("Generating %d customers → %s (seed=%s)", customers, output_path, seed)

    url = f"sqlite+aiosqlite:///{output_path}"
    engine = create_async_engine(url)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with AsyncSessionLocal() as session:
        catalog = create_catalog(session)
        await session.commit()
        logger.info("Product catalog: %d products across %d categories", 15, len(catalog))

        total_txns = 0
        total_holdings = 0
        total_incidents = 0

        for i in range(customers):
            income = generate_income()
            age = generate_age()
            seg = determine_segment(income)
            credit = generate_correlated_credit_score(income)
            risk = derive_risk_tolerance(age, seg)

            # ~3% fraud customers, guaranteed minimum 5 for small runs
            is_fraud = (random.random() < 0.03) or (i < 5 and customers >= 10 and i % (customers // 5) == 0)

            kyc_options = [KYCStatus.verified, KYCStatus.verified, KYCStatus.verified, KYCStatus.pending, KYCStatus.flagged]
            kyc = KYCStatus.flagged if is_fraud else random.choice(kyc_options)

            c = Customer(
                id=uuid.uuid4(),
                external_id=f"CUST-{uuid.uuid4().hex[:8].upper()}",
                first_name=random.choice(FIRST_NAMES),
                last_name=random.choice(LAST_NAMES),
                date_of_birth=datetime.now().date() - timedelta(days=age * 365),
                email=f"{uuid.uuid4().hex[:8]}@example.com",
                income_bracket=_income_bracket(income),
                annual_income=income,
                credit_score=credit,
                risk_tolerance=getattr(RiskTolerance, risk, RiskTolerance.moderate),
                segment=getattr(Segment, seg, Segment.mass),
                kyc_status=kyc,
            )
            session.add(c)
            await session.flush()

            # ── Accounts ──────────────────────────────────────────────────────
            num_accts = accounts_per_customer(seg)
            account_ids = []
            for j in range(num_accts):
                a = Account(
                    id=uuid.uuid4(),
                    customer_id=c.id,
                    account_number=f"{random.randint(1000000000, 9999999999)}",
                    account_type=AccountType.checking if j == 0 else random.choice(list(AccountType)),
                    balance=round(txn_amount_distribution(seg) * 10, 2),
                    opened_date=datetime.now().date() - timedelta(days=random.randint(30, 1500)),
                )
                session.add(a)
                account_ids.append(a.id)
            await session.flush()

            # ── Transactions ──────────────────────────────────────────────────
            flagged_txn_ids: list[uuid.UUID] = []
            for acct_id in account_ids:
                txns = _generate_transactions(acct_id, seg, is_fraud)
                for t in txns:
                    session.add(t)
                    if t.risk_flag:
                        flagged_txn_ids.append(t.id)
                total_txns += len(txns)

            # ── Holdings ──────────────────────────────────────────────────────
            holdings = _generate_holdings(c.id, risk, income, catalog)
            for h in holdings:
                session.add(h)
            total_holdings += len(holdings)

            # ── Risk incident (fraud customers + any with flagged txns) ───────
            if is_fraud or (flagged_txn_ids and random.random() < 0.5):
                inc = _generate_incident(c.id, seg, flagged_txn_ids)
                session.add(inc)
                total_incidents += 1

            # Commit every 50 customers to avoid huge transactions
            if (i + 1) % 50 == 0:
                await session.commit()
                logger.info(
                    "Progress: %d/%d customers | %d txns | %d holdings | %d incidents",
                    i + 1, customers, total_txns, total_holdings, total_incidents,
                )

        await session.commit()

    logger.info(
        "Generation complete: %d customers | %d transactions | %d holdings | %d incidents",
        customers, total_txns, total_holdings, total_incidents,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Triage Desk synthetic data generator")
    parser.add_argument("--customers", type=int, default=500, help="Number of customers to generate")
    parser.add_argument("--output", type=str, default="../backend/data/seed.db", help="Path to SQLite output")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducibility")
    args = parser.parse_args()

    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    asyncio.run(generate(args.customers, args.output, seed=args.seed))
