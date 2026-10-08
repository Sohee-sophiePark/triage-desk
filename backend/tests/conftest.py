"""
Shared test fixtures.

Uses a single in-memory SQLite DB for the whole session.
Tables are created once; users are seeded once and reused across all tests.
Each individual test receives the same session (reads committed data cleanly).
"""
import json
import os
import secrets
import uuid

# Secrets and passwords are generated per run, never hardcoded; set before app settings load.
os.environ["SECRET_KEY"] = secrets.token_urlsafe(32)
TEST_PASSWORD = secrets.token_urlsafe(12) + "aA1!"
WRONG_PASSWORD = secrets.token_urlsafe(12) + "bB2?"

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.security import create_access_token, get_password_hash  # noqa: E402
from app.db.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models.user import Role, User  # noqa: E402

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

_engine = create_async_engine(TEST_DB_URL, echo=False)
_Session = async_sessionmaker(bind=_engine, class_=AsyncSession, expire_on_commit=False, autoflush=False)


# ── DB lifecycle (session-scoped) ─────────────────────────────────────────────

@pytest.fixture(scope="session", autouse=True)
async def _create_schema():
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="session")
async def db(_create_schema) -> AsyncSession:
    async with _Session() as session:
        yield session


@pytest.fixture(scope="session", autouse=True)
def _override_db(db):
    async def _get_test_db():
        yield db
    app.dependency_overrides[get_db] = _get_test_db
    yield
    app.dependency_overrides.pop(get_db, None)


# ── Rate limiter reset (autouse) ──────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """Clear all in-memory rate limit counters before each test so tests are independent."""
    from app.api.deps_limiter import _request_counts
    from app.middleware.rate_limiter import _api_counts, _login_counts
    _request_counts.clear()
    _login_counts.clear()
    _api_counts.clear()
    yield


# ── Scripted LLM (autouse): no test ever reaches a real model ─────────────────

def happy_responders() -> dict:
    """Gate-passing responses for every LLM purpose, derived from each request's payload."""
    def specialist(req):
        key = next(iter(json.loads(req.user)["metrics"]))
        return {"summary": f"The main signal is {{{{m:{key}}}}}.", "concerns": [], "metric_keys": [key], "evidence": []}

    def writer(req):
        p = json.loads(req.user)
        return {"summary": "Recent activity is {{m:txn_count_30d}} transactions in the last month.",
                "disposition": p["allowed_dispositions"][0], "rationale": ["Code-computed flags were reviewed."],
                "cited_flags": p["required_flags"], "evidence": []}

    return {
        "triage": lambda req: {"specialists": [], "urgency": "medium", "reason": "Routed by lane."},
        "transactions": specialist, "customer": specialist, "compliance": specialist,
        "writer": writer,
        "evaluator": lambda req: {"grounded": 5, "complete": 5, "disposition_justified": 5, "clear": 5, "feedback": ""},
    }


@pytest.fixture(autouse=True)
def scripted_llm(monkeypatch):
    from app.agents.llm import ScriptedClient
    client = ScriptedClient(happy_responders())
    monkeypatch.setattr("app.services.workflow_service.get_client", lambda: client)
    return client


# ── HTTP client (function-scoped — cheap to recreate) ─────────────────────────

@pytest.fixture
async def client() -> AsyncClient:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


# ── User fixtures (session-scoped — created once, reused) ────────────────────

async def _make_user(db: AsyncSession, email: str, role: Role) -> User:
    user = User(
        id=uuid.uuid4(),
        email=email,
        hashed_password=get_password_hash(TEST_PASSWORD),
        role=role,
        is_active=True,
        full_name=f"Test {role.value}",
    )
    db.add(user)
    await db.commit()
    return user


@pytest.fixture(scope="session")
async def admin_user(db):
    return await _make_user(db, "admin@example.com", Role.ADMIN)


@pytest.fixture(scope="session")
async def analyst_user(db):
    return await _make_user(db, "analyst@example.com", Role.RISK_ANALYST)


@pytest.fixture(scope="session")
async def investigator_user(db):
    return await _make_user(db, "investigator@example.com", Role.INVESTIGATOR)


# ── Auth header helpers ───────────────────────────────────────────────────────

def _headers(user: User) -> dict:
    token = create_access_token(subject=str(user.id), role=user.role.value)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="session")
def admin_headers(admin_user):
    return _headers(admin_user)


@pytest.fixture(scope="session")
def analyst_headers(analyst_user):
    return _headers(analyst_user)


@pytest.fixture(scope="session")
def investigator_headers(investigator_user):
    return _headers(investigator_user)

