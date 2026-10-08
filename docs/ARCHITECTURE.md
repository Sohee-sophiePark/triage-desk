# Triage Desk — Architecture Reference

Quick reference. The agent pipeline is described in [`AGENT_ARCHITECTURE.md`](AGENT_ARCHITECTURE.md).

## System Layers (top to bottom)

1. **Presentation Layer** — React SPA (Vite + TS + Tailwind + shadcn/ui)
2. **API Gateway** — FastAPI with JWT auth, RBAC, rate limiting, audit logging
3. **Security Layer** — PII redaction on every LLM call, prompt-injection defense (multi-layer)
4. **Workflow Engine** — Case lifecycle state machine, review queue, automation rules
5. **Agent Orchestration** — LangGraph graph with typed state
6. **Agent Pool** — Triage router, Transaction / Customer / Compliance specialists, Writer, Compliance Guardian (code), Evaluator
7. **Data Access** — SQLAlchemy 2.0 async ORM
8. **Storage** — SQLite/PostgreSQL + ChromaDB + Redis

## Request Lifecycle

```
Client Request
  → JWT Validation + RBAC Check
  → Case graph (see AGENT_ARCHITECTURE.md):
      intake (code metrics, flags) → triage → parallel specialists → writer
      → Compliance Guardian gates (code) ⇄ evaluator (bounded revisions) → finalize
  → Workflow Engine (PENDING_REVIEW or ESCALATED)
  → Human Review (approve / reject / escalate)
  → Audit Trail (append-only record)
```

## Case State Machine

```
CREATED → AI_PROCESSING → AI_EVALUATED → PENDING_REVIEW → IN_REVIEW → HUMAN_DECIDED → CLOSED
                                                                    ↘ ESCALATED ↗
```

## Agent State

Agents share one typed LangGraph state, `CaseState` (`backend/app/agents/state.py`): case input,
code-computed metrics, evidence and flags, the plan, specialist findings (merged in parallel), the draft,
gate failures, evaluator verdict, revision count, final status and a node trace.

## Database Entities

customers, accounts, product_holdings, transactions, risk_incidents, workflow_cases, evaluation_log, audit_trail, product_catalog

## API Response Envelope

```json
{
  "status": "success|error",
  "data": {},
  "meta": { "timestamp": "", "request_id": "", "agent_metadata": {} }
}
```

## Automation Levels

| Level | Description |
|-------|-------------|
| 0 (default) | Human reviews all cases — no automation |
| 1 | Low-severity, high-confidence cases auto-advance; human notified |
| 2 | High-risk cases always reviewed; others auto-advance |
| 3 | Spot-check sampling only |
