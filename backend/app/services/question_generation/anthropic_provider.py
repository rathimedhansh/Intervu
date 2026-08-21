import logging

import anthropic

from app.core.config import settings
from app.models.resume import Resume
from app.services.question_generation import mock_provider
from app.services.question_generation.types import GeneratedQuestion

logger = logging.getLogger(__name__)

TOOL_NAME = "return_questions"
RESUME_TOOL_NAME = "return_resume_questions"


def _build_tools(count: int) -> list[dict]:
    return [
        {
            "name": TOOL_NAME,
            "description": "Return the generated mock interview questions.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "questions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "minItems": count,
                        "maxItems": count,
                        "description": "The interview questions, in the order they should be asked.",
                    }
                },
                "required": ["questions"],
            },
        }
    ]


def generate(role: str, difficulty: str, count: int) -> list[str]:
    if not settings.anthropic_api_key:
        logger.warning("ANTHROPIC_API_KEY not set; using mock questions.")
        return mock_provider.generate(role, difficulty, count)

    try:
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        response = client.messages.create(
            model=settings.anthropic_model,
            max_tokens=1024,
            tools=_build_tools(count),
            tool_choice={"type": "tool", "name": TOOL_NAME},
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Generate exactly {count} mock interview questions "
                        f'for a candidate applying to a "{role}" role, at "{difficulty}" '
                        "difficulty. Mix behavioral and role-relevant practical questions "
                        "appropriate for that difficulty level."
                    ),
                }
            ],
        )

        for block in response.content:
            if block.type == "tool_use" and block.name == TOOL_NAME:
                questions = block.input.get("questions")
                if questions:
                    return questions

        logger.warning("Claude response had no usable tool call; using mock questions.")
        return mock_provider.generate(role, difficulty, count)

    except Exception:
        logger.exception("Question generation failed; using mock questions.")
        return mock_provider.generate(role, difficulty, count)


def _build_resume_tools(count: int) -> list[dict]:
    return [
        {
            "name": RESUME_TOOL_NAME,
            "description": "Return resume-aware mock interview questions.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "questions": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "text": {
                                    "type": "string",
                                    "description": "The interview question.",
                                },
                                "topic": {
                                    "type": "string",
                                    "description": (
                                        "Short label of the resume project, technology, or "
                                        "experience item this question is about, e.g. "
                                        "'Project: Order Service' or 'Technology: PostgreSQL'."
                                    ),
                                },
                            },
                            "required": ["text", "topic"],
                        },
                        "minItems": count,
                        "maxItems": count,
                        "description": "The interview questions, in the order they should be asked.",
                    }
                },
                "required": ["questions"],
            },
        }
    ]


def _build_resume_prompt(role: str, difficulty: str, count: int, resume_text: str) -> str:
    return (
        f'Generate exactly {count} mock interview questions for a candidate applying to a '
        f'"{role}" role, at "{difficulty}" difficulty, based on the resume below. Ground '
        "each question in something specific from the resume — a project, a listed "
        "technology, a decision the candidate made, or a piece of their experience — "
        "rather than asking generic questions. Mix in questions about the projects "
        "listed, the technologies used, decisions made while building things, and "
        "problem-solving approach. For each question, give a short topic label naming "
        "the resume item it targets.\n\n"
        f"Resume:\n{resume_text}"
    )


def generate_from_resume(
    role: str, difficulty: str, count: int, resume: Resume
) -> list[GeneratedQuestion]:
    if not settings.anthropic_api_key:
        logger.warning("ANTHROPIC_API_KEY not set; using mock resume-based questions.")
        return mock_provider.generate_from_resume(role, difficulty, count, resume)

    try:
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        response = client.messages.create(
            model=settings.anthropic_model,
            max_tokens=1536,
            tools=_build_resume_tools(count),
            tool_choice={"type": "tool", "name": RESUME_TOOL_NAME},
            messages=[
                {
                    "role": "user",
                    "content": _build_resume_prompt(
                        role, difficulty, count, resume.extracted_text
                    ),
                }
            ],
        )

        for block in response.content:
            if block.type == "tool_use" and block.name == RESUME_TOOL_NAME:
                raw_questions = block.input.get("questions") or []
                parsed = [
                    GeneratedQuestion(
                        text=str(item["text"]),
                        source="resume",
                        topic=str(item["topic"]) if item.get("topic") else None,
                    )
                    for item in raw_questions
                    if isinstance(item, dict) and item.get("text")
                ]
                if parsed:
                    return parsed[:count]

        logger.warning(
            "Claude response had no usable tool call; using mock resume-based questions."
        )
        return mock_provider.generate_from_resume(role, difficulty, count, resume)

    except Exception:
        logger.exception("Resume-based question generation failed; using mock questions.")
        return mock_provider.generate_from_resume(role, difficulty, count, resume)
