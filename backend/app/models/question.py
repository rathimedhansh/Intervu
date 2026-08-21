from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(primary_key=True)
    interview_id: Mapped[int] = mapped_column(ForeignKey("interviews.id"))
    text: Mapped[str] = mapped_column(String(500))
    order_index: Mapped[int] = mapped_column(Integer)

    # "bank" (default, existing flow) or "resume" (generated from an
    # uploaded resume). resume_topic is a short label of what part of the
    # resume prompted the question (e.g. "Project: Order Service"), used to
    # highlight resume-sourced questions in the UI.
    source: Mapped[str] = mapped_column(String(20), default="bank")
    resume_topic: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # True when this question was dynamically generated as a follow-up to
    # the previous answer rather than a new main question (see
    # app.services.interview_flow). Follow-up depth is capped at 1 — a
    # follow-up never itself gets a follow-up.
    is_followup: Mapped[bool] = mapped_column(default=False)

    interview: Mapped["Interview"] = relationship(back_populates="questions")
    answer: Mapped["Answer | None"] = relationship(
        back_populates="question",
        uselist=False,
        cascade="all, delete-orphan",
    )
