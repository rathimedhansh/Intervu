from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.schemas.answer import AnswerRead


class QuestionRead(BaseModel):
    id: int
    text: str
    order_index: int
    source: Literal["bank", "resume"] = "bank"
    resume_topic: str | None = None
    is_followup: bool = False
    answer: AnswerRead | None = None

    model_config = ConfigDict(from_attributes=True)
