import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getDashboard } from '../api/dashboard'
import ProgressChart from '../components/ProgressChart'
import CategoryBreakdownChart from '../components/CategoryBreakdownChart'
import ErrorState from '../components/ErrorState'
import EmptyState from '../components/EmptyState'
import { SkeletonPage } from '../components/Skeleton'
import { IconChartBar } from '../components/icons'

function Panel({ title, children }) {
  return (
    <div className="surface-card p-5">
      <h2 className="mb-4 text-sm font-semibold text-ink">{title}</h2>
      {children}
    </div>
  )
}

function RecurringPatterns({ strengths, weaknesses, weakCategories, onPracticeWeakAreas }) {
  if (strengths.length === 0 && weaknesses.length === 0) {
    return (
      <p className="text-sm text-ink-faint">
        Complete a few more interviews (or a few more answers) to see
        recurring strengths and weaknesses here.
      </p>
    )
  }
  return (
    <div className="grid gap-4 sm:grid-cols-2">
      {strengths.length > 0 && (
        <div className="rounded-xl border border-success/25 bg-success-soft p-4">
          <h3 className="mb-2 text-sm font-semibold text-success">Recurring strengths</h3>
          <ul className="list-disc space-y-1 pl-5 text-sm text-ink">
            {strengths.map((item, i) => (
              <li key={i}>{item}</li>
            ))}
          </ul>
        </div>
      )}
      {weaknesses.length > 0 && (
        <div className="flex flex-col rounded-xl border border-warning/25 bg-warning-soft p-4">
          <h3 className="mb-2 text-sm font-semibold text-warning">Recurring weaknesses</h3>
          <ul className="list-disc space-y-1 pl-5 text-sm text-ink">
            {weaknesses.map((item, i) => (
              <li key={i}>{item}</li>
            ))}
          </ul>
          {weakCategories.length > 0 && (
            <button type="button" onClick={onPracticeWeakAreas} className="btn btn-primary mt-3 self-start !px-3 !py-1.5 !text-xs">
              Practice these areas &rarr;
            </button>
          )}
        </div>
      )}
    </div>
  )
}

// Deeper analytics view than the Dashboard's at-a-glance summary — same
// getDashboard() payload, just given room to show every chart and the
// full recurring-pattern breakdown together.
function PerformancePage() {
  const navigate = useNavigate()
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    getDashboard()
      .then(setData)
      .catch((err) => setError(err.message))
  }, [])

  if (error) return <ErrorState message={error} />
  if (!data) return <SkeletonPage />

  const {
    overview,
    progress,
    communication_progress: communicationProgress,
    category_breakdown: categoryBreakdown,
    recurring_strengths: recurringStrengths,
    recurring_weaknesses: recurringWeaknesses,
    weak_categories: weakCategories,
    recommendations,
  } = data

  if (overview.total_interviews === 0) {
    return (
      <EmptyState
        icon={IconChartBar}
        title="No performance data yet"
        description="Complete your first AI interview to start building your performance history."
        ctaTo="/setup"
        ctaLabel="Start your first interview"
      />
    )
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="mb-1.5 text-2xl font-semibold tracking-tight text-ink">Performance</h1>
        <p className="text-sm text-ink-muted">
          A closer look at how your interview performance is trending.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-5">
        <div className="lg:col-span-3">
          <Panel title="Overall score progression">
            {progress.length > 0 ? (
              <ProgressChart points={progress} />
            ) : (
              <p className="text-sm text-ink-faint">No scored interviews yet.</p>
            )}
          </Panel>
        </div>
        <div className="lg:col-span-2">
          <Panel title="Skill breakdown">
            {categoryBreakdown.length > 0 ? (
              <CategoryBreakdownChart categories={categoryBreakdown} />
            ) : (
              <p className="text-sm text-ink-faint">No category-level evaluation data yet.</p>
            )}
          </Panel>
        </div>
      </div>

      {communicationProgress.length > 0 && (
        <Panel title="Communication score trend">
          <ProgressChart points={communicationProgress} />
        </Panel>
      )}

      <Panel title="Recurring patterns">
        <RecurringPatterns
          strengths={recurringStrengths}
          weaknesses={recurringWeaknesses}
          weakCategories={weakCategories}
          onPracticeWeakAreas={() =>
            navigate('/setup', { state: { focusCategories: weakCategories.map((c) => c.category) } })
          }
        />
      </Panel>

      {recommendations.length > 0 && (
        <div className="rounded-xl border border-accent-border bg-accent-soft p-4">
          <h2 className="mb-2 text-sm font-semibold text-ink">Recommendations</h2>
          <ul className="list-disc space-y-1.5 pl-5 text-sm text-ink-muted">
            {recommendations.map((item, i) => (
              <li key={i}>{item}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

export default PerformancePage
