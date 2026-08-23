import { NavLink, Outlet } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import PageTransition from '../components/PageTransition'
import { IconSparkle } from '../components/icons'

// Lightweight shell for the marketing/auth pages (landing, login, signup) —
// no sidebar, just a slim top bar, matching the same dark theme as the
// authenticated app shell.
function PublicLayout() {
  const { user } = useAuth()

  return (
    <div className="min-h-screen bg-canvas">
      <header className="glass sticky top-0 z-30 border-b">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <NavLink to="/" className="flex items-center gap-2">
            <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-accent-soft text-accent">
              <IconSparkle className="h-4 w-4" />
            </span>
            <span className="text-sm font-semibold tracking-tight text-ink">
              Mock Interviewer
            </span>
          </NavLink>

          {user ? (
            <NavLink to="/dashboard" className="btn btn-secondary">
              Go to Dashboard
            </NavLink>
          ) : (
            <div className="flex items-center gap-3">
              <NavLink
                to="/login"
                className="text-sm font-medium text-ink-muted transition-colors hover:text-ink"
              >
                Log in
              </NavLink>
              <NavLink to="/signup" className="btn btn-primary">
                Sign up
              </NavLink>
            </div>
          )}
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-6 py-12">
        <PageTransition>
          <Outlet />
        </PageTransition>
      </main>
    </div>
  )
}

export default PublicLayout
