import asyncio
import os
import sys

# Add backend directory to path so we can import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from sqlalchemy.future import select

from app.core.config import settings
from app.core.security import get_password_hash
from app.db.database import AsyncSessionLocal
from app.models.user import Role, User

# role, env-var prefix, display name — logins come only from SEED_<PREFIX>_EMAIL / _PASSWORD in .env
SEED_USERS = [
    (Role.ADMIN, "ADMIN", "Admin"),
    (Role.INVESTIGATOR, "FRAUD", "Fraud Investigator"),
    (Role.RISK_ANALYST, "RISK", "Risk Analyst"),
    (Role.COMPLIANCE, "COMPLIANCE", "Compliance Officer"),
]


async def seed_users():
    """Seed one dev user per role from .env; development only; raises if any login is unset."""
    if settings.ENVIRONMENT != "development":
        print("Not in development mode. Skipping dev user seeding.")
        return

    load_dotenv()
    keys = [f"SEED_{p}_{f}" for _, p, _ in SEED_USERS for f in ("EMAIL", "PASSWORD")]
    missing = [k for k in keys if not os.environ.get(k)]
    if missing:
        raise EnvironmentError(f"Set in .env before seeding: {', '.join(missing)}")

    async with AsyncSessionLocal() as session:
        for role, prefix, name in SEED_USERS:
            email = os.environ[f"SEED_{prefix}_EMAIL"]
            result = await session.execute(select(User).where(User.email == email))
            if not result.scalar_one_or_none():
                session.add(User(
                    email=email,
                    hashed_password=get_password_hash(os.environ[f"SEED_{prefix}_PASSWORD"]),
                    full_name=name,
                    role=role,
                    is_active=True,
                ))
        await session.commit()
        print(f"Seeded {len(SEED_USERS)} dev users.")

if __name__ == "__main__":
    asyncio.run(seed_users())
