# Heuristic, text-only estimate of verbal repetitions ("I I think", "the
# the book"), immediately repeated short phrases ("I think I think"), and
# simple false starts (which mostly surface as one of the above patterns in
# a plain-text transcript). This is a rough pattern match, not a medical or
# diagnostic speech assessment — see the disclaimer carried alongside every
# reading of this data in app/schemas/answer.py.
#
# Runs on Answer.text, which the backend already receives and stores for
# scoring — no new audio/transcript capture, no second SpeechRecognition
# instance, nothing beyond what evaluate_answer() already reads.

import re

_WORD_RE = re.compile(r"[a-z0-9']+")
_MAX_PHRASE_WORDS = 3
_MAX_EXAMPLES = 5


def _tokenize(text: str) -> list[str]:
    return _WORD_RE.findall((text or "").lower())


def estimate_disfluencies(text: str) -> dict:
    """Scans the transcript left-to-right for immediately-repeated phrases
    (2-3 words) and immediately-repeated single words, preferring the
    longer match at each position so "I think I think" counts once as a
    phrase repeat rather than twice as word repeats."""
    tokens = _tokenize(text)
    n = len(tokens)

    repeated_word_count = 0
    repeated_phrase_count = 0
    examples: list[str] = []

    i = 0
    while i < n:
        matched_len = 0
        for phrase_len in range(_MAX_PHRASE_WORDS, 1, -1):
            end_first = i + phrase_len
            end_second = i + 2 * phrase_len
            if end_second <= n and tokens[i:end_first] == tokens[end_first:end_second]:
                repeated_phrase_count += 1
                if len(examples) < _MAX_EXAMPLES:
                    examples.append(" ".join(tokens[i:end_first]))
                matched_len = 2 * phrase_len
                break

        if not matched_len and i + 1 < n and tokens[i] == tokens[i + 1]:
            repeated_word_count += 1
            if len(examples) < _MAX_EXAMPLES:
                examples.append(f"{tokens[i]} {tokens[i]}")
            matched_len = 2

        i += matched_len if matched_len else 1

    return {
        "repeated_word_count": repeated_word_count,
        "repeated_phrase_count": repeated_phrase_count,
        "repeated_examples": examples,
        "total_estimated_repetitions": repeated_word_count + repeated_phrase_count,
    }
