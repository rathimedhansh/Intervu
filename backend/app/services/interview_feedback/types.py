from dataclasses import dataclass


@dataclass
class InterviewFeedback:
    overall_score: int | None
    strengths: list[str]
    weaknesses: list[str]
    summary_feedback: str
