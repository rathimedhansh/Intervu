from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class DashboardOverview(BaseModel):
    total_interviews: int
    average_score: float | None
    highest_score: int | None
    total_questions_answered: int


class ProgressPoint(BaseModel):
    interview_id: int
    date: datetime
    score: int


class RecentInterview(BaseModel):
    id: int
    date: datetime | None
    role: str
    difficulty: str
    score: int | None
    question_count: int


class CategoryBreakdown(BaseModel):
    category: str
    label: str
    average_score: float
    sample_count: int


# See app.crud.dashboard for how each of these is derived — technical_score
# is the same rubric-based average as overview.average_score (kept there too
# for backward compatibility); communication_score/presentation_score are
# None when no interview in the user's history ever had speech/camera
# analysis enabled, never a fabricated number. overall_score blends
# technical + communication when both exist, or falls back to
# technical-only.
class ScoreBreakdown(BaseModel):
    overall_score: int | None
    technical_score: float | None
    communication_score: int | None
    presentation_score: int | None


# See app.crud.dashboard._build_practice_plan for how this is derived.
class PracticePlanTrendPoint(BaseModel):
    interview_id: int
    date: datetime
    score: float


# See app.crud.dashboard._compute_practice_progress. Present only when the
# candidate has actually run a targeted practice session for this area (an
# interview whose focus_categories included it) — never fabricated when no
# such session happened.
class PracticePlanPracticeProgress(BaseModel):
    # "insufficient_data": a session happened but there isn't a scored data
    # point both before and after it to compare yet. "improved": there is,
    # and the after-average cleared PRACTICE_IMPROVEMENT_MARGIN over the
    # before-average. "practiced": there is, but it didn't clear that
    # margin — a neutral "this happened" rather than a claimed result.
    status: Literal["insufficient_data", "improved", "practiced"]
    # How many completed interviews targeted this category via
    # focus_categories.
    session_count: int
    # Average score in this category before vs. from-and-after the first
    # targeted session, in the same 0-100 units as `score` above. Both None
    # when status is "insufficient_data".
    before_avg: float | None
    after_avg: float | None
    last_practiced_at: datetime


class PracticePlanArea(BaseModel):
    # "technical" = an answer-evaluation rubric category (e.g. Structure);
    # "communication" = a delivery category from the communication report
    # (pace, fillers, fluency, pausing); "presentation" = camera/framing.
    area: Literal["technical", "communication", "presentation"]
    category: str
    label: str
    score: float
    sample_count: int
    # "high" (at/below the same WEAK_RATIO bar used elsewhere on the
    # dashboard), "medium" (below STRONG_RATIO but above WEAK_RATIO), "low"
    # (not currently reachable given the candidate filter, kept for
    # forward-compatibility if that filter loosens).
    severity: Literal["high", "medium", "low"]
    # Why this area was selected, grounded in the actual numbers behind it.
    reason: str
    # One concrete, practice-able suggestion — not "improve X".
    action: str
    # This area's score across the interviews that contributed to it, oldest
    # first. Empty until at least two interviews have data for this specific
    # area (a single point isn't a trend).
    trend: list[PracticePlanTrendPoint]
    # Whether/how a targeted practice session (a completed interview whose
    # focus_categories included this category) has paid off. None when no
    # such session has ever happened for this area.
    practice_progress: PracticePlanPracticeProgress | None


class PracticePlan(BaseModel):
    # False only when there isn't enough interview history yet (see
    # MIN_PLAN_INTERVIEWS) — distinct from `ready=True, areas=[]`, which
    # means there's enough history but no qualifying weak area was found.
    ready: bool
    # Up to PRACTICE_PLAN_SIZE areas, worst score first.
    areas: list[PracticePlanArea]
    # Explains an empty `areas` list (either reason above); None once areas
    # is non-empty.
    message: str | None


class DashboardRead(BaseModel):
    overview: DashboardOverview
    progress: list[ProgressPoint]
    # Same shape as `progress`, but each point is that interview's own
    # communication-report score — only includes interviews that actually
    # had speech/camera analysis enabled, so it's shorter than `progress`
    # whenever a user hasn't used those features on every interview.
    communication_progress: list[ProgressPoint]
    recent_interviews: list[RecentInterview]
    category_breakdown: list[CategoryBreakdown]
    scores: ScoreBreakdown
    recurring_strengths: list[str]
    recurring_weaknesses: list[str]
    # The same qualifying weak categories recurring_weaknesses' rubric-based
    # entries are phrased from (see app.crud.dashboard), kept structured
    # (category key + label) rather than a prose string so the frontend can
    # act on them directly — e.g. the dashboard's "Practice weak areas" CTA,
    # which passes these category keys straight into
    # InterviewCreate.focus_categories. Ranked weakest first, capped at 3.
    weak_categories: list[CategoryBreakdown]
    recommendations: list[str]
    # A prioritized, actionable view built on top of the fields above (see
    # app.crud.dashboard._build_practice_plan) — never duplicates their
    # logic, only ranks and re-explains a subset of the same underlying data.
    practice_plan: PracticePlan
