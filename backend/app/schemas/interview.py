from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

from app.schemas.answer import AnswerRead
from app.schemas.question import QuestionRead
from app.schemas.resume import ResumeRead
from app.services.answer_evaluation.rubrics import FOCUSABLE_CATEGORIES, MAX_FOCUS_CATEGORIES
from app.services.communication_feedback import build_camera_feedback, build_communication_report
from app.services.interview_flow.difficulty import difficulty_from_ratios

Difficulty = Literal["easy", "medium", "hard"]


class InterviewCreate(BaseModel):
    # Not a closed enum: the frontend offers a curated list (see
    # app.services.question_generation.bank.ROLES) plus an "Other / Custom
    # Role" option that submits arbitrary text. Any role — curated or
    # custom — flows unchanged into question generation (bank lookup falls
    # back to a role-agnostic pool when unrecognized; AI-backed providers
    # already treat role as free text), evaluation, and feedback.
    role: str = Field(min_length=1, max_length=100)
    difficulty: Difficulty
    question_count: int = Field(5, ge=1, le=10)
    # Optional: id of a previously-uploaded resume (see POST /api/resumes/).
    # When set, questions are generated from the resume instead of the bank.
    resume_id: int | None = None
    # Optional: rubric category keys (see app.services.answer_evaluation.
    # rubrics.FOCUSABLE_CATEGORIES) to bias question selection toward — the
    # "Practice weak areas" flow from the dashboard, or a manual pick on the
    # setup page. Deduplicated and capped; unknown keys are rejected outright
    # rather than silently dropped, since a typo here would otherwise
    # silently produce an unfocused interview.
    focus_categories: list[str] | None = Field(default=None, max_length=MAX_FOCUS_CATEGORIES)

    @field_validator("role")
    @classmethod
    def _strip_role(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("role must not be blank")
        return stripped

    @field_validator("focus_categories")
    @classmethod
    def _validate_focus_categories(cls, value: list[str] | None) -> list[str] | None:
        if not value:
            return None
        deduped = list(dict.fromkeys(value))
        unknown = [c for c in deduped if c not in FOCUSABLE_CATEGORIES]
        if unknown:
            raise ValueError(f"Unknown focus categories: {', '.join(unknown)}")
        return deduped


# Bounds are generous but finite — this data is computed client-side and
# submitted as plain JSON, so we validate it like any other untrusted input.
class CameraMetricsIn(BaseModel):
    face_visible_percentage: float = Field(ge=0, le=100)
    camera_attention_percentage: float = Field(ge=0, le=100)
    head_movement_score: float = Field(ge=0, le=100)
    # Optional, newer signals — absent (None) rather than 0 when the
    # browser/analyzer version that produced this payload didn't collect
    # them, so feedback logic never mistakes "not measured" for "measured
    # as zero".
    look_away_count: int | None = Field(default=None, ge=0, le=10_000)
    multiple_faces_percentage: float | None = Field(default=None, ge=0, le=100)


class CameraMetricsRead(CameraMetricsIn):
    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def feedback(self) -> list[str]:
        return build_camera_feedback(
            {
                "face_visible_percentage": self.face_visible_percentage,
                "camera_attention_percentage": self.camera_attention_percentage,
                "head_movement_score": self.head_movement_score,
                "look_away_count": self.look_away_count,
                "multiple_faces_percentage": self.multiple_faces_percentage,
            }
        )


# --- Communication Score -----------------------------------------------
# A transparent, rule-based rollup of the metrics above (see
# app.services.communication_feedback.report) — never persisted, always
# recomputed from the same speech_metrics/camera_metrics already stored on
# each answer/interview, so it reflects the current scoring logic even for
# interviews completed before this feature existed.


class CommunicationCategoryRead(BaseModel):
    key: str
    label: str
    score: int
    description: str


class CommunicationSpeechSummaryRead(BaseModel):
    total_duration_seconds: float
    total_words_spoken: int | None
    average_words_per_minute: int | None
    filler_word_count: int
    filler_word_breakdown: dict[str, int]
    pause_count: int
    long_pause_count: int
    estimated_repetition_count: int
    repeated_examples: list[str]
    brief_answer_count: int
    answers_with_transcript: int
    answers_measured: int


class CommunicationReportRead(BaseModel):
    overall_score: int | None
    categories: list[CommunicationCategoryRead]
    speech_summary: CommunicationSpeechSummaryRead | None
    camera_summary: CameraMetricsRead | None
    strengths: list[str]
    improvements: list[str]
    recommendations: list[str]
    note: str


class InterviewComplete(BaseModel):
    # Optional locally-computed camera metrics for the whole session (see
    # frontend/src/services/cameraAnalysis.js). Absent/null unless the user
    # explicitly opted into camera analysis for this interview.
    camera_metrics: CameraMetricsIn | None = None


class InterviewSummary(BaseModel):
    id: int
    role: str
    difficulty: str
    status: str
    created_at: datetime
    completed_at: datetime | None
    overall_score: int | None = None
    strengths: list[str] | None = None
    weaknesses: list[str] | None = None
    summary_feedback: str | None = None
    resume_id: int | None = None
    camera_metrics: CameraMetricsRead | None = None
    # Target question count for the conversational flow (see
    # app.services.interview_flow). Null for interviews created before this
    # feature — those don't support POST .../respond.
    question_count: int | None = None
    # Rubric categories this interview was set up to specifically practice,
    # if any (see InterviewCreate.focus_categories above).
    focus_categories: list[str] | None = None

    model_config = ConfigDict(from_attributes=True)


class InterviewRead(InterviewSummary):
    questions: list[QuestionRead] = []
    resume: ResumeRead | None = None

    # Read-time re-derivation of the same adaptive-difficulty logic used
    # live during the conversation (see app.services.interview_flow.
    # difficulty and app.crud.interview_flow.advance_conversation) — lets a
    # client that just loaded/refreshed an in-progress interview show the
    # currently-calibrated level without waiting for the next /respond
    # turn. Pydantic-shaped data (AnswerEvaluationRead, not a dict), so this
    # extracts ratios itself rather than reusing the ORM-only answer_ratio().
    @computed_field
    @property
    def current_difficulty(self) -> str:
        ratios: list[float] = []
        for question in self.questions:
            answer = question.answer
            if answer is None or answer.total_score is None or answer.evaluation is None:
                continue
            max_score = answer.evaluation.max_score
            if not max_score:
                continue
            ratios.append(answer.total_score / max_score)
        return difficulty_from_ratios(self.difficulty, ratios)

    @computed_field
    @property
    def communication_report(self) -> CommunicationReportRead | None:
        speech_entries: list[dict] = []
        repetition_entries: list[dict] = []
        for question in self.questions:
            metrics = question.answer.speech_metrics if question.answer else None
            if metrics is None:
                continue
            speech_entries.append(metrics.model_dump())
            repetition = question.answer.repetition_analysis
            repetition_entries.append(repetition.model_dump() if repetition else {})

        camera = self.camera_metrics.model_dump() if self.camera_metrics else None
        result = build_communication_report(speech_entries, repetition_entries, camera)
        return CommunicationReportRead(**result) if result else None


# Response for POST /interviews/{id}/questions/{qid}/respond — the result of
# one turn of the conversational interview flow (see
# app.crud.interview_flow.advance_conversation). next_question is None
# exactly when is_complete is True: the question budget has been reached
# and the frontend should call the existing POST /interviews/{id}/complete.
class InterviewTurnRead(BaseModel):
    answer: AnswerRead
    next_question: QuestionRead | None = None
    is_followup: bool = False
    is_complete: bool
    questions_asked: int
    question_count: int
    # The difficulty tier the interview is calibrated to *after* this turn's
    # answer was scored (see app.services.interview_flow.difficulty), and
    # whether that's a change from before this turn — lets the client show
    # a brief, non-scored "difficulty increased/decreased" notice.
    current_difficulty: Difficulty
    difficulty_changed: Literal["increased", "decreased"] | None = None
