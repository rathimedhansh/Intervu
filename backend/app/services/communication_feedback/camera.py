# Deterministic, threshold-based feedback only — no AI call, no inference
# about emotion, confidence, honesty, personality, or attractiveness.
# Metrics are purely geometric (face presence/position), never identity.

_LOW_FACE_VISIBLE_PCT = 70
_LOW_ATTENTION_PCT = 60
_HIGH_HEAD_MOVEMENT = 70
_HIGH_LOOK_AWAY_COUNT = 8
_MULTI_FACE_PCT_THRESHOLD = 5


def build_camera_feedback(metrics: dict) -> list[str]:
    feedback: list[str] = []

    face_visible = metrics.get("face_visible_percentage")
    attention = metrics.get("camera_attention_percentage")
    head_movement = metrics.get("head_movement_score")
    look_away_count = metrics.get("look_away_count")
    multiple_faces_pct = metrics.get("multiple_faces_percentage")

    if face_visible is not None and face_visible < _LOW_FACE_VISIBLE_PCT:
        feedback.append(
            "Your face was outside the camera frame for part of the "
            "interview. Try positioning yourself so your face stays "
            "within the frame throughout your answers."
        )

    if attention is not None and attention < _LOW_ATTENTION_PCT:
        feedback.append(
            "You looked away from the camera fairly often. Looking "
            "toward the camera more consistently can make your answers "
            "feel more directly addressed to the interviewer."
        )

    if head_movement is not None and head_movement > _HIGH_HEAD_MOVEMENT:
        feedback.append(
            "A relatively high amount of head movement was detected. "
            "Keeping a steadier position can make your presentation feel "
            "more composed."
        )

    if look_away_count is not None and look_away_count >= _HIGH_LOOK_AWAY_COUNT:
        feedback.append(
            "You looked away from the camera frequently during the "
            "interview. Try to keep your gaze toward the camera for "
            "longer stretches while answering."
        )

    if multiple_faces_pct is not None and multiple_faces_pct >= _MULTI_FACE_PCT_THRESHOLD:
        feedback.append(
            "More than one face was detected in the camera frame for "
            "part of the interview. Make sure you're the only person "
            "visible while answering."
        )

    return feedback
