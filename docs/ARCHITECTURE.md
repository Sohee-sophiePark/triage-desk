# Triage Desk — Architecture Reference

Quick reference. The agent pipeline is described in [`AGENT_ARCHITECTURE.md`](AGENT_ARCHITECTURE.md).

## System layers (top to bottom)

1. **Presentation** — React 18 SPA (Vite, TypeScript, Tailwind, Radix primitives). A demo build (`VITE_DEMO=1`) reads
   exported JSON instead of the API and replaces login with a persona switcher.
2. **API** — FastAPI with JWT auth, role-based access (4 roles), in-memory rate limiting, account lockout.
3. **Security** — PII patterns redacted on every LLM call; alert text wrapped as untrusted data; deterministic output gates.
4. **Workflow engine** — case lifecycle (below) and the append-only audit trail.
5. **Agent orchestration** — one LangGraph graph per case with typed state.
6. **Agents** — triage router; transaction, customer and compliance specialists; single writer; evaluator.
   Breach rules, the output gates (the "Compliance Guardian") and final status are code, not agents.
7. **Data access** — SQLAlchemy 2.0 async ORM, Alembic migrations.
8. **Storage** — SQLite (local and demo) or PostgreSQL (Docker Compose). The Compose file also provisions Redis and
   ChromaDB containers; the current app does not use them.

## Request lifecycle

```
Client request
  → JWT validation + role check
  → Case graph (see AGENT_ARCHITECTURE.md):
      intake (code: metrics, flags) → triage → parallel specialists → writer
      → guardian gates (code) ⇄ evaluator (at most 2 revisions) → finalize
  → Case status PENDING_REVIEW, or ESCALATED with "needs supervisor review"
  → Human decision (approve / reject / escalate, written reasoning required)
  → Audit trail (append-only)
```

## Case lifecycle

```
CREATED → AI_PROCESSING → PENDING_REVIEW ── approve / reject ──► HUMAN_DECIDED
                        ↘ ESCALATED (loop exhausted)  ↘ escalate ──► ESCALATED
```

## Roles

| Role | Sees | Can |
|---|---|---|
| admin (Ops Supervisor in the demo) | all cases, users, audit | create and evaluate cases, decide, manage users |
| risk_analyst | all cases | create and evaluate cases, decide |
| fraud_investigator | fraud cases | decide |
| compliance_officer | compliance cases | decide |

## Agent state

Agents share one typed LangGraph state, `CaseState` (`backend/app/agents/state.py`): case input, code-computed
metrics, evidence and flags, the plan, specialist findings (merged in parallel), the draft, gate failures, evaluator
verdict, revision count, final status and a node trace.

## Database entities

customers, accounts, transactions, product_holdings, product_catalog, risk_incidents, workflow_cases, audit_trails, users

## API responses

Customer and analytics endpoints use the envelope `{ "status", "data", "meta" }`. Workflow endpoints return the case,
case list or `{ "case_id", "audit_trail" }` directly.

---

_Last updated 2026-10-08 · checked against the code (models, routes, workflow service) and the 180-test suite._
