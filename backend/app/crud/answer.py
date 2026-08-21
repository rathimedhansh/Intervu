from sqlalchemy.orm import Session

from app.models.answer import Answer
from app.models.question import Question


def submit_answer(
    db: Session,
    question: Question,
    text: str,
    speech_metrics: dict | None = None,
) -> Answer:
    if question.answer is not None:
        question.answer.text = text
        question.answer.speech_metrics = speech_metrics
    else:
        db.add(
            Answer(question_id=question.id, text=text, speech_metrics=speech_metrics)
        )

    db.commit()
    db.refresh(question)
    return question.answer
