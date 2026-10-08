# Developer & Operations Playbook

Developer guide for Triage Desk.

---

## 1. Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Python | 3.10+ | Backend runtime |
| [uv](https://docs.astral.sh/uv/) | latest | Python dependency management |
| Node.js | 18+ | Frontend build |
| Docker + Compose | v2 | Containerised stack |

Install uv if you don't have it:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

---

## 2. Local Development (no Docker)

### Backend

```bash
cd backend
uv sync --dev                                      # installs all deps into .venv
cp ../.env.example .env                            # fill in SECRET_KEY, GEMINI_API_KEY, SEED_*
uv run alembic upgrade head                        # apply DB migrations
uv run python data/seed_all.py                     # seed dev users + workflow cases
uv run uvicorn app.main:app --reload --port 8001   # port 8001 (8000 may be occupied)
```

API available at `http://localhost:8001`. OpenAPI docs at `http://localhost:8001/docs`.

### Frontend

```bash
cd frontend
npm install
npm run dev    # → http://localhost:5173, proxies /api/ to :8001
```

### Tests & lint

```bash
cd backend
uv run pytest -x -v                     # 177 tests
uv run ruff check app/ tests/           # lint
uv run ruff check app/ tests/ --fix     # lint + auto-fix
```

---

## 3. Docker Stack

### Start everything

```bash
cp .env.example .env     # fill in every required key, incl. POSTGRES_USER/PASSWORD
make up                  # docker compose up -d
```

Services started:

| Service | Port | Notes |
|---------|------|-------|
| frontend (nginx) | :80 | Serves React SPA, proxies /api/ |
| backend (FastAPI) | :8000 | Gunicorn + Uvicorn workers |
| postgres | :5432 | Named volume `pgdata` |
| redis | :6379 | Named volume `redisdata` |
| chromadb | internal | Named volume `chromadata` |

### First-time setup after `make up`

```bash
make migrate-docker      # run alembic upgrade head inside container
make seed-docker         # seed dev users + workflow cases
```

### Hot-reload development mode

```bash
make dev-docker          # docker compose -f ... -f docker-compose.dev.yml up
```

Backend auto-reloads on source changes. Frontend uses Vite dev server on :5173.

### Production mode

```bash
# Set strong secrets in .env first (POSTGRES_PASSWORD, REDIS_PASSWORD, SECRET_KEY)
make prod                # 2 backend replicas, resource limits enforced
```

### Common operations

```bash
make down                # stop all containers
make logs                # docker compose logs -f backend
make clean               # stop + delete all volumes (destructive)
make build-clean         # full image rebuild (--no-cache)
```

---

## 4. Database Migrations

Always generate a migration when changing a model:

```bash
cd backend
uv run alembic revision --autogenerate -m "describe your change"
# review the generated file in alembic/versions/
uv run alembic upgrade head
```

In Docker:

```bash
docker compose exec backend uv run alembic upgrade head
```

---

## 5. Seed Data

The seed scripts are dev-only (guarded by `ENVIRONMENT=development` check):

```bash
# Local
cd backend && uv run python data/seed_all.py

# Docker
docker compose exec backend uv run python data/seed_all.py
```

`seed_all.py` runs in order:
1. `seed_users.py` — creates one dev account per role from the `SEED_*` logins in `backend/.env`
2. `seed_cases.py` — creates up to 30 workflow cases across the 3 case types (fraud, risk, compliance)

---

## 6. Managing Dependencies

Dependencies are managed with **uv** (`pyproject.toml` + `uv.lock`).

```bash
cd backend
uv add <package>          # add runtime dependency
uv add --dev <package>    # add dev-only dependency (tests, linting)
uv lock                   # regenerate lockfile after manual pyproject.toml edits
uv sync --dev             # install everything from lockfile
```

The `uv.lock` file is committed to git — it is the source of truth for exact transitive versions. Never edit it manually.

---

## 7. Key API Endpoints

| Method | Path | Access | Description |
|--------|------|--------|-------------|
| POST | `/api/v1/auth/login` | Public | JWT login |
| GET | `/api/v1/customers` | All roles | Customer list |
| GET | `/api/v1/workflow/cases` | All roles (scoped) | Case queue |
| POST | `/api/v1/workflow/cases/{incident_id}` | All roles | Create case from incident |
| POST | `/api/v1/workflow/cases/{id}/evaluate` | All roles | Trigger AI evaluation |
| POST | `/api/v1/workflow/cases/{id}/decide` | All roles | Submit human decision |
| GET | `/api/v1/users` | admin only | List all users |
| POST | `/api/v1/users` | admin only | Create user |
| PATCH | `/api/v1/users/{id}` | admin only | Update user |
| GET | `/api/v1/analytics/summary` | All roles | Aggregated portfolio + case metrics |

All endpoints are rate-limited. Login has stricter per-IP limits than authenticated endpoints.

---

## 8. Troubleshooting

**Port 8000 already in use (local dev):**
Use `--port 8001` for uvicorn and update `frontend/vite.config.ts` proxy target accordingly.

**`bcrypt` version conflict:**
`passlib 1.7.4` is incompatible with `bcrypt>=4.1`. The lockfile pins `bcrypt<4.1.0` — do not upgrade it without replacing passlib.

**Database schema out of date:**
Run `uv run alembic upgrade head` (local) or `make migrate-docker`.

**Empty dashboards after login:**
Run `make seed` (local) or `make seed-docker` to populate workflow cases.
