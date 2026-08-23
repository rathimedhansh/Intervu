// Shared skeleton-loader primitives — replace bare "Loading..." text
// throughout the app with a shape that hints at the content arriving.

export function SkeletonBlock({ className = '' }) {
  return <div className={`skeleton ${className}`} />
}

export function SkeletonText({ lines = 1, className = '' }) {
  return (
    <div className={`flex flex-col gap-2 ${className}`}>
      {Array.from({ length: lines }).map((_, i) => (
        <div
          key={i}
          className="skeleton h-3"
          style={{ width: i === lines - 1 && lines > 1 ? '60%' : '100%' }}
        />
      ))}
    </div>
  )
}

export function SkeletonCard({ className = '' }) {
  return (
    <div className={`surface-card p-4 ${className}`}>
      <SkeletonBlock className="mb-3 h-3 w-24" />
      <SkeletonBlock className="h-7 w-16" />
    </div>
  )
}

export function SkeletonStatGrid({ count = 4 }) {
  return (
    <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
      {Array.from({ length: count }).map((_, i) => (
        <SkeletonCard key={i} />
      ))}
    </div>
  )
}

export function SkeletonTable({ rows = 5 }) {
  return (
    <div className="surface-card overflow-hidden">
      <div className="border-b border-border p-4">
        <SkeletonBlock className="h-4 w-32" />
      </div>
      <div className="flex flex-col divide-y divide-border">
        {Array.from({ length: rows }).map((_, i) => (
          <div key={i} className="flex items-center gap-4 px-4 py-3.5">
            <SkeletonBlock className="h-3 w-20" />
            <SkeletonBlock className="h-3 w-28" />
            <SkeletonBlock className="ml-auto h-3 w-12" />
          </div>
        ))}
      </div>
    </div>
  )
}

export function SkeletonPage() {
  return (
    <div className="flex flex-col gap-8">
      <div>
        <SkeletonBlock className="mb-2 h-7 w-56" />
        <SkeletonBlock className="h-4 w-72" />
      </div>
      <SkeletonStatGrid />
      <SkeletonBlock className="h-64 w-full" />
    </div>
  )
}
