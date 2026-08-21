from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.interview import Interview
from app.models.question import Question
from app.models.resume import Resume
from app.services.answer_evaluation import evaluate_answer
from app.services.answer_evaluation.rubrics import FOCUSABLE_CATEGORIES, MAX_FOCUS_CATEGORIES
from app.services.interview_feedback import generate_feedback
from app.services.interview_flow import MAX_QUESTIONS, MIN_QUESTIONS
from app.services.question_generation import generate_intro_question


def create_interview(
    db: Session,
    role: str,
    difficulty: str,
    question_count: int,
    user_id: int,
    resume_id: int | None = None,
    focus_categories: list[str] | None = None,
) -> Interview:
    resume: Resume | None = None
    if resume_id is not None:
        resume = db.get(Resume, resume_id)
        # Same "not found" message whether the resume doesn't exist or
        # belongs to someone else — a user must not learn that another
        # user's resume_id is valid.
        if resume is None or resume.user_id != user_id:
            raise ValueError("Resume not found")

    # Defense-in-depth, mirroring the question_count clamp below: the HTTP
    # schema (InterviewCreate) already validates/dedupes/caps this, but
    # crud is also callable directly (tests, scripts), so never trust it
    # blindly here either.
    cleaned_focus_categories: list[str] | None = None
    if focus_categories:
        deduped = list(dict.fromkeys(focus_categories))[:MAX_FOCUS_CATEGORIES]
        unknown = [c for c in deduped if c not in FOCUSABLE_CATEGORIES]
        if unknown:
            raise ValueError(f"Unknown focus categories: {', '.join(unknown)}")
        cleaned_focus_categories = deduped

    # Server-side bound, independent of what the client requested — "keep
    # the interview reasonably bounded" (see app.services.interview_flow).
    bounded_question_count = max(MIN_QUESTIONS, min(MAX_QUESTIONS, question_count))

    interview = Interview(
        role=role,
        difficulty=difficulty,
        status="pending",
        resume_id=resume_id,
        user_id=user_id,
        question_count=bounded_question_count,
        focus_categories=cleaned_focus_categories,
    )
    db.add(interview)
    db.flush()  # assigns interview.id without committing yet

    # Only the first question is generated up front — the rest of the
    # conversation is generated dynamically as the candidate answers (see
    # app.crud.interview_flow.advance_conversation). The opener is always a
    # plain icebreaker (see generate_intro_question) regardless of the
    # resume or the difficulty chosen above, matching how a real interview
    # actually starts.
    first_question = generate_intro_question(role)
    db.add(
        Question(
            interview_id=interview.id,
            text=first_question.text,
            order_index=0,
            source=first_question.source,
            resume_topic=first_question.topic,
            is_followup=False,
        )
    )

    db.commit()
    db.refresh(interview)
    return interview


def list_interviews(db: Session, user_id: int) -> list[Interview]:
    return (
        db.query(Interview)
        .filter(Interview.user_id == user_id)
        .order_by(Interview.created_at.desc())
        .all()
    )


def get_interview(db: Session, interview_id: int) -> Interview | None:
    return db.get(Interview, interview_id)


def delete_interview(db: Session, interview: Interview) -> None:
    # Question.cascade="all, delete-orphan" (see app.models.interview) takes
    # its questions with it, which in turn take their answers with it (same
    # cascade on Question.answer) — no manual cleanup needed. The resume it
    # may have been generated from is untouched (Interview.resume has no
    # cascade): a resume is a reusable asset that can back many interviews
    # (see app.crud.resume.list_resumes / the setup page's "use a previous
    # resume" picker), so deleting one interview must never delete it.
    db.delete(interview)
    db.commit()


def complete_interview(
    db: Session, interview: Interview, camera_metrics: dict | None = None
) -> Interview:
    interview.camera_metrics = camera_metrics

    for question in interview.questions:
        if question.answer is not None and question.answer.total_score is None:
            result = evaluate_answer(
                question.text, question.answer.text, interview.role, interview.difficulty
            )
            question.answer.total_score = result.total_score
            question.answer.evaluation = result.to_dict()

    feedback = generate_feedback(interview)
    interview.overall_score = feedback.overall_score
    interview.strengths = feedback.strengths
    interview.weaknesses = feedback.weaknesses
    interview.summary_feedback = feedback.summary_feedback

    interview.status = "completed"
    interview.completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(interview)
    return interview
