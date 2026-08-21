from dataclasses import dataclass

from app.services.question_generation.types import GeneratedQuestion


@dataclass
class NextStep:
    question: GeneratedQuestion
    # True when `question` is a follow-up to the just-answered question
    # rather than a new main question.
    is_followup: bool
