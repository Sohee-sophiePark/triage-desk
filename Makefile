.PHONY: dev up dev-docker down prod migrate seed test lint clean build

# ── Local dev (no Docker) ─────────────────────────────────────────────────────

dev:
	@echo "Starting backend + frontend locally (no Docker)..."
	cd backend && uv run uvicorn app.main:app --reload --port 8001 &
	cd frontend && npm run dev

# ── Docker ────────────────────────────────────────────────────────────────────

# Full stack (production images, postgres, redis, chromadb)
up:
	docker compose up -d

# Dev mode with hot-reload
dev-docker:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up

# Production mode
prod:
	docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Stop everything
down:
	docker compose down

# ── Database ──────────────────────────────────────────────────────────────────

# Run migrations (local)
migrate:
	cd backend && uv run alembic upgrade head

# Run migrations (Docker)
migrate-docker:
	docker compose exec backend uv run alembic upgrade head

# ── Seed data ─────────────────────────────────────────────────────────────────

# Seed dev data (local — dev only)
seed:
	cd backend && uv run python data/seed_all.py

# Seed via Docker
seed-docker:
	docker compose exec backend uv run python data/seed_all.py

# ── Tests & lint ──────────────────────────────────────────────────────────────

test:
	cd backend && uv run pytest -x -v

lint:
	cd backend && uv run ruff check app/ tests/

# ── Build & clean ─────────────────────────────────────────────────────────────

build:
	docker compose build

# Full rebuild (no cache)
build-clean:
	docker compose build --no-cache

# Tear down all containers and volumes
clean:
	docker compose down -v
	cd frontend && rm -rf dist
