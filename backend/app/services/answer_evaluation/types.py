from dataclasses import dataclass
from typing import Literal

from app.services.answer_evaluation.rubrics import QuestionType

Evaluator = Literal["mock", "anthropic"]


@dataclass
class CategoryScore:
    category: str
    label: str
    score: int
    max_score: int

    def to_dict(self) -> dict:
        return {
            "category": self.category,
            "label": self.label,
            "score": self.score,
            "max_score": self.max_score,
        }


@dataclass
class AnswerEvaluation:
    question_type: QuestionType
    evaluator: Evaluator
    category_scores: list[CategoryScore]
    total_score: int
    max_score: int
    strengths: list[str]
    weaknesses: list[str]
    improvement_suggestions: list[str]
    stronger_answer_example: str
    note: str | None = None

    def to_dict(self) -> dict:
        return {
            "question_type": self.question_type,
            "evaluator": self.evaluator,
            "category_scores": [c.to_dict() for c in self.category_scores],
            "total_score": self.total_score,
            "max_score": self.max_score,
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
            "improvement_suggestions": self.improvement_suggestions,
            "stronger_answer_example": self.stronger_answer_example,
            "note": self.note,
        }
