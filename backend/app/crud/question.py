from sqlalchemy.orm import Session

from app.models.question import Question


def get_question(db: Session, question_id: int) -> Question | None:
    return db.get(Question, question_id)
