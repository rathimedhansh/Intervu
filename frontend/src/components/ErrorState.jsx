import { Link } from 'react-router-dom'

// Shared fatal-error display for page-level fetch failures — always paired
// with a way out, so a failed request never leaves the user on a dead end
// with nothing but red text (see InterviewPage, ResultsPage, DashboardPage).
function ErrorState({ message, backTo = '/dashboard', backLabel = 'Back to Dashboard' }) {
  return (
    <div className="mx-auto flex max-w-lg flex-col items-center gap-3 py-12 text-center">
      <p className="text-red-600">{message}</p>
      <Link
        to={backTo}
        className="text-sm font-medium text-indigo-600 hover:text-indigo-700"
      >
        {backLabel}
      </Link>
    </div>
  )
}

export default ErrorState
