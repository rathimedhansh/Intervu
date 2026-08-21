"""Tests for the opt-in Communication & Presentation Analysis feature:
schema validation bounds, deterministic feedback thresholds, an ethical
regression guard on feedback copy, and CRUD persistence/non-interference
with the existing interview flow.

Uses stdlib unittest only, matching test_answer_evaluation.py.

Run from backend/: venv/Scripts/python.exe -m unittest discover -s tests -v
"""

import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.crud.answer import submit_answer
from app.crud.interview import complete_interview
from app.db.base import Base
from app.models.answer import Answer
from app.models.interview import Interview
from app.models.question import Question
from app.schemas.answer import AnswerRead, SpeechMetricsIn
from app.schemas.interview import CameraMetricsIn, InterviewRead
from app.services.communication_feedback import (
    build_camera_feedback,
    build_communication_report,
    build_speech_feedback,
    estimate_disfluencies,
)

FORBIDDEN_TERMS = [
    "stutter",
    "diagnos",
    "confiden",
    "emotion",
    "honest",
    "personality",
    "attractive",
    "nervous",
    "stress",
]


class TestSpeechMetricsValidation(unittest.TestCase):
    def test_valid_metrics_accepted(self):
        metrics = SpeechMetricsIn(
            duration_seconds=42.5,
            words_per_minute=135,
            pause_count=2,
            long_pause_count=0,
            filler_word_count=1,
            filler_words={"um": 1},
            repeated_word_count=0,
            transcript_word_count=95,
            transcript_available=True,
        )
        self.assertEqual(metrics.duration_seconds, 42.5)

    def test_only_duration_required(self):
        metrics = SpeechMetricsIn(duration_seconds=10)
        self.assertFalse(metrics.transcript_available)
        self.assertEqual(metrics.filler_words, {})

    def test_negative_duration_rejected(self):
        with self.assertRaises(ValidationError):
            SpeechMetricsIn(duration_seconds=-1)

    def test_wpm_out_of_range_rejected(self):
        with self.assertRaises(ValidationError):
            SpeechMetricsIn(duration_seconds=10, words_per_minute=5000)

    def test_transcript_confidence_defaults_to_none(self):
        metrics = SpeechMetricsIn(duration_seconds=10)
        self.assertIsNone(metrics.transcript_confidence)

    def test_transcript_confidence_accepted_in_range(self):
        metrics = SpeechMetricsIn(duration_seconds=10, transcript_confidence=0.87)
        self.assertEqual(metrics.transcript_confidence, 0.87)

    def test_transcript_confidence_out_of_range_rejected(self):
        with self.assertRaises(ValidationError):
            SpeechMetricsIn(duration_seconds=10, transcript_confidence=1.5)


class TestCameraMetricsValidation(unittest.TestCase):
    def test_valid_metrics_accepted(self):
        metrics = CameraMetricsIn(
            face_visible_percentage=88.5,
            camera_attention_percentage=72.0,
            head_movement_score=30.0,
        )
        self.assertEqual(metrics.face_visible_percentage, 88.5)

    def test_percentage_over_100_rejected(self):
        with self.assertRaises(ValidationError):
            CameraMetricsIn(
                face_visible_percentage=150,
                camera_attention_percentage=50,
                head_movement_score=10,
            )

    def test_negative_rejected(self):
        with self.assertRaises(ValidationError):
            CameraMetricsIn(
                face_visible_percentage=50,
                camera_attention_percentage=-5,
                head_movement_score=10,
            )

    def test_look_away_and_multi_face_default_to_none(self):
        metrics = CameraMetricsIn(
            face_visible_percentage=80, camera_attention_percentage=70, head_movement_score=20
        )
        self.assertIsNone(metrics.look_away_count)
        self.assertIsNone(metrics.multiple_faces_percentage)

    def test_look_away_and_multi_face_accepted(self):
        metrics = CameraMetricsIn(
            face_visible_percentage=80,
            camera_attention_percentage=70,
            head_movement_score=20,
            look_away_count=5,
            multiple_faces_percentage=2.5,
        )
        self.assertEqual(metrics.look_away_count, 5)
        self.assertEqual(metrics.multiple_faces_percentage, 2.5)


class TestSpeechFeedback(unittest.TestCase):
    def _metrics(self, **overrides):
        base = {
            "transcript_available": True,
            "words_per_minute": 135,
            "transcript_word_count": 100,
            "filler_word_count": 1,
            "pause_count": 1,
            "long_pause_count": 0,
            "repeated_word_count": 0,
        }
        base.update(overrides)
        return base

    def test_nothing_notable_returns_empty(self):
        self.assertEqual(build_speech_feedback(self._metrics()), [])

    def test_fast_pace_flagged(self):
        feedback = build_speech_feedback(self._metrics(words_per_minute=200))
        self.assertTrue(any("fast" in f for f in feedback))

    def test_slow_pace_flagged(self):
        feedback = build_speech_feedback(self._metrics(words_per_minute=80))
        self.assertTrue(any("slow" in f for f in feedback))

    def test_pace_ignored_when_transcript_unavailable(self):
        feedback = build_speech_feedback(
            self._metrics(transcript_available=False, words_per_minute=200)
        )
        self.assertEqual(feedback, [])

    def test_high_filler_ratio_flagged(self):
        feedback = build_speech_feedback(
            self._metrics(filler_word_count=10, transcript_word_count=100)
        )
        self.assertTrue(any("filler" in f for f in feedback))

    def test_long_pause_flagged(self):
        feedback = build_speech_feedback(self._metrics(long_pause_count=3))
        self.assertTrue(any("long pauses" in f for f in feedback))

    def test_many_short_pauses_flagged(self):
        feedback = build_speech_feedback(self._metrics(pause_count=8))
        self.assertTrue(any("pauses" in f for f in feedback))

    def test_repeated_words_flagged(self):
        feedback = build_speech_feedback(self._metrics(repeated_word_count=4))
        self.assertTrue(any("repeated" in f for f in feedback))

    def test_brief_answer_flagged(self):
        feedback = build_speech_feedback(self._metrics(transcript_word_count=5))
        self.assertTrue(any("brief" in f for f in feedback))

    def test_brief_answer_ignored_when_transcript_unavailable(self):
        feedback = build_speech_feedback(
            self._metrics(transcript_available=False, transcript_word_count=5)
        )
        self.assertEqual(feedback, [])

    def test_long_answer_flagged(self):
        feedback = build_speech_feedback(self._metrics(duration_seconds=300))
        self.assertTrue(any("long" in f for f in feedback))

    def test_missing_duration_does_not_crash_or_flag(self):
        # duration_seconds is absent from the base fixture entirely (not
        # just None) — build_speech_feedback must tolerate that.
        feedback = build_speech_feedback(self._metrics())
        self.assertEqual(feedback, [])

    def test_feedback_never_contains_forbidden_terms(self):
        extreme = self._metrics(
            words_per_minute=250,
            filler_word_count=50,
            long_pause_count=10,
            pause_count=10,
            repeated_word_count=10,
            transcript_word_count=5,
            duration_seconds=300,
        )
        feedback = build_speech_feedback(extreme)
        self.assertTrue(feedback)  # sanity: this case should trigger comments
        joined = " ".join(feedback).lower()
        for term in FORBIDDEN_TERMS:
            self.assertNotIn(term, joined, f"forbidden term '{term}' found in speech feedback")


class TestCameraFeedback(unittest.TestCase):
    def _metrics(self, **overrides):
        base = {
            "face_visible_percentage": 90,
            "camera_attention_percentage": 85,
            "head_movement_score": 20,
        }
        base.update(overrides)
        return base

    def test_nothing_notable_returns_empty(self):
        self.assertEqual(build_camera_feedback(self._metrics()), [])

    def test_low_face_visibility_flagged(self):
        feedback = build_camera_feedback(self._metrics(face_visible_percentage=40))
        self.assertTrue(any("frame" in f for f in feedback))

    def test_low_attention_flagged(self):
        feedback = build_camera_feedback(self._metrics(camera_attention_percentage=30))
        self.assertTrue(any("looked away" in f for f in feedback))

    def test_high_head_movement_flagged(self):
        feedback = build_camera_feedback(self._metrics(head_movement_score=95))
        self.assertTrue(any("head movement" in f for f in feedback))

    def test_frequent_look_away_flagged(self):
        feedback = build_camera_feedback(self._metrics(look_away_count=12))
        self.assertTrue(any("looked away" in f for f in feedback))

    def test_look_away_ignored_when_absent(self):
        feedback = build_camera_feedback(self._metrics())
        self.assertEqual(feedback, [])

    def test_multiple_faces_flagged(self):
        feedback = build_camera_feedback(self._metrics(multiple_faces_percentage=15))
        self.assertTrue(any("more than one face" in f.lower() for f in feedback))

    def test_feedback_never_contains_forbidden_terms(self):
        extreme = self._metrics(
            face_visible_percentage=10,
            camera_attention_percentage=5,
            head_movement_score=100,
            look_away_count=20,
            multiple_faces_percentage=50,
        )
        feedback = build_camera_feedback(extreme)
        self.assertTrue(feedback)
        joined = " ".join(feedback).lower()
        for term in FORBIDDEN_TERMS:
            self.assertNotIn(term, joined, f"forbidden term '{term}' found in camera feedback")


class TestCrudPersistence(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine)
        self.db = Session()

    def _make_interview_with_question(self):
        interview = Interview(role="Software Engineer", difficulty="medium", status="pending")
        self.db.add(interview)
        self.db.flush()
        question = Question(interview_id=interview.id, text="Tell me about yourself.", order_index=0)
        self.db.add(question)
        self.db.commit()
        self.db.refresh(question)
        return interview, question

    def test_submit_answer_persists_speech_metrics(self):
        _, question = self._make_interview_with_question()
        metrics = {"duration_seconds": 30, "words_per_minute": 120, "transcript_available": True}
        answer = submit_answer(self.db, question, "My answer.", metrics)
        self.assertEqual(answer.speech_metrics, metrics)

    def test_submit_answer_without_speech_metrics_defaults_to_none(self):
        _, question = self._make_interview_with_question()
        answer = submit_answer(self.db, question, "My answer.")
        self.assertIsNone(answer.speech_metrics)

    def test_complete_interview_persists_camera_metrics(self):
        interview, question = self._make_interview_with_question()
        submit_answer(self.db, question, "My answer.")
        metrics = {"face_visible_percentage": 80, "camera_attention_percentage": 70, "head_movement_score": 15}
        completed = complete_interview(self.db, interview, metrics)
        self.assertEqual(completed.camera_metrics, metrics)

    def test_complete_interview_without_metrics_leaves_scoring_intact(self):
        """Regression guard: completing an interview with no camera_metrics
        (the pre-existing call path) must still score answers exactly as
        before this feature was added."""
        interview, question = self._make_interview_with_question()
        submit_answer(self.db, question, "I resolved a disagreement by listening first.")
        completed = complete_interview(self.db, interview)
        self.assertIsNone(completed.camera_metrics)
        self.assertEqual(completed.status, "completed")
        self.assertIsNotNone(completed.overall_score)
        self.assertIsNotNone(completed.questions[0].answer.total_score)


class TestStutterHeuristic(unittest.TestCase):
    def test_clean_text_has_no_repetitions(self):
        result = estimate_disfluencies(
            "I built a scalable backend service using Python and FastAPI."
        )
        self.assertEqual(result["total_estimated_repetitions"], 0)
        self.assertEqual(result["repeated_examples"], [])

    def test_repeated_single_word_detected(self):
        result = estimate_disfluencies("I I think the design is solid.")
        self.assertEqual(result["repeated_word_count"], 1)
        self.assertEqual(result["repeated_phrase_count"], 0)
        self.assertIn("i i", result["repeated_examples"])

    def test_repeated_phrase_detected_once_not_double_counted(self):
        result = estimate_disfluencies("I think I think this approach works well.")
        self.assertEqual(result["repeated_phrase_count"], 1)
        self.assertEqual(result["repeated_word_count"], 0)
        self.assertEqual(result["total_estimated_repetitions"], 1)

    def test_case_and_punctuation_are_normalized(self):
        result = estimate_disfluencies("Well, well, I mean it.")
        self.assertEqual(result["repeated_word_count"], 1)

    def test_empty_text_returns_zero(self):
        result = estimate_disfluencies("")
        self.assertEqual(result["total_estimated_repetitions"], 0)

    def test_examples_capped(self):
        text = " ".join(f"the the word{i} word{i}" for i in range(20))
        result = estimate_disfluencies(text)
        self.assertLessEqual(len(result["repeated_examples"]), 5)


class TestCommunicationReport(unittest.TestCase):
    def _speech_entry(self, **overrides):
        base = {
            "duration_seconds": 40,
            "words_per_minute": 140,
            "pause_count": 2,
            "long_pause_count": 0,
            "filler_word_count": 2,
            "filler_words": {"um": 2},
            "repeated_word_count": 0,
            "transcript_word_count": 90,
            "transcript_available": True,
        }
        base.update(overrides)
        return base

    def _repetition_entry(self, **overrides):
        base = {
            "repeated_word_count": 0,
            "repeated_phrase_count": 0,
            "repeated_examples": [],
            "total_estimated_repetitions": 0,
        }
        base.update(overrides)
        return base

    def test_no_data_returns_none(self):
        self.assertIsNone(build_communication_report([], [], None))

    def test_speech_only_report_has_no_presentation_category(self):
        report = build_communication_report(
            [self._speech_entry()], [self._repetition_entry()], None
        )
        self.assertIsNotNone(report)
        self.assertIsNone(report["camera_summary"])
        keys = {c["key"] for c in report["categories"]}
        self.assertEqual(keys, {"pace", "fillers", "fluency", "pausing"})
        self.assertTrue(0 <= report["overall_score"] <= 100)

    def test_camera_only_report_has_only_presentation_category(self):
        camera = {
            "face_visible_percentage": 90,
            "camera_attention_percentage": 80,
            "head_movement_score": 10,
        }
        report = build_communication_report([], [], camera)
        self.assertIsNotNone(report)
        self.assertIsNone(report["speech_summary"])
        self.assertEqual([c["key"] for c in report["categories"]], ["presentation"])

    def test_ideal_metrics_score_100(self):
        speech = self._speech_entry(
            words_per_minute=130, filler_word_count=0, filler_words={}, pause_count=1
        )
        camera = {
            "face_visible_percentage": 100,
            "camera_attention_percentage": 100,
            "head_movement_score": 0,
        }
        report = build_communication_report([speech], [self._repetition_entry()], camera)
        self.assertEqual(report["overall_score"], 100)

    def test_transcript_unavailable_entries_excluded_from_pace_and_fillers(self):
        speech = self._speech_entry(transcript_available=False, words_per_minute=None)
        report = build_communication_report([speech], [{}], None)
        self.assertIsNotNone(report)
        keys = {c["key"] for c in report["categories"]}
        # Pauses are amplitude-based (don't need a transcript); pace/fillers/
        # fluency do and must be omitted rather than guessed.
        self.assertEqual(keys, {"pausing"})

    def test_aggregates_across_multiple_answers(self):
        speech = [self._speech_entry(transcript_word_count=50), self._speech_entry(transcript_word_count=50)]
        repetitions = [self._repetition_entry(), self._repetition_entry()]
        report = build_communication_report(speech, repetitions, None)
        self.assertEqual(report["speech_summary"]["total_words_spoken"], 100)
        self.assertEqual(report["speech_summary"]["answers_measured"], 2)

    def test_extreme_metrics_narrative_never_mentions_forbidden_terms(self):
        speech = self._speech_entry(
            words_per_minute=260,
            pause_count=20,
            long_pause_count=10,
            filler_word_count=40,
            filler_words={"um": 40},
            transcript_word_count=80,
        )
        repetition = self._repetition_entry(
            repeated_word_count=10,
            repeated_phrase_count=5,
            repeated_examples=["i i", "you know you know"],
            total_estimated_repetitions=15,
        )
        camera = {
            "face_visible_percentage": 10,
            "camera_attention_percentage": 5,
            "head_movement_score": 100,
        }
        report = build_communication_report([speech], [repetition], camera)
        # The `note` field is a deliberate disclaimer and is expected to
        # name these concepts in order to disclaim them — only the
        # observation-facing text is held to the no-forbidden-terms bar.
        observational_text = " ".join(
            report["strengths"]
            + report["improvements"]
            + report["recommendations"]
            + [c["description"] for c in report["categories"]]
        ).lower()
        for term in FORBIDDEN_TERMS:
            self.assertNotIn(
                term, observational_text, f"forbidden term '{term}' found in communication report"
            )


class TestSchemaIntegration(unittest.TestCase):
    """Confirms the computed_field wiring on AnswerRead/InterviewRead
    (repetition_analysis, communication_report) actually activates end to
    end from ORM model instances, not just from the pure functions above."""

    def _speech_metrics(self, **overrides):
        base = {
            "duration_seconds": 30,
            "words_per_minute": 135,
            "pause_count": 1,
            "long_pause_count": 0,
            "filler_word_count": 1,
            "filler_words": {"um": 1},
            "repeated_word_count": 0,
            "transcript_word_count": 60,
            "transcript_available": True,
        }
        base.update(overrides)
        return base

    def test_repetition_analysis_computed_from_answer_text(self):
        answer = Answer(
            id=1,
            question_id=1,
            text="I I think this is a strong solution.",
            speech_metrics=self._speech_metrics(),
        )
        read = AnswerRead.model_validate(answer)
        self.assertIsNotNone(read.repetition_analysis)
        self.assertEqual(read.repetition_analysis.repeated_word_count, 1)

    def test_repetition_analysis_none_when_typed(self):
        answer = Answer(id=1, question_id=1, text="I I think this is fine.", speech_metrics=None)
        read = AnswerRead.model_validate(answer)
        self.assertIsNone(read.repetition_analysis)

    def test_interview_read_communication_report_end_to_end(self):
        interview = Interview(
            id=1,
            role="Software Engineer",
            difficulty="medium",
            status="completed",
            created_at=datetime.now(timezone.utc),
            camera_metrics={
                "face_visible_percentage": 90,
                "camera_attention_percentage": 85,
                "head_movement_score": 10,
            },
        )
        question = Question(
            id=1,
            interview_id=1,
            text="Tell me about yourself.",
            order_index=0,
            source="bank",
            is_followup=False,
        )
        question.answer = Answer(
            id=1, question_id=1, text="I have five years of experience.", speech_metrics=self._speech_metrics()
        )
        interview.questions = [question]

        read = InterviewRead.model_validate(interview)
        self.assertIsNotNone(read.communication_report)
        self.assertIsNotNone(read.communication_report.overall_score)
        self.assertTrue(len(read.communication_report.categories) > 0)

    def test_interview_read_communication_report_none_when_unopted(self):
        interview = Interview(
            id=1,
            role="Software Engineer",
            difficulty="medium",
            status="completed",
            created_at=datetime.now(timezone.utc),
        )
        question = Question(
            id=1,
            interview_id=1,
            text="Tell me about yourself.",
            order_index=0,
            source="bank",
            is_followup=False,
        )
        question.answer = Answer(id=1, question_id=1, text="I have five years of experience.")
        interview.questions = [question]

        read = InterviewRead.model_validate(interview)
        self.assertIsNone(read.communication_report)


if __name__ == "__main__":
    unittest.main()
