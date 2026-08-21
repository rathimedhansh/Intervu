import { Link } from 'react-router-dom'

function NotFoundPage() {
  return (
    <div className="mx-auto flex max-w-lg flex-col items-center gap-4 py-16 text-center">
      <h1 className="text-3xl font-semibold text-slate-900">Page not found</h1>
      <p className="text-slate-600">
        The page you're looking for doesn't exist or may have moved.
      </p>
      <Link
        to="/"
        className="rounded-lg bg-indigo-600 px-6 py-3 font-medium text-white transition-colors hover:bg-indigo-700"
      >
        Back to Home
      </Link>
    </div>
  )
}

export default NotFoundPage
