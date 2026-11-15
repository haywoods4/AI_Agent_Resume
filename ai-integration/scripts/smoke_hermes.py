"""Explicit live inference check. Sends only synthetic, privacy-filtered skill facts."""

import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.privacy import PIIScrubbingMiddleware  # noqa: E402
from app.providers import HermesClient  # noqa: E402
from app.settings import Settings  # noqa: E402


async def main():
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    settings = Settings.from_env()
    settings.validate()
    client = HermesClient(settings)
    try:
        import uuid

        facts = PIIScrubbingMiddleware().scrub(["Python, FastAPI, SQL and Git"], "backend-engineer")
        result = await client.assess(facts, f"smoke_{uuid.uuid4().hex}")
        print(result.model_dump_json(indent=2))
    finally:
        await client.close()


asyncio.run(main())
