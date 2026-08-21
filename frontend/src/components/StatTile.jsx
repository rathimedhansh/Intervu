function StatTile({ label, value, suffix }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <p className="text-sm text-slate-500">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-slate-900">
        {value}
        {suffix && <span className="ml-0.5 text-base font-normal text-slate-400">{suffix}</span>}
      </p>
    </div>
  )
}

export default StatTile
