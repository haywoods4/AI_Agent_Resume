import os
from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass(frozen=True)
class Settings:
    database: str = "data/resume.sqlite"
    mode: str = "hermes"
    hermes_url: str = "http://127.0.0.1:8642/v1/chat/completions"
    hermes_key: str = ""
    hermes_model: str = "hermes-agent"
    model_version: str = "groq/llama-3.3-70b-versatile"
    hermes_timeout: float = 9
    opa_url: str = "http://127.0.0.1:8181/v1/data/resume/screening/result"
    opa_timeout: float = 1
    reviewer_token: str = ""
    hmac_key: str = ""
    tenant_id: str = "group2-corp"
    reviewer_id: str = "reviewer-1"
    redis_url: str = ""

    @classmethod
    def from_env(cls):
        return cls(
            database=os.getenv("DATABASE_PATH", "data/resume.sqlite"),
            mode=os.getenv("AI_MODE", "hermes"),
            hermes_url=os.getenv("HERMES_URL", cls.hermes_url),
            hermes_key=os.getenv("HERMES_API_KEY", ""),
            hermes_model=os.getenv("HERMES_MODEL", "hermes-agent"),
            model_version=os.getenv("INFERENCE_MODEL_VERSION", cls.model_version),
            hermes_timeout=float(os.getenv("HERMES_TIMEOUT_SECONDS", "9")),
            opa_url=os.getenv("OPA_URL", cls.opa_url),
            opa_timeout=float(os.getenv("OPA_TIMEOUT_SECONDS", "1")),
            reviewer_token=os.getenv("REVIEWER_TOKEN", ""),
            hmac_key=os.getenv("PII_HMAC_KEY", ""),
            tenant_id=os.getenv("TENANT_ID", "group2-corp"),
            reviewer_id=os.getenv("REVIEWER_ID", "reviewer-1"),
            redis_url=os.getenv("REDIS_URL", ""),
        )

    def validate(self):
        if self.mode not in {"hermes", "demo"}:
            raise ValueError("AI_MODE must be hermes or demo")
        if len(self.reviewer_token) < 24 or len(self.hmac_key) < 24:
            raise ValueError("Set REVIEWER_TOKEN and PII_HMAC_KEY to independent random secrets")
        if self.reviewer_token == self.hmac_key:
            raise ValueError("Reviewer and HMAC secrets must differ")
        if self.mode == "hermes" and not self.hermes_key:
            raise ValueError("Set HERMES_API_KEY for the local Hermes API")
        if not (0 < self.hermes_timeout < 10 and 0 < self.opa_timeout <= 10):
            raise ValueError("Invalid dependency timeout")
        for value in (self.hermes_url, self.opa_url):
            url = urlparse(value)
            if url.scheme != "https" and not (
                url.scheme == "http" and url.hostname in {"127.0.0.1", "localhost", "::1"}
            ):
                raise ValueError("Remote dependencies require HTTPS")
