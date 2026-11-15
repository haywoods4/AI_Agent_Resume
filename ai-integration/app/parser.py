import asyncio
import json
import sys
from pathlib import Path

from app.privacy import PrivacyError


async def parse_document(content: bytes, filename: str) -> list[str]:
    if not content or len(content) > 2 * 1024 * 1024:
        raise PrivacyError("Document must be between 1 byte and 2 MiB")
    suffix = Path(filename).suffix.lower()
    if suffix not in {".pdf", ".docx", ".txt"}:
        raise PrivacyError("Use PDF, DOCX or TXT")
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "app.parse_worker",
        f"resume{suffix}",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
        cwd=Path(__file__).resolve().parent.parent,
    )
    try:
        output, _ = await asyncio.wait_for(process.communicate(content), timeout=6)
    except (TimeoutError, asyncio.CancelledError) as error:
        if process.returncode is None:
            process.kill()
        await process.wait()
        if isinstance(error, asyncio.CancelledError):
            raise
        raise PrivacyError("Document parsing timed out") from None
    if process.returncode != 0:
        raise PrivacyError("Unreadable document; upload a text-based PDF, DOCX or TXT")
    return json.loads(output)["pages"]
