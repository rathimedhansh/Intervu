import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getDashboard } from '../api/dashboard'
import PracticePlan from '../components/PracticePlan'
import ErrorState from '../components/ErrorState'
import EmptyState from '../components/EmptyState'
import { SkeletonPage } from '../components/Skeleton'
import { IconTarget } from '../components/icons'

// Reuses the exact same practice-plan data the Dashboard already computes
// (see app.crud.dashboard._build_practice_plan) — this page just gives it
// a dedicated, full-width home instead of being a section you scroll past.
function PracticePage() {
  const navigate = useNavigate()
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    getDashboard()
      .then(setData)
      .catch((err) => setError(err.message))
  }, [])

  if (error) return <ErrorState message={error} />
  if (!data) return <SkeletonPage />

  const { practice_plan: practicePlan, overview } = data

  function handlePracticeArea(category) {
    navigate('/setup', { state: { focusCategories: [category] } })
  }

  return (
    <div>
      <h1 className="mb-1.5 text-2xl font-semibold tracking-tight text-ink">Practice</h1>
      <p className="mb-8 text-sm text-ink-muted">
        Your top areas to work on, ranked from your interview history, with a
        concrete action for each.
      </p>

      {overview.total_interviews === 0 ? (
        <EmptyState
          icon={IconTarget}
          title="No practice data yet"
          description="Complete your first AI interview to start building a targeted practice plan."
          ctaTo="/setup"
          ctaLabel="Start your first interview"
        />
      ) : (
        <PracticePlan plan={practicePlan} onPracticeArea={handlePracticeArea} />
      )}
    </div>
  )
}

export default PracticePage
