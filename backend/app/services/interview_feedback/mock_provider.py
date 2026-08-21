from app.models.interview import Interview
from app.services.interview_feedback.types import InterviewFeedback

# Deterministic stand-in for AI-generated interview feedback. No network
# calls, no API key required. Derives overall_score/strengths/weaknesses
# from the per-answer 0-100 rubric totals already produced by
# services/answer_evaluation.

STRONG_THRESHOLD = 80
WEAK_THRESHOLD = 40
MAX_HIGHLIGHTS = 3

GENERIC_STRENGTHS = [
    "Answered every question rather than skipping the harder ones.",
    "Kept responses on-topic and structured.",
]
GENERIC_WEAKNESSES = [
    "Add specific examples with measurable outcomes to strengthen your answers.",
    "Try to be more concise and lead with the impact of your work.",
]


def generate(interview: Interview) -> InterviewFeedback:
    scored = [
        (question.text, question.answer.total_score)
        for question in interview.questions
        if question.answer is not None and question.answer.total_score is not None
    ]

    if not scored:
        return InterviewFeedback(
            overall_score=None,
            strengths=list(GENERIC_STRENGTHS),
            weaknesses=list(GENERIC_WEAKNESSES),
            summary_feedback=(
                "No answers were submitted for this interview, so there isn't enough "
                "to go on yet. Try answering each question before finishing."
            ),
        )

    overall_score = round(sum(score for _, score in scored) / len(scored))

    strengths = [text for text, score in scored if score >= STRONG_THRESHOLD][:MAX_HIGHLIGHTS]
    weaknesses = [text for text, score in scored if score <= WEAK_THRESHOLD][:MAX_HIGHLIGHTS]

    if not strengths:
        strengths = list(GENERIC_STRENGTHS)
    if not weaknesses:
        weaknesses = list(GENERIC_WEAKNESSES)

    if overall_score >= STRONG_THRESHOLD:
        tier_comment = "Strong performance overall — keep practicing to stay sharp."
    elif overall_score >= WEAK_THRESHOLD + 1:
        tier_comment = "Solid effort with room to grow — focus on the weaker areas below."
    else:
        tier_comment = "This is a good starting point — review the weaker areas below and try again."

    question_label = "question" if len(scored) == 1 else "questions"
    summary_feedback = (
        f"You answered {len(scored)} {question_label} for the {interview.role} role "
        f"at {interview.difficulty} difficulty, with an overall score of "
        f"{overall_score}/100. {tier_comment}"
    )

    return InterviewFeedback(
        overall_score=overall_score,
        strengths=strengths,
        weaknesses=weaknesses,
        summary_feedback=summary_feedback,
    )
