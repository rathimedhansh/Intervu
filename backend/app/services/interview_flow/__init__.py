from app.core.config import settings
from app.models.question import Question
from app.models.resume import Resume
from app.services.interview_flow import anthropic_provider, mock_provider
from app.services.interview_flow.types import NextStep

__all__ = ["decide_next_step", "NextStep", "MIN_QUESTIONS", "MAX_QUESTIONS"]

# "Keep the interview reasonably bounded" — the conversational flow always
# asks somewhere in this range, regardless of what a client requests at
# creation time (see app.crud.interview.create_interview, which clamps into
# this range before persisting Interview.question_count).
MIN_QUESTIONS = 5
MAX_QUESTIONS = 10


def decide_next_step(
    *,
    role: str,
    difficulty: str,
    resume: Resume | None,
    asked_questions: list[Question],
    current_is_followup: bool,
    question_count: int,
    focus_categories: list[str] | None = None,
) -> NextStep:
    if settings.ai_provider == "anthropic":
        step = anthropic_provider.decide(
            role=role,
            difficulty=difficulty,
            resume=resume,
            asked_questions=asked_questions,
            current_is_followup=current_is_followup,
            question_count=question_count,
            focus_categories=focus_categories,
        )
    else:
        step = mock_provider.decide(
            role=role,
            difficulty=difficulty,
            resume=resume,
            asked_questions=asked_questions,
            current_is_followup=current_is_followup,
            question_count=question_count,
            focus_categories=focus_categories,
        )

    # Defense in depth: never allow two follow-ups back to back, regardless
    # of what a provider decided (mock providers already respect this; an AI
    # provider that ignores the instruction in its prompt must not be able
    # to chain follow-ups indefinitely).
    if current_is_followup and step.is_followup:
        step = NextStep(question=step.question, is_followup=False)

    return step
