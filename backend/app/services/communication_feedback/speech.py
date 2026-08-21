# Deterministic, threshold-based feedback only — no AI call, no inference
# about emotion, confidence, honesty, personality, or medical conditions.
# Repeated words / pauses are described only as observable speech patterns,
# never diagnosed (e.g. never labeled as stuttering).

_FAST_WPM = 160
_SLOW_WPM = 110
_FILLER_RATIO_THRESHOLD = 0.04
_LONG_PAUSE_THRESHOLD = 3
_PAUSE_THRESHOLD = 6
_REPEATED_WORD_THRESHOLD = 3
_MIN_SUBSTANTIAL_WORDS = 15
_MAX_COMFORTABLE_DURATION_SECONDS = 180


def build_speech_feedback(metrics: dict) -> list[str]:
    feedback: list[str] = []

    transcript_available = metrics.get("transcript_available", False)
    wpm = metrics.get("words_per_minute")
    transcript_word_count = metrics.get("transcript_word_count")
    filler_word_count = metrics.get("filler_word_count") or 0
    pause_count = metrics.get("pause_count") or 0
    long_pause_count = metrics.get("long_pause_count") or 0
    repeated_word_count = metrics.get("repeated_word_count") or 0
    duration_seconds = metrics.get("duration_seconds")

    if transcript_available and wpm is not None:
        if wpm > _FAST_WPM:
            feedback.append(
                "Your speaking pace was relatively fast. Consider slowing "
                "down slightly when explaining technical concepts."
            )
        elif wpm < _SLOW_WPM:
            feedback.append(
                "Your speaking pace was relatively slow. A slightly "
                "quicker pace can help keep your answer feeling engaging."
            )

    if transcript_available and transcript_word_count:
        ratio = filler_word_count / transcript_word_count
        if ratio > _FILLER_RATIO_THRESHOLD:
            feedback.append(
                "Several filler words were detected. Try pausing briefly "
                "instead of using filler words."
            )

    if long_pause_count >= _LONG_PAUSE_THRESHOLD:
        feedback.append(
            "A number of long pauses were detected in your answer. Brief "
            "pauses to gather your thoughts are natural, but frequent long "
            "pauses can break up the flow of your answer."
        )
    elif pause_count >= _PAUSE_THRESHOLD:
        feedback.append(
            "Several pauses were detected while you were answering. "
            "Practicing the answer out loud beforehand can help it flow "
            "more smoothly."
        )

    if repeated_word_count >= _REPEATED_WORD_THRESHOLD:
        feedback.append(
            "Some words were repeated in your answer — this is a common, "
            "observable speech pattern. Pausing briefly instead of "
            "repeating a word can make your answer easier to follow."
        )

    if transcript_available and transcript_word_count is not None:
        if transcript_word_count < _MIN_SUBSTANTIAL_WORDS:
            feedback.append(
                "Your answer was quite brief. Try expanding with a "
                "specific example or a bit more detail."
            )

    if duration_seconds is not None and duration_seconds > _MAX_COMFORTABLE_DURATION_SECONDS:
        feedback.append(
            "Your answer ran quite long. Aim to be a bit more concise "
            "and focus on the key points."
        )

    return feedback
