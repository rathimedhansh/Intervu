"""Tests for the performance-dashboard aggregation added to
app.crud.dashboard.get_dashboard_stats: the blended overall/technical/
communication/presentation scores, the communication-score trend, recurring
strengths/weaknesses, and recommendations.

Uses stdlib unittest + FastAPI's TestClient against an isolated in-memory
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
from app.db.base import Base
from app.db.database import get_db
from app.main import app
from app.models.answer import Answer

SPEECH_METRICS = {
    "duration_seconds": 30,
    "words_per_minute": 130,
    "pause_count": 1,
    "long_pause_count": 0,
    "filler_word_count": 1,
    "filler_words": {"um": 1},
    "repeated_word_count": 0,
    "transcript_word_count": 60,
    "transcript_available": True,
}

CAMERA_METRICS = {
    "face_visible_percentage": 90,
    "camera_attention_percentage": 80,
    "head_movement_score": 10,
}

# Deliberately bad on pace, fillers, and pausing (see report.py's scoring
# formulas) so tests can force those communication categories into the
# Practice Plan's weak-candidate pool without depending on the mock
# evaluator's fuzzy scoring.
BAD_SPEECH_METRICS = {
    "duration_seconds": 60,
    "words_per_minute": 260,
    "pause_count": 8,
    "long_pause_count": 5,
    "filler_word_count": 20,
    "filler_words": {"um": 20},
    "repeated_word_count": 0,
    "transcript_word_count": 80,
    "transcript_available": True,
}

BAD_CAMERA_METRICS = {
    "face_visible_percentage": 20,
    "camera_attention_percentage": 15,
    "head_movement_score": 90,
}


class DashboardStatsTestCase(unittest.TestCase):
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

    def _signup(self, email="dana@example.com"):
        response = self.client.post(
            "/api/auth/signup",
            json={"name": "Dana", "email": email, "password": "supersecret1"},
        )
        return response.json()["access_token"]

    def _dashboard(self, token):
        return self.client.get("/api/dashboard/", headers=self._auth_headers(token)).json()

    def _create_and_complete_interview(
        self, token, *, question_count=1, speech_metrics=None, camera_metrics=None, focus_categories=None
    ):
        payload = {"role": "Software Engineer", "difficulty": "easy", "question_count": question_count}
        if focus_categories is not None:
            payload["focus_categories"] = focus_categories
        created = self.client.post(
            "/api/interviews/",
            json=payload,
            headers=self._auth_headers(token),
        )
        interview_id = created.json()["id"]
        answer_ids = []
        for question in created.json()["questions"]:
            payload = {"text": "A reasonably detailed answer with some real content in it."}
            if speech_metrics is not None:
                payload["speech_metrics"] = speech_metrics
            answered = self.client.post(
                f"/api/interviews/{interview_id}/questions/{question['id']}/answer",
                json=payload,
                headers=self._auth_headers(token),
            )
            answer_ids.append(answered.json()["id"])

        complete_payload = {"camera_metrics": camera_metrics} if camera_metrics is not None else {}
        self.client.post(
            f"/api/interviews/{interview_id}/complete",
            json=complete_payload,
            headers=self._auth_headers(token),
        )
        return interview_id, answer_ids

    def _force_category_score(self, answer_id: int, category: str, label: str, score: int):
        """Directly sets one answer's rubric category score, bypassing the
        mock evaluator's fuzzy text-based scoring, so recurring-category
        assertions are deterministic (mirrors _force_score in
        test_adaptive_interview.py, at category rather than total-score
        granularity)."""
        db = self.TestingSessionLocal()
        try:
            answer = db.get(Answer, answer_id)
            answer.evaluation = {
                "category_scores": [{"category": category, "label": label, "score": score, "max_score": 100}]
            }
            db.commit()
        finally:
            db.close()

    def test_zero_interviews_returns_graceful_empty_defaults(self):
        token = self._signup()
        data = self._dashboard(token)

        self.assertEqual(data["overview"]["total_interviews"], 0)
        self.assertIsNone(data["scores"]["overall_score"])
        self.assertIsNone(data["scores"]["technical_score"])
        self.assertIsNone(data["scores"]["communication_score"])
        self.assertIsNone(data["scores"]["presentation_score"])
        self.assertEqual(data["communication_progress"], [])
        self.assertEqual(data["recurring_strengths"], [])
        self.assertEqual(data["recurring_weaknesses"], [])
        self.assertEqual(data["recommendations"], [])

    def test_single_interview_without_communication_data_falls_back_to_technical_only(self):
        token = self._signup()
        self._create_and_complete_interview(token, question_count=1)

        data = self._dashboard(token)
        self.assertEqual(data["overview"]["total_interviews"], 1)
        self.assertIsNotNone(data["scores"]["technical_score"])
        self.assertIsNone(data["scores"]["communication_score"])
        self.assertIsNone(data["scores"]["presentation_score"])
        self.assertEqual(data["communication_progress"], [])
        # No communication data anywhere -> overall falls back to technical-only.
        self.assertEqual(data["scores"]["overall_score"], round(data["scores"]["technical_score"]))

    def test_communication_and_presentation_scores_appear_when_data_collected(self):
        token = self._signup()
        self._create_and_complete_interview(
            token, question_count=1, speech_metrics=SPEECH_METRICS, camera_metrics=CAMERA_METRICS
        )

        data = self._dashboard(token)
        scores = data["scores"]
        self.assertIsNotNone(scores["communication_score"])
        self.assertIsNotNone(scores["presentation_score"])
        self.assertEqual(len(data["communication_progress"]), 1)

        expected_overall = round(scores["technical_score"] * 0.7 + scores["communication_score"] * 0.3)
        self.assertEqual(scores["overall_score"], expected_overall)

    def test_communication_progress_only_includes_interviews_with_communication_data(self):
        token = self._signup()
        self._create_and_complete_interview(token, question_count=1)
        self._create_and_complete_interview(
            token, question_count=1, speech_metrics=SPEECH_METRICS, camera_metrics=CAMERA_METRICS
        )

        data = self._dashboard(token)
        self.assertEqual(len(data["progress"]), 2)
        self.assertEqual(len(data["communication_progress"]), 1)

    def test_recurring_strength_and_weakness_reflect_forced_category_scores(self):
        # Interview creation only ever pre-generates the first question (see
        # test_interview_flow.test_only_first_question_generated_at_creation)
        # — the plain POST /answer endpoint never generates a second one, so
        # each interview here contributes exactly one forced category score.
        token = self._signup()
        _, structure_1 = self._create_and_complete_interview(token, question_count=1)
        _, structure_2 = self._create_and_complete_interview(token, question_count=1)
        _, clarity_1 = self._create_and_complete_interview(token, question_count=1)
        _, clarity_2 = self._create_and_complete_interview(token, question_count=1)

        # "Structure" consistently weak, "Clarity" consistently strong,
        # across four different interviews.
        self._force_category_score(structure_1[0], "structure", "Structure", 20)
        self._force_category_score(structure_2[0], "structure", "Structure", 25)
        self._force_category_score(clarity_1[0], "clarity", "Clarity", 92)
        self._force_category_score(clarity_2[0], "clarity", "Clarity", 95)

        data = self._dashboard(token)
        strengths_text = " ".join(data["recurring_strengths"])
        weaknesses_text = " ".join(data["recurring_weaknesses"])

        self.assertIn("Clarity", strengths_text)
        self.assertIn("Structure", weaknesses_text)
        self.assertNotIn("Structure", strengths_text)
        self.assertNotIn("Clarity", weaknesses_text)

    def test_weak_categories_matches_recurring_weaknesses_and_is_structured(self):
        # weak_categories (app.schemas.dashboard.DashboardRead) is the
        # structured, machine-usable counterpart to recurring_weaknesses'
        # prose strings — same qualifying categories, but with the raw
        # category key/label/score/sample_count the frontend's "Practice
        # weak areas" CTA feeds straight into
        # InterviewCreate.focus_categories.
        token = self._signup()
        _, structure_1 = self._create_and_complete_interview(token, question_count=1)
        _, structure_2 = self._create_and_complete_interview(token, question_count=1)
        _, clarity_1 = self._create_and_complete_interview(token, question_count=1)
        _, clarity_2 = self._create_and_complete_interview(token, question_count=1)

        self._force_category_score(structure_1[0], "structure", "Structure", 20)
        self._force_category_score(structure_2[0], "structure", "Structure", 25)
        self._force_category_score(clarity_1[0], "clarity", "Clarity", 92)
        self._force_category_score(clarity_2[0], "clarity", "Clarity", 95)

        data = self._dashboard(token)
        weak_keys = [c["category"] for c in data["weak_categories"]]
        self.assertIn("structure", weak_keys)
        self.assertNotIn("clarity", weak_keys)
        structure_entry = next(c for c in data["weak_categories"] if c["category"] == "structure")
        self.assertEqual(structure_entry["label"], "Structure")
        self.assertEqual(structure_entry["sample_count"], 2)

    def test_weak_categories_capped_at_three_ranked_weakest_first(self):
        token = self._signup()
        categories = [
            ("relevance", "Relevance", 10),
            ("structure", "Structure", 15),
            ("specificity", "Specificity / Examples", 20),
            ("communication", "Communication", 25),
        ]
        for key, label, score in categories:
            for _ in range(2):
                _, answers = self._create_and_complete_interview(token, question_count=1)
                self._force_category_score(answers[0], key, label, score)

        data = self._dashboard(token)
        self.assertEqual(len(data["weak_categories"]), 3)
        self.assertEqual(
            [c["category"] for c in data["weak_categories"]],
            ["relevance", "structure", "specificity"],
        )

    def test_weak_categories_empty_when_nothing_qualifies(self):
        token = self._signup()
        data = self._dashboard(token)
        self.assertEqual(data["weak_categories"], [])

    def test_recommendation_calls_out_the_weakest_recurring_category(self):
        token = self._signup()
        _, answers_1 = self._create_and_complete_interview(token, question_count=1)
        _, answers_2 = self._create_and_complete_interview(token, question_count=1)

        self._force_category_score(answers_1[0], "specificity", "Specificity / Examples", 15)
        self._force_category_score(answers_2[0], "specificity", "Specificity / Examples", 10)

        data = self._dashboard(token)
        self.assertTrue(len(data["recommendations"]) >= 1)
        self.assertTrue(any("Specificity" in rec for rec in data["recommendations"]))

    def test_a_single_low_sample_category_is_not_called_recurring(self):
        # MIN_CATEGORY_SAMPLES=2 — one weak answer alone isn't a "pattern".
        token = self._signup()
        _, answers = self._create_and_complete_interview(token, question_count=1)
        self._force_category_score(answers[0], "reasoning", "Reasoning / Problem Solving", 5)

        data = self._dashboard(token)
        self.assertEqual(data["recurring_weaknesses"], [])

    def test_dashboard_requires_auth(self):
        response = self.client.get("/api/dashboard/")
        self.assertEqual(response.status_code, 401)

    # --- Practice Plan (app.crud.dashboard._build_practice_plan) ---

    def test_practice_plan_not_ready_with_zero_interviews(self):
        token = self._signup()
        data = self._dashboard(token)

        self.assertFalse(data["practice_plan"]["ready"])
        self.assertEqual(data["practice_plan"]["areas"], [])
        self.assertIsNotNone(data["practice_plan"]["message"])

    def test_practice_plan_not_ready_with_only_one_interview(self):
        # A single interview can't establish a "recurring" pattern even if
        # it has enough scored answers in one category — MIN_PLAN_INTERVIEWS
        # gates on interview count, not just per-category sample count.
        token = self._signup()
        _, answers = self._create_and_complete_interview(token, question_count=1)
        self._force_category_score(answers[0], "structure", "Structure", 10)

        data = self._dashboard(token)
        self.assertFalse(data["practice_plan"]["ready"])
        self.assertEqual(data["practice_plan"]["areas"], [])

    def test_practice_plan_ready_but_empty_when_no_weak_area_qualifies(self):
        token = self._signup()
        _, answers_1 = self._create_and_complete_interview(token, question_count=1)
        _, answers_2 = self._create_and_complete_interview(token, question_count=1)
        self._force_category_score(answers_1[0], "clarity", "Clarity", 95)
        self._force_category_score(answers_2[0], "clarity", "Clarity", 92)

        data = self._dashboard(token)
        plan = data["practice_plan"]
        self.assertTrue(plan["ready"])
        self.assertEqual(plan["areas"], [])
        self.assertIsNotNone(plan["message"])

    def test_practice_plan_surfaces_recurring_technical_weakness_with_trend(self):
        token = self._signup()
        _, answers_1 = self._create_and_complete_interview(token, question_count=1)
        _, answers_2 = self._create_and_complete_interview(token, question_count=1)
        self._force_category_score(answers_1[0], "structure", "Structure", 20)
        self._force_category_score(answers_2[0], "structure", "Structure", 25)

        data = self._dashboard(token)
        plan = data["practice_plan"]
        self.assertTrue(plan["ready"])
        self.assertEqual(len(plan["areas"]), 1)

        area = plan["areas"][0]
        self.assertEqual(area["area"], "technical")
        self.assertEqual(area["category"], "structure")
        self.assertEqual(area["label"], "Structure")
        self.assertEqual(area["severity"], "high")
        self.assertIn("22.5%", area["reason"])
        self.assertIn("Situation-Task-Action-Result", area["reason"])
        self.assertTrue(len(area["action"]) > 0)
        self.assertEqual(len(area["trend"]), 2)
        self.assertEqual([p["score"] for p in area["trend"]], [20.0, 25.0])

    def test_practice_plan_surfaces_communication_and_presentation_weaknesses(self):
        token = self._signup()
        self._create_and_complete_interview(
            token, question_count=1, speech_metrics=BAD_SPEECH_METRICS, camera_metrics=BAD_CAMERA_METRICS
        )
        self._create_and_complete_interview(
            token, question_count=1, speech_metrics=BAD_SPEECH_METRICS, camera_metrics=BAD_CAMERA_METRICS
        )

        data = self._dashboard(token)
        plan = data["practice_plan"]
        self.assertTrue(plan["ready"])
        self.assertGreater(len(plan["areas"]), 0)

        area_types = {a["area"] for a in plan["areas"]}
        # The forced metrics tank pace, fillers, pausing, and presentation
        # all at once, so the top-3 cap means only some of them make the
        # cut — just assert at least one delivery-side area (as opposed to
        # a rubric/"technical" area, since no answers were ever scored)
        # surfaced, with well-formed reason/action/trend fields.
        self.assertTrue(area_types & {"communication", "presentation"})
        self.assertNotIn("technical", area_types)
        for area in plan["areas"]:
            self.assertGreater(len(area["reason"]), 0)
            self.assertGreater(len(area["action"]), 0)
            self.assertEqual(len(area["trend"]), 2)

    def test_practice_plan_capped_at_three_areas_worst_first(self):
        token = self._signup()
        categories = [
            ("relevance", "Relevance", 5),
            ("structure", "Structure", 10),
            ("specificity", "Specificity / Examples", 15),
            ("communication", "Communication", 20),
        ]
        for key, label, score in categories:
            for _ in range(2):
                _, answers = self._create_and_complete_interview(token, question_count=1)
                self._force_category_score(answers[0], key, label, score)

        data = self._dashboard(token)
        plan = data["practice_plan"]
        self.assertEqual(len(plan["areas"]), 3)
        self.assertEqual(
            [a["category"] for a in plan["areas"]],
            ["relevance", "structure", "specificity"],
        )
        scores = [a["score"] for a in plan["areas"]]
        self.assertEqual(scores, sorted(scores))

    def test_practice_plan_excludes_category_with_insufficient_samples(self):
        # Mirrors test_a_single_low_sample_category_is_not_called_recurring
        # above, for the Practice Plan: MIN_CATEGORY_SAMPLES=2 applies here
        # too, so a category scored in only one interview never qualifies.
        token = self._signup()
        _, answers_1 = self._create_and_complete_interview(token, question_count=1)
        _, answers_2 = self._create_and_complete_interview(token, question_count=1)
        self._force_category_score(answers_1[0], "reasoning", "Reasoning / Problem Solving", 10)
        # Second interview only scores a *different* category, so
        # "reasoning" still only has one sample overall and shouldn't
        # qualify for the plan at all (MIN_CATEGORY_SAMPLES=2).
        self._force_category_score(answers_2[0], "examples", "Examples", 90)

        data = self._dashboard(token)
        plan = data["practice_plan"]
        self.assertNotIn("reasoning", [a["category"] for a in plan["areas"]])

    def test_practice_plan_action_matches_rubric_category_action_hint(self):
        from app.services.answer_evaluation.rubrics import CATEGORY_ACTIONS

        token = self._signup()
        _, answers_1 = self._create_and_complete_interview(token, question_count=1)
        _, answers_2 = self._create_and_complete_interview(token, question_count=1)
        self._force_category_score(answers_1[0], "reasoning", "Reasoning / Problem Solving", 10)
        self._force_category_score(answers_2[0], "reasoning", "Reasoning / Problem Solving", 12)

        data = self._dashboard(token)
        area = next(a for a in data["practice_plan"]["areas"] if a["category"] == "reasoning")
        self.assertEqual(area["action"], CATEGORY_ACTIONS["reasoning"])

    def test_practice_plan_severity_drops_as_weakness_improves(self):
        # Same category, three interviews, clearly trending upward. The
        # per-interview trend must show the raw improvement even though the
        # category's overall average (which drives ranking/severity) is
        # still pulled down by the earlier weak interviews — i.e. an
        # improving weakness is reflected in the data, and its severity
        # eases from "high" toward "medium" as the average rises, without
        # the app pretending the early low scores never happened.
        token = self._signup()
        _, a1 = self._create_and_complete_interview(token, question_count=1)
        _, a2 = self._create_and_complete_interview(token, question_count=1)
        _, a3 = self._create_and_complete_interview(token, question_count=1)
        self._force_category_score(a1[0], "structure", "Structure", 20)
        self._force_category_score(a2[0], "structure", "Structure", 25)
        self._force_category_score(a3[0], "structure", "Structure", 85)

        data = self._dashboard(token)
        area = next(a for a in data["practice_plan"]["areas"] if a["category"] == "structure")

        self.assertEqual([p["score"] for p in area["trend"]], [20.0, 25.0, 85.0])
        # Average is (20+25+85)/3 = 43.3 -> above WEAK_RATIO*100 (40), so no
        # longer "high" severity, even though it started there.
        self.assertAlmostEqual(area["score"], 43.3, places=1)
        self.assertEqual(area["severity"], "medium")

    def test_practice_plan_stays_high_severity_when_weakness_persists(self):
        # Same category, three interviews, consistently low with no
        # improvement — severity must stay "high" and the area must keep
        # surfacing rather than fading out on its own.
        token = self._signup()
        _, a1 = self._create_and_complete_interview(token, question_count=1)
        _, a2 = self._create_and_complete_interview(token, question_count=1)
        _, a3 = self._create_and_complete_interview(token, question_count=1)
        self._force_category_score(a1[0], "structure", "Structure", 20)
        self._force_category_score(a2[0], "structure", "Structure", 18)
        self._force_category_score(a3[0], "structure", "Structure", 22)

        data = self._dashboard(token)
        area = next(a for a in data["practice_plan"]["areas"] if a["category"] == "structure")

        self.assertEqual([p["score"] for p in area["trend"]], [20.0, 18.0, 22.0])
        self.assertEqual(area["severity"], "high")

    def test_practice_plan_is_isolated_per_user(self):
        # One user's forced weak category must never leak into another
        # user's practice plan, and each user's plan must only reflect
        # their own interview history.
        token_a = self._signup(email="plan-a@example.com")
        token_b = self._signup(email="plan-b@example.com")

        _, a1 = self._create_and_complete_interview(token_a, question_count=1)
        _, a2 = self._create_and_complete_interview(token_a, question_count=1)
        self._force_category_score(a1[0], "structure", "Structure", 15)
        self._force_category_score(a2[0], "structure", "Structure", 18)

        data_a = self._dashboard(token_a)
        data_b = self._dashboard(token_b)

        self.assertTrue(data_a["practice_plan"]["ready"])
        self.assertIn("structure", [area["category"] for area in data_a["practice_plan"]["areas"]])

        # User B has no interviews at all -> plan isn't ready, and certainly
        # doesn't contain user A's weak category.
        self.assertFalse(data_b["practice_plan"]["ready"])
        self.assertEqual(data_b["practice_plan"]["areas"], [])

    # --- Practice progress: did a targeted session (Interview.focus_categories)
    # actually happen, and did it move the score? (app.crud.dashboard.
    # _compute_practice_progress) ---

    def test_practice_progress_none_when_no_targeted_session_ever_happened(self):
        # Two qualifying interviews, neither ever set focus_categories ->
        # nothing to report, must not fabricate a practice signal.
        token = self._signup()
        _, a1 = self._create_and_complete_interview(token, question_count=1)
        _, a2 = self._create_and_complete_interview(token, question_count=1)
        self._force_category_score(a1[0], "structure", "Structure", 20)
        self._force_category_score(a2[0], "structure", "Structure", 25)

        data = self._dashboard(token)
        area = next(a for a in data["practice_plan"]["areas"] if a["category"] == "structure")
        self.assertIsNone(area["practice_progress"])

    def test_practice_progress_ignores_interview_targeting_a_different_category(self):
        # The one interview with focus_categories targets "relevance", not
        # "structure" -> structure's practice_progress must stay None even
        # though a targeted session happened elsewhere.
        token = self._signup()
        _, a1 = self._create_and_complete_interview(
            token, question_count=1, focus_categories=["relevance"]
        )
        _, a2 = self._create_and_complete_interview(token, question_count=1)
        self._force_category_score(a1[0], "structure", "Structure", 20)
        self._force_category_score(a2[0], "structure", "Structure", 25)

        data = self._dashboard(token)
        area = next(a for a in data["practice_plan"]["areas"] if a["category"] == "structure")
        self.assertIsNone(area["practice_progress"])

    def test_practice_progress_insufficient_data_when_no_baseline_before_the_session(self):
        # The targeted session is the *first* time "structure" was ever
        # scored -> there's no pre-practice baseline to compare against, so
        # this must be "insufficient_data", never a guessed result.
        token = self._signup()
        _, a1 = self._create_and_complete_interview(
            token, question_count=1, focus_categories=["structure"]
        )
        _, a2 = self._create_and_complete_interview(token, question_count=1)
        self._force_category_score(a1[0], "structure", "Structure", 20)
        self._force_category_score(a2[0], "structure", "Structure", 25)

        data = self._dashboard(token)
        area = next(a for a in data["practice_plan"]["areas"] if a["category"] == "structure")
        progress = area["practice_progress"]
        self.assertIsNotNone(progress)
        self.assertEqual(progress["status"], "insufficient_data")
        self.assertEqual(progress["session_count"], 1)
        self.assertIsNone(progress["before_avg"])
        self.assertIsNone(progress["after_avg"])
        self.assertIsNotNone(progress["last_practiced_at"])

    def test_practice_progress_improved_when_post_session_average_clears_margin(self):
        token = self._signup()
        _, a1 = self._create_and_complete_interview(token, question_count=1)
        _, a2 = self._create_and_complete_interview(token, question_count=1)
        _, a3 = self._create_and_complete_interview(
            token, question_count=1, focus_categories=["structure"]
        )
        self._force_category_score(a1[0], "structure", "Structure", 20)
        self._force_category_score(a2[0], "structure", "Structure", 25)
        self._force_category_score(a3[0], "structure", "Structure", 90)

        data = self._dashboard(token)
        area = next(a for a in data["practice_plan"]["areas"] if a["category"] == "structure")
        progress = area["practice_progress"]
        self.assertEqual(progress["status"], "improved")
        self.assertEqual(progress["session_count"], 1)
        self.assertAlmostEqual(progress["before_avg"], 22.5, places=1)
        self.assertAlmostEqual(progress["after_avg"], 90.0, places=1)

    def test_practice_progress_practiced_when_improvement_does_not_clear_margin(self):
        # A small bump (4 points) that doesn't clear PRACTICE_IMPROVEMENT_MARGIN
        # (8) -> "practiced", not "improved" and not "insufficient_data": we
        # have real before/after data, we just don't claim a result it
        # doesn't support.
        token = self._signup()
        _, a1 = self._create_and_complete_interview(token, question_count=1)
        _, a2 = self._create_and_complete_interview(
            token, question_count=1, focus_categories=["structure"]
        )
        self._force_category_score(a1[0], "structure", "Structure", 20)
        self._force_category_score(a2[0], "structure", "Structure", 24)

        data = self._dashboard(token)
        area = next(a for a in data["practice_plan"]["areas"] if a["category"] == "structure")
        progress = area["practice_progress"]
        self.assertEqual(progress["status"], "practiced")
        self.assertAlmostEqual(progress["before_avg"], 20.0, places=1)
        self.assertAlmostEqual(progress["after_avg"], 24.0, places=1)

    def test_practice_progress_counts_every_targeted_session(self):
        token = self._signup()
        _, a1 = self._create_and_complete_interview(token, question_count=1)
        _, a2 = self._create_and_complete_interview(
            token, question_count=1, focus_categories=["structure"]
        )
        _, a3 = self._create_and_complete_interview(
            token, question_count=1, focus_categories=["structure"]
        )
        self._force_category_score(a1[0], "structure", "Structure", 20)
        self._force_category_score(a2[0], "structure", "Structure", 22)
        self._force_category_score(a3[0], "structure", "Structure", 30)

        data = self._dashboard(token)
        area = next(a for a in data["practice_plan"]["areas"] if a["category"] == "structure")
        self.assertEqual(area["practice_progress"]["session_count"], 2)

    def test_practice_progress_isolated_per_user(self):
        # User A's targeted practice session for "structure" must never
        # surface on user B's plan.
        token_a = self._signup(email="progress-a@example.com")
        token_b = self._signup(email="progress-b@example.com")

        _, a1 = self._create_and_complete_interview(token_a, question_count=1)
        _, a2 = self._create_and_complete_interview(
            token_a, question_count=1, focus_categories=["structure"]
        )
        self._force_category_score(a1[0], "structure", "Structure", 20)
        self._force_category_score(a2[0], "structure", "Structure", 22)

        _, b1 = self._create_and_complete_interview(token_b, question_count=1)
        _, b2 = self._create_and_complete_interview(token_b, question_count=1)
        self._force_category_score(b1[0], "structure", "Structure", 15)
        self._force_category_score(b2[0], "structure", "Structure", 18)

        data_b = self._dashboard(token_b)
        area_b = next(a for a in data_b["practice_plan"]["areas"] if a["category"] == "structure")
        self.assertIsNone(area_b["practice_progress"])


if __name__ == "__main__":
    unittest.main()
