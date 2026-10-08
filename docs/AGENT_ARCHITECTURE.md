# Agent Architecture

How an alert becomes a case brief that a human approves. One LangGraph graph (`backend/app/agents/graph.py`)
runs per case: code computes every number, read-only specialists analyse in parallel, one writer drafts,
deterministic gates and a separate evaluator check the draft in a bounded loop, and a human decides.

## 1. Pipeline

```
 POST /workflow/cases/{id}/evaluate
        │
        ▼
 intake (code) ── G0: alert text capped, injection phrases labelled, wrapped as <untrusted_alert_text>
        │         tools compute metrics + evidence refs (T1..T8); rules raise flags; severity = highest flag
        ▼
 triage (LLM router) ── picks extra specialists; code enforces the lane minimum
        │                and adds compliance whenever a compliance flag fired; on error → lane routing
        ▼
 ┌──────────────┬──────────────┬──────────────┐   parallel, read-only, isolated metric slices
 │ transactions │   customer   │  compliance  │   G4: a finding citing unknown metrics/refs or raw
 └──────┬───────┴──────┬───────┴──────┬───────┘       digits is rejected; the run continues
        └──────────────┼──────────────┘
                       ▼
 writer (LLM, single writer) ── numbers only as {{m:key}}, transactions only as {{t:Tn}}
        ▼
 guardian (code, G5 "Compliance Guardian") ──fail──► writer (max 2 revisions) ──► finalize
        ▼ pass
 evaluator (LLM judge, rubric 1–5; code decides pass) ──fail──► writer (same budget) ──► finalize
        ▼ pass
 finalize (code) ── render placeholders from metrics; PENDING_REVIEW, or ESCALATED with
                    "needs supervisor review" when the loop is exhausted or the evaluator is down
        ▼
 human decision (approve / reject / escalate, written reasoning required) → immutable audit trail
```

Lanes come from the incident type: `fraud` (fraud alert, suspicious transaction, identity theft),
`risk` (credit breach), `compliance` (AML flag).

## 2. Code decides, models interpret

| Concern | Decided by | Where |
|---|---|---|
| Metrics (volume, velocity, outliers, near-threshold amounts, KYC, credit) | Code | `agents/tools.py` |
| Flags and severity (inclusive thresholds) | Code | `agents/rules.py` |
| Allowed dispositions per severity | Code | `rules.ALLOWED_DISPOSITIONS` |
| Which specialists run (minimum) | Code | `rules.plan_specialists` |
| Extra specialists, interpretation, wording | LLM | triage, specialists, writer |
| Brief quality (grounded, complete, justified, clear) | LLM scores, code verdict | evaluator |

Flags: `VELOCITY_SPIKE` (≥2× medium, ≥3× high), `AMOUNT_OUTLIER` (≥10× baseline median),
`STRUCTURING` (≥3 recent amounts in $9,000–$9,999.99), `FLAGGED_TRANSACTIONS`, `KYC_FLAGGED`,
`KYC_EXPIRED`, `LOW_CREDIT` (<580), `INPUT_INJECTION`. Windows are anchored to the customer's latest
transaction: the last 30 days against the prior baseline.

Dispositions: high → `escalate` | `sar_review`; medium → `escalate` | `request_info` | `monitor`;
low → `dismiss` | `monitor` | `request_info`. Agents only recommend; nothing is filed or blocked.

## 3. Gates

| Gate | Checks |
|---|---|
| G0 intake | length cap, injection phrases labelled, alert wrapped as untrusted data |
| G4 findings | metric keys and evidence refs exist in the specialist's slice; no digits outside placeholders; no PII, canary or echoed injection |
| G5 guardian | same text checks on the brief; disposition allowed for the code severity; every high flag cited; only raised flags cited; evidence refs exist; rationale present |

Every number a reviewer sees is filled in by `gates.render` from a code-computed metric after G5 passes.

## 4. LLM boundary

`agents/llm.py` is the only path to a model. `ask()` redacts email, phone and SSN patterns from the
payload, sends it, and validates the JSON against the node's Pydantic schema.

| Mode (`LLM_MODE`) | Client | Use |
|---|---|---|
| `live` | `LiveClient` — async LiteLLM, Gemini free tier, falls back down `MODELS` (free-tier only: 3.8 Flash → … → 2.5 Flash-Lite) on quota, unavailable, access or retired-model errors | laptop with a key |
| `record` | `CassetteClient` wrapping live, appends to `CASSETTE_PATH` | recording demo scenarios |
| `replay` | `CassetteClient`, recorded responses only | public demo, CI — no key |
| tests | `ScriptedClient` — canned responses per node | unit and graph tests |

Cassette keys hash purpose, system prompt and payload, excluding the per-run canary line. Each system
prompt carries a fresh canary; G4/G5 reject any output that contains it.

## 5. Stored result

`workflow_cases.ai_evaluation` holds the run snapshot: brief, severity, flags, metrics, findings,
triage reason, evaluator verdict, revision count, review reason and a trace of every node
(kind, duration, ok, note, LLM source). It also keeps `risk_assessment`, `compliance_result` and
`evaluation` for the case page.

## 6. Human review and audit

Decisions: **approve** and **reject** → `human_decided`; **escalate** → `escalated`. Each needs written
reasoning (minimum 10 characters). Case creation, AI evaluation and every decision append a row to the
audit trail; no endpoint updates or deletes audit rows.

## 7. Extending

| Change | Where |
|---|---|
| New metric | `tools.py` (+ add the key to a `SLICES` entry) |
| New flag or threshold | `rules.evaluate_flags` + a boundary test |
| New specialist | `tools.SLICES`, a prompt YAML in `agents/prompts/`, `Literal` in `TriageOut` |
| New output check | `gates.output_gate` + a test in `tests/agents/test_gates_llm.py` |
