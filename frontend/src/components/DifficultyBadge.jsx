const DIFFICULTY_STYLES = {
  easy: 'bg-success-soft text-success',
  medium: 'bg-warning-soft text-warning',
  hard: 'bg-danger-soft text-danger',
}

function DifficultyBadge({ difficulty }) {
  return (
    <span className={`badge capitalize ${DIFFICULTY_STYLES[difficulty] || 'bg-surface-2 text-ink-muted'}`}>
      {difficulty}
    </span>
  )
}

export default DifficultyBadge
