from datetime import datetime, timedelta, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    generate_password_reset_token,
    hash_password,
    hash_reset_token,
    verify_password,
)
from app.models.password_reset_token import PasswordResetToken
from app.models.user import User


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email.strip().lower()).first()


def get_user_by_id(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)


def create_user(db: Session, name: str, email: str, password: str) -> User:
    normalized_email = email.strip().lower()
    if get_user_by_email(db, normalized_email) is not None:
        raise ValueError("Email already registered")

    user = User(
        name=name.strip(),
        email=normalized_email,
        password_hash=hash_password(password),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        # Race with a concurrent signup for the same email; the unique
        # constraint is the source of truth, the check above is just a
        # fast path for the common case.
        db.rollback()
        raise ValueError("Email already registered") from None
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    user = get_user_by_email(db, email)
    if user is None:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def create_password_reset_token(db: Session, user: User) -> str:
    """Create a fresh reset token for `user` and return the plaintext
    (only the hash is persisted). Any of the user's earlier, still-valid
    tokens are left alone — they simply also work until they expire or are
    used, since a user may have re-requested a link after losing the first
    email."""
    plaintext, token_hash = generate_password_reset_token()
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.password_reset_expire_minutes
    )
    db.add(PasswordResetToken(user_id=user.id, token_hash=token_hash, expires_at=expires_at))
    db.commit()
    return plaintext


def get_valid_reset_token(db: Session, plaintext_token: str) -> PasswordResetToken | None:
    token_hash = hash_reset_token(plaintext_token)
    record = (
        db.query(PasswordResetToken)
        .filter(PasswordResetToken.token_hash == token_hash)
        .first()
    )
    if record is None or record.used_at is not None:
        return None
    expires_at = record.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        return None
    return record


def reset_password(db: Session, token_record: PasswordResetToken, new_password: str) -> None:
    user = db.get(User, token_record.user_id)
    user.password_hash = hash_password(new_password)
    token_record.used_at = datetime.now(timezone.utc)
    db.commit()
