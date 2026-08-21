from app.core.config import settings
from app.services.answer_evaluation import anthropic_provider, mock_provider
from app.services.answer_evaluation.rubrics import classify_question_type
from app.services.answer_evaluation.types import AnswerEvaluation, CategoryScore

__all__ = ["evaluate_answer", "classify_question_type", "AnswerEvaluation", "CategoryScore"]


def evaluate_answer(question: str, answer: str, role: str, difficulty: str) -> AnswerEvaluation:
    question_type = classify_question_type(question)
    if settings.ai_provider == "anthropic":
        return anthropic_provider.generate(question, answer, role, difficulty, question_type)
    return mock_provider.generate(question, answer, role, difficulty, question_type)
