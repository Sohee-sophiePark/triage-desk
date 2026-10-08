import operator
from typing import Annotated, Optional, TypedDict


def _merge(a: dict, b: dict) -> dict:
    return {**a, **b}


class CaseState(TypedDict, total=False):
    """Typed state of one case run; agents exchange only these fields, never free text."""
    # ── Input (set by the caller) ──
    case_id: str
    lane: str                  # fraud | risk | compliance (case type)
    incident_id: str
    canary: str

    # ── Intake (code) ──
    alert_text: str            # G0-wrapped untrusted alert description
    metrics: dict              # key -> Metric dict
    evidence: dict             # T-ref -> transaction summary
    flags: list[dict]
    severity: str

    # ── Agents ──
    plan: list[str]
    triage_reason: str
    findings: Annotated[dict, _merge]   # specialist -> finding (written in parallel)
    draft: Optional[dict]
    gate_failures: list[str]
    verdict: Optional[dict]
    feedback: list[str]
    revisions: int
    next_step: str             # set by guardian / evaluator: writer | evaluator | finalize

    # ── Result ──
    status: str                # pending_review | escalated
    review_reason: str
    snapshot: dict
    trace: Annotated[list, operator.add]
