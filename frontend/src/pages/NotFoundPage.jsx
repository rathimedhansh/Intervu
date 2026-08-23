import { Link } from 'react-router-dom'

function NotFoundPage() {
  return (
    <div className="mx-auto flex max-w-lg flex-col items-center gap-4 py-16 text-center">
      <span className="text-sm font-semibold text-accent">404</span>
      <h1 className="text-3xl font-semibold tracking-tight text-ink">Page not found</h1>
      <p className="text-ink-muted">
        The page you're looking for doesn't exist or may have moved.
      </p>
      <Link to="/" className="btn btn-primary mt-2">
        Back to Home
      </Link>
    </div>
  )
}

export default NotFoundPage
