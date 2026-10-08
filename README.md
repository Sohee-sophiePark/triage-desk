# Triage Desk

[![ci](https://github.com/Sohee-sophiePark/triage-desk/actions/workflows/ci.yml/badge.svg)](https://github.com/Sohee-sophiePark/triage-desk/actions/workflows/ci.yml)

**Live demo (no login, fictional data, replayed AI runs):** https://sohee-sophiepark.github.io/triage-desk/

AI-augmented operations case management. Alerts from fraud, risk and compliance queues are triaged and analysed by AI agents automatically — with mandatory human-in-the-loop review before any decision is finalised.

One LangGraph graph per case: code computes every number, read-only specialists analyse in parallel, a single writer
drafts the case brief, deterministic gates and a separate evaluator check it in a bounded revision loop, and a human
decides. See [`docs/AGENT_ARCHITECTURE.md`](docs/AGENT_ARCHITECTURE.md).

## What it does

Internal tool for bank operations staff:

| Role | Workflow |
|---|---|
| Fraud Investigator | Reviews AI-analysed fraud alerts, confirms or dismisses |
| Risk Analyst | AI-scored risk assessments queued for human sign-off |
| Compliance Officer | Flagged transactions with AI compliance pre-check |

Every case follows a strict state machine: `Created → AI_Processing → Pending_Review (or Escalated) → Human_Decided`. The AI recommends; the human always decides.

## Tech stack

| Layer | Technology |
|---|---|
| Backend API | Python 3.10+ / FastAPI / SQLAlchemy 2.0 async / Pydantic v2 |
| Agent orchestration | LangGraph + LiteLLM |
| LLM | Gemini free tier via LiteLLM — newest-first fallback (3.8 Flash → 2.5 Flash-Lite); replay mode needs no key |
| Auth | JWT + RBAC (4 roles) |
| Database | SQLite (dev) / PostgreSQL (prod) — Alembic migrations |
| Frontend | React 18 / Vite / TypeScript / Tailwind CSS |
| Dependency management | uv (`pyproject.toml` + `uv.lock`) |
| Containers | Docker + Docker Compose (multi-stage, non-root) |

## Security

- JWT + RBAC enforced at middleware level — 4 roles with automatic case-type scoping
- Rate limiting on authentication and all API endpoints
- PII patterns (email, phone, SSN) redacted before every LLM call
- Multi-layer prompt injection defence
- Immutable audit trail (append-only)
- Deterministic output gates: every number in a brief is filled from a code-computed metric
- Account lockout on repeated failed logins

## Project structure

```
triage-desk/
  backend/           # FastAPI app — agents, API, models, services
    app/
      agents/        # LangGraph case graph: tools, rules, gates, LLM client, prompts
      api/v1/        # Route handlers (auth, customers, workflow, users, risk, products, analytics)
      middleware/    # Rate limiting
      models/        # SQLAlchemy ORM models
      services/      # Business logic (workflow, data access)
    data/            # Seed scripts (seed_users.py, seed_cases.py, seed_all.py)
    demo/            # Demo builder/exporter + recorded model responses (cassette.jsonl)
    evals/           # Golden-case expectations for the eight demo cases
    tests/           # 180 tests — agents, API, services
    pyproject.toml   # Dependencies (uv)
    uv.lock          # Full transitive lockfile
    Dockerfile       # Multi-stage production image
  frontend/          # React SPA
    src/             # Pages, components, stores, services, types
    Dockerfile       # Multi-stage: node build → nginx:alpine
    nginx.conf       # SPA routing + /api/ proxy + security headers
  docs/              # Architecture reference and dev playbook
  .github/workflows/ # CI (tests, lint, evals, builds) and GitHub Pages (replay, build, deploy the demo)
  docker-compose.yml       # Full stack: backend + frontend + postgres + redis + chromadb
  docker-compose.dev.yml   # Hot-reload override
  docker-compose.prod.yml  # Production override (replicas, resource limits)
  Makefile                 # One-command shortcuts
  .env.example
```

## Quick start

### Option 1 — Docker (recommended)

```bash
git clone <repo> && cd triage-desk
cp .env.example .env       # fill in every required key (see comments in the file)
make up                    # builds images, starts all 5 services
# → frontend: http://localhost:80
# → backend API: http://localhost:8000/docs
```

Run migrations and seed dev data after first boot:

```bash
make migrate-docker
make seed-docker
```

### Option 2 — Local (no Docker)

Requires: Python 3.10+, Node 18+, [uv](https://docs.astral.sh/uv/)

```bash
# Backend
cd backend
uv sync --dev              # creates .venv and installs all deps
uv run alembic upgrade head
uv run python data/seed_all.py
uv run uvicorn app.main:app --reload --port 8001

# Frontend (separate terminal)
cd frontend
npm install
npm run dev                # → http://localhost:5173 (proxies /api to :8001)
```

Copy `.env.example` to `backend/.env` and fill in SECRET_KEY, GEMINI_API_KEY and the `SEED_*` logins before starting. No credentials live in code; the app refuses to start without its secrets.

## Replay demo (no key, no login)

The public demo is a static build: eight fictional alert cases run through the real case graph, the model responses are
recorded once (`backend/demo/cassette.jsonl`, free-tier Gemini), and every API response the UI reads is exported as JSON.
Pick a persona (Ops Supervisor, Fraud Investigator, Risk Analyst, Compliance Officer); actions are read-only.

```bash
cd backend && uv run python -m demo.export            # replay the recordings, write frontend/public/demo/
cd ../frontend && VITE_DEMO=1 npm run build           # static site in frontend/dist
```

`uv run python -m demo.export --record` re-records the cases live (needs `GEMINI_API_KEY` in `backend/.env`).
The Pages workflow (`.github/workflows/pages.yml`) replays, builds and deploys on every push to `main`.

## Evals

- **Golden cases** — `backend/evals/golden.json` states, for each of the eight demo cases, the expected status, severity,
  exact flag set, minimum specialists, acceptable dispositions, and that every flag is cited and all gates and the evaluator
  passed. `uv run python -m evals.golden` checks the replay export against it (8/8 pass).
- **Adversarial cases** — scripted-model tests in `backend/tests/agents/` cover prompt injection and PII in the alert,
  canary leakage, raw digits, number words and unknown placeholders in model output, disallowed dispositions, and evaluator failure
  (always ends in "needs supervisor review").

CI (`.github/workflows/ci.yml`) runs lint, tests, the replay export, the golden evals and both frontend builds on every
push and pull request.

## Dev commands

```bash
make test          # uv run pytest -x -v  (180 tests)
make lint          # uv run ruff check app/ tests/
make migrate       # uv run alembic upgrade head (local)
make seed          # uv run python data/seed_all.py (local, dev only)
make dev-docker    # Docker with hot-reload
make clean         # tear down containers and volumes
```

## Docs

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — system layers, request lifecycle, state machine, DB entities
- [`docs/AGENT_ARCHITECTURE.md`](docs/AGENT_ARCHITECTURE.md) — agent pipeline, evaluation methodology, human review loop
- [`docs/PLAYBOOK_DEV.md`](docs/PLAYBOOK_DEV.md) — local dev, DB migrations, seeding, testing, Docker

_Last updated 2026-10-08 · verified against the code, the 180-test suite and the live demo._

---

Built by [Sohee Park](https://github.com/Sohee-sophiePark). AI-assisted development with [Claude Code](https://claude.ai/claude-code).
