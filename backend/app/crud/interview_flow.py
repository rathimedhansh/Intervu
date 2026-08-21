from sqlalchemy.orm import Session

from app.crud import answer as answer_crud
from app.models.interview import Interview
from app.models.question import Question
from app.services.answer_evaluation import evaluate_answer
from app.services.interview_flow import decide_next_step
from app.services.interview_flow.difficulty import difficulty_direction, effective_difficulty


def advance_conversation(
    db: Session,
    interview: Interview,
    question: Question,
    text: str,
    speech_metrics: dict | None,
) -> dict:
    """Save + evaluate the answer to `question`, then decide and persist the
    next step of the conversation (a follow-up, a new main question, or
    nothing if the interview's question budget has been reached).

    Precondition: interview.question_count is set (the route guards this —
    interviews created before this feature don't support this flow).
    """
    # Captured before this answer is scored, so it reflects only prior
    # history — compared against the post-score recalculation below to tell
    # the client whether this specific answer shifted the calibrated level.
    previous_difficulty = effective_difficulty(interview.difficulty, interview.questions)

    answer = answer_crud.submit_answer(db, question, text, speech_metrics)

    evaluation = evaluate_answer(question.text, text, interview.role, interview.difficulty)
    answer.total_score = evaluation.total_score
    answer.evaluation = evaluation.to_dict()
    db.commit()

    current_difficulty = effective_difficulty(interview.difficulty, interview.questions)
    difficulty_changed = difficulty_direction(previous_difficulty, current_difficulty)

    question_count = interview.question_count
    questions_asked = len(interview.questions)

    if questions_asked >= question_count:
        return {
            "answer": answer,
            "next_question": None,
            "is_followup": False,
            "is_complete": True,
            "questions_asked": questions_asked,
            "question_count": question_count,
            "current_difficulty": current_difficulty,
            "difficulty_changed": difficulty_changed,
        }

    step = decide_next_step(
        role=interview.role,
        difficulty=interview.difficulty,
        resume=interview.resume,
        asked_questions=interview.questions,
        current_is_followup=question.is_followup,
        question_count=question_count,
        focus_categories=interview.focus_categories,
    )

    next_question = Question(
        interview_id=interview.id,
        text=step.question.text,
        order_index=questions_asked,
        source=step.question.source,
        resume_topic=step.question.topic,
        is_followup=step.is_followup,
    )
    db.add(next_question)
    db.commit()
    db.refresh(next_question)

    return {
        "answer": answer,
        "next_question": next_question,
        "is_followup": step.is_followup,
        "is_complete": False,
        "questions_asked": questions_asked,
        "question_count": question_count,
        "current_difficulty": current_difficulty,
        "difficulty_changed": difficulty_changed,
    }
