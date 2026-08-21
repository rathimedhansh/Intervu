"""Tests for focused practice: InterviewCreate.focus_categories, its
validation/persistence, and how it biases question selection in
app.services.interview_flow toward the rubric categories the candidate
picked (surfaced on the dashboard as "Practice weak areas" and as an
optional picker on interview setup).

Uses stdlib unittest + unittest.mock, matching test_interview_flow.py.
API-level tests use FastAPI's TestClient against an isolated in-memory
SQLite DB — never touches the real app.db.

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
from app.crud import interview as interview_crud
from app.db.base import Base
from app.db.database import get_db
from app.main import app
from app.services.answer_evaluation.rubrics import classify_question_type
from app.services.interview_flow import anthropic_provider, mock_provider
from app.services.question_generation.bank import QUESTION_BANK

ROLE = "Software Engineer"
DIFFICULTY = "easy"
SHORT_ANSWER = "I'm not very familiar with that."

# The one item in QUESTION_BANK["Software Engineer"]["easy"] the existing
# keyword classifier (app.services.answer_evaluation.rubrics.
# classify_question_type) tags "technical" — see bank.py. Used to assert an
# exact, deterministic pick when biasing toward a technical focus category.
_ONLY_TECHNICAL_EASY_SWE_QUESTION = (
    "How do you approach learning a new framework or library?"
)


class TestFocusQuestionType(unittest.TestCase):
    """Pure unit tests for the technical/behavioral bias helper — no DB, no
    network."""

    def test_technical_categories_bias_technical(self):
        self.assertEqual(
            mock_provider._focus_question_type(["technical_accuracy", "completeness"]),
            "technical",
        )

    def test_behavioral_categories_bias_behavioral(self):
        self.assertEqual(
            mock_provider._focus_question_type(["structure", "specificity"]),
            "behavioral",
        )

    def test_tie_defers_to_normal_balance(self):
        self.assertIsNone(
            mock_provider._focus_question_type(["technical_accuracy", "structure"])
        )

    def test_clarity_only_never_tips_the_balance(self):
        # "clarity" exists in both rubrics with the same meaning — must not
        # count toward either side.
        self.assertIsNone(mock_provider._focus_question_type(["clarity"]))

    def test_no_focus_categories_returns_none(self):
        self.assertIsNone(mock_provider._focus_question_type(None))
        self.assertIsNone(mock_provider._focus_question_type([]))


class TestNextBankQuestionFocusBias(unittest.TestCase):
    """app.services.interview_flow.mock_provider._next_bank_question actually
    picks from the biased type pool when a focus is given."""

    def test_technical_focus_picks_the_only_technical_easy_question(self):
        question = mock_provider._next_bank_question(
            ROLE, DIFFICULTY, asked_texts=set(), asked_questions=[],
            focus_categories=["technical_accuracy"],
        )
        self.assertEqual(question.text, _ONLY_TECHNICAL_EASY_SWE_QUESTION)

    def test_behavioral_focus_never_picks_the_technical_question(self):
        for _ in range(20):
            question = mock_provider._next_bank_question(
                ROLE, DIFFICULTY, asked_texts=set(), asked_questions=[],
                focus_categories=["structure"],
            )
            self.assertEqual(classify_question_type(question.text), "behavioral")

    def test_no_focus_categories_behaves_as_before(self):
        question = mock_provider._next_bank_question(
            ROLE, DIFFICULTY, asked_texts=set(), asked_questions=[], focus_categories=None
        )
        self.assertIn(question.text, QUESTION_BANK[ROLE][DIFFICULTY])


class TestAnthropicPromptIncludesFocusSection(unittest.TestCase):
    def test_focus_categories_appear_in_prompt(self):
        prompt = anthropic_provider._build_prompt(
            ROLE, DIFFICULTY, None, [], False, 5, focus_categories=["technical_accuracy"]
        )
        self.assertIn("focused practice session", prompt)
        self.assertIn("Technical Accuracy", prompt)

    def test_no_focus_categories_omits_focus_section(self):
        prompt = anthropic_provider._build_prompt(ROLE, DIFFICULTY, None, [], False, 5)
        self.assertNotIn("focused practice session", prompt)


class TestCrudCreateInterviewFocusCategories(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine)
        self.db = Session()
        from app.models.user import User

        user = User(name="Test", email="test@example.com", password_hash="x")
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        self.user_id = user.id

    def test_valid_focus_categories_persisted(self):
        interview = interview_crud.create_interview(
            self.db, role=ROLE, difficulty=DIFFICULTY, question_count=5,
            user_id=self.user_id, focus_categories=["structure", "specificity"],
        )
        self.assertEqual(interview.focus_categories, ["structure", "specificity"])

    def test_unknown_focus_category_rejected(self):
        with self.assertRaises(ValueError):
            interview_crud.create_interview(
                self.db, role=ROLE, difficulty=DIFFICULTY, question_count=5,
                user_id=self.user_id, focus_categories=["not_a_real_category"],
            )

    def test_focus_categories_deduped_and_capped_defense_in_depth(self):
        # Direct crud call bypassing InterviewCreate's own validation —
        # crud must not blindly trust more than MAX_FOCUS_CATEGORIES either.
        interview = interview_crud.create_interview(
            self.db, role=ROLE, difficulty=DIFFICULTY, question_count=5,
            user_id=self.user_id,
            focus_categories=[
                "structure", "structure", "specificity", "communication", "relevance",
            ],
        )
        self.assertEqual(len(interview.focus_categories), 3)

    def test_no_focus_categories_stays_none(self):
        interview = interview_crud.create_interview(
            self.db, role=ROLE, difficulty=DIFFICULTY, question_count=5, user_id=self.user_id,
        )
        self.assertIsNone(interview.focus_categories)


class FocusedPracticeAPITestCase(unittest.TestCase):
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

    def test_create_interview_persists_focus_categories(self):
        token = self._signup()
        response = self.client.post(
            "/api/interviews/",
            json={
                "role": ROLE, "difficulty": DIFFICULTY, "question_count": 5,
                "focus_categories": ["structure", "specificity"],
            },
            headers=self._auth_headers(token),
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["focus_categories"], ["structure", "specificity"])

    def test_create_interview_without_focus_categories_is_null(self):
        token = self._signup()
        response = self.client.post(
            "/api/interviews/",
            json={"role": ROLE, "difficulty": DIFFICULTY, "question_count": 5},
            headers=self._auth_headers(token),
        )
        self.assertEqual(response.status_code, 201)
        self.assertIsNone(response.json()["focus_categories"])

    def test_unknown_focus_category_is_422(self):
        token = self._signup()
        response = self.client.post(
            "/api/interviews/",
            json={
                "role": ROLE, "difficulty": DIFFICULTY, "question_count": 5,
                "focus_categories": ["made_up_category"],
            },
            headers=self._auth_headers(token),
        )
        self.assertEqual(response.status_code, 422)

    def test_too_many_focus_categories_is_422(self):
        token = self._signup()
        response = self.client.post(
            "/api/interviews/",
            json={
                "role": ROLE, "difficulty": DIFFICULTY, "question_count": 5,
                "focus_categories": [
                    "structure", "specificity", "communication", "relevance",
                ],
            },
            headers=self._auth_headers(token),
        )
        self.assertEqual(response.status_code, 422)

    def test_respond_biases_next_question_toward_technical_focus(self):
        token = self._signup()
        created = self.client.post(
            "/api/interviews/",
            json={
                "role": ROLE, "difficulty": DIFFICULTY, "question_count": 5,
                "focus_categories": ["technical_accuracy"],
            },
            headers=self._auth_headers(token),
        )
        interview_id = created.json()["id"]
        question_id = created.json()["questions"][0]["id"]

        turn = self.client.post(
            f"/api/interviews/{interview_id}/questions/{question_id}/respond",
            json={"text": SHORT_ANSWER},
            headers=self._auth_headers(token),
        )
        self.assertEqual(turn.status_code, 200)
        next_question = turn.json()["next_question"]
        self.assertEqual(next_question["text"], _ONLY_TECHNICAL_EASY_SWE_QUESTION)

    def test_respond_biases_next_question_toward_behavioral_focus(self):
        token = self._signup()
        created = self.client.post(
            "/api/interviews/",
            json={
                "role": ROLE, "difficulty": DIFFICULTY, "question_count": 5,
                "focus_categories": ["structure"],
            },
            headers=self._auth_headers(token),
        )
        interview_id = created.json()["id"]
        question_id = created.json()["questions"][0]["id"]

        turn = self.client.post(
            f"/api/interviews/{interview_id}/questions/{question_id}/respond",
            json={"text": SHORT_ANSWER},
            headers=self._auth_headers(token),
        )
        next_question_text = turn.json()["next_question"]["text"]
        self.assertEqual(classify_question_type(next_question_text), "behavioral")

    def test_focus_categories_survive_get_interview(self):
        token = self._signup()
        created = self.client.post(
            "/api/interviews/",
            json={
                "role": ROLE, "difficulty": DIFFICULTY, "question_count": 5,
                "focus_categories": ["reasoning"],
            },
            headers=self._auth_headers(token),
        )
        interview_id = created.json()["id"]
        fetched = self.client.get(
            f"/api/interviews/{interview_id}", headers=self._auth_headers(token)
        )
        self.assertEqual(fetched.json()["focus_categories"], ["reasoning"])


if __name__ == "__main__":
    unittest.main()
