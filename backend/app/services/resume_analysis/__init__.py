from app.core.config import settings
from app.services.resume_analysis import anthropic_provider, mock_provider
from app.services.resume_analysis.types import ResumeAnalysis
from app.services.resume_parsing import ParsedResume

__all__ = ["analyze_resume", "ResumeAnalysis"]


def analyze_resume(parsed: ParsedResume, resume_text: str) -> ResumeAnalysis:
    if settings.ai_provider == "anthropic":
        return anthropic_provider.generate(parsed, resume_text)
    return mock_provider.generate(parsed, resume_text)
