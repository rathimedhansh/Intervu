"""Tests for the expanded Target Role system: the full curated role list,
arbitrary "Other / Custom Role" text, and that role flows through question
generation, follow-ups, and evaluation without being restricted to a closed
set.

Uses FastAPI's TestClient against an isolated in-memory SQLite DB
(dependency override), matching test_auth.py / test_interview_flow.py —
never touches the real app.db.

Run from backend/: venv/Scripts/python.exe -m unittest discover -s tests -v
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401 — registers all models on Base
from app.db.base import Base
from app.db.database import get_db
from app.main import app
from app.services.answer_evaluation import evaluate_answer
from app.services.interview_feedback import generate_feedback
from app.services.question_generation.bank import QUESTION_BANK, ROLES

EXPECTED_ROLES = (
    "Software Engineer",
    "Frontend Engineer",
    "Backend Engineer",
    "Full Stack Engineer",
    "Mobile Developer",
    "DevOps Engineer",
    "Cloud Engineer",
    "Data Engineer",
    "ML Engineer",
    "AI Engineer",
    "Cybersecurity Engineer",
    "QA/Automation Engineer",
    "Data Scientist",
    "Data Analyst",
    "AI Researcher",
    "Product Manager",
    "Business Analyst",
    "Project Manager",
    "UX/UI Designer",
)


class TestRoleBankCoverage(unittest.TestCase):
    def test_all_expected_roles_present(self):
        self.assertEqual(set(ROLES), set(EXPECTED_ROLES))

    def test_every_role_has_full_bank_coverage(self):
        for role in ROLES:
            for difficulty in ("easy", "medium", "hard"):
                questions = QUESTION_BANK[role][difficulty]
                self.assertGreaterEqual(
                    len(questions), 4, f"{role}/{difficulty} has too few questions"
                )

    def test_general_fallback_pool_still_present(self):
        # Custom/unrecognized roles rely on this — must not be removed.
        for difficulty in ("easy", "medium", "hard"):
            self.assertTrue(QUESTION_BANK["General"][difficulty])


class RoleAPITestCase(unittest.TestCase):
    def setUp(self):
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=engine)
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

        def override_get_db():
            db = TestingSessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()

    def _auth_headers(self, token: str) -> dict:
        return {"Authorization": f"Bearer {token}"}

    def _signup(self, email="ada@example.com"):
        response = self.client.post(
            "/api/auth/signup",
            json={"name": "Ada", "email": email, "password": "supersecret1"},
        )
        return response.json()["access_token"]

    def _create_interview(self, token, role, difficulty="easy", question_count=5):
        return self.client.post(
            "/api/interviews/",
            json={"role": role, "difficulty": difficulty, "question_count": question_count},
            headers=self._auth_headers(token),
        )

    def test_every_curated_role_creates_an_interview(self):
        token = self._signup()
        for role in ROLES:
            response = self._create_interview(token, role)
            self.assertEqual(response.status_code, 201, role)
            self.assertEqual(response.json()["role"], role)

    def test_custom_role_not_in_curated_list_is_accepted(self):
        token = self._signup()
        response = self._create_interview(token, "Blockchain Engineer")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["role"], "Blockchain Engineer")
        # Falls back to the role-agnostic pool rather than crashing.
        self.assertTrue(response.json()["questions"][0]["text"])

    def test_role_is_trimmed(self):
        token = self._signup()
        response = self._create_interview(token, "  Blockchain Engineer  ")
        self.assertEqual(response.json()["role"], "Blockchain Engineer")

    def test_blank_role_rejected(self):
        token = self._signup()
        response = self._create_interview(token, "   ")
        self.assertEqual(response.status_code, 422)

    def test_empty_role_rejected(self):
        token = self._signup()
        response = self._create_interview(token, "")
        self.assertEqual(response.status_code, 422)

    def test_overlong_role_rejected(self):
        token = self._signup()
        response = self._create_interview(token, "X" * 101)
        self.assertEqual(response.status_code, 422)

    def test_new_curated_role_produces_role_specific_first_question(self):
        token = self._signup()
        response = self._create_interview(token, "DevOps Engineer", difficulty="easy")
        first_question = response.json()["questions"][0]["text"]
        self.assertIn(first_question, QUESTION_BANK["DevOps Engineer"]["easy"])

    def test_role_flows_through_dynamic_next_question(self):
        token = self._signup()
        created = self._create_interview(token, "UX/UI Designer", difficulty="medium")
        interview_id = created.json()["id"]
        question_id = created.json()["questions"][0]["id"]

        turn = self.client.post(
            f"/api/interviews/{interview_id}/questions/{question_id}/respond",
            json={"text": "I'm not very familiar with that."},
            headers=self._auth_headers(token),
        )
        self.assertEqual(turn.status_code, 200)
        next_text = turn.json()["next_question"]["text"]
        # Short, non-substantive answer -> no follow-up -> pulled from the
        # UX/UI Designer bank (medium), not a generic/other-role question.
        self.assertIn(next_text, QUESTION_BANK["UX/UI Designer"]["medium"])

    def test_role_flows_through_completion_and_dashboard(self):
        token = self._signup()
        created = self._create_interview(token, "Cloud Engineer", question_count=5)
        interview_id = created.json()["id"]
        question_id = created.json()["questions"][0]["id"]

        while True:
            turn = self.client.post(
                f"/api/interviews/{interview_id}/questions/{question_id}/respond",
                json={"text": "I'm not very familiar with that."},
                headers=self._auth_headers(token),
            )
            body = turn.json()
            if body["is_complete"]:
                break
            question_id = body["next_question"]["id"]

        complete = self.client.post(
            f"/api/interviews/{interview_id}/complete", headers=self._auth_headers(token)
        )
        result = complete.json()
        self.assertIn("Cloud Engineer", result["summary_feedback"])

        dashboard = self.client.get(
            "/api/dashboard/", headers=self._auth_headers(token)
        ).json()
        self.assertEqual(dashboard["recent_interviews"][0]["role"], "Cloud Engineer")


class TestRoleFlowsIntoEvaluationAndFeedback(unittest.TestCase):
    """Role was never actually gated by a Literal below the API boundary —
    these confirm evaluation and feedback already accept arbitrary role
    strings without special-casing (no changes were needed there)."""

    def test_evaluate_answer_accepts_custom_role(self):
        result = evaluate_answer(
            "Tell me about a challenging technical problem you solved.",
            "I optimized a slow query by adding an index.",
            role="Blockchain Engineer",
            difficulty="medium",
        )
        self.assertIsNotNone(result.total_score)

    def test_feedback_mentions_custom_role(self):
        from app.models.answer import Answer
        from app.models.interview import Interview
        from app.models.question import Question

        interview = Interview(role="Blockchain Engineer", difficulty="medium", status="pending")
        question = Question(text="Q", order_index=0)
        question.answer = Answer(text="A", total_score=70)
        interview.questions = [question]

        feedback = generate_feedback(interview)
        self.assertIn("Blockchain Engineer", feedback.summary_feedback)


if __name__ == "__main__":
    unittest.main()
