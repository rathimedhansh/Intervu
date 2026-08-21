from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Answer(Base):
    __tablename__ = "answers"

    id: Mapped[int] = mapped_column(primary_key=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"), unique=True)
    text: Mapped[str] = mapped_column(Text)
    # 0-100 rubric total; see app.services.answer_evaluation. `evaluation`
    # holds the full structured result (category_scores, strengths,
    # weaknesses, improvement_suggestions, stronger_answer_example, ...).
    total_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    evaluation: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # Derived, locally-computed speech metrics for this answer (see
    # app.services.communication_feedback). Never raw audio — only counts/
    # durations the browser computed client-side. Null when speech analysis
    # wasn't opted into or the browser couldn't produce metrics.
    speech_metrics: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    question: Mapped["Question"] = relationship(back_populates="answer")
