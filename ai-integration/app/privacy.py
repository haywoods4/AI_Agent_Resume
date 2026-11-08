"""Fail-closed privacy middleware: project raw documents onto a fixed skills vocabulary.

No free-form resume text, contact fields, names, dates, schools or locations are
forwarded to Hermes, Groq, OPA or application logs. Missing evidence is not proof
that a candidate lacks a qualification.
"""

import hashlib
import hmac
import io
import json
import re
import zipfile
from pathlib import Path

from docx import Document
from pypdf import PdfReader

from app.contracts import ScreeningFacts, SkillEvidence

SKILLS = {
    "python": ("python",),
    "javascript": ("javascript", "js"),
    "typescript": ("typescript",),
    "react": ("react", "react.js", "reactjs"),
    "fastapi": ("fastapi",),
    "sql": ("sql", "sqlite", "postgresql", "mysql"),
    "git": ("git", "github", "gitlab"),
    "docker": ("docker",),
    "java": ("java",),
    "linux": ("linux",),
}
JOBS_PATH = Path(__file__).resolve().parent.parent / "config" / "jobs.json"


class PrivacyError(ValueError):
    pass


def jobs() -> dict:
    catalog = json.loads(JOBS_PATH.read_text())
    for job in catalog.values():
        required = job["required_skills"]
        if not required or len(required) != len(set(required)) or set(required) - SKILLS.keys():
            raise ValueError("Job requirements must use unique approved skill IDs")
    return catalog


def normalize_identifier(value: str, kind: str) -> str:
    if kind == "email":
        value = value.strip().casefold()
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value) or len(value) > 254:
            raise PrivacyError("Invalid email address")
    elif kind == "phone":
        value = re.sub(r"[ ()\-.]", "", value)
        if not re.fullmatch(r"\+[1-9][0-9]{6,14}", value):
            raise PrivacyError("Phone must use international +country-code format")
    else:
        raise PrivacyError("Unsupported identifier")
    return value


def identifier_hash(secret: str, tenant: str, kind: str, value: str) -> str:
    normalized = normalize_identifier(value, kind)
    message = json.dumps([tenant, kind, normalized], separators=(",", ":"))
    return hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()


def document_pages(content: bytes, filename: str) -> list[str]:
    if not content or len(content) > 2 * 1024 * 1024:
        raise PrivacyError("Upload a nonempty document no larger than 2 MiB")
    suffix = Path(filename).suffix.lower()
    try:
        if suffix == ".txt":
            pages = [content.decode("utf-8")]
        elif suffix == ".pdf":
            if not content.startswith(b"%PDF-"):
                raise PrivacyError("Invalid PDF")
            reader = PdfReader(io.BytesIO(content), strict=True)
            if reader.is_encrypted or len(reader.pages) > 30:
                raise PrivacyError("Encrypted PDFs and documents over 30 pages are unsupported")
            pages = [page.extract_text() or "" for page in reader.pages]
        elif suffix == ".docx":
            with zipfile.ZipFile(io.BytesIO(content)) as archive:
                if sum(item.file_size for item in archive.infolist()) > 10 * 1024 * 1024:
                    raise PrivacyError("Expanded DOCX is too large")
            document = Document(io.BytesIO(content))
            paragraphs = [p.text for p in document.paragraphs]
            paragraphs += [
                cell.text for table in document.tables for row in table.rows for cell in row.cells
            ]
            pages = ["\n".join(paragraphs)]
        else:
            raise PrivacyError("Use a text-based PDF, DOCX or UTF-8 TXT file")
    except PrivacyError:
        raise
    except Exception as error:
        raise PrivacyError(
            "Document could not be read; use a text-based PDF, DOCX or TXT"
        ) from error
    if not any(page.strip() for page in pages) or sum(map(len, pages)) > 100_000:
        raise PrivacyError("No readable text, or extracted text exceeds 100,000 characters")
    return pages


class PIIScrubbingMiddleware:
    """Application pipeline middleware, shared by every upload route and model call."""

    def scrub(self, pages: list[str], job_id: str) -> ScreeningFacts:
        catalog = jobs()
        if job_id not in catalog:
            raise PrivacyError("Unknown job")
        required = catalog[job_id]["required_skills"]
        evidence = []
        for skill in required:
            aliases = "|".join(re.escape(word) for word in SKILLS[skill])
            pattern = re.compile(r"(?<![\w])(?:" + aliases + r")(?![\w])", re.IGNORECASE)
            matches = [index + 1 for index, page in enumerate(pages) if pattern.search(page)]
            if matches:
                evidence.append(SkillEvidence(skill_id=skill, pages=matches))
        return ScreeningFacts(
            job_id=job_id,
            required_skills=required,
            observed_skills=evidence,
            page_count=len(pages),
        )
