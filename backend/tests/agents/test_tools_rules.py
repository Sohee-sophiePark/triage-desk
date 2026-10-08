"""Tools compute every number; rules decide flags, severity and routing with inclusive boundaries."""
import pytest

from app.agents.rules import evaluate_flags, overall_severity, plan_specialists
from app.agents.tools import Metric, customer_metrics, transaction_metrics


def _metrics(**values) -> dict[str, Metric]:
    return {k: Metric(key=k, value=v, unit="text" if isinstance(v, str) else "ratio", label=k, source="test")
            for k, v in values.items()}


def _codes(flags) -> dict[str, str]:
    return {f.code: f.severity for f in flags}


# ── tools ─────────────────────────────────────────────────────────────────────

async def test_transaction_metrics_baseline_velocity_and_threshold(db, make_incident):
    inc = await make_incident(recent=[100.0] * 27 + [9500.0, 9600.0, 9700.0], prior=[100.0] * 50, flagged_recent=2)
    m, evidence = await transaction_metrics(db, inc.customer_id)
    assert m["txn_count_30d"].value == 30
    assert m["txn_monthly_avg_prior"].value == pytest.approx(10.0, abs=0.5)
    assert m["velocity_ratio"].value == pytest.approx(3.0, abs=0.2)
    assert m["near_threshold_count_30d"].value == 3
    assert m["flagged_txn_count_30d"].value == 2
    assert m["max_amount_30d"].value == 9700.0
    assert m["median_amount_prior"].value == 100.0
    assert m["amount_outlier_ratio"].value == 97.0
    assert list(evidence)[:3] == ["T1", "T2", "T3"]
    assert evidence["T1"]["amount"] == 9700.0


async def test_transaction_metrics_no_history_returns_zeros(db, make_incident):
    inc = await make_incident(recent=[], prior=[])
    m, evidence = await transaction_metrics(db, inc.customer_id)
    assert evidence == {}
    assert all(v.value == 0.0 for v in m.values())


async def test_customer_metrics_have_no_names_or_contacts(db, make_incident):
    inc = await make_incident(kyc="expired", credit=610)
    m = await customer_metrics(db, inc)
    assert m["kyc_status"].value == "expired"
    assert m["credit_score"].value == 610
    dumped = str({k: v.model_dump() for k, v in m.items()})
    assert "Agent" not in dumped and "@test.com" not in dumped


# ── rules ─────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("ratio,expected", [(1.99, None), (2.0, "medium"), (2.99, "medium"), (3.0, "high")])
def test_velocity_boundaries(ratio, expected):
    assert _codes(evaluate_flags(_metrics(velocity_ratio=ratio), False)).get("VELOCITY_SPIKE") == expected


@pytest.mark.parametrize("key,below,at,code", [
    ("amount_outlier_ratio", 9.99, 10.0, "AMOUNT_OUTLIER"),
    ("near_threshold_count_30d", 2.0, 3.0, "STRUCTURING"),
])
def test_high_flag_boundaries(key, below, at, code):
    assert code not in _codes(evaluate_flags(_metrics(**{key: below}), False))
    assert _codes(evaluate_flags(_metrics(**{key: at}), False))[code] == "high"


def test_kyc_credit_and_injection_flags():
    flags = _codes(evaluate_flags(_metrics(kyc_status="flagged", credit_score=579.0), True))
    assert flags == {"KYC_FLAGGED": "high", "LOW_CREDIT": "medium", "INPUT_INJECTION": "medium"}
    assert "LOW_CREDIT" not in _codes(evaluate_flags(_metrics(credit_score=580.0), False))


def test_overall_severity_is_highest_flag():
    assert overall_severity([]) == "low"
    assert overall_severity(evaluate_flags(_metrics(velocity_ratio=2.0, kyc_status="flagged"), False)) == "high"


def test_plan_enforces_lane_minimum_and_compliance_flags():
    assert plan_specialists("fraud", [], []) == ["transactions"]
    assert plan_specialists("risk", [], []) == ["transactions", "customer"]
    assert plan_specialists("fraud", [], ["customer"]) == ["transactions", "customer"]
    kyc = evaluate_flags(_metrics(kyc_status="expired"), False)
    assert plan_specialists("fraud", kyc, []) == ["transactions", "compliance"]
