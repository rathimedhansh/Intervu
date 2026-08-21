const DIFFICULTY_STYLES = {
  easy: 'bg-emerald-100 text-emerald-700',
  medium: 'bg-amber-100 text-amber-700',
  hard: 'bg-rose-100 text-rose-700',
}

function DifficultyBadge({ difficulty }) {
  return (
    <span
      className={`rounded-full px-2.5 py-1 text-xs font-medium ${
        DIFFICULTY_STYLES[difficulty] || 'bg-slate-100 text-slate-700'
      }`}
    >
      {difficulty}
    </span>
  )
}

export default DifficultyBadge
