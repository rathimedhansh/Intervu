function CategoryBreakdownChart({ categories }) {
  return (
    <div className="flex flex-col gap-3">
      {categories.map((category) => (
        <div key={category.category}>
          <div className="mb-1 flex items-center justify-between text-sm">
            <span className="text-slate-700">{category.label}</span>
            <span className="font-medium text-slate-900">
              {category.average_score}%
            </span>
          </div>
          <div className="h-2.5 w-full overflow-hidden rounded-full bg-slate-100">
            <div
              className="h-full rounded-full bg-indigo-500"
              style={{ width: `${Math.min(100, category.average_score)}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  )
}

export default CategoryBreakdownChart
