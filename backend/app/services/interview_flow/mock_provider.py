import random

from app.models.question import Question
from app.models.resume import Resume
from app.services.answer_evaluation.rubrics import classify_question_type
from app.services.interview_flow.difficulty import answer_ratio as _answer_ratio
from app.services.interview_flow.difficulty import effective_difficulty as _effective_difficulty
from app.services.interview_flow.difficulty import WEAK_RATIO as _WEAK_RATIO
from app.services.interview_flow.topics import extract_topic
from app.services.interview_flow.types import NextStep
from app.services.question_generation.bank import QUESTION_BANK
from app.services.question_generation.types import GeneratedQuestion

# Deterministic (in shape, not content) stand-in for AI-driven conversation
# steering. No network calls, no API key required — this is what runs by
# default (AI_PROVIDER=mock). Also doubles as the guaranteed fallback for
# the Anthropic provider (see anthropic_provider.py), so its behavior must
# stay fully deterministic given the same inputs.
#
# Adaptive-difficulty scoring/thresholds live in difficulty.py (shared with
# the read-time computed fields in app.schemas.interview) — imported here
# under their original private names so this module's own logic/tests don't
# need to change shape.

_FOLLOWUP_MIN_WORDS = 12
_FOLLOWUP_SNIPPET_LEN = 70


def _snippet(text: str, max_len: int = _FOLLOWUP_SNIPPET_LEN) -> str:
    text = text.strip()
    return text if len(text) <= max_len else text[: max_len - 1].rstrip() + "…"


def _should_follow_up(
    last_answer: str, current_is_followup: bool, questions_asked: int, question_count: int
) -> bool:
    if current_is_followup:
        return False  # never chain a follow-up onto a follow-up
    if questions_asked >= question_count - 1:
        return False  # no budget left to spend on a follow-up
    # A short/thin answer usually has nothing concrete to probe further —
    # only substantive answers earn a follow-up, never forced every time.
    return len(last_answer.split()) >= _FOLLOWUP_MIN_WORDS


def _follow_up_question(last_answer: str, last_ratio: float | None) -> GeneratedQuestion:
    """Always grounded in the candidate's own words (the quoted snippet)
    so it never invents content. What's asked *about* that snippet adapts:
    a weak/vague answer gets a plain clarification request; a strong answer
    that named a recognizable technology/topic gets a targeted follow-up
    about it; otherwise falls back to a generic probe."""
    snippet = _snippet(last_answer)

    if last_ratio is not None and last_ratio < _WEAK_RATIO:
        ask = (
            "can you walk me through that in more detail? I'd like to "
            "understand your specific approach and reasoning."
        )
    else:
        topic = extract_topic(last_answer)
        if topic:
            ask = (
                f"why did you choose {topic}, and what challenges (if any) "
                "did you run into while using it?"
            )
        else:
            ask = "what was the most challenging part of that, and how did you approach it?"

    return GeneratedQuestion(text=f'You mentioned "{snippet}" — {ask}', source="bank")


def _preferred_question_type(asked_questions: list[Question]) -> str:
    """Balances behavioral vs. technical questions across the interview —
    whichever type has been asked less so far is preferred for the next
    main question, so the interview naturally mixes both instead of
    drifting entirely toward one (scenario/problem-solving questions are a
    natural subset of "technical" in the existing rubric classifier)."""
    behavioral = sum(1 for q in asked_questions if classify_question_type(q.text) == "behavioral")
    technical = sum(1 for q in asked_questions if classify_question_type(q.text) == "technical")
    return "behavioral" if behavioral <= technical else "technical"


# Which rubric each focusable category (app.services.answer_evaluation.
# rubrics.FOCUSABLE_CATEGORIES) belongs to. "clarity" is intentionally
# excluded — it appears in both rubrics with the same meaning, so it never
# tips the balance toward either question type.
_TECHNICAL_FOCUS_CATEGORIES = {"technical_accuracy", "completeness", "reasoning", "examples"}
_BEHAVIORAL_FOCUS_CATEGORIES = {"relevance", "structure", "specificity", "communication"}


def _focus_question_type(focus_categories: list[str] | None) -> str | None:
    """When this is a focused-practice session (Interview.focus_categories),
    the picked categories usually skew toward one rubric more than the
    other — bias main-question selection toward that type so the candidate
    actually gets asked questions scored against the categories they wanted
    to practice, overriding the normal behavioral/technical balance below.
    Returns None (defer to the normal balance) when there's no focus, or
    when the categories tie (including an all-"clarity" selection)."""
    if not focus_categories:
        return None
    technical_hits = sum(1 for c in focus_categories if c in _TECHNICAL_FOCUS_CATEGORIES)
    behavioral_hits = sum(1 for c in focus_categories if c in _BEHAVIORAL_FOCUS_CATEGORIES)
    if technical_hits > behavioral_hits:
        return "technical"
    if behavioral_hits > technical_hits:
        return "behavioral"
    return None


def _next_bank_question(
    role: str,
    difficulty: str,
    asked_texts: set[str],
    asked_questions: list[Question],
    focus_categories: list[str] | None = None,
) -> GeneratedQuestion:
    role_pool = [q for q in QUESTION_BANK.get(role, {}).get(difficulty, []) if q not in asked_texts]
    general_pool = [q for q in QUESTION_BANK["General"][difficulty] if q not in asked_texts]
    pool = role_pool or general_pool or list(QUESTION_BANK["General"][difficulty])

    preferred_type = _focus_question_type(focus_categories) or _preferred_question_type(asked_questions)
    typed_pool = [q for q in pool if classify_question_type(q) == preferred_type]
    chosen_pool = typed_pool or pool

    return GeneratedQuestion(text=random.choice(chosen_pool), source="bank")


def _next_resume_question(
    resume: Resume, asked_topics: set[str]
) -> GeneratedQuestion | None:
    parsed = resume.parsed or {}
    candidates: list[GeneratedQuestion] = []

    for project in parsed.get("projects") or []:
        label = project.strip()[:90]
        topic = f"Project: {label}"
        if topic not in asked_topics:
            candidates.append(
                GeneratedQuestion(
                    text=(
                        f'Earlier you mentioned "{label}" — what was the hardest '
                        "technical decision you made while building it?"
                    ),
                    source="resume",
                    topic=topic,
                )
            )

    for tech in parsed.get("technologies") or []:
        topic = f"Technology: {tech}"
        if topic not in asked_topics:
            candidates.append(
                GeneratedQuestion(
                    text=f'How have you used "{tech}" to solve a real problem in one of your projects?',
                    source="resume",
                    topic=topic,
                )
            )

    for item in parsed.get("experience") or []:
        label = item.strip()[:90]
        topic = f"Experience: {label}"
        if topic not in asked_topics:
            candidates.append(
                GeneratedQuestion(
                    text=f'You mentioned "{label}" in your experience — what was the impact of that work?',
                    source="resume",
                    topic=topic,
                )
            )

    if not candidates:
        return None
    return random.choice(candidates)


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
    questions_asked = len(asked_questions)
    last = asked_questions[-1] if asked_questions else None
    last_answer = last.answer.text if last and last.answer else ""
    last_ratio = _answer_ratio(last)

    if _should_follow_up(last_answer, current_is_followup, questions_asked, question_count):
        return NextStep(question=_follow_up_question(last_answer, last_ratio), is_followup=True)

    asked_texts = {q.text for q in asked_questions}

    if resume is not None:
        asked_topics = {q.resume_topic for q in asked_questions if q.resume_topic}
        resume_question = _next_resume_question(resume, asked_topics)
        if resume_question is not None:
            return NextStep(question=resume_question, is_followup=False)

    effective_difficulty = _effective_difficulty(difficulty, asked_questions)
    return NextStep(
        question=_next_bank_question(
            role, effective_difficulty, asked_texts, asked_questions, focus_categories
        ),
        is_followup=False,
    )
