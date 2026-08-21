import ProgressChart from './ProgressChart'

const AREA_STYLES = {
  technical: { badge: 'bg-indigo-100 text-indigo-700', tag: 'Technical' },
  communication: { badge: 'bg-sky-100 text-sky-700', tag: 'Communication' },
  presentation: { badge: 'bg-purple-100 text-purple-700', tag: 'Presentation' },
}

const SEVERITY_STYLES = {
  high: { badge: 'bg-rose-100 text-rose-700', label: 'High priority' },
  medium: { badge: 'bg-amber-100 text-amber-700', label: 'Medium priority' },
  low: { badge: 'bg-slate-100 text-slate-600', label: 'Low priority' },
}

// Practice Plan progress loop: does this area have a targeted practice
// session behind it (an interview whose focus_categories included it — see
// app.crud.dashboard._compute_practice_progress), and did it help? Three
// distinguishable states, never a fabricated result.
const PRACTICE_PROGRESS_STYLES = {
  improved: { badge: 'bg-emerald-100 text-emerald-700', icon: '✓', label: 'Improvement detected' },
  practiced: { badge: 'bg-sky-100 text-sky-700', icon: '●', label: 'Practice completed' },
  insufficient_data: { badge: 'bg-slate-100 text-slate-500', icon: '○', label: 'Not enough data yet' },
}

function PracticeProgressIndicator({ progress }) {
  if (!progress) return null
  const style = PRACTICE_PROGRESS_STYLES[progress.status] || PRACTICE_PROGRESS_STYLES.practiced

  return (
    <div className="mt-3 rounded-md border border-slate-100 bg-slate-50 p-2.5">
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
        <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${style.badge}`}>
          <span aria-hidden="true">{style.icon}</span>
          {style.label}
        </span>
        <span className="text-xs text-slate-500">
          {progress.session_count} focused session{progress.session_count === 1 ? '' : 's'}
        </span>
      </div>
      {progress.before_avg != null && progress.after_avg != null && (
        <p className="mt-1.5 text-xs text-slate-500">
          Before: {progress.before_avg}% &rarr; After: {progress.after_avg}%
        </p>
      )}
    </div>
  )
}

function PracticePlanEmptyState({ message, tone }) {
  const toneClasses =
    tone === 'positive'
      ? 'border-emerald-200 bg-emerald-50 text-emerald-800'
      : 'border-dashed border-slate-300 text-slate-500'
  return (
    <div className={`flex flex-col items-center rounded-lg border px-6 py-10 text-center ${toneClasses}`}>
      <p className="max-w-md text-sm">{message}</p>
    </div>
  )
}

function PracticePlanAreaCard({ area, rank, onPracticeArea }) {
  const areaStyle = AREA_STYLES[area.area] || AREA_STYLES.technical
  const severityStyle = SEVERITY_STYLES[area.severity] || SEVERITY_STYLES.medium

  return (
    <div className="flex flex-col rounded-lg border border-slate-200 bg-white p-4">
      <div className="mb-3 flex items-start justify-between gap-2">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
            #{rank} · <span className={`rounded px-1.5 py-0.5 ${areaStyle.badge}`}>{areaStyle.tag}</span>
          </p>
          <h3 className="mt-1.5 text-base font-semibold text-slate-900">{area.label}</h3>
        </div>
        <span className={`shrink-0 rounded-full px-2.5 py-1 text-xs font-medium ${severityStyle.badge}`}>
          {severityStyle.label}
        </span>
      </div>

      <p className="mb-1 text-2xl font-semibold text-slate-900">
        {area.score}
        <span className="ml-0.5 text-sm font-normal text-slate-400">
          /100 · {area.sample_count} sample{area.sample_count === 1 ? '' : 's'}
        </span>
      </p>

      <p className="mt-2 text-sm text-slate-600">{area.reason}</p>

      <div className="mt-3 rounded-md bg-indigo-50 p-3">
        <p className="text-xs font-semibold uppercase tracking-wide text-indigo-500">Do this</p>
        <p className="mt-1 text-sm text-indigo-900">{area.action}</p>
      </div>

      {area.trend.length > 0 ? (
        <div className="mt-4">
          <p className="mb-1 text-xs font-medium text-slate-500">Progress over time</p>
          <ProgressChart points={area.trend} />
        </div>
      ) : (
        <p className="mt-4 text-xs text-slate-400">
          Not enough history yet to chart a trend for this area.
        </p>
      )}

      <PracticeProgressIndicator progress={area.practice_progress} />

      {area.area === 'technical' && (
        <button
          type="button"
          onClick={() => onPracticeArea(area.category)}
          className="mt-4 self-start rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-indigo-700"
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
