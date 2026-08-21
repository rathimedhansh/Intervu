# Adaptive difficulty: a pure, stateless read of recent answer quality used
# to (a) pick which difficulty tier to draw the next bank question from
# (see mock_provider.py/anthropic_provider.py) and (b) tell the client what
# level the interview is currently calibrated to (see
# app.schemas.interview.InterviewRead.current_difficulty and
# InterviewTurnRead.current_difficulty/difficulty_changed, and __init__.py's
# decide_next_step). The candidate's *selected* difficulty
# (Interview.difficulty) never changes — this is always re-derived fresh
# from already-stored answer scores, never persisted, so it automatically
# reflects the current scoring logic and needs no schema migration.

DIFFICULTY_ORDER = ("easy", "medium", "hard")

# An answer's total_score/max_score ratio below this is "weak" — worth a
# clarifying follow-up, or a nudge toward an easier next question — and at
# or above this is "strong" — worth gradually raising difficulty. Between
# the two is "mixed": difficulty holds steady.
WEAK_RATIO = 0.40
STRONG_RATIO = 0.72

# How many of the most recent scored answers feed the difficulty decision.
# A window (not the whole interview) so difficulty keeps responding to how
# the candidate is doing *now*, not a stale early impression.
WINDOW = 3
# Net strong/weak signals required within that window before difficulty
# actually moves a tier — "use several signals", never react to one answer.
SHIFT_THRESHOLD = 2


def difficulty_from_ratios(base_difficulty: str, ratios: list[float]) -> str:
    """Pure: given the candidate's selected baseline difficulty and an
    ordered list of recent answer-quality ratios (oldest first), returns
    the difficulty tier the interview is currently calibrated to. No
    dependency on ORM/Pydantic shapes — callers extract ratios however is
    natural for their data (see answer_ratio() for the ORM case, and
    app.schemas.interview for the Pydantic-read case)."""
    if base_difficulty not in DIFFICULTY_ORDER:
        base_difficulty = "medium"

    recent = ratios[-WINDOW:]
    momentum = sum(1 if r >= STRONG_RATIO else (-1 if r <= WEAK_RATIO else 0) for r in recent)

    shift = 0
    if momentum >= SHIFT_THRESHOLD:
        shift = 1
    elif momentum <= -SHIFT_THRESHOLD:
        shift = -1

    index = DIFFICULTY_ORDER.index(base_difficulty) + shift
    return DIFFICULTY_ORDER[max(0, min(len(DIFFICULTY_ORDER) - 1, index))]


def answer_ratio(question) -> float | None:
    """The given (ORM) Question's total_score/max_score, if it's already
    been evaluated (see app.crud.interview_flow.advance_conversation, which
    always evaluates before deciding the next step). None when there's no
    answer, or evaluation hasn't happened/produced a usable max_score —
    never guessed at."""
    if question is None or question.answer is None:
        return None
    answer = question.answer
    if answer.total_score is None or not answer.evaluation:
        return None
    max_score = answer.evaluation.get("max_score")
    if not max_score:
        return None
    return answer.total_score / max_score


def effective_difficulty(base_difficulty: str, asked_questions: list) -> str:
    """ORM convenience wrapper around difficulty_from_ratios() — extracts
    ratios from a list of (ORM) Question objects via answer_ratio()."""
    ratios = [r for r in (answer_ratio(q) for q in asked_questions) if r is not None]
    return difficulty_from_ratios(base_difficulty, ratios)


def difficulty_direction(previous: str, new: str) -> str | None:
    """None if unchanged, else "increased" or "decreased" — used to power a
    brief, non-scored UI notice (see InterviewTurnRead.difficulty_changed).
    Never exposes the underlying score, only the direction."""
    if previous == new:
        return None
    return "increased" if DIFFICULTY_ORDER.index(new) > DIFFICULTY_ORDER.index(previous) else "decreased"
