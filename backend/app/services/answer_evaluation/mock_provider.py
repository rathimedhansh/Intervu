import re

from app.services.answer_evaluation import rubrics
from app.services.answer_evaluation.rubrics import QuestionType
from app.services.answer_evaluation.types import AnswerEvaluation, CategoryScore

# Deterministic stand-in for AI evaluation. No network calls, no API key
# required. Derives per-category ratios from simple textual signals (answer
# length, keyword overlap with the question, presence of examples/numbers,
# presence of STAR-style structure words) so scores still vary meaningfully
# across answers during testing without calling an LLM.

MOCK_NOTE = (
    "Mock evaluator — set AI_PROVIDER=anthropic and ANTHROPIC_API_KEY to enable "
    "AI-generated scoring."
)

STRONGER_ANSWER_TEMPLATES: dict[QuestionType, str] = {
    "behavioral": (
        "A stronger answer would follow the STAR method: briefly set up the "
        "Situation and Task, describe the concrete Action you personally took "
        '(using "I" statements, not "we"), and close with a measurable Result '
        '(e.g. "cut deploy time from 40 minutes to 10" or "reduced churn by 8%"). '
        "Anchor it to one specific example instead of speaking in generalities."
    ),
    "technical": (
        "A stronger answer would state the core approach up front, walk through "
        "the reasoning step-by-step (tradeoffs, complexity, edge cases), name "
        "the relevant tools or techniques explicitly, and close with a concrete "
        "example or metric showing the approach actually worked in practice."
    ),
}

CATEGORY_STRENGTH: dict[str, str] = {
    "relevance": "Directly addressed what the question was asking.",
    "clarity": "Explained the idea in a clear, easy-to-follow way.",
    "structure": "Organized the answer with a clear beginning, middle, and end.",
    "specificity": "Backed up the answer with a specific, concrete example.",
    "communication": "Communicated confidently and stayed on topic.",
    "technical_accuracy": "Demonstrated solid technical understanding of the topic.",
    "completeness": "Covered the key aspects of the problem thoroughly.",
    "reasoning": "Walked through the reasoning and tradeoffs behind the approach.",
    "examples": "Illustrated the answer with a concrete example or metric.",
}

CATEGORY_WEAKNESS: dict[str, str] = {
    "relevance": "Drifted away from what the question actually asked.",
    "clarity": "The explanation was hard to follow in places.",
    "structure": "Lacked a clear structure (e.g. Situation-Task-Action-Result).",
    "specificity": "Stayed general instead of citing a specific example or outcome.",
    "communication": "Could be more concise and direct.",
    "technical_accuracy": "Contained gaps or imprecision in the technical explanation.",
    "completeness": "Left out important considerations or edge cases.",
    "reasoning": "Didn't explain the reasoning or tradeoffs behind the approach.",
    "examples": "Didn't include a concrete example, metric, or use case.",
}

CATEGORY_SUGGESTION: dict[str, str] = {
    "relevance": "Re-read the question before answering and make sure every part of it is addressed.",
    "clarity": "Simplify sentences and lead with the main point before adding detail.",
    "structure": "Use the STAR method: Situation, Task, Action, Result.",
    "specificity": "Add a specific example with a measurable outcome (numbers, %, time saved).",
    "communication": "Trim filler words and keep the answer focused on the core message.",
    "technical_accuracy": "Double-check the technical details and terminology used.",
    "completeness": "Cover edge cases and tradeoffs, not just the happy path.",
    "reasoning": "Explain *why* each step or decision was made, not just *what* was done.",
    "examples": "Ground the explanation in a concrete example, metric, or past project.",
}

_STOPWORDS = {
    "the", "a", "an", "and", "or", "to", "of", "in", "on", "for", "with", "is",
    "are", "was", "were", "how", "what", "tell", "me", "about", "your", "you",
    "describe", "did", "do", "does", "that", "this", "it", "as", "at", "by",
    "be", "have", "has", "would", "when", "why", "walk", "through",
}

_EXAMPLE_PHRASES = (
    "for example", "for instance", "e.g.", "such as", "specifically",
    "in my", "when i", "at my last", "one time", "%",
)

_STRUCTURE_MARKERS = (
    "first", "then", "next", "finally", "because", "as a result", "situation",
    "task", "action", "result", "so that", "which led", "eventually",
)

_REASONING_MARKERS = (
    "because", "tradeoff", "trade-off", "however", "versus", " vs ",
    "compared to", "instead of", "rather than", "in order to", "avoids",
    "avoid", "which means", "so that", "this way", "the reason",
)


def _keywords(text: str) -> set[str]:
    words = re.findall(r"[a-zA-Z]+", text.lower())
    return {w for w in words if len(w) > 3 and w not in _STOPWORDS}


def _keyword_overlap(question: str, answer: str) -> float:
    q_words = _keywords(question)
    if not q_words:
        return 0.5
    a_words = _keywords(answer)
    overlap = len(q_words & a_words)
    return min(1.0, overlap / max(3, len(q_words) // 2))


def _signals(question: str, answer: str) -> dict[str, float]:
    word_count = len(answer.split())
    lower = answer.lower()

    length_signal = min(1.0, word_count / 80)
    has_numbers = bool(re.search(r"\d", answer))
    has_example_phrase = any(p in lower for p in _EXAMPLE_PHRASES)
    example_signal = (
        1.0 if (has_numbers or has_example_phrase) else min(1.0, word_count / 150)
    )
    structure_hits = sum(1 for m in _STRUCTURE_MARKERS if m in lower)
    structure_signal = min(1.0, structure_hits / 3)
    reasoning_hits = sum(1 for m in _REASONING_MARKERS if m in lower)
    reasoning_signal = min(1.0, reasoning_hits / 2)
    overlap_signal = _keyword_overlap(question, answer)

    return {
        "length": length_signal,
        "example": example_signal,
        "structure": structure_signal,
        "reasoning": reasoning_signal,
        "overlap": overlap_signal,
    }


def _behavioral_ratios(s: dict[str, float]) -> dict[str, float]:
    return {
        "relevance": 0.3 + 0.7 * s["overlap"],
        "clarity": 0.3 + 0.7 * s["length"],
        "structure": 0.25 + 0.75 * s["structure"],
        "specificity": 0.2 + 0.8 * s["example"],
        "communication": 0.3 + 0.7 * ((s["length"] + s["structure"]) / 2),
    }


def _technical_ratios(s: dict[str, float]) -> dict[str, float]:
    return {
        "technical_accuracy": 0.3 + 0.7 * s["overlap"],
        "completeness": 0.25 + 0.75 * s["length"],
        "reasoning": 0.25 + 0.75 * s["reasoning"],
        "clarity": 0.3 + 0.7 * s["length"],
        "examples": 0.2 + 0.8 * s["example"],
    }


def generate(
    question: str,
    answer: str,
    role: str,
    difficulty: str,
    question_type: QuestionType | None = None,
) -> AnswerEvaluation:
    qtype = question_type or rubrics.classify_question_type(question)
    rubric = rubrics.get_rubric(qtype)

    signals = _signals(question, answer)
    ratios = _technical_ratios(signals) if qtype == "technical" else _behavioral_ratios(signals)

    scored: list[tuple[str, CategoryScore, float]] = []
    for key, (label, max_score) in rubric.items():
        ratio = max(0.0, min(1.0, ratios[key]))
        score = round(ratio * max_score)
        scored.append((key, CategoryScore(category=key, label=label, score=score, max_score=max_score), ratio))

    # Rank by ratio rather than raw score so categories with different max
    # points (e.g. Technical Accuracy /30 vs Examples /10) are compared fairly.
    # Ties are excluded from the "weak" side (via the < 0.85 threshold) so a
    # perfect-score category never gets flagged as a weakness just because it
    # sorted last among equals.
    ranked_desc = sorted(scored, key=lambda item: item[2], reverse=True)
    ranked_asc = sorted(scored, key=lambda item: item[2])

    strong_keys = [key for key, _, ratio in ranked_desc if ratio > 0.55][:2]
    if not strong_keys:
        strong_keys = [ranked_desc[0][0]]

    weak_keys = [key for key, _, ratio in ranked_asc if ratio < 0.85][:2]

    strengths = [CATEGORY_STRENGTH[key] for key in strong_keys]
    if weak_keys:
        weaknesses = [CATEGORY_WEAKNESS[key] for key in weak_keys]
        suggestions = [CATEGORY_SUGGESTION[key] for key in weak_keys]
    else:
        weaknesses = ["No notable weaknesses — this was a strong answer across every category."]
        suggestions = ["Keep using this level of detail and structure in future answers."]
    if len(answer.split()) < 15:
        suggestions.insert(
            0,
            "Expand your answer — it's quite short, and interviewers want to hear your "
            "full thought process.",
        )

    category_scores = [cs for _, cs, _ in scored]

    return AnswerEvaluation(
        question_type=qtype,
        evaluator="mock",
        category_scores=category_scores,
        total_score=sum(c.score for c in category_scores),
        max_score=sum(c.max_score for c in category_scores),
        strengths=strengths,
        weaknesses=weaknesses,
        improvement_suggestions=suggestions,
        stronger_answer_example=STRONGER_ANSWER_TEMPLATES[qtype],
        note=MOCK_NOTE,
    )
