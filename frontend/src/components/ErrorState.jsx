import { Link } from 'react-router-dom'
import { IconAlert } from './icons'

// Shared fatal-error display for page-level fetch failures — always paired
// with a way out, so a failed request never leaves the user on a dead end
// with nothing but red text (see InterviewPage, ResultsPage, DashboardPage).
// `message` is always a cleaned-up string from api/client.js (FastAPI's
// `detail`, or a generic "Request failed: <status>") — never a raw
// exception/stack trace.
function ErrorState({ message, backTo = '/dashboard', backLabel = 'Back to Dashboard' }) {
  return (
    <div className="mx-auto flex max-w-lg flex-col items-center gap-3 py-16 text-center">
      <span className="flex h-11 w-11 items-center justify-center rounded-full bg-danger-soft text-danger">
        <IconAlert className="h-5 w-5" />
      </span>
      <p className="text-sm text-ink-muted">{message}</p>
      <Link to={backTo} className="btn btn-secondary mt-2">
        {backLabel}
      </Link>
    </div>
  )
}

export default ErrorState
