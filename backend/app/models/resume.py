from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Resume(Base):
    __tablename__ = "resumes"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Generated filename on disk (see app.services.resume_storage) — never
    # derived from client input. original_filename is metadata only, never
    # used to build a filesystem path.
    stored_filename: Mapped[str] = mapped_column(String(80), unique=True)
    original_filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int] = mapped_column(Integer)

    extracted_text: Mapped[str] = mapped_column(Text)
    # {"skills": [...], "projects": [...], "education": [...],
    #  "experience": [...], "technologies": [...]}
    parsed: Mapped[dict] = mapped_column(JSON)
    # {"summary": str, "strong_areas": [...], "missing_details": [...],
    #  "key_projects": [...], "key_technologies": [...]}
    analysis: Mapped[dict] = mapped_column(JSON)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    # Owning user. Nullable at the DB level only so pre-auth local dev rows
    # keep loading — every resume uploaded through the API from here on
    # always has a user_id, enforced by app.crud.resume.create_resume.
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    user: Mapped["User | None"] = relationship(back_populates="resumes")
