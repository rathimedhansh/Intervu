"""Tests for the conversational interview flow: dynamic next-question
generation, follow-up decisions, the 5-10 question budget/termination
guarantee, resume-aware generation, AI failure fallback, and the new
/respond endpoint's ownership + invalid-state handling.

Uses stdlib unittest + unittest.mock (Anthropic client mocked, matching
test_answer_evaluation.py) and FastAPI's TestClient against an isolated
in-memory SQLite DB (matching test_auth.py) — never touches the real app.db.

Run from backend/: venv/Scripts/python.exe -m unittest discover -s tests -v
"""

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401 — registers all models on Base
from app.core.config import settings
from app.crud import interview as interview_crud
from app.db.base import Base
from app.db.database import get_db
from app.main import app
from app.models.answer import Answer
from app.models.question import Question
from app.models.resume import Resume
from app.services.interview_flow import MAX_QUESTIONS, MIN_QUESTIONS, decide_next_step
from app.services.interview_flow import anthropic_provider, mock_provider

ROLE = "Software Engineer"
DIFFICULTY = "easy"

SHORT_ANSWER = "I'm not very familiar with that."
LONG_ANSWER = (
    "I built a full-stack weather application using React for the frontend "
    "and a Node.js Express backend that fetched data from a public weather "
    "API and cached results in Redis to avoid rate limits."
)


def _question(text: str, *, order_index: int = 0, is_followup: bool = False,
              resume_topic: str | None = None, answer_text: str | None = None) -> Question:
    question = Question(
        id=order_index + 1,
        interview_id=1,
        text=text,
        order_index=order_index,
        source="resume" if resume_topic else "bank",
        resume_topic=resume_topic,
        is_followup=is_followup,
    )
    if answer_text is not None:
        question.answer = Answer(question_id=question.id, text=answer_text)
    return question


# --- Pure decision-logic tests (no DB, no network) -------------------------


class TestMockProviderDecision(unittest.TestCase):
    def test_follow_up_triggered_for_substantial_answer(self):
        asked = [_question("Tell me about a project.", answer_text=LONG_ANSWER)]
        step = mock_provider.decide(
            role=ROLE, difficulty=DIFFICULTY, resume=None,
            asked_questions=asked, current_is_followup=False, question_count=5,
        )
        self.assertTrue(step.is_followup)
        # Grounded in the candidate's own words — never invents content.
        self.assertIn("weather application", step.question.text.lower())

    def test_no_follow_up_for_short_answer(self):
        asked = [_question("Tell me about a project.", answer_text=SHORT_ANSWER)]
        step = mock_provider.decide(
            role=ROLE, difficulty=DIFFICULTY, resume=None,
            asked_questions=asked, current_is_followup=False, question_count=5,
        )
        self.assertFalse(step.is_followup)

    def test_never_follows_up_on_a_follow_up(self):
        asked = [_question("Tell me about a project.", is_followup=True, answer_text=LONG_ANSWER)]
        step = mock_provider.decide(
            role=ROLE, difficulty=DIFFICULTY, resume=None,
            asked_questions=asked, current_is_followup=True, question_count=5,
        )
        self.assertFalse(step.is_followup)

    def test_no_follow_up_when_budget_nearly_exhausted(self):
        # question_count=5, 4 already asked -> only 1 slot left, must be
        # spent on a main question so the interview can still terminate.
        asked = [
            _question(f"Q{i}", order_index=i, answer_text=LONG_ANSWER) for i in range(4)
        ]
        step = mock_provider.decide(
            role=ROLE, difficulty=DIFFICULTY, resume=None,
            asked_questions=asked, current_is_followup=False, question_count=5,
        )
        self.assertFalse(step.is_followup)

    def test_bank_question_never_repeats_already_asked(self):
        from app.services.question_generation.bank import QUESTION_BANK

        already_asked = set(QUESTION_BANK[ROLE][DIFFICULTY])
        asked = [
            _question(text, order_index=i, answer_text=SHORT_ANSWER)
            for i, text in enumerate(already_asked)
        ]
        step = mock_provider.decide(
            role=ROLE, difficulty=DIFFICULTY, resume=None,
            asked_questions=asked, current_is_followup=False, question_count=10,
        )
        self.assertNotIn(step.question.text, already_asked)

    def test_resume_grounded_question_uses_only_provided_resume_data(self):
        resume = Resume(
            stored_filename="x.pdf", original_filename="x.pdf",
            content_type="application/pdf", size_bytes=1,
            extracted_text="...",
            parsed={"projects": ["Order Service"], "technologies": [], "experience": []},
            analysis={},
        )
        asked = [_question("Tell me about yourself.", answer_text=SHORT_ANSWER)]
        step = mock_provider.decide(
            role=ROLE, difficulty=DIFFICULTY, resume=resume,
            asked_questions=asked, current_is_followup=False, question_count=5,
        )
        self.assertEqual(step.question.source, "resume")
        self.assertIn("Order Service", step.question.text)
        self.assertEqual(step.question.topic, "Project: Order Service")

    def test_resume_topics_already_asked_are_not_repeated(self):
        resume = Resume(
            stored_filename="x.pdf", original_filename="x.pdf",
            content_type="application/pdf", size_bytes=1,
            extracted_text="...",
            parsed={"projects": ["Order Service"], "technologies": ["PostgreSQL"], "experience": []},
            analysis={},
        )
        asked = [
            _question(
                "Tell me about Order Service.",
                resume_topic="Project: Order Service",
                answer_text=SHORT_ANSWER,
            )
        ]
        step = mock_provider.decide(
            role=ROLE, difficulty=DIFFICULTY, resume=resume,
            asked_questions=asked, current_is_followup=False, question_count=5,
        )
        self.assertEqual(step.question.topic, "Technology: PostgreSQL")


class TestCreateInterviewClamping(unittest.TestCase):
    """Direct crud-level test: app.crud.interview.create_interview clamps
    question_count into [MIN_QUESTIONS, MAX_QUESTIONS] independent of the
    HTTP schema's own le=10/ge=1 bounds — defense-in-depth for any caller
    that isn't going through InterviewCreate validation."""

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

    def test_clamps_above_maximum(self):
        interview = interview_crud.create_interview(
            self.db, role=ROLE, difficulty=DIFFICULTY, question_count=999, user_id=self.user_id
        )
        self.assertEqual(interview.question_count, MAX_QUESTIONS)

    def test_clamps_below_minimum(self):
        interview = interview_crud.create_interview(
            self.db, role=ROLE, difficulty=DIFFICULTY, question_count=1, user_id=self.user_id
        )
        self.assertEqual(interview.question_count, MIN_QUESTIONS)


class TestDecideNextStepDefenseInDepth(unittest.TestCase):
    """Even if a provider misbehaves, the dispatcher must not allow two
    follow-ups in a row."""

    def test_overrides_provider_that_chains_follow_ups(self):
        from app.services.interview_flow.types import NextStep
        from app.services.question_generation.types import GeneratedQuestion

        misbehaving_step = NextStep(
            question=GeneratedQuestion(text="Another follow-up?"), is_followup=True
        )
        with patch.object(mock_provider, "decide", return_value=misbehaving_step):
            step = decide_next_step(
                role=ROLE, difficulty=DIFFICULTY, resume=None,
                asked_questions=[_question("Q", is_followup=True, answer_text=LONG_ANSWER)],
                current_is_followup=True, question_count=5,
            )
        self.assertFalse(step.is_followup)


# --- Anthropic provider fallback (never crashes, mirrors answer_evaluation) -


def _tool_response(tool_input: dict):
    return SimpleNamespace(
        content=[SimpleNamespace(type="tool_use", name=anthropic_provider.TOOL_NAME, input=tool_input)]
    )


class SettingsOverrideTestCase(unittest.TestCase):
    def setUp(self):
        self._original_provider = settings.ai_provider
        self._original_key = settings.anthropic_api_key

    def tearDown(self):
        settings.ai_provider = self._original_provider
        settings.anthropic_api_key = self._original_key


class TestAnthropicProviderFallback(SettingsOverrideTestCase):
    def _asked(self):
        return [_question("Tell me about a project.", answer_text=LONG_ANSWER)]

    def test_successful_response_used_as_is(self):
        settings.anthropic_api_key = "fake-key-for-test"
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _tool_response(
            {"action": "follow_up", "question": "What was hardest about that?"}
        )
        with patch.object(anthropic_provider.anthropic, "Anthropic", return_value=mock_client):
            step = anthropic_provider.decide(
                role=ROLE, difficulty=DIFFICULTY, resume=None,
                asked_questions=self._asked(), current_is_followup=False, question_count=5,
            )
        self.assertTrue(step.is_followup)
        self.assertEqual(step.question.text, "What was hardest about that?")

    def test_network_exception_falls_back_to_mock(self):
        settings.anthropic_api_key = "fake-key-for-test"
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = RuntimeError("connection reset")
        with patch.object(anthropic_provider.anthropic, "Anthropic", return_value=mock_client):
            step = anthropic_provider.decide(
                role=ROLE, difficulty=DIFFICULTY, resume=None,
                asked_questions=self._asked(), current_is_followup=False, question_count=5,
            )
        # Falls back to the deterministic mock decision instead of raising.
        self.assertTrue(step.is_followup)

    def test_no_tool_call_falls_back_to_mock(self):
        settings.anthropic_api_key = "fake-key-for-test"
        mock_client = MagicMock()
        mock_client.messages.create.return_value = SimpleNamespace(content=[])
        with patch.object(anthropic_provider.anthropic, "Anthropic", return_value=mock_client):
            step = anthropic_provider.decide(
                role=ROLE, difficulty=DIFFICULTY, resume=None,
                asked_questions=self._asked(), current_is_followup=False, question_count=5,
            )
        self.assertIsNotNone(step.question)

    def test_invalid_action_falls_back_to_mock(self):
        settings.anthropic_api_key = "fake-key-for-test"
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _tool_response(
            {"action": "do_something_else", "question": "??"}
        )
        with patch.object(anthropic_provider.anthropic, "Anthropic", return_value=mock_client):
            step = anthropic_provider.decide(
                role=ROLE, difficulty=DIFFICULTY, resume=None,
                asked_questions=self._asked(), current_is_followup=False, question_count=5,
            )
        self.assertTrue(step.is_followup)  # mock fallback for this LONG_ANSWER fixture

    def test_no_api_key_never_calls_anthropic_sdk(self):
        settings.anthropic_api_key = ""
        with patch.object(anthropic_provider.anthropic, "Anthropic") as mock_ctor:
            anthropic_provider.decide(
                role=ROLE, difficulty=DIFFICULTY, resume=None,
                asked_questions=self._asked(), current_is_followup=False, question_count=5,
            )
        mock_ctor.assert_not_called()

    def test_dispatch_routes_to_anthropic_provider_when_configured(self):
        settings.ai_provider = "anthropic"
        settings.anthropic_api_key = ""  # falls back internally, but the provider must be invoked
        with patch.object(anthropic_provider, "decide", wraps=anthropic_provider.decide) as spy:
            decide_next_step(
                role=ROLE, difficulty=DIFFICULTY, resume=None,
                asked_questions=self._asked(), current_is_followup=False, question_count=5,
            )
        spy.assert_called_once()


# --- Full conversational flow over HTTP -------------------------------------


class InterviewFlowAPITestCase(unittest.TestCase):
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

    def _signup(self, email="ada@example.com", password="supersecret1", name="Ada"):
        response = self.client.post(
            "/api/auth/signup", json={"name": name, "email": email, "password": password}
        )
        return response.json()["access_token"]

    def _create_interview(self, token, question_count=5, role=ROLE, difficulty=DIFFICULTY):
        return self.client.post(
            "/api/interviews/",
            json={"role": role, "difficulty": difficulty, "question_count": question_count},
            headers=self._auth_headers(token),
        )

    def _respond(self, token, interview_id, question_id, text=SHORT_ANSWER):
        return self.client.post(
            f"/api/interviews/{interview_id}/questions/{question_id}/respond",
            json={"text": text},
            headers=self._auth_headers(token),
        )

    def test_only_first_question_generated_at_creation(self):
        token = self._signup()
        created = self._create_interview(token, question_count=5)
        self.assertEqual(created.status_code, 201)
        self.assertEqual(len(created.json()["questions"]), 1)

    def test_question_count_clamped_to_minimum(self):
        token = self._signup()
        created = self._create_interview(token, question_count=1)
        interview_id = created.json()["id"]
        question_id = created.json()["questions"][0]["id"]

        asked = 0
        while True:
            turn = self._respond(token, interview_id, question_id, text=SHORT_ANSWER)
            self.assertEqual(turn.status_code, 200)
            body = turn.json()
            asked = body["questions_asked"]
            if body["is_complete"]:
                break
            question_id = body["next_question"]["id"]
            self.assertLessEqual(asked, MAX_QUESTIONS)

        self.assertEqual(body["question_count"], MIN_QUESTIONS)
        self.assertEqual(asked, MIN_QUESTIONS)

    def test_question_count_rejected_above_schema_maximum(self):
        # InterviewCreate.question_count already caps at 10 (le=10) — the
        # crud-level clamp is defense-in-depth for direct/internal callers,
        # covered separately by test_create_interview_clamps_above_maximum.
        token = self._signup()
        response = self._create_interview(token, question_count=999)
        self.assertEqual(response.status_code, 422)

    def test_interview_never_exceeds_configured_budget(self):
        token = self._signup()
        created = self._create_interview(token, question_count=5)
        interview_id = created.json()["id"]
        question_id = created.json()["questions"][0]["id"]

        turns_taken = 0
        while True:
            turn = self._respond(token, interview_id, question_id, text=SHORT_ANSWER)
            body = turn.json()
            turns_taken += 1
            self.assertLessEqual(turns_taken, MAX_QUESTIONS)  # hard safety net against infinite loop
            if body["is_complete"]:
                self.assertIsNone(body["next_question"])
                break
            question_id = body["next_question"]["id"]

        self.assertEqual(turns_taken, 5)

        interview = self.client.get(
            f"/api/interviews/{interview_id}", headers=self._auth_headers(token)
        ).json()
        self.assertEqual(len(interview["questions"]), 5)
        self.assertTrue(all(q["answer"] is not None for q in interview["questions"]))

    def test_follow_up_appears_and_is_flagged_in_response(self):
        token = self._signup()
        created = self._create_interview(token, question_count=5)
        interview_id = created.json()["id"]
        question_id = created.json()["questions"][0]["id"]

        turn = self._respond(token, interview_id, question_id, text=LONG_ANSWER)
        body = turn.json()

        self.assertTrue(body["is_followup"])
        self.assertTrue(body["next_question"]["is_followup"])

    def test_completion_after_respond_preserves_scoring_pipeline(self):
        token = self._signup()
        created = self._create_interview(token, question_count=5)
        interview_id = created.json()["id"]
        question_id = created.json()["questions"][0]["id"]

        while True:
            turn = self._respond(token, interview_id, question_id, text=SHORT_ANSWER)
            body = turn.json()
            # Evaluation already ran inline, per-answer.
            self.assertIsNotNone(body["answer"]["evaluation"])
            self.assertIsNotNone(body["answer"]["total_score"])
            if body["is_complete"]:
                break
            question_id = body["next_question"]["id"]

        complete = self.client.post(
            f"/api/interviews/{interview_id}/complete", headers=self._auth_headers(token)
        )
        self.assertEqual(complete.status_code, 200)
        result = complete.json()
        self.assertEqual(result["status"], "completed")
        self.assertIsNotNone(result["overall_score"])
        self.assertIsNotNone(result["summary_feedback"])

        dashboard = self.client.get(
            "/api/dashboard/", headers=self._auth_headers(token)
        ).json()
        self.assertEqual(dashboard["overview"]["total_interviews"], 1)

    def test_user_cannot_respond_to_another_users_interview(self):
        token_a = self._signup(email="alice@example.com")
        token_b = self._signup(email="bob@example.com", name="Bob")
        created = self._create_interview(token_a, question_count=5)
        interview_id = created.json()["id"]
        question_id = created.json()["questions"][0]["id"]

        response = self._respond(token_b, interview_id, question_id, text=SHORT_ANSWER)
        self.assertEqual(response.status_code, 403)

    def test_respond_without_token_is_401(self):
        token = self._signup()
        created = self._create_interview(token, question_count=5)
        interview_id = created.json()["id"]
        question_id = created.json()["questions"][0]["id"]

        response = self.client.post(
            f"/api/interviews/{interview_id}/questions/{question_id}/respond",
            json={"text": SHORT_ANSWER},
        )
        self.assertEqual(response.status_code, 401)

    def test_respond_to_already_answered_question_is_409(self):
        token = self._signup()
        created = self._create_interview(token, question_count=5)
        interview_id = created.json()["id"]
        question_id = created.json()["questions"][0]["id"]

        first = self._respond(token, interview_id, question_id, text=SHORT_ANSWER)
        self.assertEqual(first.status_code, 200)

        retry = self._respond(token, interview_id, question_id, text="a second try")
        self.assertEqual(retry.status_code, 409)

    def test_respond_after_interview_completed_is_409(self):
        token = self._signup()
        created = self._create_interview(token, question_count=5)
        interview_id = created.json()["id"]
        question_id = created.json()["questions"][0]["id"]

        while True:
            turn = self._respond(token, interview_id, question_id, text=SHORT_ANSWER)
            body = turn.json()
            if body["is_complete"]:
                break
            question_id = body["next_question"]["id"]

        self.client.post(
            f"/api/interviews/{interview_id}/complete", headers=self._auth_headers(token)
        )

        # Nothing left to answer, but simulate a stale client retrying the
        # last question anyway.
        stale_retry = self._respond(token, interview_id, question_id, text="late answer")
        self.assertEqual(stale_retry.status_code, 409)

    def test_respond_on_legacy_interview_without_question_count_is_400(self):
        token = self._signup()
        created = self._create_interview(token, question_count=5)
        interview_id = created.json()["id"]
        question_id = created.json()["questions"][0]["id"]

        # Simulate an interview created before this feature (question_count
        # is null at the DB level for those rows).
        db = next(app.dependency_overrides[get_db]())
        interview = interview_crud.get_interview(db, interview_id)
        interview.question_count = None
        db.commit()
        db.close()

        response = self._respond(token, interview_id, question_id, text=SHORT_ANSWER)
        self.assertEqual(response.status_code, 400)

    def test_empty_answer_rejected(self):
        token = self._signup()
        created = self._create_interview(token, question_count=5)
        interview_id = created.json()["id"]
        question_id = created.json()["questions"][0]["id"]

        response = self._respond(token, interview_id, question_id, text="")
        self.assertEqual(response.status_code, 422)

    # GET /interviews/ — powers the History page (see frontend/src/pages/
    # HistoryPage.jsx). Deliberately unfiltered/unpaginated (both pending
    # and completed interviews, in full) — the dashboard's own listing is
    # capped and completed-only (see
    # app.crud.dashboard.RECENT_INTERVIEWS_LIMIT); this endpoint is where
    # "see everything you've ever done" actually lives.
    def test_list_includes_both_pending_and_completed_interviews(self):
        token = self._signup()
        pending = self._create_interview(token, question_count=5)
        pending_id = pending.json()["id"]

        completed = self._create_interview(token, question_count=5)
        completed_id = completed.json()["id"]
        question_id = completed.json()["questions"][0]["id"]
        while True:
            turn = self._respond(token, completed_id, question_id, text=SHORT_ANSWER)
            body = turn.json()
            if body["is_complete"]:
                break
            question_id = body["next_question"]["id"]
        self.client.post(
            f"/api/interviews/{completed_id}/complete", headers=self._auth_headers(token)
        )

        response = self.client.get("/api/interviews/", headers=self._auth_headers(token))
        self.assertEqual(response.status_code, 200)
        by_id = {i["id"]: i for i in response.json()}
        self.assertEqual(by_id[pending_id]["status"], "pending")
        self.assertEqual(by_id[completed_id]["status"], "completed")
        self.assertIsNotNone(by_id[completed_id]["overall_score"])

    def test_list_ordered_most_recently_created_first(self):
        token = self._signup()
        first = self._create_interview(token, question_count=5).json()["id"]
        second = self._create_interview(token, question_count=5).json()["id"]
        third = self._create_interview(token, question_count=5).json()["id"]

        response = self.client.get("/api/interviews/", headers=self._auth_headers(token))
        ids = [i["id"] for i in response.json()]
        self.assertEqual(ids, [third, second, first])

    def test_list_is_scoped_to_the_requesting_user_only(self):
        token_a = self._signup(email="alice2@example.com")
        token_b = self._signup(email="bob2@example.com", name="Bob")
        self._create_interview(token_a, question_count=5)
        self._create_interview(token_a, question_count=5)
        self._create_interview(token_b, question_count=5)

        response_a = self.client.get("/api/interviews/", headers=self._auth_headers(token_a))
        response_b = self.client.get("/api/interviews/", headers=self._auth_headers(token_b))
        self.assertEqual(len(response_a.json()), 2)
        self.assertEqual(len(response_b.json()), 1)

    def test_not_capped_at_the_dashboards_recent_interviews_limit(self):
        # Regression guard for the exact gap this endpoint/page fixes: the
        # dashboard truncates to RECENT_INTERVIEWS_LIMIT (10) completed
        # interviews — this listing must not inherit that cap.
        from app.crud.dashboard import RECENT_INTERVIEWS_LIMIT

        token = self._signup()
        for _ in range(RECENT_INTERVIEWS_LIMIT + 3):
            self._create_interview(token, question_count=5)

        response = self.client.get("/api/interviews/", headers=self._auth_headers(token))
        self.assertEqual(len(response.json()), RECENT_INTERVIEWS_LIMIT + 3)

    def test_list_requires_authentication(self):
        response = self.client.get("/api/interviews/")
        self.assertEqual(response.status_code, 401)

    # DELETE /interviews/{id} — powers the History page's cleanup action
    # (frontend/src/pages/HistoryPage.jsx). Relies entirely on the cascade
    # relationships already configured on Interview.questions and
    # Question.answer (see app.models.interview/question) rather than any
    # new manual cleanup logic.
    def test_owner_can_delete_a_pending_interview(self):
        token = self._signup()
        created = self._create_interview(token, question_count=5)
        interview_id = created.json()["id"]

        response = self.client.delete(
            f"/api/interviews/{interview_id}", headers=self._auth_headers(token)
        )
        self.assertEqual(response.status_code, 200)

        follow_up = self.client.get(
            f"/api/interviews/{interview_id}", headers=self._auth_headers(token)
        )
        self.assertEqual(follow_up.status_code, 404)

    def test_owner_can_delete_a_completed_interview(self):
        token = self._signup()
        created = self._create_interview(token, question_count=5)
        interview_id = created.json()["id"]
        question_id = created.json()["questions"][0]["id"]
        while True:
            turn = self._respond(token, interview_id, question_id, text=SHORT_ANSWER)
            body = turn.json()
            if body["is_complete"]:
                break
            question_id = body["next_question"]["id"]
        self.client.post(
            f"/api/interviews/{interview_id}/complete", headers=self._auth_headers(token)
        )

        response = self.client.delete(
            f"/api/interviews/{interview_id}", headers=self._auth_headers(token)
        )
        self.assertEqual(response.status_code, 200)

    def test_delete_cascades_to_questions_and_answers(self):
        token = self._signup()
        created = self._create_interview(token, question_count=5)
        interview_id = created.json()["id"]
        question_id = created.json()["questions"][0]["id"]
        self._respond(token, interview_id, question_id, text=SHORT_ANSWER)

        db = next(app.dependency_overrides[get_db]())
        question_ids_before = [q.id for q in db.query(Question).filter(Question.interview_id == interview_id)]
        self.assertGreaterEqual(len(question_ids_before), 1)
        answer_ids_before = [
            a.id for a in db.query(Answer).filter(Answer.question_id.in_(question_ids_before))
        ]
        self.assertGreaterEqual(len(answer_ids_before), 1)
        db.close()

        self.client.delete(f"/api/interviews/{interview_id}", headers=self._auth_headers(token))

        db = next(app.dependency_overrides[get_db]())
        remaining_questions = db.query(Question).filter(Question.interview_id == interview_id).count()
        remaining_answers = db.query(Answer).filter(Answer.id.in_(answer_ids_before)).count()
        db.close()
        self.assertEqual(remaining_questions, 0)
        self.assertEqual(remaining_answers, 0)

    def test_delete_does_not_remove_the_underlying_resume(self):
        token = self._signup()
        resume = Resume(
            stored_filename="x.pdf",
            original_filename="x.pdf",
            content_type="application/pdf",
            size_bytes=10,
            extracted_text="text",
            parsed={},
            analysis={},
        )
        db = next(app.dependency_overrides[get_db]())
        from app.models.user import User as UserModel

        user = db.query(UserModel).filter(UserModel.email == "ada@example.com").first()
        resume.user_id = user.id
        db.add(resume)
        db.commit()
        db.refresh(resume)
        resume_id = resume.id
        db.close()

        created = self._create_interview(token, question_count=5)
        # Attach the resume directly (bypassing the create-interview API,
        # which already has its own resume_id coverage) to isolate this
        # test to the delete path.
        db = next(app.dependency_overrides[get_db]())
        interview = interview_crud.get_interview(db, created.json()["id"])
        interview.resume_id = resume_id
        db.commit()
        interview_id = interview.id
        db.close()

        self.client.delete(f"/api/interviews/{interview_id}", headers=self._auth_headers(token))

        db = next(app.dependency_overrides[get_db]())
        self.assertIsNotNone(db.get(Resume, resume_id))
        db.close()

    def test_user_cannot_delete_another_users_interview(self):
        token_a = self._signup(email="carol@example.com")
        token_b = self._signup(email="dave@example.com", name="Dave")
        created = self._create_interview(token_a, question_count=5)
        interview_id = created.json()["id"]

        response = self.client.delete(
            f"/api/interviews/{interview_id}", headers=self._auth_headers(token_b)
        )
        self.assertEqual(response.status_code, 403)

        # Confirm it's still there for the actual owner.
        still_there = self.client.get(
            f"/api/interviews/{interview_id}", headers=self._auth_headers(token_a)
        )
        self.assertEqual(still_there.status_code, 200)

    def test_delete_nonexistent_interview_is_404(self):
        token = self._signup()
        response = self.client.delete(
            "/api/interviews/999999", headers=self._auth_headers(token)
        )
        self.assertEqual(response.status_code, 404)

    def test_delete_requires_authentication(self):
        token = self._signup()
        created = self._create_interview(token, question_count=5)
        interview_id = created.json()["id"]

        response = self.client.delete(f"/api/interviews/{interview_id}")
        self.assertEqual(response.status_code, 401)

    def test_deleted_interview_excluded_from_list_and_dashboard_totals(self):
        token = self._signup()
        keep = self._create_interview(token, question_count=5).json()["id"]
        gone = self._create_interview(token, question_count=5).json()["id"]

        self.client.delete(f"/api/interviews/{gone}", headers=self._auth_headers(token))

        listing = self.client.get("/api/interviews/", headers=self._auth_headers(token))
        ids = [i["id"] for i in listing.json()]
        self.assertIn(keep, ids)
        self.assertNotIn(gone, ids)

        dashboard = self.client.get("/api/dashboard/", headers=self._auth_headers(token))
        self.assertEqual(dashboard.json()["overview"]["total_interviews"], 0)  # neither was completed


if __name__ == "__main__":
    unittest.main()
