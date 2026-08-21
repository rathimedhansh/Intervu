from app.core.config import settings
from app.models.resume import Resume
from app.services.question_generation import anthropic_provider, mock_provider
from app.services.question_generation.types import GeneratedQuestion

__all__ = ["generate_questions", "generate_intro_question", "GeneratedQuestion"]


def generate_intro_question(role: str) -> GeneratedQuestion:
    """The interview's opening question (see mock_provider.generate_intro) —
    always a plain, deterministic icebreaker, independent of AI provider or
    the difficulty/resume the candidate selected. Every question from here
    on is handled by the adaptive conversational flow (see
    app.services.interview_flow) as the candidate answers."""
    return GeneratedQuestion(text=mock_provider.generate_intro(role), source="bank")


def generate_questions(
    role: str, difficulty: str, count: int, resume: Resume | None = None
) -> list[GeneratedQuestion]:
    if resume is not None:
        if settings.ai_provider == "anthropic":
            return anthropic_provider.generate_from_resume(role, difficulty, count, resume)
        return mock_provider.generate_from_resume(role, difficulty, count, resume)

    if settings.ai_provider == "anthropic":
        texts = anthropic_provider.generate(role, difficulty, count)
    else:
        texts = mock_provider.generate(role, difficulty, count)
    return [GeneratedQuestion(text=text, source="bank") for text in texts]
