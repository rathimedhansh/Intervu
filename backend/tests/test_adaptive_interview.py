"""Tests for the adaptive interviewer feature: keyword-aware and quality-
aware follow-ups, momentum-based adaptive difficulty, behavioral/technical
type balancing, the guaranteed intro question, and a regression guard that
communication metrics still flow through the (unchanged) /respond and
/complete endpoints under the new decision logic.

Uses stdlib unittest, matching the rest of the suite. API-level tests use
FastAPI's TestClient against an isolated in-memory SQLite DB — never
touches the real app.db.

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
from app.models.answer import Answer
from app.models.question import Question
from app.models.resume import Resume
from app.models.user import User
from app.services.interview_flow import mock_provider
from app.services.interview_flow.topics import extract_topic
from app.services.question_generation.bank import QUESTION_BANK

ROLE = "Software Engineer"

SHORT_ANSWER = "I'm not very familiar with that."
# Crafted to reliably score >= _STRONG_RATIO via the mock evaluator's own
# signal formulas (see app/services/answer_evaluation/mock_provider.py)
# regardless of which random bank question it's answering or how much
# keyword overlap that happens to produce: length >= 80 words (maxes
# length/clarity/completeness), >= 3 structure markers ("first", "then",
# "finally", "as a result") and >= 2 reasoning markers ("because",
# "tradeoff", "instead of", "compared to", "avoid") (maxes structure/
# reasoning), and a number + "for example" (maxes the examples signal) —
# even at zero keyword overlap this nets ~0.79-0.86, comfortably above the
# 0.72 strong threshold on both the behavioral and technical rubrics.
STRONG_ANSWER = (
    "First, I identified the core requirements and constraints for the problem. "
    "Then I evaluated a few different approaches, because each one had different "
    "tradeoffs in terms of performance and complexity. For example, I considered "
    "a simpler solution first, but instead of that I chose a more scalable "
    "approach since it would handle 10x the load compared to the naive version. "
    "As a result, the system became more reliable, and finally I documented the "
    "decision so the team could understand the reasoning behind it and avoid "
    "repeating the same tradeoff discussion later."
)
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


def _scored_question(ratio: float, order_index: int) -> Question:
    q = _question(f"Question {order_index}", order_index=order_index, answer_text=LONG_ANSWER)
    q.answer.total_score = round(ratio * 100)
    q.answer.evaluation = {"max_score": 100}
    return q


# --- Topic extraction --------------------------------------------------


class TestTopicExtraction(unittest.TestCase):
    def test_finds_known_technology(self):
        self.assertEqual(extract_topic("I used JWT for authentication."), "jwt")

    def test_prefers_longer_more_specific_match(self):
        self.assertEqual(
            extract_topic("I trained a machine learning model with PyTorch."),
            "machine learning model",
        )

    def test_returns_none_for_no_match(self):
        self.assertIsNone(extract_topic("I worked hard and did my best on the project."))

    def test_case_insensitive(self):
        self.assertEqual(extract_topic("We used DOCKER for deployment."), "docker")


# --- Adaptive follow-up content -----------------------------------------


class TestAdaptiveFollowUpContent(unittest.TestCase):
    def test_keyword_mentioned_gets_targeted_follow_up(self):
        answer_text = (
            "I used JWT authentication to secure the endpoints and issued "
            "short-lived access tokens so unauthorized clients could not "
            "stay authenticated indefinitely after logging out."
        )
        asked = [_question("How did you handle authentication?", answer_text=answer_text)]
        step = mock_provider.decide(
            role=ROLE, difficulty="medium", resume=None,
            asked_questions=asked, current_is_followup=False, question_count=5,
        )
        self.assertTrue(step.is_followup)
        text = step.question.text.lower()
        self.assertIn("jwt", text)
        self.assertIn("why did you choose", text)

    def test_weak_answer_gets_clarification_follow_up(self):
        question = _question(
            "Describe a challenging bug you fixed.",
            answer_text=(
                "It was hard and I do not really remember what I did but I "
                "think I fixed it eventually after trying some stuff for a while."
            ),
        )
        question.answer.total_score = 20
        question.answer.evaluation = {"max_score": 100}

        step = mock_provider.decide(
            role=ROLE, difficulty="medium", resume=None,
            asked_questions=[question], current_is_followup=False, question_count=5,
        )
        self.assertTrue(step.is_followup)
        self.assertIn("walk me through that in more detail", step.question.text.lower())

    def test_strong_answer_still_grounded_in_candidates_words(self):
        # Regression guard for the pre-existing contract: whatever kind of
        # follow-up fires, it must quote the candidate's own answer, never
        # invent content.
        asked = [_question("Tell me about a project.", answer_text=LONG_ANSWER)]
        step = mock_provider.decide(
            role=ROLE, difficulty="medium", resume=None,
            asked_questions=asked, current_is_followup=False, question_count=5,
        )
        self.assertTrue(step.is_followup)
        self.assertIn("weather application", step.question.text.lower())


# --- Adaptive difficulty (pure function) --------------------------------


class TestEffectiveDifficulty(unittest.TestCase):
    def test_no_scored_answers_keeps_baseline(self):
        self.assertEqual(mock_provider._effective_difficulty("medium", []), "medium")

    def test_unscored_answers_are_ignored(self):
        # _question()'s answer_text fixture has no total_score/evaluation.
        asked = [_question("Q", answer_text=LONG_ANSWER)]
        self.assertEqual(mock_provider._effective_difficulty("medium", asked), "medium")

    def test_single_strong_answer_does_not_shift(self):
        asked = [_scored_question(0.9, 0)]
        self.assertEqual(mock_provider._effective_difficulty("easy", asked), "easy")

    def test_two_strong_answers_shift_up_one_tier(self):
        asked = [_scored_question(0.9, 0), _scored_question(0.85, 1)]
        self.assertEqual(mock_provider._effective_difficulty("easy", asked), "medium")

    def test_two_weak_answers_shift_down_one_tier(self):
        asked = [_scored_question(0.1, 0), _scored_question(0.2, 1)]
        self.assertEqual(mock_provider._effective_difficulty("hard", asked), "medium")

    def test_clamped_at_ceiling(self):
        asked = [_scored_question(0.95, i) for i in range(3)]
        self.assertEqual(mock_provider._effective_difficulty("hard", asked), "hard")

    def test_clamped_at_floor(self):
        asked = [_scored_question(0.05, i) for i in range(3)]
        self.assertEqual(mock_provider._effective_difficulty("easy", asked), "easy")

    def test_mixed_signals_hold_steady(self):
        asked = [_scored_question(0.9, 0), _scored_question(0.1, 1)]
        self.assertEqual(mock_provider._effective_difficulty("medium", asked), "medium")

    def test_only_recent_window_considered(self):
        # window=3 -> looks at the last 3 (weak, strong, strong) = momentum
        # +1, not enough on its own to shift (needs +/-2).
        asked = [
            _scored_question(0.1, 0),
            _scored_question(0.1, 1),
            _scored_question(0.9, 2),
            _scored_question(0.9, 3),
        ]
        self.assertEqual(mock_provider._effective_difficulty("medium", asked), "medium")


# --- Question-type balancing (pure function) ----------------------------


class TestPreferredQuestionType(unittest.TestCase):
    def test_favors_underrepresented_type(self):
        asked = [
            _question("How would you design a rate limiter for a public API?"),
            _question("Describe a system you designed that had to scale significantly."),
        ]
        self.assertEqual(mock_provider._preferred_question_type(asked), "behavioral")

    def test_favors_technical_when_behavioral_dominant(self):
        asked = [
            _question("Tell me about a time you disagreed with a teammate."),
            _question("Describe a time you made a mistake at work."),
        ]
        self.assertEqual(mock_provider._preferred_question_type(asked), "technical")

    def test_no_history_defaults_to_behavioral(self):
        self.assertEqual(mock_provider._preferred_question_type([]), "behavioral")


# --- Intro question guarantee (CRUD-level) -------------------------------


class TestIntroQuestionGuarantee(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine)
        self.db = Session()

        user = User(name="Test", email="test@example.com", password_hash="x")
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        self.user_id = user.id

    def test_intro_used_even_at_hard_difficulty(self):
        interview = interview_crud.create_interview(
            self.db, role=ROLE, difficulty="hard", question_count=5, user_id=self.user_id
        )
        self.assertEqual(interview.questions[0].text, QUESTION_BANK[ROLE]["easy"][0])

    def test_intro_used_even_with_resume_attached(self):
        resume = Resume(
            user_id=self.user_id,
            stored_filename="intro-test.pdf",
            original_filename="resume.pdf",
            content_type="application/pdf",
            size_bytes=1,
            extracted_text="...",
            parsed={"projects": ["Order Service"], "technologies": [], "experience": []},
            analysis={},
        )
        self.db.add(resume)
        self.db.commit()
        self.db.refresh(resume)

        interview = interview_crud.create_interview(
            self.db, role=ROLE, difficulty="medium", question_count=5,
            user_id=self.user_id, resume_id=resume.id,
        )
        self.assertEqual(interview.questions[0].text, QUESTION_BANK[ROLE]["easy"][0])

    def test_intro_falls_back_to_general_pool_for_custom_role(self):
        interview = interview_crud.create_interview(
            self.db, role="Blockchain Engineer", difficulty="easy",
            question_count=5, user_id=self.user_id,
        )
        self.assertEqual(interview.questions[0].text, QUESTION_BANK["General"]["easy"][0])


# --- End-to-end adaptive behavior over HTTP ------------------------------


class AdaptiveInterviewAPITestCase(unittest.TestCase):
    def setUp(self):
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=engine)
        self.TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

        def override_get_db():
            db = self.TestingSessionLocal()
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

    def _create_interview(self, token, role=ROLE, difficulty="easy", question_count=8):
        return self.client.post(
            "/api/interviews/",
            json={"role": role, "difficulty": difficulty, "question_count": question_count},
            headers=self._auth_headers(token),
        )

    def _respond(self, token, interview_id, question_id, text=SHORT_ANSWER, speech_metrics=None):
        payload = {"text": text}
        if speech_metrics is not None:
            payload["speech_metrics"] = speech_metrics
        return self.client.post(
            f"/api/interviews/{interview_id}/questions/{question_id}/respond",
            json=payload,
            headers=self._auth_headers(token),
        )

    def _force_score(self, answer_id: int, ratio: float, max_score: int = 100):
        # Bypasses the mock evaluator's fuzzy text-based scoring so a test
        # can control "strong"/"weak" exactly. NOTE: this only affects
        # decisions made *after* it's called — the answer just submitted in
        # the current /respond call has already been evaluated for real (in
        # -request) by the time a test can call this, so it's only useful
        # for shaping *earlier* turns' recorded scores, not the just-
        # submitted one. See test_weak_streak_gradually_decreases_difficulty
        # for why SHORT_ANSWER doesn't need this at all (it's already
        # naturally weak for real).
        db = self.TestingSessionLocal()
        try:
            answer = db.get(Answer, answer_id)
            answer.total_score = round(ratio * max_score)
            answer.evaluation = {"max_score": max_score}
            db.commit()
        finally:
            db.close()

    def test_first_question_is_always_the_intro_question(self):
        token = self._signup()
        created = self._create_interview(token, difficulty="hard")
        self.assertEqual(created.json()["questions"][0]["text"], QUESTION_BANK[ROLE]["easy"][0])

    def test_strong_streak_gradually_increases_difficulty(self):
        token = self._signup()
        created = self._create_interview(token, difficulty="easy", question_count=8)
        interview_id = created.json()["id"]
        question_id = created.json()["questions"][0]["id"]

        # STRONG_ANSWER is long/substantial enough to earn a follow-up too
        # (see the class-level comment) — that's fine and expected (a
        # strong, detailed answer naturally invites one), it just means the
        # bucket check below happens on the second *main* question rather
        # than literally "the second question".
        turn = self._respond(token, interview_id, question_id, text=STRONG_ANSWER)
        body = turn.json()
        self.assertTrue(body["is_followup"])  # Q1 was substantial and strong
        question_id = body["next_question"]["id"]

        turn = self._respond(token, interview_id, question_id, text=STRONG_ANSWER)
        body = turn.json()
        self.assertFalse(body["is_followup"])  # can never chain onto a follow-up

        # Two consecutive strong real answers (Q1 and the follow-up) ->
        # this next main bank pick should have moved up to "medium".
        self.assertIn(body["next_question"]["text"], QUESTION_BANK[ROLE]["medium"])

    def test_weak_streak_gradually_decreases_difficulty(self):
        token = self._signup()
        created = self._create_interview(token, difficulty="hard", question_count=8)
        interview_id = created.json()["id"]
        question_id = created.json()["questions"][0]["id"]

        turn = self._respond(token, interview_id, question_id, text=SHORT_ANSWER)
        self._force_score(turn.json()["answer"]["id"], ratio=0.1)
        question_id = turn.json()["next_question"]["id"]

        turn = self._respond(token, interview_id, question_id, text=SHORT_ANSWER)
        self._force_score(turn.json()["answer"]["id"], ratio=0.1)
        question_id = turn.json()["next_question"]["id"]

        next_text = turn.json()["next_question"]["text"]
        self.assertIn(next_text, QUESTION_BANK[ROLE]["medium"])

    def test_no_question_repeated_across_full_interview(self):
        token = self._signup()
        created = self._create_interview(token, difficulty="easy", question_count=8)
        interview_id = created.json()["id"]
        question_id = created.json()["questions"][0]["id"]
        seen_texts = {created.json()["questions"][0]["text"]}

        while True:
            turn = self._respond(token, interview_id, question_id, text=SHORT_ANSWER)
            body = turn.json()
            self.assertEqual(turn.status_code, 200)
            if body["is_complete"]:
                break
            next_text = body["next_question"]["text"]
            self.assertNotIn(next_text, seen_texts)
            seen_texts.add(next_text)
            question_id = body["next_question"]["id"]

        self.assertEqual(body["questions_asked"], 8)

    def test_follow_up_depth_capped_and_budget_enforced(self):
        token = self._signup()
        created = self._create_interview(token, difficulty="easy", question_count=5)
        interview_id = created.json()["id"]
        question_id = created.json()["questions"][0]["id"]

        turns = 0
        follow_up_run_lengths = []
        current_run = 0
        while True:
            turn = self._respond(token, interview_id, question_id, text=LONG_ANSWER)
            body = turn.json()
            turns += 1
            self.assertLessEqual(turns, 5)  # budget must never be exceeded
            if body["is_followup"]:
                current_run += 1
            else:
                if current_run:
                    follow_up_run_lengths.append(current_run)
                current_run = 0
            if body["is_complete"]:
                break
            question_id = body["next_question"]["id"]

        self.assertEqual(turns, 5)
        # No two consecutive follow-ups anywhere in the run.
        self.assertTrue(all(length == 1 for length in follow_up_run_lengths))

    def test_role_based_questioning_without_resume(self):
        token = self._signup()
        created = self._create_interview(token, role="Data Scientist", difficulty="easy", question_count=5)
        interview_id = created.json()["id"]
        question_id = created.json()["questions"][0]["id"]

        turn = self._respond(token, interview_id, question_id, text=SHORT_ANSWER)
        body = turn.json()
        self.assertFalse(body["is_followup"])
        self.assertEqual(body["next_question"]["source"], "bank")

    def test_communication_metrics_survive_adaptive_flow_to_results(self):
        token = self._signup()
        created = self._create_interview(token, difficulty="easy", question_count=5)
        interview_id = created.json()["id"]
        question_id = created.json()["questions"][0]["id"]

        speech_metrics = {
            "duration_seconds": 30,
            "words_per_minute": 120,
            "pause_count": 1,
            "long_pause_count": 0,
            "filler_word_count": 1,
            "filler_words": {"um": 1},
            "repeated_word_count": 0,
            "transcript_word_count": 60,
            "transcript_available": True,
        }
        turn = self._respond(token, interview_id, question_id, text=SHORT_ANSWER, speech_metrics=speech_metrics)
        self.assertEqual(turn.status_code, 200)
        self.assertIsNotNone(turn.json()["answer"]["speech_metrics"])

        body = turn.json()
        while not body["is_complete"]:
            question_id = body["next_question"]["id"]
            turn = self._respond(token, interview_id, question_id, text=SHORT_ANSWER)
            body = turn.json()

        complete = self.client.post(
            f"/api/interviews/{interview_id}/complete",
            json={
                "camera_metrics": {
                    "face_visible_percentage": 90,
                    "camera_attention_percentage": 80,
                    "head_movement_score": 10,
                }
            },
            headers=self._auth_headers(token),
        )
        self.assertEqual(complete.status_code, 200)
        result = complete.json()
        self.assertIsNotNone(result["communication_report"])
        self.assertIsNotNone(result["communication_report"]["overall_score"])

        fetched = self.client.get(
            f"/api/interviews/{interview_id}", headers=self._auth_headers(token)
        ).json()
        self.assertIsNotNone(fetched["communication_report"])

    def test_turn_reports_current_difficulty_and_no_change_by_default(self):
        # A single so-so real answer shouldn't be enough to move the needle
        # (SHIFT_THRESHOLD requires several signals) — current_difficulty
        # stays at baseline and difficulty_changed stays null.
        token = self._signup()
        created = self._create_interview(token, difficulty="medium", question_count=8)
        interview_id = created.json()["id"]
        question_id = created.json()["questions"][0]["id"]

        turn = self._respond(token, interview_id, question_id, text=SHORT_ANSWER)
        body = turn.json()
        self.assertEqual(body["current_difficulty"], "medium")
        self.assertIsNone(body["difficulty_changed"])

    def test_turn_reports_difficulty_increased_after_strong_streak(self):
        token = self._signup()
        created = self._create_interview(token, difficulty="easy", question_count=8)
        interview_id = created.json()["id"]
        question_id = created.json()["questions"][0]["id"]

        # Q1 (real strong answer, likely also earns a follow-up)
        turn = self._respond(token, interview_id, question_id, text=STRONG_ANSWER)
        body = turn.json()
        self.assertEqual(body["current_difficulty"], "easy")
        question_id = body["next_question"]["id"]

        # Second strong real answer -> two-strong-in-a-row shifts up a tier.
        turn = self._respond(token, interview_id, question_id, text=STRONG_ANSWER)
        body = turn.json()
        self.assertEqual(body["current_difficulty"], "medium")
        self.assertEqual(body["difficulty_changed"], "increased")

    def test_turn_reports_difficulty_decreased_after_weak_streak(self):
        token = self._signup()
        created = self._create_interview(token, difficulty="hard", question_count=8)
        interview_id = created.json()["id"]
        question_id = created.json()["questions"][0]["id"]

        turn = self._respond(token, interview_id, question_id, text=SHORT_ANSWER)
        self._force_score(turn.json()["answer"]["id"], ratio=0.1)
        question_id = turn.json()["next_question"]["id"]

        turn = self._respond(token, interview_id, question_id, text=SHORT_ANSWER)
        self._force_score(turn.json()["answer"]["id"], ratio=0.1)
        body = turn.json()
        self.assertEqual(body["current_difficulty"], "medium")
        self.assertEqual(body["difficulty_changed"], "decreased")

    def test_get_interview_current_difficulty_matches_last_turn(self):
        # A page refresh mid-interview (GET /interviews/{id}) should show the
        # same calibrated level the last /respond turn reported — read-time
        # recomputation (InterviewRead.current_difficulty) must agree with
        # the live crud-layer computation.
        token = self._signup()
        created = self._create_interview(token, difficulty="easy", question_count=8)
        interview_id = created.json()["id"]
        question_id = created.json()["questions"][0]["id"]

        turn = self._respond(token, interview_id, question_id, text=STRONG_ANSWER)
        question_id = turn.json()["next_question"]["id"]
        turn = self._respond(token, interview_id, question_id, text=STRONG_ANSWER)
        self.assertEqual(turn.json()["current_difficulty"], "medium")

        fetched = self.client.get(
            f"/api/interviews/{interview_id}", headers=self._auth_headers(token)
        ).json()
        self.assertEqual(fetched["current_difficulty"], "medium")


if __name__ == "__main__":
    unittest.main()
