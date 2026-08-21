from app.services.interview_feedback import mock_provider

# Only a mock implementation exists today. If an anthropic-backed provider
# is added later, follow the same settings.ai_provider dispatch pattern
# used in services/answer_evaluation and services/question_generation.
generate_feedback = mock_provider.generate
