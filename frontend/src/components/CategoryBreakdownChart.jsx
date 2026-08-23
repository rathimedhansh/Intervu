function CategoryBreakdownChart({ categories }) {
  return (
    <div className="flex flex-col gap-4">
      {categories.map((category) => (
        <div key={category.category}>
          <div className="mb-1.5 flex items-center justify-between text-sm">
            <span className="text-ink-muted">{category.label}</span>
            <span className="font-medium text-ink">{category.average_score}%</span>
          </div>
          <div className="h-2 w-full overflow-hidden rounded-full bg-surface-2">
            <div
              className="h-full rounded-full bg-accent transition-[width] duration-700 ease-out"
              style={{ width: `${Math.min(100, category.average_score)}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  )
}

export default CategoryBreakdownChart
