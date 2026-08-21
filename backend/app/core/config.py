import logging
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

_INSECURE_DEV_JWT_SECRET = "insecure-dev-secret-change-in-production"


class Settings(BaseSettings):
    app_name: str = "AI Mock Interviewer API"
    database_url: str = "sqlite:///./app.db"
    # Explicit dev-origin whitelist, not a wildcard: Vite falls back to the
    # next port (5174, 5175, ...) whenever the default 5173 is already taken
    # by another process on the machine, so the frontend doesn't always run
    # on the same port. Covers 5173-5176 to absorb that without allowing
    # arbitrary origins.
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5175",
        "http://localhost:5176",
        "http://127.0.0.1:5176",
    ]

    ai_provider: Literal["mock", "anthropic"] = "mock"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-5"

    # Resume uploads: stored outside any statically-served directory, under a
    # generated (non-user-controlled) filename. Never exposed via a public URL.
    resume_upload_dir: str = "uploads/resumes"
    resume_max_size_bytes: int = 5 * 1024 * 1024  # 5 MB
    resume_max_pages: int = 10
    resume_max_text_chars: int = 20_000

    # JWT auth. The default below is dev-only and intentionally weak — every
    # deployment must override JWT_SECRET_KEY via the environment (see
    # .env.example). Tokens are stateless (sub = user id); "logout" is a
    # frontend-only action (discard the token), there is no server-side
    # session to invalidate.
    jwt_secret_key: str = _INSECURE_DEV_JWT_SECRET
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7  # 7 days

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # An empty JWT_SECRET_KEY in the environment (e.g. .env copied from
    # .env.example without filling it in) must never silently become an
    # empty signing key — fall back to the dev secret and warn instead.
    @field_validator("jwt_secret_key")
    @classmethod
    def _default_when_blank(cls, value: str) -> str:
        if not value.strip():
            logger.warning(
                "JWT_SECRET_KEY is not set; using an insecure development "
                "default. Set a real secret before deploying."
            )
            return _INSECURE_DEV_JWT_SECRET
        return value


settings = Settings()
