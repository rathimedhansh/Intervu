from dataclasses import dataclass
from typing import Literal

QuestionSource = Literal["bank", "resume"]


@dataclass
class GeneratedQuestion:
    text: str
    source: QuestionSource = "bank"
    # Short label of the resume project/technology/experience item this
    # question targets (e.g. "Project: Order Service"). None for bank questions.
    topic: str | None = None
