import { useCountUp } from '../hooks/useCountUp'

// `value` is animated with a count-up when numeric; non-numeric values
// (e.g. "—") render as-is. `icon` and `trend` are optional so this stays
// usable for the many plain stat tiles that don't have either.
function StatTile({ label, value, suffix, icon: Icon, trend }) {
  const isNumeric = typeof value === 'number'
  const animated = useCountUp(isNumeric ? value : null)

  return (
    <div className="surface-card surface-card-hover p-4">
      <div className="mb-2 flex items-center justify-between">
        <p className="text-xs font-medium text-ink-muted">{label}</p>
        {Icon && (
          <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-accent-soft text-accent">
            <Icon className="h-3.5 w-3.5" />
          </span>
        )}
      </div>
      <p className="text-2xl font-semibold tracking-tight text-ink">
        {isNumeric ? animated : value}
        {suffix && <span className="ml-0.5 text-sm font-normal text-ink-faint">{suffix}</span>}
      </p>
      {trend && (
        <p
          className={`mt-1 text-xs font-medium ${
            trend.direction === 'up'
              ? 'text-success'
              : trend.direction === 'down'
                ? 'text-danger'
                : 'text-ink-faint'
          }`}
        >
          {trend.label}
        </p>
      )}
    </div>
  )
}

export default StatTile
