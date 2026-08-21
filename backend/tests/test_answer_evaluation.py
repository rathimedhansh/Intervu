"""Tests for app.services.answer_evaluation.

Uses stdlib unittest + unittest.mock only (no new dependency). The Anthropic
client is mocked throughout — these tests never make a real network call or
require a real API key.

Run from backend/: venv/Scripts/python.exe -m unittest discover -s tests -v
"""

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings
from app.services.answer_evaluation import evaluate_answer
from app.services.answer_evaluation import anthropic_provider, mock_provider, rubrics

QUESTION = "Tell me about a time you disagreed with a teammate."
ANSWER = "I raised my concerns in a 1:1, we compared tradeoffs, and agreed on a plan."
ROLE = "Software Engineer"
DIFFICULTY = "medium"

VALID_BEHAVIORAL_INPUT = {
    "relevance": 18,
    "clarity": 17,
    "structure": 16,
    "specificity": 15,
    "communication": 19,
    "strengths": ["Clear example", "Good structure"],
    "weaknesses": ["Could be more specific"],
    "improvement_suggestions": ["Quantify the outcome"],
    "stronger_answer_example": "A stronger answer would include a measurable result.",
}


def _tool_response(tool_input):
    return SimpleNamespace(
        content=[
            SimpleNamespace(type="tool_use", name=anthropic_provider.TOOL_NAME, input=tool_input)
        ]
    )


class SettingsOverrideTestCase(unittest.TestCase):
    """Saves/restores the handful of settings fields these tests mutate."""

    def setUp(self):
        self._original_provider = settings.ai_provider
        self._original_key = settings.anthropic_api_key

    def tearDown(self):
        settings.ai_provider = self._original_provider
        settings.anthropic_api_key = self._original_key


class TestSuccessfulAnthropicEvaluation(SettingsOverrideTestCase):
    def test_successful_evaluation_returns_anthropic_result(self):
        settings.anthropic_api_key = "fake-key-for-test"
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _tool_response(VALID_BEHAVIORAL_INPUT)

        with patch.object(anthropic_provider.anthropic, "Anthropic", return_value=mock_client):
            result = anthropic_provider.generate(
                QUESTION, ANSWER, ROLE, DIFFICULTY, question_type="behavioral"
            )

        self.assertEqual(result.evaluator, "anthropic")
        self.assertIsNone(result.note)
        expected_total = sum(
            VALID_BEHAVIORAL_INPUT[key] for key in rubrics.BEHAVIORAL_RUBRIC
        )
        self.assertEqual(result.total_score, expected_total)
        self.assertEqual(result.max_score, 100)
        self.assertEqual(len(result.category_scores), len(rubrics.BEHAVIORAL_RUBRIC))
        self.assertEqual(result.strengths, VALID_BEHAVIORAL_INPUT["strengths"])
        self.assertEqual(
            result.stronger_answer_example, VALID_BEHAVIORAL_INPUT["stronger_answer_example"]
        )


class TestInvalidAiResponse(SettingsOverrideTestCase):
    def test_out_of_range_score_falls_back_to_mock(self):
        settings.anthropic_api_key = "fake-key-for-test"
        bad_input = {**VALID_BEHAVIORAL_INPUT, "relevance": 999}
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _tool_response(bad_input)

        with patch.object(anthropic_provider.anthropic, "Anthropic", return_value=mock_client):
            result = anthropic_provider.generate(
                QUESTION, ANSWER, ROLE, DIFFICULTY, question_type="behavioral"
            )

        self.assertEqual(result.evaluator, "mock")
        self.assertIsNotNone(result.note)

    def test_missing_category_falls_back_to_mock(self):
        settings.anthropic_api_key = "fake-key-for-test"
        bad_input = dict(VALID_BEHAVIORAL_INPUT)
        del bad_input["clarity"]
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _tool_response(bad_input)

        with patch.object(anthropic_provider.anthropic, "Anthropic", return_value=mock_client):
            result = anthropic_provider.generate(
                QUESTION, ANSWER, ROLE, DIFFICULTY, question_type="behavioral"
            )

        self.assertEqual(result.evaluator, "mock")

    def test_wrong_type_falls_back_to_mock(self):
        settings.anthropic_api_key = "fake-key-for-test"
        bad_input = {**VALID_BEHAVIORAL_INPUT, "strengths": "not a list"}
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _tool_response(bad_input)

        with patch.object(anthropic_provider.anthropic, "Anthropic", return_value=mock_client):
            result = anthropic_provider.generate(
                QUESTION, ANSWER, ROLE, DIFFICULTY, question_type="behavioral"
            )

        self.assertEqual(result.evaluator, "mock")

    def test_no_tool_call_falls_back_to_mock(self):
        settings.anthropic_api_key = "fake-key-for-test"
        mock_client = MagicMock()
        mock_client.messages.create.return_value = SimpleNamespace(content=[])

        with patch.object(anthropic_provider.anthropic, "Anthropic", return_value=mock_client):
            result = anthropic_provider.generate(
                QUESTION, ANSWER, ROLE, DIFFICULTY, question_type="behavioral"
            )

        self.assertEqual(result.evaluator, "mock")


class TestApiFailure(SettingsOverrideTestCase):
    def test_network_exception_falls_back_to_mock(self):
        settings.anthropic_api_key = "fake-key-for-test"
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = RuntimeError("connection reset")

        with patch.object(anthropic_provider.anthropic, "Anthropic", return_value=mock_client):
            result = anthropic_provider.generate(
                QUESTION, ANSWER, ROLE, DIFFICULTY, question_type="behavioral"
            )

        self.assertEqual(result.evaluator, "mock")
        self.assertIsNotNone(result.note)


class TestMockFallbackWhenNoApiKey(SettingsOverrideTestCase):
    def test_no_api_key_never_calls_anthropic_sdk(self):
        settings.anthropic_api_key = ""

        with patch.object(anthropic_provider.anthropic, "Anthropic") as mock_ctor:
            result = anthropic_provider.generate(
                QUESTION, ANSWER, ROLE, DIFFICULTY, question_type="behavioral"
            )

        mock_ctor.assert_not_called()
        self.assertEqual(result.evaluator, "mock")
        self.assertIsNotNone(result.note)

    def test_dispatch_with_anthropic_provider_but_no_key_still_returns_mock(self):
        settings.ai_provider = "anthropic"
        settings.anthropic_api_key = ""

        result = evaluate_answer(QUESTION, ANSWER, ROLE, DIFFICULTY)

        self.assertEqual(result.evaluator, "mock")


class TestRubricAndProviderSelection(SettingsOverrideTestCase):
    def test_behavioral_question_classified_correctly(self):
        self.assertEqual(
            rubrics.classify_question_type(
                "Tell me about a time you disagreed with a teammate."
            ),
            "behavioral",
        )

    def test_technical_question_classified_correctly(self):
        self.assertEqual(
            rubrics.classify_question_type("How would you design a rate limiter for a public API?"),
            "technical",
        )

    def test_evaluate_answer_uses_matching_rubric_categories(self):
        settings.ai_provider = "mock"
        behavioral_result = evaluate_answer(
            "Tell me about a time you disagreed with a teammate.", ANSWER, ROLE, DIFFICULTY
        )
        technical_result = evaluate_answer(
            "How would you design a rate limiter for a public API?", ANSWER, ROLE, DIFFICULTY
        )

        behavioral_keys = {c.category for c in behavioral_result.category_scores}
        technical_keys = {c.category for c in technical_result.category_scores}
        self.assertEqual(behavioral_keys, set(rubrics.BEHAVIORAL_RUBRIC.keys()))
        self.assertEqual(technical_keys, set(rubrics.TECHNICAL_RUBRIC.keys()))

    def test_dispatch_routes_to_mock_provider_when_configured(self):
        settings.ai_provider = "mock"
        with patch.object(mock_provider, "generate", wraps=mock_provider.generate) as spy:
            evaluate_answer(QUESTION, ANSWER, ROLE, DIFFICULTY)
        spy.assert_called_once()

    def test_dispatch_routes_to_anthropic_provider_when_configured(self):
        settings.ai_provider = "anthropic"
        with patch.object(anthropic_provider, "generate", wraps=anthropic_provider.generate) as spy:
            evaluate_answer(QUESTION, ANSWER, ROLE, DIFFICULTY)
        spy.assert_called_once()


if __name__ == "__main__":
    unittest.main()
