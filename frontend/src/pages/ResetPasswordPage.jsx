import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { resetPassword } from '../api/auth'

function ResetPasswordPage() {
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token') ?? ''
  const navigate = useNavigate()

  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  async function handleSubmit(event) {
    event.preventDefault()
    setError(null)

    if (newPassword !== confirmPassword) {
      setError('Passwords do not match.')
      return
    }

    setIsSubmitting(true)
    try {
      await resetPassword(token, newPassword)
      navigate('/login', {
        replace: true,
        state: { notice: 'Password updated — log in with your new password.' },
      })
    } catch (err) {
      setError(err.message)
    } finally {
      setIsSubmitting(false)
    }
  }

  if (!token) {
    return (
      <div className="mx-auto max-w-sm py-8">
        <div className="surface-card p-6 sm:p-8">
          <h1 className="mb-1.5 text-2xl font-semibold tracking-tight text-ink">
            Invalid reset link
          </h1>
          <p className="text-sm text-ink-muted">
            This link is missing its reset token. Request a new one below.
          </p>
        </div>
        <p className="mt-6 text-center text-sm text-ink-muted">
          <Link to="/forgot-password" className="font-medium text-accent hover:text-accent-hover">
            Request a new reset link
          </Link>
        </p>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-sm py-8">
      <div className="surface-card p-6 sm:p-8">
        <h1 className="mb-1.5 text-2xl font-semibold tracking-tight text-ink">
          Reset password
        </h1>
        <p className="mb-8 text-sm text-ink-muted">Choose a new password for your account.</p>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div>
            <label
              htmlFor="new-password"
              className="mb-1.5 block text-sm font-medium text-ink-muted"
            >
              New password
            </label>
            <input
              id="new-password"
              type="password"
              autoComplete="new-password"
              required
              minLength={8}
              value={newPassword}
              onChange={(event) => setNewPassword(event.target.value)}
              className="input-field"
            />
          </div>

          <div>
            <label
              htmlFor="confirm-password"
              className="mb-1.5 block text-sm font-medium text-ink-muted"
            >
              Confirm new password
            </label>
            <input
              id="confirm-password"
              type="password"
              autoComplete="new-password"
              required
              minLength={8}
              value={confirmPassword}
              onChange={(event) => setConfirmPassword(event.target.value)}
              className="input-field"
            />
          </div>

          {error && (
            <p className="rounded-lg border border-danger/30 bg-danger-soft px-3 py-2 text-sm text-danger">
              {error}
            </p>
          )}

          <button type="submit" disabled={isSubmitting} className="btn btn-primary mt-2 w-full">
            {isSubmitting ? 'Updating...' : 'Update password'}
          </button>
        </form>
      </div>

      <p className="mt-6 text-center text-sm text-ink-muted">
        <Link to="/login" className="font-medium text-accent hover:text-accent-hover">
          Back to log in
        </Link>
      </p>
    </div>
  )
}

export default ResetPasswordPage
