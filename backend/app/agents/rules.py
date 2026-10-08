"""Deterministic breach rules: code, not a model, decides flags, severity and allowed dispositions."""
from pydantic import BaseModel

from app.agents.tools import Metric

SEVERITY_ORDER = ["low", "medium", "high"]

ALLOWED_DISPOSITIONS = {
    "high": ["escalate", "sar_review"],
    "medium": ["escalate", "request_info", "monitor"],
    "low": ["dismiss", "monitor", "request_info"],
}

# Minimum specialists per lane; code adds compliance whenever a compliance flag fires.
LANE_SPECIALISTS = {"fraud": ["transactions"], "risk": ["transactions", "customer"], "compliance": ["transactions", "compliance"]}
COMPLIANCE_FLAGS = {"STRUCTURING", "KYC_FLAGGED", "KYC_EXPIRED", "INPUT_INJECTION"}


class Flag(BaseModel):
    code: str
    severity: str
    metric: str | None
    label: str


def _num(metrics: dict[str, Metric], key: str) -> float:
    v = metrics[key].value if key in metrics else 0.0
    return float(v) if isinstance(v, (int, float)) else 0.0


def evaluate_flags(metrics: dict[str, Metric], injection_suspected: bool) -> list[Flag]:
    """Apply threshold rules to metrics; boundaries are inclusive (>=)."""
    flags = []

    def add(code, severity, metric, label):
        flags.append(Flag(code=code, severity=severity, metric=metric, label=label))

    v = _num(metrics, "velocity_ratio")
    if v >= 3:
        add("VELOCITY_SPIKE", "high", "velocity_ratio", "Recent volume at least 3x baseline")
    elif v >= 2:
        add("VELOCITY_SPIKE", "medium", "velocity_ratio", "Recent volume at least 2x baseline")
    if _num(metrics, "amount_outlier_ratio") >= 10:
        add("AMOUNT_OUTLIER", "high", "amount_outlier_ratio", "Largest recent amount at least 10x baseline median")
    if _num(metrics, "near_threshold_count_30d") >= 3:
        add("STRUCTURING", "high", "near_threshold_count_30d", "Three or more recent amounts just under $10,000")
    if _num(metrics, "flagged_txn_count_30d") >= 1:
        add("FLAGGED_TRANSACTIONS", "medium", "flagged_txn_count_30d", "Recent transactions flagged by rules")
    kyc = metrics["kyc_status"].value if "kyc_status" in metrics else "unknown"
    if kyc == "flagged":
        add("KYC_FLAGGED", "high", "kyc_status", "KYC status is flagged")
    elif kyc == "expired":
        add("KYC_EXPIRED", "medium", "kyc_status", "KYC status is expired")
    if 0 < _num(metrics, "credit_score") < 580:
        add("LOW_CREDIT", "medium", "credit_score", "Credit score below 580")
    if injection_suspected:
        add("INPUT_INJECTION", "medium", None, "Alert text contained instruction-like content")
    return flags


def overall_severity(flags: list[Flag]) -> str:
    return max((f.severity for f in flags), key=SEVERITY_ORDER.index, default="low")


def plan_specialists(lane: str, flags: list[Flag], requested: list[str]) -> list[str]:
    """Union of the lane minimum, the triage request and compliance when a compliance flag fired; stable order."""
    chosen = set(LANE_SPECIALISTS.get(lane, ["transactions"])) | set(requested)
    if any(f.code in COMPLIANCE_FLAGS for f in flags):
        chosen.add("compliance")
    return [s for s in ("transactions", "customer", "compliance") if s in chosen]
