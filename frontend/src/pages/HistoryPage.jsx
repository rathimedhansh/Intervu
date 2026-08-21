import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { deleteInterview, listInterviews } from '../api/interviews'
import DifficultyBadge from '../components/DifficultyBadge'
import ErrorState from '../components/ErrorState'

const STATUS_FILTERS = [
  { value: 'all', label: 'All' },
  { value: 'pending', label: 'In progress' },
  { value: 'completed', label: 'Completed' },
]

function formatDate(dateString) {
  if (!dateString) return '—'
  return new Date(dateString).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

function StatusBadge({ status }) {
  const isCompleted = status === 'completed'
  return (
    <span
      className={`rounded-full px-2.5 py-1 text-xs font-medium ${
        isCompleted ? 'bg-indigo-100 text-indigo-700' : 'bg-slate-100 text-slate-600'
      }`}
    >
      {isCompleted ? 'Completed' : 'In progress'}
    </span>
  )
}

function EmptyState({ hasAnyInterviews }) {
  return (
    <div className="flex flex-col items-center rounded-lg border border-dashed border-slate-300 bg-white px-6 py-16 text-center">
      <h2 className="text-lg font-semibold text-slate-900">
        {hasAnyInterviews ? 'No interviews match these filters' : 'No interviews yet'}
      </h2>
      <p className="mt-2 max-w-sm text-slate-600">
        {hasAnyInterviews
          ? 'Try a different role or status filter.'
          : 'Every interview you start or complete will show up here, so you can always find and revisit it later.'}
      </p>
      {!hasAnyInterviews && (
        <Link
          to="/setup"
          className="mt-6 rounded-lg bg-indigo-600 px-6 py-3 font-medium text-white transition-colors hover:bg-indigo-700"
        >
          Start Your First Interview
        </Link>
      )}
    </div>
  )
}

function HistoryPage() {
  const navigate = useNavigate()
  const [interviews, setInterviews] = useState(null)
  const [error, setError] = useState(null)
  const [statusFilter, setStatusFilter] = useState('all')
  const [roleFilter, setRoleFilter] = useState('all')
  const [deletingId, setDeletingId] = useState(null)
  const [deleteError, setDeleteError] = useState(null)

  useEffect(() => {
    listInterviews()
      .then(setInterviews)
      .catch((err) => setError(err.message))
  }, [])

  const roles = useMemo(() => {
    if (!interviews) return []
    return [...new Set(interviews.map((i) => i.role))].sort()
  }, [interviews])

  const filtered = useMemo(() => {
    if (!interviews) return []
    return interviews.filter((interview) => {
      if (statusFilter !== 'all' && interview.status !== statusFilter) return false
      if (roleFilter !== 'all' && interview.role !== roleFilter) return false
      return true
    })
  }, [interviews, statusFilter, roleFilter])

  async function handleDelete(event, interview) {
    event.stopPropagation()
    const label = interview.status === 'completed' ? 'completed' : 'in-progress'
    if (!window.confirm(`Delete this ${label} ${interview.role} interview? This can't be undone.`)) {
      return
    }
    setDeleteError(null)
    setDeletingId(interview.id)
    try {
      await deleteInterview(interview.id)
      setInterviews((current) => current.filter((i) => i.id !== interview.id))
    } catch (err) {
      setDeleteError(err.message)
    } finally {
      setDeletingId(null)
    }
  }

  if (error) {
    return <ErrorState message={error} backTo="/" backLabel="Back to Home" />
  }

  if (!interviews) {
    return <p className="text-slate-600">Loading interview history...</p>
  }

  return (
    <div>
      <h1 className="mb-2 text-2xl font-semibold text-slate-900">Interview History</h1>
      <p className="mb-8 text-slate-600">
        Every interview you've started or completed — resume one that's still in
        progress, or revisit past results.
      </p>

      {interviews.length > 0 && (
        <div className="mb-6 flex flex-wrap gap-4">
          <div className="flex gap-1.5">
            {STATUS_FILTERS.map((option) => (
              <button
                key={option.value}
                type="button"
                onClick={() => setStatusFilter(option.value)}
                aria-pressed={statusFilter === option.value}
                className={`rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
                  statusFilter === option.value
                    ? 'bg-indigo-600 text-white'
                    : 'border border-slate-300 text-slate-700 hover:bg-slate-100'
                }`}
              >
                {option.label}
              </button>
            ))}
          </div>

          {roles.length > 1 && (
            <select
              value={roleFilter}
              onChange={(event) => setRoleFilter(event.target.value)}
              className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm focus:border-indigo-500 focus:outline-none"
            >
              <option value="all">All roles</option>
              {roles.map((role) => (
                <option key={role} value={role}>
                  {role}
                </option>
              ))}
            </select>
          )}
        </div>
      )}

      {deleteError && (
        <p className="mb-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
          {deleteError}
        </p>
      )}

      {filtered.length === 0 ? (
        <EmptyState hasAnyInterviews={interviews.length > 0} />
      ) : (
        <div className="rounded-lg border border-slate-200 bg-white">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500">
                  <th className="px-4 py-2 font-medium">Date</th>
                  <th className="px-4 py-2 font-medium">Role</th>
                  <th className="px-4 py-2 font-medium">Difficulty</th>
                  <th className="px-4 py-2 font-medium">Status</th>
                  <th className="px-4 py-2 font-medium">Questions</th>
                  <th className="px-4 py-2 font-medium">Score</th>
                  <th className="px-4 py-2 font-medium">
                    <span className="sr-only">Actions</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((interview) => {
                  const isCompleted = interview.status === 'completed'
                  const target = isCompleted
                    ? `/results/${interview.id}`
                    : `/interview/${interview.id}`
                  return (
                    <tr
                      key={interview.id}
                      onClick={() => navigate(target)}
                      tabIndex={0}
                      onKeyDown={(event) => {
                        if (event.key === 'Enter') navigate(target)
                      }}
                      className="cursor-pointer border-b border-slate-100 transition-colors last:border-0 hover:bg-slate-50"
                    >
                      <td className="px-4 py-3 text-slate-600">
                        {formatDate(interview.completed_at || interview.created_at)}
                      </td>
                      <td className="px-4 py-3 font-medium text-slate-900">
                        {interview.role}
                      </td>
                      <td className="px-4 py-3">
                        <DifficultyBadge difficulty={interview.difficulty} />
                      </td>
                      <td className="px-4 py-3">
                        <StatusBadge status={interview.status} />
                      </td>
                      <td className="px-4 py-3 text-slate-600">
                        {interview.question_count ?? '—'}
                      </td>
                      <td className="px-4 py-3 font-semibold text-slate-900">
                        {isCompleted
                          ? interview.overall_score != null
                            ? `${interview.overall_score}/100`
                            : '—'
                          : <span className="font-normal text-indigo-600">Continue &rarr;</span>}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <button
                          type="button"
                          onClick={(event) => handleDelete(event, interview)}
                          disabled={deletingId === interview.id}
                          className="text-xs font-medium text-slate-400 transition-colors hover:text-rose-600 disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          {deletingId === interview.id ? 'Deleting...' : 'Delete'}
                        </button>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}

export default HistoryPage
