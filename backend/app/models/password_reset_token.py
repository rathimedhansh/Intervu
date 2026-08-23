from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    user: Mapped["User"] = relationship()

    # SHA-256 hex digest of the token, never the token itself — same
    # reasoning as password_hash: a DB read (backup, injection, etc.) must
    # not hand over a usable reset credential. High-entropy + single-use +
    # short-lived means a fast hash (unlike bcrypt for passwords) is fine.
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)

    expires_at: Mapped[datetime] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    # Set once the token is redeemed; a used token is never valid again
    # even if it hasn't expired yet.
    used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
