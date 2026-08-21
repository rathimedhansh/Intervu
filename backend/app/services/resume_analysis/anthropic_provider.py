import logging

import anthropic

from app.core.config import settings
from app.services.resume_analysis import mock_provider
from app.services.resume_analysis.types import ResumeAnalysis
from app.services.resume_parsing import ParsedResume

logger = logging.getLogger(__name__)

TOOL_NAME = "return_resume_analysis"


def _build_tools() -> list[dict]:
    return [
        {
            "name": TOOL_NAME,
            "description": "Return a structured analysis of a candidate's resume.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "summary": {
                        "type": "string",
                        "description": "2-3 sentence overview of the candidate's background.",
                    },
                    "strong_areas": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "3-5 specific strengths evident from the resume.",
                    },
                    "missing_details": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "3-5 gaps or missing details that would strengthen the resume.",
                    },
                    "key_projects": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Up to 5 of the most notable projects mentioned, briefly described.",
                    },
                    "key_technologies": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Up to 10 key technologies/tools the candidate has used.",
                    },
                },
                "required": [
                    "summary",
                    "strong_areas",
                    "missing_details",
                    "key_projects",
                    "key_technologies",
                ],
            },
        }
    ]


def _build_prompt(resume_text: str) -> str:
    return (
        "You are an expert technical recruiter analyzing a candidate's resume ahead of "
        "a mock interview. Read the resume text below and identify the candidate's "
        "strong areas, any missing details that would make the resume stronger, their "
        "key projects, and key technologies.\n\n"
        f"Resume text:\n{resume_text}"
    )


def generate(parsed: ParsedResume, resume_text: str) -> ResumeAnalysis:
    if not settings.anthropic_api_key:
        logger.warning("ANTHROPIC_API_KEY not set; using mock resume analysis.")
        return mock_provider.generate(parsed, resume_text)

    try:
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        response = client.messages.create(
            model=settings.anthropic_model,
            max_tokens=1024,
            tools=_build_tools(),
            tool_choice={"type": "tool", "name": TOOL_NAME},
            messages=[{"role": "user", "content": _build_prompt(resume_text)}],
        )
    except Exception:
        logger.exception("Resume analysis API call failed; using mock analysis.")
        return mock_provider.generate(parsed, resume_text)

    tool_input = next(
        (
            block.input
            for block in response.content
            if block.type == "tool_use" and block.name == TOOL_NAME
        ),
        None,
    )
    if tool_input is None:
        logger.warning("Claude response had no usable tool call; using mock resume analysis.")
        return mock_provider.generate(parsed, resume_text)

    try:
        return ResumeAnalysis(
            analyzer="anthropic",
            summary=str(tool_input["summary"]),
            strong_areas=[str(item) for item in tool_input["strong_areas"]],
            missing_details=[str(item) for item in tool_input["missing_details"]],
            key_projects=[str(item) for item in tool_input["key_projects"]],
            key_technologies=[str(item) for item in tool_input["key_technologies"]],
        )
    except (KeyError, TypeError):
        logger.exception(
            "Anthropic resume analysis response failed validation; using mock analysis."
        )
        return mock_provider.generate(parsed, resume_text)
