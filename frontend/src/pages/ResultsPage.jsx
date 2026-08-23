import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { getInterview } from '../api/interviews'
import CommunicationResults from '../components/CommunicationResults'
import ErrorState from '../components/ErrorState'
import { SkeletonPage } from '../components/Skeleton'
import { categoryLabel } from '../constants/rubricCategories'

// Compact per-question communication strip — only rendered when this
// specific answer has speech_metrics attached (i.e. speech analysis was
// active for it). Interview-level aggregation/scoring lives in
// CommunicationResults; this is the per-question breakdown.
function AnswerCommunicationBadges({ speechMetrics, repetitionAnalysis }) {
  if (!speechMetrics) return null

  const badges = []
  if (speechMetrics.transcript_available && speechMetrics.words_per_minute != null) {
    badges.push(`${speechMetrics.words_per_minute} wpm`)
  }
  badges.push(`${formatSeconds(speechMetrics.duration_seconds)} speaking`)
  if (speechMetrics.filler_word_count > 0) {
    badges.push(`${speechMetrics.filler_word_count} filler word${speechMetrics.filler_word_count === 1 ? '' : 's'}`)
  }
  if (speechMetrics.pause_count > 0) {
    badges.push(`${speechMetrics.pause_count} pause${speechMetrics.pause_count === 1 ? '' : 's'}`)
  }
  if (repetitionAnalysis?.total_estimated_repetitions > 0) {
    badges.push(`${repetitionAnalysis.total_estimated_repetitions} repetition(s) (est.)`)
  }

  return (
    <div className="mb-3 flex flex-wrap gap-1.5">
      {badges.map((badge, i) => (
        <span
          key={i}
          className="rounded-full border border-border bg-surface-2 px-2 py-0.5 text-[11px] text-ink-muted"
        >
          {badge}
        </span>
      ))}
    </div>
  )
}

function formatSeconds(seconds) {
  const mins = Math.floor(seconds / 60)
  const secs = Math.round(seconds % 60)
  return mins > 0 ? `${mins}m ${secs}s` : `${secs}s`
}

function CategoryScoreBar({ category }) {
  const percent = (category.score / category.max_score) * 100
  return (
    <div>
      <div className="mb-1 flex items-center justify-between text-xs text-ink-muted">
        <span>{category.label}</span>
        <span className="font-medium text-ink">
          {category.score}/{category.max_score}
        </span>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-surface-2">
        <div
          className="h-full rounded-full bg-accent"
          style={{ width: `${percent}%` }}
        />
      </div>
    </div>
  )
}

function ResultsPage() {
  const { interviewId } = useParams()
  const navigate = useNavigate()

  const [interview, setInterview] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    getInterview(interviewId)
      .then(setInterview)
      .catch((err) => setError(err.message))
  }, [interviewId])

  if (error) {
    return <ErrorState message={error} />
  }

  if (!interview) {
    return <SkeletonPage />
  }

  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="mb-1 text-2xl font-semibold text-ink">Results</h1>
      <p className="mb-1 text-ink-muted">
        {interview.role} &middot; {interview.difficulty} &middot;{' '}
        {interview.status}
      </p>
      <p className="mb-8 text-sm text-accent">
        {interview.focus_categories?.length > 0 &&
          `Focused practice: ${interview.focus_categories.map(categoryLabel).join(', ')}`}
      </p>

      {typeof interview.overall_score === 'number' && (
        <div className="mb-8 flex items-center gap-3 rounded-xl border border-accent-border bg-accent-soft p-4">
          <span className="text-3xl font-semibold text-accent">
            {interview.overall_score}
            <span className="text-lg text-accent/60">/100</span>
          </span>
          <span className="text-sm text-accent">Overall score</span>
        </div>
      )}

      {interview.resume && (
        <div className="mb-8 rounded-xl border border-accent-border bg-accent-soft p-4">
          <h2 className="mb-2 text-sm font-semibold text-ink">
            Based on your resume: {interview.resume.original_filename}
          </h2>
          <p className="mb-3 text-sm text-ink-muted">
            {interview.resume.analysis.summary}
          </p>
          <div className="grid gap-4 sm:grid-cols-2">
            {interview.resume.analysis.strong_areas.length > 0 && (
              <div>
                <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-accent">
                  Resume strengths
                </h3>
                <ul className="list-disc space-y-1 pl-5 text-sm text-ink-muted">
                  {interview.resume.analysis.strong_areas.map((item, i) => (
                    <li key={i}>{item}</li>
                  ))}
                </ul>
              </div>
            )}
            {interview.resume.analysis.missing_details.length > 0 && (
              <div>
                <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-accent">
                  Could be stronger
                </h3>
                <ul className="list-disc space-y-1 pl-5 text-sm text-ink-muted">
                  {interview.resume.analysis.missing_details.map((item, i) => (
                    <li key={i}>{item}</li>
                  ))}
                </ul>
              </div>
            )}
            {interview.resume.analysis.key_projects.length > 0 && (
              <div>
                <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-accent">
                  Key projects
                </h3>
                <ul className="list-disc space-y-1 pl-5 text-sm text-ink-muted">
                  {interview.resume.analysis.key_projects.map((item, i) => (
                    <li key={i}>{item}</li>
                  ))}
                </ul>
              </div>
            )}
            {interview.resume.analysis.key_technologies.length > 0 && (
              <div>
                <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-accent">
                  Key technologies
                </h3>
                <div className="flex flex-wrap gap-1">
                  {interview.resume.analysis.key_technologies.map((tech, i) => (
                    <span
                      key={i}
                      className="rounded-full bg-surface-2 px-2 py-0.5 text-xs text-ink-muted"
                    >
                      {tech}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {interview.summary_feedback && (
        <div className="surface-card mb-8 p-4">
          <h2 className="mb-2 text-sm font-semibold text-ink">Summary</h2>
          <p className="text-ink-muted">{interview.summary_feedback}</p>
        </div>
      )}

      {(interview.strengths?.length > 0 || interview.weaknesses?.length > 0) && (
        <div className="mb-8 grid gap-6 sm:grid-cols-2">
          {interview.strengths?.length > 0 && (
            <div className="rounded-xl border border-success/25 bg-success-soft p-4">
              <h2 className="mb-2 text-sm font-semibold text-success">
                Strongest questions
              </h2>
              <ul className="list-disc space-y-1 pl-5 text-sm text-ink">
                {interview.strengths.map((strength, index) => (
                  <li key={index}>{strength}</li>
                ))}
              </ul>
            </div>
          )}
          {interview.weaknesses?.length > 0 && (
            <div className="rounded-xl border border-warning/25 bg-warning-soft p-4">
              <h2 className="mb-2 text-sm font-semibold text-warning">
                Weakest questions
              </h2>
              <ul className="list-disc space-y-1 pl-5 text-sm text-ink">
                {interview.weaknesses.map((weakness, index) => (
                  <li key={index}>{weakness}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      <CommunicationResults interview={interview} />

      <div className="flex flex-col gap-6">
        {interview.questions.map((question, index) => {
          const evaluation = question.answer?.evaluation

          return (
            <div key={question.id} className="surface-card p-4">
              <div className="mb-2 flex items-start justify-between gap-3">
                <div>
                  <p className="font-medium text-ink">
                    {index + 1}. {question.text}
                  </p>
                  <div className="mt-1 flex flex-wrap gap-1.5">
                    {question.source === 'resume' && (
                      <span className="inline-block rounded-full bg-accent-soft px-2 py-0.5 text-[11px] font-medium uppercase tracking-wide text-accent">
                        From your resume
                        {question.resume_topic ? ` · ${question.resume_topic}` : ''}
                      </span>
                    )}
                    {evaluation && (
                      <span className="inline-block rounded-full bg-surface-2 px-2 py-0.5 text-[11px] font-medium uppercase tracking-wide text-ink-muted">
                        {evaluation.question_type}
                      </span>
                    )}
                  </div>
                </div>
                {typeof question.answer?.total_score === 'number' && (
                  <span className="shrink-0 rounded-full bg-surface-2 px-2.5 py-1 text-xs font-semibold text-ink">
                    {question.answer.total_score}/100
                  </span>
                )}
              </div>

              <p className="mb-3 text-ink-muted">
                {question.answer?.text || (
                  <span className="italic text-ink-faint">No answer given</span>
                )}
              </p>

              <AnswerCommunicationBadges
                speechMetrics={question.answer?.speech_metrics}
                repetitionAnalysis={question.answer?.repetition_analysis}
              />

              {evaluation && (
                <div className="flex flex-col gap-4">
                  {evaluation.note && (
                    <p className="rounded-md bg-warning-soft p-2 text-xs italic text-warning">
                      {evaluation.note}
                    </p>
                  )}

                  <div className="grid gap-3 rounded-md bg-surface-2 p-3 sm:grid-cols-2">
                    {evaluation.category_scores.map((category) => (
                      <CategoryScoreBar key={category.category} category={category} />
                    ))}
                  </div>

                  <div className="grid gap-4 sm:grid-cols-2">
                    {evaluation.strengths.length > 0 && (
                      <div>
                        <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-success">
                          Strengths
                        </h3>
                        <ul className="list-disc space-y-1 pl-5 text-sm text-ink-muted">
                          {evaluation.strengths.map((strength, i) => (
                            <li key={i}>{strength}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {evaluation.weaknesses.length > 0 && (
                      <div>
                        <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-warning">
                          Weaknesses
                        </h3>
                        <ul className="list-disc space-y-1 pl-5 text-sm text-ink-muted">
                          {evaluation.weaknesses.map((weakness, i) => (
                            <li key={i}>{weakness}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>

                  {evaluation.improvement_suggestions.length > 0 && (
                    <div>
                      <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-accent">
                        Improvement suggestions
                      </h3>
                      <ul className="list-disc space-y-1 pl-5 text-sm text-ink-muted">
                        {evaluation.improvement_suggestions.map((suggestion, i) => (
                          <li key={i}>{suggestion}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {evaluation.stronger_answer_example && (
                    <div>
                      <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-ink-faint">
                        What a stronger answer looks like
                      </h3>
                      <p className="rounded-md bg-surface-2 p-3 text-sm text-ink-muted">
                        {evaluation.stronger_answer_example}
                      </p>
                    </div>
                  )}
                </div>
              )}
            </div>
          )
        })}
      </div>

      <button onClick={() => navigate('/dashboard')} className="btn btn-primary mt-8">
        Go to Dashboard
      </button>
    </div>
  )
}

export default ResultsPage
