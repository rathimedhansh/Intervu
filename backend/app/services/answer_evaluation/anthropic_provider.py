import logging

import anthropic

from app.core.config import settings
from app.services.answer_evaluation import mock_provider, rubrics
from app.services.answer_evaluation.rubrics import QuestionType
from app.services.answer_evaluation.types import AnswerEvaluation, CategoryScore

logger = logging.getLogger(__name__)

TOOL_NAME = "return_evaluation"

LIST_FIELDS = ("strengths", "weaknesses", "improvement_suggestions")


class InvalidEvaluationError(ValueError):
    """Raised when the AI's tool-call output doesn't match the expected shape."""


def _build_tools(rubric: dict[str, tuple[str, int]]) -> list[dict]:
    properties = {
        key: {
            "type": "integer",
            "minimum": 0,
            "maximum": max_score,
            "description": f"{label} score, 0-{max_score}.",
        }
        for key, (label, max_score) in rubric.items()
    }
    properties.update(
        {
            "strengths": {
                "type": "array",
                "items": {"type": "string"},
                "description": "2-3 specific strengths of this answer.",
            },
            "weaknesses": {
                "type": "array",
                "items": {"type": "string"},
                "description": "2-3 specific weaknesses of this answer.",
            },
            "improvement_suggestions": {
                "type": "array",
                "items": {"type": "string"},
                "description": "2-3 concrete, actionable suggestions to improve this answer.",
            },
            "stronger_answer_example": {
                "type": "string",
                "description": "A brief illustrative example of what a stronger answer would look like.",
            },
        }
    )
    return [
        {
            "name": TOOL_NAME,
            "description": "Return a structured rubric evaluation of a candidate's interview answer.",
            "input_schema": {
                "type": "object",
                "properties": properties,
                "required": list(rubric.keys())
                + ["strengths", "weaknesses", "improvement_suggestions", "stronger_answer_example"],
            },
        }
    ]


def _rubric_text(rubric: dict[str, tuple[str, int]]) -> str:
    lines = []
    for key, (label, max_score) in rubric.items():
        criteria = rubrics.CATEGORY_DESCRIPTIONS.get(key, "")
        lines.append(f"- {label} (0-{max_score}): {criteria}")
    return "\n".join(lines)


def _build_prompt(question: str, answer: str, role: str, difficulty: str, qtype: QuestionType) -> str:
    rubric = rubrics.get_rubric(qtype)
    total_points = sum(max_score for _, max_score in rubric.values())
    return (
        "You are an expert interviewer evaluating a candidate's answer in a mock "
        f'interview for a "{role}" role at "{difficulty}" difficulty.\n\n'
        f"Question type: {qtype}\n"
        f"Question: {question}\n\n"
        f"Candidate's answer:\n{answer}\n\n"
        f"Rubric ({qtype}, {total_points} points total):\n{_rubric_text(rubric)}\n\n"
        "Evaluate ONLY the candidate's submitted answer above against this rubric. "
        "Do not reward claims or context that aren't actually present in the answer, "
        "and do not score anything outside these categories. Score each category, "
        "then give strengths, weaknesses, improvement suggestions, and a brief "
        "example of what a stronger answer would look like."
    )


def _validate_evaluation_data(data: dict, rubric: dict[str, tuple[str, int]]) -> None:
    if not isinstance(data, dict):
        raise InvalidEvaluationError(f"expected a JSON object, got {type(data).__name__}")

    for key, (label, max_score) in rubric.items():
        if key not in data:
            raise InvalidEvaluationError(f"missing rubric category '{key}' ({label})")
        value = data[key]
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise InvalidEvaluationError(f"category '{key}' score is not numeric: {value!r}")
        if not (0 <= value <= max_score):
            raise InvalidEvaluationError(
                f"category '{key}' score {value} is out of range 0-{max_score}"
            )

    for field in LIST_FIELDS:
        value = data.get(field)
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise InvalidEvaluationError(f"field '{field}' must be a list of strings, got {value!r}")

    example = data.get("stronger_answer_example")
    if not isinstance(example, str) or not example.strip():
        raise InvalidEvaluationError(
            f"field 'stronger_answer_example' must be a non-empty string, got {example!r}"
        )


def _to_answer_evaluation(
    data: dict, qtype: QuestionType, rubric: dict[str, tuple[str, int]]
) -> AnswerEvaluation:
    category_scores = [
        CategoryScore(category=key, label=label, score=int(data[key]), max_score=max_score)
        for key, (label, max_score) in rubric.items()
    ]
    return AnswerEvaluation(
        question_type=qtype,
        evaluator="anthropic",
        category_scores=category_scores,
        total_score=sum(c.score for c in category_scores),
        max_score=sum(max_score for _, max_score in rubric.values()),
        strengths=list(data["strengths"]),
        weaknesses=list(data["weaknesses"]),
        improvement_suggestions=list(data["improvement_suggestions"]),
        stronger_answer_example=data["stronger_answer_example"],
        note=None,
    )


def generate(
    question: str,
    answer: str,
    role: str,
    difficulty: str,
    question_type: QuestionType | None = None,
) -> AnswerEvaluation:
    qtype = question_type or rubrics.classify_question_type(question)
    rubric = rubrics.get_rubric(qtype)

    if not settings.anthropic_api_key:
        logger.warning("ANTHROPIC_API_KEY not set; using mock evaluation.")
        return mock_provider.generate(question, answer, role, difficulty, question_type=qtype)

    try:
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        response = client.messages.create(
            model=settings.anthropic_model,
            max_tokens=1024,
            tools=_build_tools(rubric),
            tool_choice={"type": "tool", "name": TOOL_NAME},
            messages=[{"role": "user", "content": _build_prompt(question, answer, role, difficulty, qtype)}],
        )
    except Exception:
        logger.exception("Anthropic API call failed; using mock evaluation.")
        return mock_provider.generate(question, answer, role, difficulty, question_type=qtype)

    tool_input = next(
        (block.input for block in response.content if block.type == "tool_use" and block.name == TOOL_NAME),
        None,
    )
    if tool_input is None:
        logger.warning("Claude response had no usable tool call; using mock evaluation.")
        return mock_provider.generate(question, answer, role, difficulty, question_type=qtype)

    try:
        _validate_evaluation_data(tool_input, rubric)
        return _to_answer_evaluation(tool_input, qtype, rubric)
    except InvalidEvaluationError:
        logger.exception("Anthropic response failed validation; using mock evaluation.")
        return mock_provider.generate(question, answer, role, difficulty, question_type=qtype)
