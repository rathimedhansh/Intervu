import { Link } from 'react-router-dom'

// Generic polished empty state — icon + title + description + optional CTA.
// Used wherever a list/collection is legitimately empty (no interviews yet,
// filters matched nothing, no practice data yet) instead of plain text.
function EmptyState({ icon: Icon, title, description, ctaTo, ctaLabel }) {
  return (
    <div className="flex flex-col items-center rounded-2xl border border-dashed border-border-strong bg-surface/40 px-6 py-16 text-center">
      {Icon && (
        <span className="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-surface-2 text-ink-faint">
          <Icon className="h-5 w-5" />
        </span>
      )}
      <h2 className="text-base font-semibold text-ink">{title}</h2>
      {description && (
        <p className="mt-2 max-w-sm text-sm text-ink-muted">{description}</p>
      )}
      {ctaTo && (
        <Link to={ctaTo} className="btn btn-primary mt-6">
          {ctaLabel} &rarr;
        </Link>
      )}
    </div>
  )
}

export default EmptyState
