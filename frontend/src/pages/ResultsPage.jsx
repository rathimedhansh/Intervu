import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { getInterview } from '../api/interviews'
import CommunicationResults from '../components/CommunicationResults'
import ErrorState from '../components/ErrorState'
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
          className="rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5 text-[11px] text-slate-500"
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
      <div className="mb-1 flex items-center justify-between text-xs text-slate-600">
        <span>{category.label}</span>
        <span className="font-medium text-slate-700">
          {category.score}/{category.max_score}
        </span>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-200">
        <div
          className="h-full rounded-full bg-indigo-500"
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
    return <p className="text-slate-600">Loading results...</p>
  }

  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="mb-1 text-2xl font-semibold text-slate-900">Results</h1>
      <p className="mb-1 text-slate-600">
        {interview.role} &middot; {interview.difficulty} &middot;{' '}
        {interview.status}
      </p>
      <p className="mb-8 text-sm text-indigo-600">
        {interview.focus_categories?.length > 0 &&
          `Focused practice: ${interview.focus_categories.map(categoryLabel).join(', ')}`}
      </p>

      {typeof interview.overall_score === 'number' && (
        <div className="mb-8 flex items-center gap-3 rounded-lg border border-indigo-200 bg-indigo-50 p-4">
          <span className="text-3xl font-semibold text-indigo-700">
            {interview.overall_score}
            <span className="text-lg text-indigo-400">/100</span>
          </span>
          <span className="text-sm text-indigo-700">Overall score</span>
        </div>
      )}

      {interview.resume && (
        <div className="mb-8 rounded-lg border border-indigo-200 bg-indigo-50 p-4">
          <h2 className="mb-2 text-sm font-semibold text-indigo-900">
            Based on your resume: {interview.resume.original_filename}
          </h2>
          <p className="mb-3 text-sm text-indigo-800">
            {interview.resume.analysis.summary}
          </p>
          <div className="grid gap-4 sm:grid-cols-2">
            {interview.resume.analysis.strong_areas.length > 0 && (
              <div>
                <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-indigo-700">
                  Resume strengths
                </h3>
                <ul className="list-disc space-y-1 pl-5 text-sm text-indigo-800">
                  {interview.resume.analysis.strong_areas.map((item, i) => (
                    <li key={i}>{item}</li>
                  ))}
                </ul>
              </div>
            )}
            {interview.resume.analysis.missing_details.length > 0 && (
              <div>
                <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-indigo-700">
                  Could be stronger
                </h3>
                <ul className="list-disc space-y-1 pl-5 text-sm text-indigo-800">
                  {interview.resume.analysis.missing_details.map((item, i) => (
                    <li key={i}>{item}</li>
                  ))}
                </ul>
              </div>
            )}
            {interview.resume.analysis.key_projects.length > 0 && (
              <div>
                <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-indigo-700">
                  Key projects
                </h3>
                <ul className="list-disc space-y-1 pl-5 text-sm text-indigo-800">
                  {interview.resume.analysis.key_projects.map((item, i) => (
                    <li key={i}>{item}</li>
                  ))}
                </ul>
              </div>
            )}
            {interview.resume.analysis.key_technologies.length > 0 && (
              <div>
                <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-indigo-700">
                  Key technologies
                </h3>
                <div className="flex flex-wrap gap-1">
                  {interview.resume.analysis.key_technologies.map((tech, i) => (
                    <span
                      key={i}
                      className="rounded-full bg-indigo-100 px-2 py-0.5 text-xs text-indigo-800"
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
        <div className="mb-8 rounded-lg border border-slate-200 bg-white p-4">
          <h2 className="mb-2 text-sm font-semibold text-slate-900">Summary</h2>
          <p className="text-slate-600">{interview.summary_feedback}</p>
        </div>
      )}

      {(interview.strengths?.length > 0 || interview.weaknesses?.length > 0) && (
        <div className="mb-8 grid gap-6 sm:grid-cols-2">
          {interview.strengths?.length > 0 && (
            <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4">
              <h2 className="mb-2 text-sm font-semibold text-emerald-800">
                Strongest questions
              </h2>
              <ul className="list-disc space-y-1 pl-5 text-sm text-emerald-800">
                {interview.strengths.map((strength, index) => (
                  <li key={index}>{strength}</li>
                ))}
              </ul>
            </div>
          )}
          {interview.weaknesses?.length > 0 && (
            <div className="rounded-lg border border-amber-200 bg-amber-50 p-4">
              <h2 className="mb-2 text-sm font-semibold text-amber-800">
                Weakest questions
              </h2>
              <ul className="list-disc space-y-1 pl-5 text-sm text-amber-800">
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
            <div
              key={question.id}
              className="rounded-lg border border-slate-200 bg-white p-4"
            >
              <div className="mb-2 flex items-start justify-between gap-3">
                <div>
                  <p className="font-medium text-slate-900">
                    {index + 1}. {question.text}
                  </p>
                  <div className="mt-1 flex flex-wrap gap-1.5">
                    {question.source === 'resume' && (
                      <span className="inline-block rounded-full bg-indigo-50 px-2 py-0.5 text-[11px] font-medium uppercase tracking-wide text-indigo-600">
                        From your resume
                        {question.resume_topic ? ` · ${question.resume_topic}` : ''}
                      </span>
                    )}
                    {evaluation && (
                      <span className="inline-block rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-medium uppercase tracking-wide text-slate-500">
                        {evaluation.question_type}
                      </span>
                    )}
                  </div>
                </div>
                {typeof question.answer?.total_score === 'number' && (
                  <span className="shrink-0 rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-700">
                    {question.answer.total_score}/100
                  </span>
                )}
              </div>

              <p className="mb-3 text-slate-600">
                {question.answer?.text || (
                  <span className="italic text-slate-400">No answer given</span>
                )}
              </p>

              <AnswerCommunicationBadges
                speechMetrics={question.answer?.speech_metrics}
                repetitionAnalysis={question.answer?.repetition_analysis}
              />

              {evaluation && (
                <div className="flex flex-col gap-4">
                  {evaluation.note && (
                    <p className="rounded-md bg-amber-50 p-2 text-xs italic text-amber-700">
                      {evaluation.note}
                    </p>
                  )}

                  <div className="grid gap-3 rounded-md bg-slate-50 p-3 sm:grid-cols-2">
                    {evaluation.category_scores.map((category) => (
                      <CategoryScoreBar key={category.category} category={category} />
                    ))}
                  </div>

                  <div className="grid gap-4 sm:grid-cols-2">
                    {evaluation.strengths.length > 0 && (
                      <div>
                        <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-emerald-700">
                          Strengths
                        </h3>
                        <ul className="list-disc space-y-1 pl-5 text-sm text-slate-600">
                          {evaluation.strengths.map((strength, i) => (
                            <li key={i}>{strength}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {evaluation.weaknesses.length > 0 && (
                      <div>
                        <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-amber-700">
                          Weaknesses
                        </h3>
                        <ul className="list-disc space-y-1 pl-5 text-sm text-slate-600">
                          {evaluation.weaknesses.map((weakness, i) => (
                            <li key={i}>{weakness}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>

                  {evaluation.improvement_suggestions.length > 0 && (
                    <div>
                      <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-indigo-700">
                        Improvement suggestions
                      </h3>
                      <ul className="list-disc space-y-1 pl-5 text-sm text-slate-600">
                        {evaluation.improvement_suggestions.map((suggestion, i) => (
                          <li key={i}>{suggestion}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {evaluation.stronger_answer_example && (
                    <div>
                      <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
                        What a stronger answer looks like
                      </h3>
                      <p className="rounded-md bg-slate-50 p-3 text-sm text-slate-600">
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

      <button
        onClick={() => navigate('/dashboard')}
        className="mt-8 rounded-lg bg-indigo-600 px-6 py-3 font-medium text-white transition-colors hover:bg-indigo-700"
      >
        Go to Dashboard
      </button>
    </div>
  )
}

export default ResultsPage
