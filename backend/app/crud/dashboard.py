from datetime import datetime

from sqlalchemy.orm import Session

from app.models.interview import Interview
from app.services.answer_evaluation.rubrics import CATEGORY_ACTIONS, CATEGORY_DESCRIPTIONS
from app.services.communication_feedback import build_communication_report, estimate_disfluencies
from app.services.interview_flow.difficulty import STRONG_RATIO, WEAK_RATIO

RECENT_INTERVIEWS_LIMIT = 10

# A rubric category needs at least this many scored answers behind it before
# it's called out as a "recurring" strength/weakness — a single answer isn't
# a pattern (see difficulty.py's WINDOW/SHIFT_THRESHOLD for the same idea
# applied to adaptive difficulty).
MIN_CATEGORY_SAMPLES = 2

# The Practice Plan (see _build_practice_plan below) additionally requires
# at least this many *completed interviews* before it will surface anything
# at all — stricter than MIN_CATEGORY_SAMPLES, which a single interview
# with two low-scored answers could already satisfy. A "recurring" pattern
# the plan builds a prioritized, actionable list from should span more than
# one sitting.
MIN_PLAN_INTERVIEWS = 2

# How many of the lowest-scoring qualifying areas (technical or
# communication/presentation) the plan surfaces, worst first.
PRACTICE_PLAN_SIZE = 3

# A trend needs at least two points to show a direction.
MIN_TREND_POINTS = 2

# How many percentage points a category's post-practice average must exceed
# its pre-practice average by before the Practice Plan calls it "Improvement
# detected" rather than just "Practice completed" — a small margin so normal
# score noise between interviews doesn't get reported as improvement.
PRACTICE_IMPROVEMENT_MARGIN = 8

# The blended "overall performance" score weights answer-quality (the
# existing rubric-based evaluation) over delivery (the communication score)
# — content is still the primary thing being assessed, communication is a
# secondary signal layered on top. Falls back to evaluation-only when no
# interview in the user's history ever had speech/camera analysis enabled,
# rather than inventing a communication number that was never measured.
_TECHNICAL_WEIGHT = 0.7
_COMMUNICATION_WEIGHT = 0.3

# All figures below are derived from Interview/Question/Answer rows already
# written by the interview-completion flow (app.crud.interview) and the
# per-answer evaluation JSON produced by app.services.answer_evaluation.
# Nothing here is stored separately — it's recomputed from that data on
# every request so it can never drift out of sync.


def _communication_inputs(interview: Interview) -> tuple[list[dict], list[dict]]:
    """ORM-side counterpart to InterviewRead.communication_report's
    extraction (app.schemas.interview) — that one works off Pydantic-shaped
    data for a single already-serialized interview; this one works off raw
    ORM rows and is reused both per-interview (for the trend) and pooled
    across a user's whole history (for the aggregate score) below."""
    speech_entries: list[dict] = []
    repetition_entries: list[dict] = []
    for question in interview.questions:
        answer = question.answer
        if answer is None or answer.speech_metrics is None:
            continue
        speech_entries.append(answer.speech_metrics)
        repetition_entries.append(estimate_disfluencies(answer.text))
    return speech_entries, repetition_entries


def _average_camera_metrics(camera_metrics_list: list[dict]) -> dict | None:
    """A straightforward numeric average of each interview's already-stored
    whole-session camera metrics — never fabricated, just aggregated."""
    if not camera_metrics_list:
        return None
    averaged = {
        key: round(sum(cm.get(key) or 0 for cm in camera_metrics_list) / len(camera_metrics_list), 1)
        for key in ("face_visible_percentage", "camera_attention_percentage", "head_movement_score")
    }
    for optional_key in ("look_away_count", "multiple_faces_percentage"):
        values = [cm[optional_key] for cm in camera_metrics_list if cm.get(optional_key) is not None]
        if values:
            averaged[optional_key] = round(sum(values) / len(values), 1)
    return averaged


def _compute_practice_progress(
    trend: list[dict], practiced_interviews: list[dict]
) -> dict | None:
    """Closes the Practice Plan loop: did the candidate ever run a targeted
    practice session for this category (an interview whose focus_categories
    included it — see Interview.focus_categories), and if so did their score
    in this category actually move afterward?

    `trend` is this category's full, chronologically-ordered list of
    {interview_id, date, score} points (see category_trends/
    comm_category_trends in get_dashboard_stats — the same data the area's
    own `trend` field is built from, never a separate calculation).
    `practiced_interviews` is this category's list of {interview_id, date}
    for every completed interview whose focus_categories targeted it,
    regardless of whether that interview happened to produce a scored
    answer in this category.

    Returns None when no targeted session ever happened (nothing to show).
    Otherwise returns one of three statuses, matching the three states the
    Practice Plan UI distinguishes:
      - "insufficient_data": a session happened, but there isn't at least
        one scored data point both before and after it to compare — never
        guesses at improvement from too little evidence.
      - "improved": both sides exist and the after-average beats the
        before-average by at least PRACTICE_IMPROVEMENT_MARGIN.
      - "practiced": both sides exist but the improvement didn't clear that
        margin — a neutral "this happened" rather than a claimed result.
    """
    if not practiced_interviews:
        return None

    session_count = len(practiced_interviews)
    last_practiced_at = max(p["date"] for p in practiced_interviews)
    practiced_ids = {p["interview_id"] for p in practiced_interviews}

    trend_index_by_id = {point["interview_id"]: i for i, point in enumerate(trend)}
    practiced_trend_indices = sorted(
        trend_index_by_id[iid] for iid in practiced_ids if iid in trend_index_by_id
    )

    if not practiced_trend_indices:
        return {
            "status": "insufficient_data",
            "session_count": session_count,
            "before_avg": None,
            "after_avg": None,
            "last_practiced_at": last_practiced_at,
        }

    first_practice_index = practiced_trend_indices[0]
    before_scores = [point["score"] for point in trend[:first_practice_index]]
    after_scores = [point["score"] for point in trend[first_practice_index:]]

    if not before_scores or not after_scores:
        return {
            "status": "insufficient_data",
            "session_count": session_count,
            "before_avg": None,
            "after_avg": None,
            "last_practiced_at": last_practiced_at,
        }

    before_avg = round(sum(before_scores) / len(before_scores), 1)
    after_avg = round(sum(after_scores) / len(after_scores), 1)
    status = "improved" if (after_avg - before_avg) >= PRACTICE_IMPROVEMENT_MARGIN else "practiced"
    return {
        "status": status,
        "session_count": session_count,
        "before_avg": before_avg,
        "after_avg": after_avg,
        "last_practiced_at": last_practiced_at,
    }


def _build_practice_plan(
    *,
    total_interviews: int,
    qualifying_categories: list[dict],
    aggregate_report: dict | None,
    category_trends: dict[str, list[dict]],
    comm_category_trends: dict[str, list[dict]],
    camera_interview_count: int,
    category_practice_interviews: dict[str, list[dict]],
) -> dict:
    """The Practice Plan: a ranked, cross-system view of the user's top
    improvement areas, built entirely from data already computed above —
    the rubric category breakdown (qualifying_categories, gated by
    MIN_CATEGORY_SAMPLES) and the aggregate communication report
    (aggregate_report, from build_communication_report). Nothing here
    re-scores anything; it only selects, ranks, and explains.

    A candidate area (technical rubric category, or communication/
    presentation category) qualifies once it has enough samples behind it
    (MIN_CATEGORY_SAMPLES) and scores below STRONG_RATIO*100 — the same
    "not yet strong" bar dashboard.py already uses elsewhere, reused here
    so technical (0-100 rubric ratio) and communication (0-100 weighted
    score) areas are ranked on one comparable scale. The three
    lowest-scoring qualifying areas become the plan, worst first.
    """
    if total_interviews < MIN_PLAN_INTERVIEWS:
        return {
            "ready": False,
            "areas": [],
            "message": (
                f"Complete at least {MIN_PLAN_INTERVIEWS} interviews to unlock a personalized "
                "practice plan. A single interview isn't enough to tell a recurring pattern from "
                "a one-off."
            ),
        }

    candidates: list[dict] = []

    for c in qualifying_categories:
        if c["average_score"] >= STRONG_RATIO * 100:
            continue
        candidates.append(
            {
                "area": "technical",
                "category": c["category"],
                "label": c["label"],
                "score": c["average_score"],
                "sample_count": c["sample_count"],
                "reason": (
                    f"Averaged {c['average_score']}% across {c['sample_count']} scored answers in "
                    f"this rubric category. {CATEGORY_DESCRIPTIONS.get(c['category'], '')}"
                ),
                "action": CATEGORY_ACTIONS.get(
                    c["category"], f"Focus your next few practice answers on {c['label'].lower()}."
                ),
                "trend": category_trends.get(c["category"], []),
                "practice_progress": _compute_practice_progress(
                    category_trends.get(c["category"], []),
                    category_practice_interviews.get(c["category"], []),
                ),
            }
        )

    if aggregate_report:
        speech_summary = aggregate_report.get("speech_summary") or {}
        # How many data points actually back each communication-report
        # category — pace/fillers/fluency come from transcribed answers,
        # pausing from any timed answer, presentation from interviews that
        # had camera analysis on. Mirrors MIN_CATEGORY_SAMPLES's "don't call
        # it a pattern from too little evidence" for the rubric side.
        category_sample_counts = {
            "pace": speech_summary.get("answers_with_transcript") or 0,
            "fillers": speech_summary.get("answers_with_transcript") or 0,
            "fluency": speech_summary.get("answers_with_transcript") or 0,
            "pausing": speech_summary.get("answers_measured") or 0,
            "presentation": camera_interview_count,
        }
        recommendations_by_category = aggregate_report.get("recommendations_by_category") or {}
        for cat in aggregate_report["categories"]:
            key = cat["key"]
            sample_count = category_sample_counts.get(key, 0)
            if sample_count < MIN_CATEGORY_SAMPLES or cat["score"] >= STRONG_RATIO * 100:
                continue
            candidates.append(
                {
                    "area": "presentation" if key == "presentation" else "communication",
                    "category": key,
                    "label": cat["label"],
                    "score": cat["score"],
                    "sample_count": sample_count,
                    "reason": cat["description"],
                    "action": recommendations_by_category.get(
                        key, f"Keep an eye on {cat['label'].lower()} in your next few interviews."
                    ),
                    "trend": comm_category_trends.get(key, []),
                    "practice_progress": _compute_practice_progress(
                        comm_category_trends.get(key, []),
                        category_practice_interviews.get(key, []),
                    ),
                }
            )

    if not candidates:
        return {
            "ready": True,
            "areas": [],
            "message": (
                "No consistent weak areas found across your interview history yet — nice work. "
                "Keep completing interviews and this plan will update automatically as patterns "
                "emerge."
            ),
        }

    candidates.sort(key=lambda c: c["score"])

    areas = []
    for c in candidates[:PRACTICE_PLAN_SIZE]:
        if c["score"] <= WEAK_RATIO * 100:
            severity = "high"
        elif c["score"] < STRONG_RATIO * 100:
            severity = "medium"
        else:
            severity = "low"
        areas.append(
            {
                "area": c["area"],
                "category": c["category"],
                "label": c["label"],
                "score": c["score"],
                "sample_count": c["sample_count"],
                "severity": severity,
                "reason": c["reason"],
                "action": c["action"],
                "trend": c["trend"] if len(c["trend"]) >= MIN_TREND_POINTS else [],
                "practice_progress": c["practice_progress"],
            }
        )

    return {"ready": True, "areas": areas, "message": None}


def get_dashboard_stats(db: Session, user_id: int) -> dict:
    interviews = (
        db.query(Interview)
        .filter(Interview.status == "completed", Interview.user_id == user_id)
        .order_by(Interview.completed_at.asc())
        .all()
    )

    scores = [i.overall_score for i in interviews if i.overall_score is not None]
    total_questions_answered = 0
    progress = []
    communication_progress = []
    recent_interviews = []
    # category_key -> {"label": str, "ratio_sum": float, "count": int}
    category_totals: dict[str, dict] = {}
    # category_key -> [{"interview_id", "date", "score"}, ...], one point per
    # interview that had at least one scored answer in that rubric category
    # — the per-category counterpart to `progress` above, feeding the
    # Practice Plan's per-area trend (see _build_practice_plan).
    category_trends: dict[str, list[dict]] = {}
    # Same idea for the communication-report categories (pace/fillers/
    # fluency/pausing/presentation): one point per interview that produced
    # that category (i.e. had the underlying speech/camera data).
    comm_category_trends: dict[str, list[dict]] = {}
    # category_key -> [{"interview_id", "date"}, ...], one entry per completed
    # interview whose Interview.focus_categories targeted that category —
    # i.e. a targeted practice session for it, regardless of whether that
    # interview ended up producing a scored answer in the category. Feeds
    # the Practice Plan's before/after progress tracking (see
    # _compute_practice_progress) — never a separate practice-tracking
    # system, just a regrouping of the focus_categories every interview
    # already carries.
    category_practice_interviews: dict[str, list[dict]] = {}

    all_speech_entries: list[dict] = []
    all_repetition_entries: list[dict] = []
    all_camera_metrics: list[dict] = []

    for interview in interviews:
        answered_questions = [q for q in interview.questions if q.answer is not None]
        total_questions_answered += len(answered_questions)

        if interview.overall_score is not None:
            progress.append(
                {
                    "interview_id": interview.id,
                    "date": interview.completed_at,
                    "score": interview.overall_score,
                }
            )

        recent_interviews.append(
            {
                "id": interview.id,
                "date": interview.completed_at,
                "role": interview.role,
                "difficulty": interview.difficulty,
                "score": interview.overall_score,
                "question_count": len(interview.questions),
            }
        )

        for focus_category in interview.focus_categories or []:
            category_practice_interviews.setdefault(focus_category, []).append(
                {"interview_id": interview.id, "date": interview.completed_at}
            )

        # interview-scoped counterpart to category_totals, used only to
        # derive this interview's one trend point per category below.
        interview_category_totals: dict[str, dict] = {}
        for question in answered_questions:
            evaluation = question.answer.evaluation
            if not evaluation:
                continue
            for category in evaluation.get("category_scores", []):
                max_score = category["max_score"]
                if not max_score:
                    continue
                ratio = category["score"] / max_score
                bucket = category_totals.setdefault(
                    category["category"],
                    {"label": category["label"], "ratio_sum": 0.0, "count": 0},
                )
                bucket["ratio_sum"] += ratio
                bucket["count"] += 1
                interview_bucket = interview_category_totals.setdefault(
                    category["category"], {"ratio_sum": 0.0, "count": 0}
                )
                interview_bucket["ratio_sum"] += ratio
                interview_bucket["count"] += 1

        for key, bucket in interview_category_totals.items():
            category_trends.setdefault(key, []).append(
                {
                    "interview_id": interview.id,
                    "date": interview.completed_at,
                    "score": round((bucket["ratio_sum"] / bucket["count"]) * 100, 1),
                }
            )

        speech_entries, repetition_entries = _communication_inputs(interview)
        interview_report = build_communication_report(speech_entries, repetition_entries, interview.camera_metrics)
        if interview_report and interview_report["overall_score"] is not None:
            communication_progress.append(
                {
                    "interview_id": interview.id,
                    "date": interview.completed_at,
                    "score": interview_report["overall_score"],
                }
            )
        if interview_report:
            for category in interview_report["categories"]:
                comm_category_trends.setdefault(category["key"], []).append(
                    {
                        "interview_id": interview.id,
                        "date": interview.completed_at,
                        "score": category["score"],
                    }
                )
        all_speech_entries.extend(speech_entries)
        all_repetition_entries.extend(repetition_entries)
        if interview.camera_metrics:
            all_camera_metrics.append(interview.camera_metrics)

    category_breakdown = sorted(
        (
            {
                "category": key,
                "label": bucket["label"],
                "average_score": round((bucket["ratio_sum"] / bucket["count"]) * 100, 1),
                "sample_count": bucket["count"],
            }
            for key, bucket in category_totals.items()
        ),
        key=lambda c: c["category"],
    )

    recent_interviews.sort(key=lambda r: r["date"] or datetime.min, reverse=True)

    # --- Aggregate communication/presentation score, pooled across every
    # interview's answers rather than averaging per-interview averages, so
    # it reflects the same "one number per raw data point" methodology the
    # single-interview report already uses (see communication_feedback.report).
    aggregate_report = build_communication_report(
        all_speech_entries, all_repetition_entries, _average_camera_metrics(all_camera_metrics)
    )
    communication_score = aggregate_report["overall_score"] if aggregate_report else None
    presentation_score = None
    if aggregate_report:
        presentation_category = next(
            (c for c in aggregate_report["categories"] if c["key"] == "presentation"), None
        )
        if presentation_category:
            presentation_score = presentation_category["score"]

    technical_score = round(sum(scores) / len(scores), 1) if scores else None
    if technical_score is None:
        overall_score = None
    elif communication_score is None:
        overall_score = round(technical_score)
    else:
        overall_score = round(
            technical_score * _TECHNICAL_WEIGHT + communication_score * _COMMUNICATION_WEIGHT
        )

    # --- Recurring strengths/weaknesses: rubric categories with enough
    # samples to call a pattern, plus (when available) the aggregate
    # communication report's own already-specific narrative lines.
    qualifying_categories = [c for c in category_breakdown if c["sample_count"] >= MIN_CATEGORY_SAMPLES]
    recurring_strengths = [
        f"{c['label']} ({c['average_score']}% avg across {c['sample_count']} answers)"
        for c in qualifying_categories
        if c["average_score"] >= STRONG_RATIO * 100
    ]
    recurring_weaknesses = [
        f"{c['label']} ({c['average_score']}% avg across {c['sample_count']} answers)"
        for c in qualifying_categories
        if c["average_score"] <= WEAK_RATIO * 100
    ]
    if aggregate_report:
        recurring_strengths.extend(aggregate_report["strengths"][:2])
        recurring_weaknesses.extend(aggregate_report["improvements"][:2])

    # --- Recommendations: the communication report's own (already concrete,
    # data-driven) suggestions, plus one pointed at the single weakest
    # recurring rubric category, if any qualify.
    recommendations: list[str] = []
    if aggregate_report:
        recommendations.extend(aggregate_report["recommendations"][:2])
    weak_ranked = sorted(
        (c for c in qualifying_categories if c["average_score"] <= WEAK_RATIO * 100),
        key=lambda c: c["average_score"],
    )
    if weak_ranked:
        weakest = weak_ranked[0]
        description = CATEGORY_DESCRIPTIONS.get(weakest["category"], "")
        recommendations.append(
            f"Your most recurring weak area is {weakest['label']} "
            f"({weakest['average_score']}% avg across {weakest['sample_count']} answers). "
            f"{description} Focus your next few practice answers here."
        )
    recommendations = recommendations[:4]

    practice_plan = _build_practice_plan(
        total_interviews=len(interviews),
        qualifying_categories=qualifying_categories,
        aggregate_report=aggregate_report,
        category_trends=category_trends,
        comm_category_trends=comm_category_trends,
        camera_interview_count=len(all_camera_metrics),
        category_practice_interviews=category_practice_interviews,
    )

    return {
        "overview": {
            "total_interviews": len(interviews),
            "average_score": technical_score,
            "highest_score": max(scores) if scores else None,
            "total_questions_answered": total_questions_answered,
        },
        "progress": progress,
        "communication_progress": communication_progress,
        "recent_interviews": recent_interviews[:RECENT_INTERVIEWS_LIMIT],
        "category_breakdown": category_breakdown,
        "scores": {
            "overall_score": overall_score,
            "technical_score": technical_score,
            "communication_score": communication_score,
            "presentation_score": presentation_score,
        },
        "recurring_strengths": recurring_strengths,
        "recurring_weaknesses": recurring_weaknesses,
        "weak_categories": weak_ranked[:3],
        "recommendations": recommendations,
        "practice_plan": practice_plan,
    }
