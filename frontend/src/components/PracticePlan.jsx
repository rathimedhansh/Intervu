import ProgressChart from './ProgressChart'

const AREA_STYLES = {
  technical: { badge: 'bg-accent-soft text-accent', tag: 'Technical' },
  communication: { badge: 'bg-cyan-soft text-cyan', tag: 'Communication' },
  presentation: { badge: 'bg-surface-2 text-ink-muted', tag: 'Presentation' },
}

const SEVERITY_STYLES = {
  high: { badge: 'bg-danger-soft text-danger', label: 'High priority' },
  medium: { badge: 'bg-warning-soft text-warning', label: 'Medium priority' },
  low: { badge: 'bg-surface-2 text-ink-muted', label: 'Low priority' },
}

// Practice Plan progress loop: does this area have a targeted practice
// session behind it (an interview whose focus_categories included it — see
// app.crud.dashboard._compute_practice_progress), and did it help? Three
// distinguishable states, never a fabricated result.
const PRACTICE_PROGRESS_STYLES = {
  improved: { badge: 'bg-success-soft text-success', icon: '✓', label: 'Improvement detected' },
  practiced: { badge: 'bg-cyan-soft text-cyan', icon: '●', label: 'Practice completed' },
  insufficient_data: { badge: 'bg-surface-2 text-ink-faint', icon: '○', label: 'Not enough data yet' },
}

function PracticeProgressIndicator({ progress }) {
  if (!progress) return null
  const style = PRACTICE_PROGRESS_STYLES[progress.status] || PRACTICE_PROGRESS_STYLES.practiced

  return (
    <div className="mt-3 rounded-lg border border-border bg-surface-2/60 p-2.5">
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
        <span className={`badge ${style.badge}`}>
          <span aria-hidden="true">{style.icon}</span>
          {style.label}
        </span>
        <span className="text-xs text-ink-faint">
          {progress.session_count} focused session{progress.session_count === 1 ? '' : 's'}
        </span>
      </div>
      {progress.before_avg != null && progress.after_avg != null && (
        <p className="mt-1.5 text-xs text-ink-faint">
          Before: {progress.before_avg}% &rarr; After: {progress.after_avg}%
        </p>
      )}
    </div>
  )
}

function PracticePlanEmptyState({ message, tone }) {
  const toneClasses =
    tone === 'positive'
      ? 'border-success/30 bg-success-soft text-success'
      : 'border-dashed border-border-strong text-ink-muted'
  return (
    <div className={`flex flex-col items-center rounded-2xl border px-6 py-10 text-center ${toneClasses}`}>
      <p className="max-w-md text-sm">{message}</p>
    </div>
  )
}

function PracticePlanAreaCard({ area, rank, onPracticeArea }) {
  const areaStyle = AREA_STYLES[area.area] || AREA_STYLES.technical
  const severityStyle = SEVERITY_STYLES[area.severity] || SEVERITY_STYLES.medium

  return (
    <div className="surface-card surface-card-hover flex flex-col p-4">
      <div className="mb-3 flex items-start justify-between gap-2">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-ink-faint">
            #{rank} · <span className={`badge ${areaStyle.badge}`}>{areaStyle.tag}</span>
          </p>
          <h3 className="mt-1.5 text-base font-semibold text-ink">{area.label}</h3>
        </div>
        <span className={`badge shrink-0 ${severityStyle.badge}`}>{severityStyle.label}</span>
      </div>

      <p className="mb-1 text-2xl font-semibold text-ink">
        {area.score}
        <span className="ml-0.5 text-sm font-normal text-ink-faint">
          /100 · {area.sample_count} sample{area.sample_count === 1 ? '' : 's'}
        </span>
      </p>

      <p className="mt-2 text-sm text-ink-muted">{area.reason}</p>

      <div className="mt-3 rounded-lg bg-accent-soft p-3">
        <p className="text-xs font-semibold uppercase tracking-wide text-accent">Do this</p>
        <p className="mt-1 text-sm text-ink">{area.action}</p>
      </div>

      {area.trend.length > 0 ? (
        <div className="mt-4">
          <p className="mb-1 text-xs font-medium text-ink-faint">Progress over time</p>
          <ProgressChart points={area.trend} />
        </div>
      ) : (
        <p className="mt-4 text-xs text-ink-faint">
          Not enough history yet to chart a trend for this area.
        </p>
      )}

      <PracticeProgressIndicator progress={area.practice_progress} />

      {area.area === 'technical' && (
        <button
          type="button"
          onClick={() => onPracticeArea(area.category)}
          className="btn btn-primary mt-4 self-start !px-3 !py-1.5 !text-xs"
        >
          Start focused practice &rarr;
        </button>
      )}
    </div>
  )
}

// The dashboard's actionable centerpiece: past interviews -> recurring
// weaknesses -> a ranked, explained, practice-able plan. Built entirely
// from data the dashboard already computes (see
// app.crud.dashboard._build_practice_plan) — this component only renders
// it, never re-derives anything.
function PracticePlan({ plan, onPracticeArea }) {
  if (!plan.ready) {
    return <PracticePlanEmptyState message={plan.message} tone="neutral" />
  }

  if (plan.areas.length === 0) {
    return <PracticePlanEmptyState message={plan.message} tone="positive" />
  }

  return (
    <div className="grid gap-4 md:grid-cols-3">
      {plan.areas.map((area, index) => (
        <PracticePlanAreaCard
          key={`${area.area}-${area.category}`}
          area={area}
          rank={index + 1}
          onPracticeArea={onPracticeArea}
        />
      ))}
    </div>
  )
}

export default PracticePlan
