import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

const MIN_PASSWORD_LENGTH = 8

function SignupPage() {
  const { signup } = useAuth()
  const navigate = useNavigate()

  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  async function handleSubmit(event) {
    event.preventDefault()
    setError(null)

    if (password.length < MIN_PASSWORD_LENGTH) {
      setError(`Password must be at least ${MIN_PASSWORD_LENGTH} characters.`)
      return
    }

    setIsSubmitting(true)
    try {
      await signup(name, email, password)
      navigate('/dashboard', { replace: true })
    } catch (err) {
      setError(err.message)
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="mx-auto max-w-sm py-8">
      <div className="surface-card p-6 sm:p-8">
        <h1 className="mb-1.5 text-2xl font-semibold tracking-tight text-ink">Create your account</h1>
        <p className="mb-8 text-sm text-ink-muted">
          Track your interview practice and progress over time.
        </p>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div>
            <label htmlFor="name" className="mb-1.5 block text-sm font-medium text-ink-muted">
              Name
            </label>
            <input
              id="name"
              type="text"
              autoComplete="name"
              required
              value={name}
              onChange={(event) => setName(event.target.value)}
              className="input-field"
            />
          </div>

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
            <label htmlFor="password" className="mb-1.5 block text-sm font-medium text-ink-muted">
              Password
            </label>
            <input
              id="password"
              type="password"
              autoComplete="new-password"
              required
              minLength={MIN_PASSWORD_LENGTH}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className="input-field"
            />
            <p className="mt-1.5 text-xs text-ink-faint">At least {MIN_PASSWORD_LENGTH} characters.</p>
          </div>

          {error && (
            <p className="rounded-lg border border-danger/30 bg-danger-soft px-3 py-2 text-sm text-danger">
              {error}
            </p>
          )}

          <button type="submit" disabled={isSubmitting} className="btn btn-primary mt-2 w-full">
            {isSubmitting ? 'Creating account...' : 'Sign up'}
          </button>
        </form>
      </div>

      <p className="mt-6 text-center text-sm text-ink-muted">
        Already have an account?{' '}
        <Link to="/login" className="font-medium text-accent hover:text-accent-hover">
          Log in
        </Link>
      </p>
    </div>
  )
}

export default SignupPage
