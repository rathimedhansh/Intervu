from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Interview(Base):
    __tablename__ = "interviews"

    id: Mapped[int] = mapped_column(primary_key=True)
    role: Mapped[str] = mapped_column(String(100))
    difficulty: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    overall_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    strengths: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    weaknesses: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    summary_feedback: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Set when this interview was generated from an uploaded resume; null
    # for the standard bank/AI-generated flow (existing behavior).
    resume_id: Mapped[int | None] = mapped_column(
        ForeignKey("resumes.id"), nullable=True
    )
    resume: Mapped["Resume | None"] = relationship()

    # Owning user. Nullable at the DB level only so pre-auth local dev rows
    # (created before this column existed) keep loading — every interview
    # created through the API from here on always has a user_id, enforced
    # by app.crud.interview.create_interview requiring it.
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    user: Mapped["User | None"] = relationship(back_populates="interviews")

    # Derived, locally-computed camera/presentation metrics for the whole
    # session (see app.services.communication_feedback). Never raw video or
    # face images — only aggregate percentages/scores the browser computed
    # client-side. Null when camera analysis wasn't opted into.
    camera_metrics: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    questions: Mapped[list["Question"]] = relationship(
        back_populates="interview",
        cascade="all, delete-orphan",
        order_by="Question.order_index",
    )

    # Target number of questions for the conversational interview flow (see
    # app.services.interview_flow), clamped server-side to [MIN_QUESTIONS,
    # MAX_QUESTIONS] at creation — never trusted from the client as-is.
    # Null for interviews created before this feature; those don't support
    # the dynamic /respond flow (see the 400 guard on that route).
    question_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Rubric category keys (app.services.answer_evaluation.rubrics.
    # FOCUSABLE_CATEGORIES) the candidate specifically wants to practice this
    # session — set via the dashboard's "Practice weak areas" flow or the
    # optional focus-area picker on interview setup. Biases question
    # selection in app.services.interview_flow toward exercising these; null
    # for a normal, unfocused interview.
    focus_categories: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
