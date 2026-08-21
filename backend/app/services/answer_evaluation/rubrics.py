from typing import Literal

QuestionType = Literal["behavioral", "technical"]

# category_key -> (display label, max points). Keys are also used as the
# JSON field names returned by the evaluators, so keep them stable.
BEHAVIORAL_RUBRIC: dict[str, tuple[str, int]] = {
    "relevance": ("Relevance", 20),
    "clarity": ("Clarity", 20),
    "structure": ("Structure", 20),
    "specificity": ("Specificity / Examples", 20),
    "communication": ("Communication", 20),
}

TECHNICAL_RUBRIC: dict[str, tuple[str, int]] = {
    "technical_accuracy": ("Technical Accuracy", 30),
    "completeness": ("Completeness", 25),
    "reasoning": ("Reasoning / Problem Solving", 20),
    "clarity": ("Clarity", 15),
    "examples": ("Examples", 10),
}


def get_rubric(question_type: QuestionType) -> dict[str, tuple[str, int]]:
    return TECHNICAL_RUBRIC if question_type == "technical" else BEHAVIORAL_RUBRIC


# One-line criteria per category, used to spell the rubric out in plain
# language for the AI evaluator prompt (in addition to the tool schema).
CATEGORY_DESCRIPTIONS: dict[str, str] = {
    "relevance": "How directly the answer addresses what was actually asked.",
    "clarity": "How clear and easy to follow the explanation is.",
    "structure": "Whether the answer is organized, e.g. Situation-Task-Action-Result.",
    "specificity": "Whether the answer cites a specific, concrete example or outcome.",
    "communication": "Confidence, concision, and overall communication quality.",
    "technical_accuracy": "Correctness of the technical claims and terminology used.",
    "completeness": "Whether the answer covers the key aspects, edge cases, and tradeoffs.",
    "reasoning": "Whether the answer explains the reasoning and tradeoffs behind the approach.",
    "examples": "Whether the answer is grounded in a concrete example, metric, or use case.",
}

# One concrete, practice-able action per category — distinct from
# CATEGORY_DESCRIPTIONS above (which states what the category *measures*,
# for the evaluator prompt). Used by the dashboard's Practice Plan
# (app.crud.dashboard) to turn a low category score into something the
# candidate can actually go do, not just a restated score.
CATEGORY_ACTIONS: dict[str, str] = {
    "relevance": "Before answering, restate the question in one sentence to yourself, then check "
    "every part of your answer actually addresses it.",
    "clarity": "Practice explaining the same answer in three sentences or fewer, then expand — "
    "it forces the core idea to come first.",
    "structure": "Outline Situation-Task-Action-Result as four bullet points before you start "
    "speaking, even mentally, so the answer doesn't wander.",
    "specificity": "Keep a running list of 3-4 real projects/metrics you can drop into any answer "
    "as a concrete example instead of speaking in generalities.",
    "communication": "Record yourself answering one practice question and listen back once — "
    "most candidates are more hesitant or roundabout than they think.",
    "technical_accuracy": "Pick one weak topic per session and explain it out loud to someone "
    "(or to yourself) without notes; gaps in accuracy show up immediately when spoken.",
    "completeness": "After answering, ask yourself 'what edge case or tradeoff did I skip?' and "
    "add one sentence covering it.",
    "reasoning": "Narrate your tradeoffs explicitly — say 'I chose X over Y because...' rather "
    "than just stating the final choice.",
    "examples": "Anchor your answer to one specific metric, tool, or outcome instead of describing "
    "the approach in the abstract.",
}

# category_key -> display label, merged across both rubrics (a few keys —
# e.g. "clarity" — appear in both with the same meaning, so either source
# wins). The canonical set of keys any caller can validate/reference a
# rubric category against independent of question type: the dashboard's
# category breakdown (app.crud.dashboard) and the optional focus-category
# picker on interview setup (see InterviewCreate.focus_categories in
# app.schemas.interview and app.services.interview_flow's use of it).
CATEGORY_LABELS: dict[str, str] = {
    **{key: label for key, (label, _) in TECHNICAL_RUBRIC.items()},
    **{key: label for key, (label, _) in BEHAVIORAL_RUBRIC.items()},
}

FOCUSABLE_CATEGORIES: tuple[str, ...] = tuple(CATEGORY_DESCRIPTIONS.keys())

# Keep a focused-practice interview focused — a handful of categories to
# stretch, not a checklist covering the whole rubric (see
# app.schemas.interview.InterviewCreate.focus_categories).
MAX_FOCUS_CATEGORIES = 3


# Heuristic classifier: the question bank (app/services/question_generation/bank.py)
# stores questions as plain strings with no type tag, so we classify by keyword
# cues rather than requiring a schema change. Good enough to route to the right
# rubric; swap for an explicit tag or AI classification later if it needs to be
# more precise.
_TECHNICAL_KEYWORDS = (
    "design", "algorithm", "architecture", "database", "sql", "nosql", "query",
    "queries", "api", "code", "coding", "cache", "caching", "scale", "scalability",
    "system", "complexity", "data structure", "difference between", "implement",
    "rate limiter", "microservice", "latency", "throughput", "index", "schema",
    "model ", "machine learning", "a/b test", "experiment", "framework",
    "bug", "debug", "optimiz", "component library", "bundle size",
)

_BEHAVIORAL_KEYWORDS = (
    "tell me about a time", "describe a time", "tell me about yourself",
    "describe a situation", "disagreed", "disagreement", "conflict", "mistake",
    "failure", "failed", "proud of", "feedback you received", "feedback to",
    "stakeholder", "pressure", "led a", "manage a team", "your ideal",
    "looking for", "sunset a product", "difficult decision",
)


def classify_question_type(question: str) -> QuestionType:
    text = question.lower()
    behavioral_hits = sum(1 for kw in _BEHAVIORAL_KEYWORDS if kw in text)
    technical_hits = sum(1 for kw in _TECHNICAL_KEYWORDS if kw in text)
    if technical_hits > behavioral_hits:
        return "technical"
    return "behavioral"
