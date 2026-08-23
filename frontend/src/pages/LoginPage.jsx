import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const notice = location.state?.notice

  async function handleSubmit(event) {
    event.preventDefault()
    setError(null)
    setIsSubmitting(true)
    try {
      await login(email, password)
      const redirectTo = location.state?.from?.pathname || '/dashboard'
      navigate(redirectTo, { replace: true })
    } catch (err) {
      setError(err.message)
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="mx-auto max-w-sm py-8">
      <div className="surface-card p-6 sm:p-8">
        <h1 className="mb-1.5 text-2xl font-semibold tracking-tight text-ink">Log in</h1>
        <p className="mb-8 text-sm text-ink-muted">
          Welcome back. Enter your details to continue.
        </p>

        {notice && (
          <p className="mb-4 rounded-lg border border-success/30 bg-success-soft px-3 py-2 text-sm text-success">
            {notice}
          </p>
        )}

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div>
            <label htmlFor="email" className="mb-1.5 block text-sm font-medium text-ink-muted">
              Email
            </label>
            <input
              id="email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              className="input-field"
            />
          </div>

          <div>
            <div className="mb-1.5 flex items-center justify-between">
              <label htmlFor="password" className="block text-sm font-medium text-ink-muted">
                Password
              </label>
              <Link
                to="/forgot-password"
                className="text-xs font-medium text-accent hover:text-accent-hover"
              >
                Forgot password?
              </Link>
            </div>
            <input
              id="password"
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className="input-field"
            />
          </div>

          {error && (
            <p className="rounded-lg border border-danger/30 bg-danger-soft px-3 py-2 text-sm text-danger">
              {error}
            </p>
          )}

          <button type="submit" disabled={isSubmitting} className="btn btn-primary mt-2 w-full">
            {isSubmitting ? 'Logging in...' : 'Log in'}
          </button>
        </form>
      </div>

      <p className="mt-6 text-center text-sm text-ink-muted">
        Don&apos;t have an account?{' '}
        <Link to="/signup" className="font-medium text-accent hover:text-accent-hover">
          Sign up
        </Link>
      </p>
    </div>
  )
}

export default LoginPage
