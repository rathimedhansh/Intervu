import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import settings

# bcrypt has a hard 72-byte input limit; Pydantic schemas cap password
# length at or below this, but truncate defensively here too rather than
# letting bcrypt raise on an unexpectedly long value.
_BCRYPT_MAX_BYTES = 72


def hash_password(password: str) -> str:
    """Hash a plaintext password with bcrypt. Never log or persist the input."""
    encoded = password.encode("utf-8")[:_BCRYPT_MAX_BYTES]
    return bcrypt.hashpw(encoded, bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    encoded = password.encode("utf-8")[:_BCRYPT_MAX_BYTES]
    try:
        return bcrypt.checkpw(encoded, password_hash.encode("utf-8"))
    except ValueError:
        # Malformed/foreign hash format — treat as a failed match, not a crash.
        return False


def create_access_token(user_id: int) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.jwt_expire_minutes
    )
    payload = {"sub": str(user_id), "exp": expires_at}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def generate_password_reset_token() -> tuple[str, str]:
    """Return (plaintext_token, token_hash). Only the hash is ever stored;
    the plaintext is put in the reset link and never persisted."""
    plaintext = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(plaintext.encode("utf-8")).hexdigest()
    return plaintext, token_hash


def hash_reset_token(plaintext_token: str) -> str:
    return hashlib.sha256(plaintext_token.encode("utf-8")).hexdigest()


def decode_access_token(token: str) -> int | None:
    """Return the user id encoded in a valid, unexpired token, else None."""
    try:
        payload = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
    except jwt.PyJWTError:
        return None

    subject = payload.get("sub")
    if subject is None:
        return None
    try:
        return int(subject)
    except (TypeError, ValueError):
        return None
