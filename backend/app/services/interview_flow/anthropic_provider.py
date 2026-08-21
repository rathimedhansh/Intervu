import logging

import anthropic

from app.core.config import settings
from app.models.question import Question
from app.models.resume import Resume
from app.services.answer_evaluation.rubrics import CATEGORY_DESCRIPTIONS, CATEGORY_LABELS
from app.services.interview_flow import mock_provider
from app.services.interview_flow.difficulty import answer_ratio
from app.services.interview_flow.difficulty import effective_difficulty as compute_effective_difficulty
from app.services.interview_flow.types import NextStep
from app.services.question_generation.types import GeneratedQuestion

logger = logging.getLogger(__name__)

TOOL_NAME = "decide_next_interview_step"


def _build_tool() -> list[dict]:
    return [
        {
            "name": TOOL_NAME,
            "description": "Decide the next step in an ongoing mock interview conversation.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["follow_up", "next_question"],
                        "description": (
                            "'follow_up' only if the candidate's most recent answer "
                            "mentioned something specific worth probing deeper; "
                            "'next_question' otherwise."
                        ),
                    },
                    "question": {
                        "type": "string",
                        "description": "The question text to ask next.",
                    },
                    "topic": {
                        "type": "string",
                        "description": (
                            "If this question is grounded in a specific resume item, a "
                            "short label for it (e.g. 'Project: Order Service'). Omit "
                            "if not resume-grounded."
                        ),
                    },
                },
                "required": ["action", "question"],
            },
        }
    ]


def _build_prompt(
    role: str,
    difficulty: str,
    resume: Resume | None,
    asked_questions: list[Question],
    current_is_followup: bool,
    question_count: int,
    focus_categories: list[str] | None = None,
) -> str:
    questions_asked = len(asked_questions)
    lines = []
    for index, question in enumerate(asked_questions, start=1):
        tag = " (follow-up)" if question.is_followup else ""
        lines.append(f"Q{index}{tag}: {question.text}")
        if question.answer:
            lines.append(f"A{index}: {question.answer.text}")
            ratio = answer_ratio(question)
            if ratio is not None:
                lines.append(f"  [scored {round(ratio * 100)}% by the rubric]")
    transcript = "\n".join(lines)

    resume_section = ""
    if resume is not None:
        resume_section = (
            "\n\nThe candidate's resume — only reference things actually present "
            f"here, never invent details that aren't stated:\n{resume.extracted_text}"
        )

    followup_note = (
        "The current question was itself a follow-up, so choose 'next_question', "
        "not another follow-up. "
        if current_is_followup
        else ""
    )

    # Deterministic, computed-from-history hints (see mock_provider.py) —
    # not instructions the model must obey verbatim, just the same signal
    # the deterministic fallback uses, so both providers adapt consistently.
    effective_difficulty = compute_effective_difficulty(difficulty, asked_questions)
    preferred_type = (
        mock_provider._focus_question_type(focus_categories)
        or mock_provider._preferred_question_type(asked_questions)
    )

    focus_section = ""
    if focus_categories:
        criteria = "; ".join(
            f"{CATEGORY_LABELS.get(c, c)} — {CATEGORY_DESCRIPTIONS.get(c, '')}"
            for c in focus_categories
        )
        focus_section = (
            "\n\nThis is a focused practice session: the candidate specifically "
            f"wants to strengthen these areas: {criteria}. Favor questions (and "
            "follow-ups) that give them a real opportunity to demonstrate and "
            "improve on these dimensions, without making the interview feel "
            "mechanical or artificial."
        )

    return (
        f'You are conducting a mock interview for a "{role}" role. The candidate '
        f'selected "{difficulty}" difficulty at the start. {questions_asked} of '
        f"{question_count} total questions have been asked so far.\n\n"
        f'Based on recent answer quality, aim for roughly "{effective_difficulty}" '
        "difficulty for the next main question — raise difficulty gradually after "
        "strong answers, step back to an easier or clarifying question after a weak "
        "one, and never make an extreme jump based on a single answer. To keep a "
        f'natural mix of question types, lean toward a "{preferred_type}" question '
        "next if a new main question (not a follow-up) is appropriate.\n\n"
        f"Transcript so far:\n{transcript}{resume_section}{focus_section}\n\n"
        "Decide what happens next. Choose 'follow_up' only if the candidate's most "
        "recent answer mentioned something specific and interesting worth probing "
        "deeper (a project, a technical decision, a technology, a challenge) — do "
        "not force a follow-up on every answer, and if the answer was weak, vague, "
        "or missing key details, prefer a clarifying follow-up over a harder one. "
        f"{followup_note}"
        "Otherwise choose 'next_question' for a new main question appropriate for "
        "the role, grounded in the resume when relevant, drawing from a natural mix "
        "of introduction/background, behavioral, technical, and scenario/problem-"
        "solving questions as the interview progresses, and not already asked above."
    )


def decide(
    *,
    role: str,
    difficulty: str,
    resume: Resume | None,
    asked_questions: list[Question],
    current_is_followup: bool,
    question_count: int,
    focus_categories: list[str] | None = None,
) -> NextStep:
    if not settings.anthropic_api_key:
        logger.warning("ANTHROPIC_API_KEY not set; using mock interview flow decision.")
        return mock_provider.decide(
            role=role,
            difficulty=difficulty,
            resume=resume,
            asked_questions=asked_questions,
            current_is_followup=current_is_followup,
            question_count=question_count,
            focus_categories=focus_categories,
        )

    try:
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        response = client.messages.create(
            model=settings.anthropic_model,
            max_tokens=512,
            tools=_build_tool(),
            tool_choice={"type": "tool", "name": TOOL_NAME},
            messages=[
                {
                    "role": "user",
                    "content": _build_prompt(
                        role,
                        difficulty,
                        resume,
                        asked_questions,
                        current_is_followup,
                        question_count,
                        focus_categories,
                    ),
                }
            ],
        )

        for block in response.content:
            if block.type == "tool_use" and block.name == TOOL_NAME:
                action = block.input.get("action")
                question_text = block.input.get("question")
                topic = block.input.get("topic")
                if action in ("follow_up", "next_question") and question_text:
                    is_followup = action == "follow_up" and not current_is_followup
                    return NextStep(
                        question=GeneratedQuestion(
                            text=str(question_text),
                            source="resume" if topic else "bank",
                            topic=str(topic) if topic else None,
                        ),
                        is_followup=is_followup,
                    )

        logger.warning(
            "Claude response had no usable tool call; using mock interview flow decision."
        )
    except Exception:
        logger.exception("Interview flow decision failed; using mock decision.")

    return mock_provider.decide(
        role=role,
        difficulty=difficulty,
        resume=resume,
        asked_questions=asked_questions,
        current_is_followup=current_is_followup,
        question_count=question_count,
        focus_categories=focus_categories,
    )
