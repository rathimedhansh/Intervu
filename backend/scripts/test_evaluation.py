"""Manual smoke test for the answer_evaluation service.

Run from backend/: venv/Scripts/python.exe scripts/test_evaluation.py

Exercises the mock evaluator (no API key needed) against a behavioral and a
technical question, each with a weak and a strong answer, and prints the
resulting JSON. Also confirms that requesting the anthropic provider without
an API key falls back to the mock evaluator instead of crashing.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.answer_evaluation import evaluate_answer, classify_question_type
from app.services.answer_evaluation import anthropic_provider

CASES = [
    (
        "behavioral / weak",
        "Tell me about a time you disagreed with a teammate. How did you resolve it?",
        "I don't really remember, it happens sometimes and we just talk it out.",
    ),
    (
        "behavioral / strong",
        "Tell me about a time you disagreed with a teammate. How did you resolve it?",
        "On my last team, a teammate and I disagreed on whether to rewrite our "
        "auth service or patch it. The situation was that our sprint deadline "
        "was in a week. My task was to make the call as the tech lead. I set up "
        "a 30-minute meeting where we each listed the risks, then I proposed a "
        "middle path: patch now, file a ticket for the rewrite next quarter. As "
        "a result, we shipped on time and completed the rewrite two months "
        "later with zero production incidents.",
    ),
    (
        "technical / weak",
        "How would you design a rate limiter for a public API?",
        "You could use a counter I guess and block people who send too many requests.",
    ),
    (
        "technical / strong",
        "How would you design a rate limiter for a public API?",
        "I'd use a token bucket algorithm per API key, backed by Redis so it "
        "works across multiple servers. Each key gets a bucket with a fixed "
        "capacity, for example 100 tokens, refilled at a fixed rate like 10 "
        "tokens per second. On each request I'd atomically decrement via a Lua "
        "script to avoid race conditions, and return a 429 with a Retry-After "
        "header when the bucket is empty. The tradeoff versus a fixed window "
        "counter is a bit more complexity, but it avoids bursty edge effects at "
        "window boundaries.",
    ),
]

for label, question, answer in CASES:
    print(f"\n=== {label} (classified as: {classify_question_type(question)}) ===")
    result = evaluate_answer(question, answer, role="Software Engineer", difficulty="medium")
    print(json.dumps(result.to_dict(), indent=2))

print("\n=== anthropic provider, no API key configured (should fall back to mock) ===")
fallback = anthropic_provider.generate(
    "How would you design a rate limiter for a public API?",
    "Use a token bucket per key.",
    role="Software Engineer",
    difficulty="medium",
)
print(f"evaluator field: {fallback.evaluator} (expected: mock)")
assert fallback.evaluator == "mock", "expected fallback to mock when no API key is set"
print("OK: anthropic provider fell back to mock cleanly.")
