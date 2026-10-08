"""
Orchestrator: run all seed scripts in the correct order.
Usage: python data/seed_all.py
"""
import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.seed_cases import seed_cases
from data.seed_users import seed_users


async def main() -> None:
    print("=== Triage Desk seed: users ===")
    await seed_users()
    print()
    print("=== Triage Desk seed: cases ===")
    await seed_cases()
    print()
    print("Seed complete.")


if __name__ == "__main__":
    asyncio.run(main())
