import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

// Wraps a route element that requires a logged-in user. Unauthenticated
// visitors are redirected to /login, remembering where they were headed so
// login can send them back afterwards.
function ProtectedRoute({ children }) {
  const { user, isLoading } = useAuth()
  const location = useLocation()

  if (isLoading) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center">
        <span className="h-5 w-5 animate-spin rounded-full border-2 border-border-strong border-t-accent" />
      </div>
    )
  }

  if (!user) {
    return <Navigate to="/login" replace state={{ from: location }} />
  }

  return children
}

export default ProtectedRoute
