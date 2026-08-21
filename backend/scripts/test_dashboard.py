"""Manual smoke test for app.crud.dashboard.get_dashboard_stats.

Uses an isolated in-memory SQLite DB (never touches the real app.db) to
verify both the empty state and a populated state.

Run from backend/: venv/Scripts/python.exe scripts/test_dashboard.py
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.answer import Answer
from app.models.interview import Interview
from app.models.question import Question
from app.models.user import User
from app.crud.dashboard import get_dashboard_stats

engine = create_engine("sqlite:///:memory:")
Base.metadata.create_all(bind=engine)
Session = sessionmaker(bind=engine)
db = Session()

user = User(name="Test User", email="test@example.com", password_hash="x")
db.add(user)
db.commit()
db.refresh(user)

print("=== empty state ===")
empty_stats = get_dashboard_stats(db, user.id)
print(json.dumps(empty_stats, default=str, indent=2))
assert empty_stats["overview"]["total_interviews"] == 0
assert empty_stats["overview"]["average_score"] is None
assert empty_stats["overview"]["highest_score"] is None
assert empty_stats["overview"]["total_questions_answered"] == 0
assert empty_stats["progress"] == []
assert empty_stats["recent_interviews"] == []
assert empty_stats["category_breakdown"] == []
print("OK: empty state is all zeros/empty, no errors.\n")


def make_completed_interview(role, difficulty, overall_score, answers):
    interview = Interview(
        role=role,
        difficulty=difficulty,
        status="completed",
        completed_at=datetime.now(timezone.utc),
        overall_score=overall_score,
        strengths=[],
        weaknesses=[],
        summary_feedback="test",
        user_id=user.id,
    )
    db.add(interview)
    db.flush()
    for index, (text, total_score, evaluation) in enumerate(answers):
        question = Question(interview_id=interview.id, text=f"Q{index}", order_index=index)
        db.add(question)
        db.flush()
        db.add(
            Answer(
                question_id=question.id,
                text=text,
                total_score=total_score,
                evaluation=evaluation,
            )
        )
    db.commit()


def behavioral_eval(total):
    return {
        "question_type": "behavioral",
        "evaluator": "mock",
        "category_scores": [
            {"category": "relevance", "label": "Relevance", "score": total // 5, "max_score": 20},
            {"category": "clarity", "label": "Clarity", "score": total // 5, "max_score": 20},
        ],
        "total_score": total,
        "max_score": 100,
        "strengths": [],
        "weaknesses": [],
        "improvement_suggestions": [],
        "stronger_answer_example": "",
        "note": None,
    }


def technical_eval(total):
    return {
        "question_type": "technical",
        "evaluator": "mock",
        "category_scores": [
            {"category": "technical_accuracy", "label": "Technical Accuracy", "score": round(total * 0.3), "max_score": 30},
            {"category": "clarity", "label": "Clarity", "score": round(total * 0.15), "max_score": 15},
        ],
        "total_score": total,
        "max_score": 100,
        "strengths": [],
        "weaknesses": [],
        "improvement_suggestions": [],
        "stronger_answer_example": "",
        "note": None,
    }


make_completed_interview(
    "Software Engineer", "medium", 70,
    [("answer 1", 80, behavioral_eval(80)), ("answer 2", 60, technical_eval(60))],
)
make_completed_interview(
    "Product Manager", "easy", 90,
    [("answer 1", 90, behavioral_eval(90))],
)

print("=== populated state ===")
stats = get_dashboard_stats(db, user.id)
print(json.dumps(stats, default=str, indent=2))

assert stats["overview"]["total_interviews"] == 2
assert stats["overview"]["average_score"] == 80.0
assert stats["overview"]["highest_score"] == 90
assert stats["overview"]["total_questions_answered"] == 3
assert len(stats["progress"]) == 2
assert len(stats["recent_interviews"]) == 2
assert stats["recent_interviews"][0]["role"] == "Product Manager"  # most recent first
category_keys = {c["category"] for c in stats["category_breakdown"]}
assert category_keys == {"relevance", "clarity", "technical_accuracy"}
print("OK: populated state totals, ordering, and category set are all correct.")
