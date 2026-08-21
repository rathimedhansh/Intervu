import random

from app.models.resume import Resume
from app.services.question_generation.bank import QUESTION_BANK
from app.services.question_generation.types import GeneratedQuestion

# Deterministic (in shape, not content) stand-in for AI-generated questions.
# No network calls, no API key required. This is what runs by default
# (AI_PROVIDER=mock). Pulls from the local question bank, topping up with
# the role-agnostic "General" pool when a role/difficulty combination
# doesn't have enough questions of its own.


def generate_intro(role: str) -> str:
    """The interview's opening question — deliberately deterministic and
    drawn straight from the role's "easy" bucket (every curated role's easy
    bucket opens with a "tell me about yourself"-style question) rather
    than routed through generate()/an AI provider. This guarantees every
    interview opens with a plain icebreaker regardless of the difficulty
    the candidate selected at setup; adaptive difficulty (see
    app.services.interview_flow) takes over from the second question on."""
    role_pool = QUESTION_BANK.get(role, {}).get("easy")
    if role_pool:
        return role_pool[0]
    return QUESTION_BANK["General"]["easy"][0]


def generate(role: str, difficulty: str, count: int) -> list[str]:
    role_pool = list(QUESTION_BANK.get(role, {}).get(difficulty, []))
    general_pool = list(QUESTION_BANK["General"][difficulty])

    random.shuffle(role_pool)
    random.shuffle(general_pool)

    combined = role_pool + [q for q in general_pool if q not in role_pool]

    selected = combined[:count]
    # Last-resort padding if the bank is somehow still short: cycle through
    # what we have rather than crash.
    while combined and len(selected) < count:
        selected.append(combined[len(selected) % len(combined)])

    return selected


# --- Resume-aware generation -------------------------------------------------
# Deterministic stand-in for AI-generated resume-based questions. Builds
# questions directly from the parsed resume (projects / technologies /
# experience) using templates, and tops up with the standard bank when the
# resume doesn't have enough material to fill the requested count.

_PROJECT_TEMPLATES = [
    'Tell me more about "{item}". What was your specific role, and what was the most challenging part?',
    'Walk me through the technical decisions you made while building "{item}". What tradeoffs did you consider?',
    'What would you do differently if you rebuilt "{item}" today?',
]

_TECH_TEMPLATES: dict[str, list[str]] = {
    "easy": [
        'You\'ve listed "{item}" on your resume — what do you use it for, and why?',
    ],
    "medium": [
        'How have you used "{item}" to solve a real problem in one of your projects?',
        'What\'s a limitation of "{item}" you\'ve run into, and how did you work around it?',
    ],
    "hard": [
        'How would you evaluate whether "{item}" is still the right choice as a system scales?',
        'Tell me about a time "{item}" wasn\'t the right tool for the job. How did you realize that?',
    ],
}

_EXPERIENCE_TEMPLATE = (
    'You mentioned "{item}" in your experience — what was the impact of that work, '
    "and how did you measure it?"
)


def _truncate(text: str, max_len: int = 90) -> str:
    text = text.strip()
    return text if len(text) <= max_len else text[: max_len - 1].rstrip() + "…"


def generate_from_resume(
    role: str, difficulty: str, count: int, resume: Resume
) -> list[GeneratedQuestion]:
    parsed = resume.parsed or {}
    tech_templates = _TECH_TEMPLATES.get(difficulty, _TECH_TEMPLATES["medium"])

    candidates: list[GeneratedQuestion] = []

    for project in parsed.get("projects") or []:
        label = _truncate(project)
        candidates.append(
            GeneratedQuestion(
                text=random.choice(_PROJECT_TEMPLATES).format(item=label),
                source="resume",
                topic=f"Project: {label}",
            )
        )

    for tech in parsed.get("technologies") or []:
        candidates.append(
            GeneratedQuestion(
                text=random.choice(tech_templates).format(item=tech),
                source="resume",
                topic=f"Technology: {tech}",
            )
        )

    for item in parsed.get("experience") or []:
        label = _truncate(item)
        candidates.append(
            GeneratedQuestion(
                text=_EXPERIENCE_TEMPLATE.format(item=label),
                source="resume",
                topic=f"Experience: {label}",
            )
        )

    random.shuffle(candidates)
    selected = candidates[:count]

    if len(selected) < count:
        # Resume didn't have enough material — top up with the standard
        # role/difficulty bank so the interview still has `count` questions.
        fallback_texts = generate(role, difficulty, count - len(selected))
        selected += [GeneratedQuestion(text=text, source="bank") for text in fallback_texts]

    return selected[:count]
