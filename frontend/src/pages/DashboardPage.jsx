import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { getDashboard } from '../api/dashboard'
import StatTile from '../components/StatTile'
import ProgressChart from '../components/ProgressChart'
import CategoryBreakdownChart from '../components/CategoryBreakdownChart'
import ErrorState from '../components/ErrorState'
import EmptyState from '../components/EmptyState'
import DifficultyBadge from '../components/DifficultyBadge'
import PracticePlan from '../components/PracticePlan'
import { SkeletonPage } from '../components/Skeleton'
import { IconGrid } from '../components/icons'

function formatDate(dateString) {
  if (!dateString) return '—'
  return new Date(dateString).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

function ScoreTile({ label, value, explanation }) {
  return (
    <div className="surface-card p-4">
      <p className="text-sm text-ink-muted">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-ink">
        {value != null ? (
          <>
            {value}
            <span className="ml-0.5 text-base font-normal text-ink-faint">/100</span>
          </>
        ) : (
          <span className="text-base font-normal text-ink-faint">Not enough data</span>
        )}
      </p>
      <p className="mt-1 text-xs text-ink-faint">{explanation}</p>
    </div>
  )
}

function RecurringPatterns({ strengths, weaknesses, weakCategories, onPracticeWeakAreas }) {
  if (strengths.length === 0 && weaknesses.length === 0) {
    return (
      <div className="flex h-full flex-col items-center justify-center rounded-lg border border-dashed border-border p-6 text-center">
        <p className="text-sm text-ink-faint">
          Complete a few more interviews (or a few more answers) to see
          recurring strengths and weaknesses here.
        </p>
      </div>
    )
  }
  return (
    <div className="grid gap-4 sm:grid-cols-2">
      {strengths.length > 0 && (
        <div className="rounded-xl border border-success/25 bg-success-soft p-4">
          <h3 className="mb-2 text-sm font-semibold text-success">
            Recurring strengths
          </h3>
          <ul className="list-disc space-y-1 pl-5 text-sm text-ink">
            {strengths.map((item, i) => (
              <li key={i}>{item}</li>
            ))}
          </ul>
        </div>
      )}
      {weaknesses.length > 0 && (
        <div className="flex flex-col rounded-xl border border-warning/25 bg-warning-soft p-4">
          <h3 className="mb-2 text-sm font-semibold text-warning">
            Recurring weaknesses
          </h3>
          <ul className="list-disc space-y-1 pl-5 text-sm text-ink">
            {weaknesses.map((item, i) => (
              <li key={i}>{item}</li>
            ))}
          </ul>
          {weakCategories.length > 0 && (
            <button
              type="button"
              onClick={onPracticeWeakAreas}
              className="btn btn-primary mt-3 self-start !px-3 !py-1.5 !text-xs"
            >
              Practice these areas &rarr;
            </button>
          )}
        </div>
      )}
    </div>
  )
}

function DashboardPage() {
  const navigate = useNavigate()
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    getDashboard()
      .then(setData)
      .catch((err) => setError(err.message))
  }, [])

  if (error) {
    return <ErrorState message={error} backTo="/" backLabel="Back to Home" />
  }

  if (!data) {
    return <SkeletonPage />
  }

  const {
    overview,
    progress,
    communication_progress: communicationProgress,
    recent_interviews: recentInterviews,
    category_breakdown: categoryBreakdown,
    scores,
    recurring_strengths: recurringStrengths,
    recurring_weaknesses: recurringWeaknesses,
    weak_categories: weakCategories,
    recommendations,
    practice_plan: practicePlan,
  } = data

  function handlePracticeArea(category) {
    navigate('/setup', { state: { focusCategories: [category] } })
  }

  return (
    <div>
      <h1 className="mb-2 text-2xl font-semibold text-ink">Dashboard</h1>
      <p className="mb-8 text-ink-muted">
        Your interview performance at a glance.
      </p>

      {overview.total_interviews === 0 ? (
        <EmptyState
          icon={IconGrid}
          title="No interviews completed yet"
          description="Finish your first mock interview to see your scores, progress over time, and category-level feedback here."
          ctaTo="/setup"
          ctaLabel="Start Your First Interview"
        />
      ) : (
        <>
          <div className="mb-8 grid grid-cols-2 gap-4 lg:grid-cols-4">
            <ScoreTile
              label="Overall performance"
              value={scores.overall_score}
              explanation={
                scores.communication_score != null
                  ? 'Answer quality and communication combined.'
                  : 'Based on answer quality (no communication data yet).'
              }
            />
            <ScoreTile
              label="Technical / evaluation"
              value={scores.technical_score != null ? Math.round(scores.technical_score) : null}
              explanation="How well your answers scored against the rubric."
            />
            <ScoreTile
              label="Communication"
              value={scores.communication_score}
              explanation="Speaking pace, filler words, and fluency."
            />
            <ScoreTile
              label="Presentation"
              value={scores.presentation_score}
              explanation="Camera framing and gaze toward the camera."
            />
          </div>

          <div className="mb-8 grid grid-cols-2 gap-4 sm:grid-cols-4">
            <StatTile
              label="Interviews completed"
              value={overview.total_interviews}
            />
            <StatTile
              label="Average score"
              value={overview.average_score ?? '—'}
              suffix={overview.average_score != null ? '/100' : undefined}
            />
            <StatTile
              label="Highest score"
              value={overview.highest_score ?? '—'}
              suffix={overview.highest_score != null ? '/100' : undefined}
            />
            <StatTile
              label="Questions answered"
              value={overview.total_questions_answered}
            />
          </div>

          <div className="mb-8">
            <h2 className="mb-1 text-lg font-semibold text-ink">
              Your practice plan
            </h2>
            <p className="mb-4 text-sm text-ink-muted">
              Your top areas to work on, ranked from your interview history, with a
              concrete action for each.
            </p>
            <PracticePlan plan={practicePlan} onPracticeArea={handlePracticeArea} />
          </div>

          <div className="mb-8 grid gap-6 lg:grid-cols-5">
            <div className="surface-card p-4 lg:col-span-3">
              <h2 className="mb-4 text-sm font-semibold text-ink">
                Score progression
              </h2>
              {progress.length > 0 ? (
                <ProgressChart points={progress} />
              ) : (
                <p className="text-sm text-ink-faint">
                  No scored interviews yet.
                </p>
              )}
            </div>

            <div className="surface-card p-4 lg:col-span-2">
              <h2 className="mb-4 text-sm font-semibold text-ink">
                Performance by category
              </h2>
              {categoryBreakdown.length > 0 ? (
                <CategoryBreakdownChart categories={categoryBreakdown} />
              ) : (
                <p className="text-sm text-ink-faint">
                  No category-level evaluation data yet.
                </p>
              )}
            </div>
          </div>

          <div className="mb-8 grid gap-6 lg:grid-cols-5">
            {communicationProgress.length > 0 && (
              <div className="surface-card p-4 lg:col-span-3">
                <h2 className="mb-4 text-sm font-semibold text-ink">
                  Communication score trend
                </h2>
                <ProgressChart points={communicationProgress} />
              </div>
            )}

            <div
              className={`surface-card p-4 ${
                communicationProgress.length > 0 ? 'lg:col-span-2' : 'lg:col-span-5'
              }`}
            >
              <h2 className="mb-4 text-sm font-semibold text-ink">
                Recurring patterns
              </h2>
              <RecurringPatterns
                strengths={recurringStrengths}
                weaknesses={recurringWeaknesses}
                weakCategories={weakCategories}
                onPracticeWeakAreas={() =>
                  navigate('/setup', {
                    state: { focusCategories: weakCategories.map((c) => c.category) },
                  })
                }
              />
            </div>
          </div>

          {recommendations.length > 0 && (
            <div className="mb-8 rounded-xl border border-accent-border bg-accent-soft p-4">
              <h2 className="mb-2 text-sm font-semibold text-ink">
                Recommendations
              </h2>
              <ul className="list-disc space-y-1.5 pl-5 text-sm text-ink-muted">
                {recommendations.map((item, i) => (
                  <li key={i}>{item}</li>
                ))}
              </ul>
            </div>
          )}

          <div className="surface-card overflow-hidden">
            <div className="flex items-center justify-between border-b border-border p-4">
              <h2 className="text-sm font-semibold text-ink">
                Recent interviews
              </h2>
              <Link
                to="/history"
                className="text-sm font-medium text-accent hover:text-accent-hover"
              >
                View all &rarr;
              </Link>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-border text-xs uppercase tracking-wide text-ink-faint">
                    <th className="px-4 py-2 font-medium">Date</th>
                    <th className="px-4 py-2 font-medium">Role</th>
                    <th className="px-4 py-2 font-medium">Difficulty</th>
                    <th className="px-4 py-2 font-medium">Questions</th>
                    <th className="px-4 py-2 font-medium">Score</th>
                  </tr>
                </thead>
                <tbody>
                  {recentInterviews.map((interview) => (
                    <tr
                      key={interview.id}
                      onClick={() => navigate(`/results/${interview.id}`)}
                      tabIndex={0}
                      onKeyDown={(event) => {
                        if (event.key === 'Enter') navigate(`/results/${interview.id}`)
                      }}
                      className="cursor-pointer border-b border-border transition-colors last:border-0 hover:bg-surface-hover"
                    >
                      <td className="px-4 py-3 text-ink-muted">
                        {formatDate(interview.date)}
                      </td>
                      <td className="px-4 py-3 font-medium text-ink">
                        {interview.role}
                      </td>
                      <td className="px-4 py-3">
                        <DifficultyBadge difficulty={interview.difficulty} />
                      </td>
                      <td className="px-4 py-3 text-ink-muted">
                        {interview.question_count}
                      </td>
                      <td className="px-4 py-3 font-semibold text-ink">
                        {interview.score != null ? `${interview.score}/100` : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  )
}

export default DashboardPage
