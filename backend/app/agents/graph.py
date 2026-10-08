"""Case graph: intake → triage → parallel specialists → writer → guardian ⇄ evaluator (bounded) → finalize."""
import secrets
import statistics
import time
import uuid
from datetime import datetime, timezone
from typing import Literal

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.agents.config import agent_settings
from app.agents.gates import findings_gate, intake_gate, output_gate, render, text_failures
from app.agents.llm import LLMClient, ask
from app.agents.prompt_loader import load_prompt
from app.agents.rules import (
    ALLOWED_DISPOSITIONS,
    Flag,
    evaluate_flags,
    overall_severity,
    plan_specialists,
)
from app.agents.state import CaseState
from app.agents.tools import SLICES, Metric, customer_metrics, transaction_metrics
from app.models.risk_incident import RiskIncident

SPECIALISTS = list(SLICES)
Disposition = Literal["dismiss", "monitor", "request_info", "escalate", "sar_review"]


class TriageOut(BaseModel):
    specialists: list[Literal["transactions", "customer", "compliance"]] = []
    urgency: Literal["low", "medium", "high"]
    reason: str


class Finding(BaseModel):
    summary: str
    concerns: list[str] = []
    metric_keys: list[str] = []
    evidence: list[str] = []


class Brief(BaseModel):
    summary: str
    disposition: Disposition
    rationale: list[str]
    cited_flags: list[str] = []
    evidence: list[str] = []


class Verdict(BaseModel):
    grounded: int = Field(ge=1, le=5)
    complete: int = Field(ge=1, le=5)
    disposition_justified: int = Field(ge=1, le=5)
    clear: int = Field(ge=1, le=5)
    feedback: str = ""

    def scores(self) -> dict[str, int]:
        return self.model_dump(exclude={"feedback"})


# ── helpers ───────────────────────────────────────────────────────────────────

def _cfg(config: RunnableConfig, key: str):
    return config["configurable"][key]


def _step(node: str, kind: str, t0: float, ok: bool, note: str = "", resp=None) -> dict:
    t1 = time.perf_counter()
    return {"node": node, "kind": kind, "start": round(t0, 4), "end": round(t1, 4),
            "ms": round((t1 - t0) * 1000), "ok": ok, "note": note,
            "source": resp.source if resp else None, "model": resp.model if resp else None}


def _metrics(state: CaseState) -> dict[str, Metric]:
    return {k: Metric(**v) for k, v in state["metrics"].items()}


def _flags(state: CaseState) -> list[Flag]:
    return [Flag(**f) for f in state["flags"]]


def _values(metrics: dict[str, Metric], keys=None) -> dict:
    return {k: {"label": m.label, "value": m.value, "unit": m.unit} for k, m in metrics.items() if keys is None or k in keys}


def _context(state: CaseState) -> dict:
    return {"lane": state["lane"], "alert": state["alert_text"], "severity": state["severity"],
            "flags": [{k: f[k] for k in ("code", "severity", "label")} for f in state["flags"]]}


# ── nodes ─────────────────────────────────────────────────────────────────────

async def intake(state: CaseState, config: RunnableConfig) -> dict:
    """Code only: G0 on the alert text, tools compute metrics and evidence, rules raise flags."""
    t0 = time.perf_counter()
    db = _cfg(config, "db")
    incident = (await db.execute(select(RiskIncident).where(RiskIncident.id == uuid.UUID(state["incident_id"])))).scalar_one()
    alert_text, injection = intake_gate(incident.description)
    txn, evidence = await transaction_metrics(db, incident.customer_id)
    metrics = {**txn, **await customer_metrics(db, incident)}
    flags = evaluate_flags(metrics, injection)
    return {
        "alert_text": alert_text, "evidence": evidence,
        "metrics": {k: m.model_dump() for k, m in metrics.items()},
        "flags": [f.model_dump() for f in flags], "severity": overall_severity(flags),
        "findings": {}, "revisions": 0, "feedback": [], "verdict": None,
        "trace": [_step("intake", "code", t0, True, f"{len(metrics)} metrics, {len(flags)} flags")],
    }


async def triage(state: CaseState, config: RunnableConfig) -> dict:
    """LLM router picks extra specialists; code enforces the lane minimum and compliance on compliance flags."""
    t0 = time.perf_counter()
    payload = {**_context(state), "available_specialists": SPECIALISTS}
    try:
        out, resp = await ask(_cfg(config, "llm"), "triage", load_prompt("triage", state["canary"]), payload, TriageOut)
        requested, reason, ok, note = out.specialists, out.reason, True, ""
        if text_failures([reason], {}, set(), state["canary"]):
            reason = ""
    except Exception as e:
        requested, reason, ok, resp = [], "", False, None
        note = f"fallback to lane routing: {type(e).__name__}"
    plan = plan_specialists(state["lane"], _flags(state), requested)
    return {"plan": plan, "triage_reason": reason,
            "trace": [_step("triage", "llm", t0, ok, note or ", ".join(plan), resp)]}


def _specialist(name: str):
    async def node(state: CaseState, config: RunnableConfig) -> dict:
        t0 = time.perf_counter()
        visible = {k: m for k, m in _metrics(state).items() if k in SLICES[name]}
        refs = state["evidence"] if name != "customer" else {}
        payload = {**_context(state), "metrics": _values(visible), "evidence": refs}
        try:
            out, resp = await ask(_cfg(config, "llm"), name, load_prompt(name, state["canary"]), payload, Finding)
            finding = out.model_dump()
            fails = findings_gate(finding, visible, set(refs), state["canary"])
            if fails:
                finding = {"rejected": True, "reasons": fails}
            step = _step(name, "llm", t0, not fails, "; ".join(fails[:2]), resp)
        except Exception as e:
            finding = {"error": type(e).__name__}
            step = _step(name, "llm", t0, False, f"error: {type(e).__name__}")
        return {"findings": {name: finding}, "trace": [step]}
    return node


async def writer(state: CaseState, config: RunnableConfig) -> dict:
    """Single writer drafts the case brief; numbers only as {{m:key}}, evidence only as {{t:Tn}}."""
    t0 = time.perf_counter()
    accepted = {k: f for k, f in state["findings"].items() if "summary" in f}
    payload = {
        **_context(state), "metrics": _values(_metrics(state)), "evidence": state["evidence"], "findings": accepted,
        "allowed_dispositions": ALLOWED_DISPOSITIONS[state["severity"]],
        "required_flags": [f["code"] for f in state["flags"] if f["severity"] == "high"],
        "feedback": state["feedback"],
    }
    try:
        out, resp = await ask(_cfg(config, "llm"), "writer", load_prompt("writer", state["canary"]), payload, Brief)
        return {"draft": out.model_dump(), "gate_failures": [],
                "trace": [_step("writer", "llm", t0, True, f"revision {state['revisions']}", resp)]}
    except Exception as e:
        return {"draft": None, "gate_failures": [f"writer error: {type(e).__name__}"],
                "trace": [_step("writer", "llm", t0, False, f"error: {type(e).__name__}")]}


def _retry_or_finalize(state: CaseState, reasons: list[str]) -> dict:
    if state["revisions"] < agent_settings.MAX_REVISIONS:
        return {"next_step": "writer", "revisions": state["revisions"] + 1, "feedback": reasons}
    return {"next_step": "finalize"}


async def guardian(state: CaseState, config: RunnableConfig) -> dict:
    """Compliance Guardian (G5, code): every draft passes these checks before the evaluator sees it."""
    t0 = time.perf_counter()
    fails = state["gate_failures"] or output_gate(
        state["draft"], _metrics(state), set(state["evidence"]), _flags(state), state["severity"], state["canary"])
    route = _retry_or_finalize(state, fails) if fails else {"next_step": "evaluator"}
    return {"gate_failures": fails, **route, "trace": [_step("guardian", "code", t0, not fails, "; ".join(fails[:3]))]}


async def evaluator(state: CaseState, config: RunnableConfig) -> dict:
    """Separate LLM judge scores the rendered brief on a rubric; code decides pass/fail."""
    t0 = time.perf_counter()
    metrics, d = _metrics(state), state["draft"]
    payload = {
        **_context(state), "metrics": _values(metrics), "evidence": state["evidence"],
        "allowed_dispositions": ALLOWED_DISPOSITIONS[state["severity"]],
        "brief": {"summary": render(d["summary"], metrics, state["evidence"]), "disposition": d["disposition"],
                  "rationale": [render(r, metrics, state["evidence"]) for r in d["rationale"]],
                  "cited_flags": d["cited_flags"]},
    }
    try:
        v, resp = await ask(_cfg(config, "llm"), "evaluator", load_prompt("evaluator", state["canary"]), payload, Verdict)
    except Exception as e:
        return {"verdict": None, "next_step": "finalize", "review_reason": "evaluator unavailable",
                "trace": [_step("evaluator", "llm", t0, False, f"error: {type(e).__name__}")]}
    low = [k for k, s in v.scores().items() if s < agent_settings.EVAL_PASS_SCORE]
    verdict = {**v.model_dump(), "passed": not low}
    route = _retry_or_finalize(state, [f"evaluator: {', '.join(low)} below threshold. {v.feedback}"]) if low \
        else {"next_step": "finalize"}
    return {"verdict": verdict, **route,
            "trace": [_step("evaluator", "llm", t0, not low, f"low: {', '.join(low)}" if low else "passed", resp)]}


async def finalize(state: CaseState, config: RunnableConfig) -> dict:
    """Code only: render the approved brief, choose PENDING_REVIEW or ESCALATED, build the stored snapshot."""
    t0 = time.perf_counter()
    metrics, d, v = _metrics(state), state.get("draft"), state.get("verdict")
    fails = state.get("gate_failures") or []
    ok = bool(d) and not fails and bool(v and v["passed"])
    reason = "" if ok else "needs supervisor review: " + (
        "; ".join(fails[:3]) or state.get("review_reason") or "evaluator did not pass the brief")
    brief = None
    if d and not fails:
        brief = {"summary": render(d["summary"], metrics, state["evidence"]), "disposition": d["disposition"],
                 "rationale": [render(r, metrics, state["evidence"]) for r in d["rationale"]],
                 "cited_flags": d["cited_flags"], "evidence": {r: state["evidence"][r] for r in d["evidence"]}}
    confidence = round(statistics.mean(Verdict(**v).scores().values()) / 5 * 100, 1) if v else 0.0
    trace = state["trace"] + [_step("finalize", "code", t0, ok, "pending_review" if ok else "escalated")]
    snapshot = {
        # fields read by the current case page
        "intent": state["lane"], "routed_agents": state["plan"],
        "risk_assessment": {"is_fraud": bool(brief) and brief["disposition"] in ("escalate", "sar_review"),
                            "confidence": confidence,
                            "justification": brief["summary"] if brief else reason,
                            "evidence": brief["rationale"] if brief else []},
        "compliance_result": {"passed": not fails, "reason": "Passed all output gates." if not fails else reason,
                              "violations": fails},
        "evaluation": {"confidence_score": confidence,
                       "hallucination_flags": [f for f in fails if "unknown" in f],
                       "hallucination_count": sum("unknown" in f for f in fails),
                       "compliance_score": 0 if fails else 100,
                       "evaluated_at": datetime.now(timezone.utc).isoformat()},
        # full run record
        "brief": brief, "severity": state["severity"], "flags": state["flags"], "metrics": state["metrics"],
        "findings": state["findings"], "triage_reason": state["triage_reason"], "verdict": v,
        "revisions": state["revisions"], "review_reason": reason, "trace": trace,
    }
    return {"status": "pending_review" if ok else "escalated", "review_reason": reason, "snapshot": snapshot,
            "trace": trace[-1:]}


# ── graph ─────────────────────────────────────────────────────────────────────

def build_graph():
    g = StateGraph(CaseState)
    g.add_node("intake", intake)
    g.add_node("triage", triage)
    for name in SPECIALISTS:
        g.add_node(name, _specialist(name))
        g.add_edge(name, "writer")
    g.add_node("writer", writer)
    g.add_node("guardian", guardian)
    g.add_node("evaluator", evaluator)
    g.add_node("finalize", finalize)
    g.add_edge(START, "intake")
    g.add_edge("intake", "triage")
    g.add_conditional_edges("triage", lambda s: s["plan"], SPECIALISTS)
    g.add_edge("writer", "guardian")
    g.add_conditional_edges("guardian", lambda s: s["next_step"], ["writer", "evaluator", "finalize"])
    g.add_conditional_edges("evaluator", lambda s: s["next_step"], ["writer", "finalize"])
    g.add_edge("finalize", END)
    return g.compile()


case_graph = build_graph()


async def run_case(db, client: LLMClient, case_id: str, lane: str, incident_id: str) -> CaseState:
    """Run one case end to end; the canary is fresh per run."""
    state = {"case_id": case_id, "lane": lane, "incident_id": incident_id, "canary": secrets.token_hex(16), "trace": []}
    return await case_graph.ainvoke(state, config={"configurable": {"db": db, "llm": client}})
