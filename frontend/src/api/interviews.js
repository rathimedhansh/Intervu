import { apiFetch } from './client'

export function createInterview(role, difficulty, questionCount, resumeId, focusCategories) {
  return apiFetch('/interviews/', {
    method: 'POST',
    body: JSON.stringify({
      role,
      difficulty,
      question_count: questionCount,
      resume_id: resumeId ?? null,
      focus_categories: focusCategories?.length > 0 ? focusCategories : null,
    }),
  })
}

export function listInterviews() {
  return apiFetch('/interviews/')
}

export function getInterview(interviewId) {
  return apiFetch(`/interviews/${interviewId}`)
}

export function deleteInterview(interviewId) {
  return apiFetch(`/interviews/${interviewId}`, { method: 'DELETE' })
}

export function completeInterview(interviewId, cameraMetrics) {
  return apiFetch(`/interviews/${interviewId}/complete`, {
    method: 'POST',
    body: JSON.stringify({ camera_metrics: cameraMetrics ?? null }),
  })
}

export function submitAnswer(interviewId, questionId, text, speechMetrics) {
  return apiFetch(`/interviews/${interviewId}/questions/${questionId}/answer`, {
    method: 'POST',
    body: JSON.stringify({ text, speech_metrics: speechMetrics ?? null }),
  })
}

// Conversational interview flow: saves + evaluates the answer, then
// returns the dynamically-generated next question (or is_complete: true
// once the interview's question budget has been reached).
export function respondToQuestion(interviewId, questionId, text, speechMetrics) {
  return apiFetch(`/interviews/${interviewId}/questions/${questionId}/respond`, {
    method: 'POST',
    body: JSON.stringify({ text, speech_metrics: speechMetrics ?? null }),
  })
}
