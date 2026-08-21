from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.services.communication_feedback import build_speech_feedback, estimate_disfluencies


# Bounds are generous but finite — this data is computed client-side and
# submitted as plain JSON, so we validate it like any other untrusted input.
class SpeechMetricsIn(BaseModel):
    duration_seconds: float = Field(ge=0, le=3600)
    words_per_minute: float | None = Field(default=None, ge=0, le=1000)
    pause_count: int = Field(default=0, ge=0, le=1000)
    long_pause_count: int = Field(default=0, ge=0, le=1000)
    filler_word_count: int = Field(default=0, ge=0, le=1000)
    filler_words: dict[str, int] = Field(default_factory=dict)
    repeated_word_count: int = Field(default=0, ge=0, le=1000)
    transcript_word_count: int | None = Field(default=None, ge=0, le=100_000)
    # False when browser speech recognition was unavailable/denied — in that
    # case transcript-based fields above are meaningless and should be
    # ignored by feedback logic and the UI alike.
    transcript_available: bool = False
    # Average SpeechRecognitionAlternative.confidence across final results,
    # when the browser actually reports one (many engines report 0/omit it
    # entirely, in which case this stays null rather than showing a fake
    # value — see frontend/src/services/speechAnalysis.js).
    transcript_confidence: float | None = Field(default=None, ge=0, le=1)


class SpeechMetricsRead(SpeechMetricsIn):
    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def feedback(self) -> list[str]:
        return build_speech_feedback(
            {
                "transcript_available": self.transcript_available,
                "words_per_minute": self.words_per_minute,
                "transcript_word_count": self.transcript_word_count,
                "filler_word_count": self.filler_word_count,
                "pause_count": self.pause_count,
                "long_pause_count": self.long_pause_count,
                "repeated_word_count": self.repeated_word_count,
            }
        )


# Heuristic estimate of repeated words/short phrases (and, by extension,
# simple false starts) in the transcribed answer — see
# app.services.communication_feedback.stutter. Deliberately not a subset of
# SpeechMetricsRead: it's derived from Answer.text (already stored/sent for
# scoring), not from the browser's own live-transcript word counting.
class RepetitionAnalysisRead(BaseModel):
    repeated_word_count: int
    repeated_phrase_count: int
    repeated_examples: list[str]
    total_estimated_repetitions: int
    note: str = (
        "Heuristic estimate of repeated words/phrases (and simple false "
        "starts) in your transcribed answer. This is not a medical "
        "diagnosis or a definitive speech assessment."
    )


class AnswerCreate(BaseModel):
    text: str = Field(min_length=1, max_length=5000)
    # Optional locally-computed speech metrics for this answer (see
    # frontend/src/services/speechAnalysis.js). Absent/null unless the user
    # explicitly opted into speech analysis for this interview.
    speech_metrics: SpeechMetricsIn | None = None


class CategoryScoreRead(BaseModel):
    category: str
    label: str
    score: int
    max_score: int

    model_config = ConfigDict(from_attributes=True)


class AnswerEvaluationRead(BaseModel):
    question_type: Literal["behavioral", "technical"]
    evaluator: Literal["mock", "anthropic"]
    category_scores: list[CategoryScoreRead]
    total_score: int
    max_score: int
    strengths: list[str]
    weaknesses: list[str]
    improvement_suggestions: list[str]
    stronger_answer_example: str
    note: str | None = None

    model_config = ConfigDict(from_attributes=True)


class AnswerRead(BaseModel):
    id: int
    question_id: int
    text: str
    total_score: int | None = None
    evaluation: AnswerEvaluationRead | None = None
    speech_metrics: SpeechMetricsRead | None = None

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def repetition_analysis(self) -> RepetitionAnalysisRead | None:
        # Only meaningful for an answer that actually came from speech
        # recognition — running this on a typed answer wouldn't measure
        # anything about the candidate's speech.
        if self.speech_metrics is None or not self.speech_metrics.transcript_available:
            return None
        return RepetitionAnalysisRead(**estimate_disfluencies(self.text))
