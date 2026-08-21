# Combines per-answer speech metrics (speech.py), the per-answer repetition
# heuristic (stutter.py), and the whole-session camera metrics (camera.py)
# into one transparent Communication Score.
#
# Every category is a simple, documented, threshold-based formula computed
# only from numbers the browser already measured — no AI call, no inference
# about emotion, confidence, honesty, personality, or mental state. A
# category is left out entirely (never guessed at) when its underlying data
# wasn't collected for this interview, and the whole report is omitted when
# nothing was collected at all.

_PACE_IDEAL_LOW = 110
_PACE_IDEAL_HIGH = 160
_MIN_SUBSTANTIAL_WORDS = 15

# Relative weight of each category out of 100 when every category has data;
# renormalized over whichever subset is actually available for a given
# interview (e.g. camera-only, speech-only, or partial combinations).
_WEIGHTS = {
    "pace": 20,
    "fillers": 20,
    "fluency": 20,
    "pausing": 15,
    "presentation": 25,
}


def _clamp_round(value: float, lo: float = 0, hi: float = 100) -> int:
    return round(max(lo, min(hi, value)))


def _score_pace(wpm: float) -> int:
    if _PACE_IDEAL_LOW <= wpm <= _PACE_IDEAL_HIGH:
        return 100
    distance = _PACE_IDEAL_LOW - wpm if wpm < _PACE_IDEAL_LOW else wpm - _PACE_IDEAL_HIGH
    return _clamp_round(100 - distance * 2)


def _score_fillers(filler_count: int, word_count: int) -> int:
    if not word_count:
        return 100
    ratio_pct = (filler_count / word_count) * 100
    return _clamp_round(100 - ratio_pct * 10)


def _score_fluency(repetitions: int, word_count: int) -> int:
    if not word_count:
        return 100
    ratio_pct = (repetitions / word_count) * 100
    return _clamp_round(100 - ratio_pct * 12)


def _score_pausing(pause_count: int, long_pause_count: int) -> int:
    return _clamp_round(100 - long_pause_count * 15 - max(0, pause_count - 3) * 5)


def _score_presentation(face_visible_pct: float, attention_pct: float, head_movement: float) -> int:
    base = 0.6 * face_visible_pct + 0.4 * attention_pct
    penalty = max(0, head_movement - 50) * 0.3
    return _clamp_round(base - penalty)


def _narrative(
    by_key: dict,
    avg_wpm,
    total_filler: int,
    total_words: int,
    total_repetitions: int,
    total_pause: int,
    total_long_pause: int,
    brief_answer_count: int,
    camera_metrics: dict | None,
    repeated_examples: list[str],
) -> tuple[list[str], list[str], list[str], dict[str, str]]:
    strengths: list[str] = []
    improvements: list[str] = []
    recommendations: list[str] = []
    # Same recommendation strings as `recommendations` above, but keyed by
    # category so callers that need to attach one specific, already-worded
    # tip to one specific category (the dashboard's Practice Plan — see
    # app.crud.dashboard) don't have to re-derive it. setdefault() so the
    # first (primary) recommendation for a category wins if a category ever
    # appends more than one (presentation can, below).
    recommendations_by_category: dict[str, str] = {}

    if "pace" in by_key:
        if by_key["pace"]["score"] >= 85:
            strengths.append(f"Your speaking pace ({avg_wpm} wpm) stayed in a comfortable, easy-to-follow range.")
        elif avg_wpm > _PACE_IDEAL_HIGH:
            improvements.append(f"Your speaking pace was fast (about {avg_wpm} words per minute).")
            tip = "Your speaking pace was slightly fast. Try adding short pauses between major points."
            recommendations.append(tip)
            recommendations_by_category.setdefault("pace", tip)
        elif avg_wpm < _PACE_IDEAL_LOW:
            improvements.append(f"Your speaking pace was slow (about {avg_wpm} words per minute).")
            tip = (
                "Your speaking pace was on the slow side. A slightly quicker, more energetic pace "
                "can help your answers feel more engaging."
            )
            recommendations.append(tip)
            recommendations_by_category.setdefault("pace", tip)

    if "fillers" in by_key:
        pct = round((total_filler / total_words) * 100, 1) if total_words else 0
        if by_key["fillers"]["score"] >= 85:
            strengths.append(f"You used very few filler words ({total_filler} across all your answers).")
        else:
            improvements.append(f"Filler words made up about {pct}% of what you said ({total_filler} total).")
            tip = "You used filler words frequently. Replace them with a brief pause when collecting your thoughts."
            recommendations.append(tip)
            recommendations_by_category.setdefault("fillers", tip)

    if "fluency" in by_key:
        if by_key["fluency"]["score"] >= 85:
            strengths.append("Your answers flowed smoothly, with very few repeated words or phrases.")
        else:
            improvements.append(f"An estimated {total_repetitions} repeated word/phrase pattern(s) were detected.")
            example_hint = f' (e.g. "{repeated_examples[0]}")' if repeated_examples else ""
            tip = (
                f"Some words or phrases were repeated{example_hint}. Slowing down slightly can help "
                "you speak in fuller, more complete sentences."
            )
            recommendations.append(tip)
            recommendations_by_category.setdefault("fluency", tip)

    if "pausing" in by_key:
        if by_key["pausing"]["score"] >= 85:
            strengths.append("Your pausing was natural and didn't disrupt the flow of your answers.")
        elif total_long_pause > 0:
            improvements.append(f"{total_long_pause} longer pause(s) (4s+) were detected.")
            tip = (
                "A few long pauses broke up your answers. Practicing your key points out loud "
                "beforehand can help them come more fluidly."
            )
            recommendations.append(tip)
            recommendations_by_category.setdefault("pausing", tip)
        else:
            improvements.append(f"{total_pause} pause(s) were detected during your answers.")
            tip = (
                "You paused somewhat frequently. Outlining your answer's structure before speaking "
                "can reduce mid-answer hesitation."
            )
            recommendations.append(tip)
            recommendations_by_category.setdefault("pausing", tip)

    if "presentation" in by_key and camera_metrics:
        face_pct = camera_metrics.get("face_visible_percentage")
        attention_pct = camera_metrics.get("camera_attention_percentage")
        if face_pct is not None and face_pct >= 85:
            strengths.append(f"Your face was detected consistently ({face_pct}% of the time), which is good.")
        elif face_pct is not None:
            improvements.append(f"Your face was only visible {face_pct}% of the time.")
            tip = (
                "Your face left the camera frame at times. Try positioning your camera so your "
                "whole face stays in view throughout your answers."
            )
            recommendations.append(tip)
            recommendations_by_category.setdefault("presentation", tip)
        if attention_pct is not None and attention_pct < 70:
            improvements.append(f"Your gaze was toward the camera only {attention_pct}% of the time.")
            tip = (
                "Try keeping your gaze closer to the camera when answering — it helps simulate "
                "direct eye contact with the interviewer."
            )
            recommendations.append(tip)
            recommendations_by_category.setdefault("presentation", tip)
        elif attention_pct is not None and face_pct is not None and face_pct >= 85:
            tip = (
                "Your face was detected consistently, which is good. Try keeping your gaze closer "
                "to the camera when answering."
            )
            recommendations.append(tip)
            recommendations_by_category.setdefault("presentation", tip)

    if brief_answer_count:
        plural = "s were" if brief_answer_count != 1 else " was"
        improvements.append(f"{brief_answer_count} answer{plural} quite brief.")
        recommendations.append(
            "A few of your answers were quite short. Adding a specific example or a bit more "
            "detail can make them more convincing."
        )

    if not strengths:
        strengths.append("You completed the interview with communication analysis enabled, giving us data to work with.")
    if not improvements:
        improvements.append("No notable communication issues were detected — nice work.")
    if not recommendations:
        recommendations.append("Keep practicing to stay comfortable speaking under interview conditions.")

    return strengths, improvements, recommendations, recommendations_by_category


def build_communication_report(
    speech_entries: list[dict],
    repetition_entries: list[dict],
    camera_metrics: dict | None,
) -> dict | None:
    """speech_entries: one raw speech_metrics dict per answered question that
    has them (order doesn't matter). repetition_entries: the matching
    estimate_disfluencies() result for each entry in speech_entries (same
    length, `{}` where unavailable). camera_metrics: the whole-session
    camera metrics dict, or None if camera analysis wasn't used.

    Returns None when there is nothing measurable at all — never a report
    built from invented numbers.
    """
    if not speech_entries and not camera_metrics:
        return None

    total_duration = sum(e.get("duration_seconds") or 0 for e in speech_entries)
    total_filler = sum(e.get("filler_word_count") or 0 for e in speech_entries)
    total_pause = sum(e.get("pause_count") or 0 for e in speech_entries)
    total_long_pause = sum(e.get("long_pause_count") or 0 for e in speech_entries)

    filler_breakdown: dict[str, int] = {}
    for entry in speech_entries:
        for word, count in (entry.get("filler_words") or {}).items():
            filler_breakdown[word] = filler_breakdown.get(word, 0) + count

    with_transcript = [
        e for e in speech_entries if e.get("transcript_available") and e.get("words_per_minute") is not None
    ]
    total_words = sum(e.get("transcript_word_count") or 0 for e in with_transcript)
    avg_wpm = (
        round(sum(e["words_per_minute"] for e in with_transcript) / len(with_transcript))
        if with_transcript
        else None
    )
    brief_answer_count = sum(
        1 for e in with_transcript if (e.get("transcript_word_count") or 0) < _MIN_SUBSTANTIAL_WORDS
    )

    total_repetitions = sum(r.get("total_estimated_repetitions") or 0 for r in repetition_entries)
    repeated_examples = [ex for r in repetition_entries for ex in (r.get("repeated_examples") or [])][:6]

    categories: list[dict] = []
    weighted_sum = 0.0
    weight_total = 0.0

    def add_category(key: str, label: str, score: int, description: str) -> None:
        nonlocal weighted_sum, weight_total
        categories.append({"key": key, "label": label, "score": score, "description": description})
        weighted_sum += score * _WEIGHTS[key]
        weight_total += _WEIGHTS[key]

    if with_transcript and avg_wpm is not None:
        add_category(
            "pace",
            "Speaking Pace",
            _score_pace(avg_wpm),
            f"Averaged {avg_wpm} words per minute across {len(with_transcript)} timed answer(s) "
            f"(a comfortable pace is roughly {_PACE_IDEAL_LOW}-{_PACE_IDEAL_HIGH} wpm).",
        )

    if with_transcript and total_words:
        pct = round((total_filler / total_words) * 100, 1)
        add_category(
            "fillers",
            "Filler Words",
            _score_fillers(total_filler, total_words),
            f'Filler words ("um", "like", ...) made up about {pct}% of the {total_words} words '
            f"you spoke ({total_filler} total).",
        )
        add_category(
            "fluency",
            "Clarity / Fluency",
            _score_fluency(total_repetitions, total_words),
            f"Detected an estimated {total_repetitions} repeated word/phrase pattern(s) across "
            "your answers (a heuristic proxy for verbal disfluency — see note below).",
        )

    if speech_entries and total_duration > 0:
        add_category(
            "pausing",
            "Pausing",
            _score_pausing(total_pause, total_long_pause),
            f"{total_pause} pause(s) detected ({total_long_pause} longer than 4s) across "
            f"{round(total_duration)}s of speaking.",
        )

    if camera_metrics:
        add_category(
            "presentation",
            "Presentation / Camera Presence",
            _score_presentation(
                camera_metrics.get("face_visible_percentage", 0),
                camera_metrics.get("camera_attention_percentage", 0),
                camera_metrics.get("head_movement_score", 0),
            ),
            f"Your face was visible {camera_metrics.get('face_visible_percentage')}% of the time "
            f"and your gaze stayed toward the camera {camera_metrics.get('camera_attention_percentage')}% "
            "of the time.",
        )

    if not categories:
        return None

    overall_score = round(weighted_sum / weight_total) if weight_total else None
    by_key = {c["key"]: c for c in categories}
    strengths, improvements, recommendations, recommendations_by_category = _narrative(
        by_key,
        avg_wpm,
        total_filler,
        total_words,
        total_repetitions,
        total_pause,
        total_long_pause,
        brief_answer_count,
        camera_metrics,
        repeated_examples,
    )

    return {
        "overall_score": overall_score,
        "categories": categories,
        "speech_summary": (
            {
                "total_duration_seconds": round(total_duration, 1),
                "total_words_spoken": total_words or None,
                "average_words_per_minute": avg_wpm,
                "filler_word_count": total_filler,
                "filler_word_breakdown": filler_breakdown,
                "pause_count": total_pause,
                "long_pause_count": total_long_pause,
                "estimated_repetition_count": total_repetitions,
                "repeated_examples": repeated_examples,
                "brief_answer_count": brief_answer_count,
                "answers_with_transcript": len(with_transcript),
                "answers_measured": len(speech_entries),
            }
            if speech_entries
            else None
        ),
        "camera_summary": camera_metrics,
        "strengths": strengths,
        "improvements": improvements,
        "recommendations": recommendations,
        # category key -> the one recommendation string above that pertains
        # to it (a subset of "categories" — only present when that category
        # scored low enough for _narrative to have generated a tip). Lets
        # callers attach one specific, evidence-grounded action to one
        # specific category instead of a flat list (see the Practice Plan
        # in app.crud.dashboard).
        "recommendations_by_category": recommendations_by_category,
        "note": (
            "All metrics are computed locally in your browser from timing, word counts, and face-"
            "position geometry. This is not an assessment of your emotions, confidence, honesty, "
            "or personality, and the repetition estimate is a heuristic, not a medical or "
            "diagnostic evaluation."
        ),
    }
