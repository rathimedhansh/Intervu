import { useState } from 'react'
import { Link } from 'react-router-dom'
import { forgotPassword } from '../api/auth'

function ForgotPasswordPage() {
  const [email, setEmail] = useState('')
  const [error, setError] = useState(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  // Only ever populated in dev mode (no email provider is wired up yet —
  // see backend Settings.password_reset_dev_mode). In production this
  // stays null and the link only reaches the user via a real mailer.
  const [devResetLink, setDevResetLink] = useState(null)
  const [submitted, setSubmitted] = useState(false)

  async function handleSubmit(event) {
    event.preventDefault()
    setError(null)
    setIsSubmitting(true)
    try {
      const result = await forgotPassword(email)
      setDevResetLink(result.reset_link)
      setSubmitted(true)
    } catch (err) {
      setError(err.message)
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="mx-auto max-w-sm py-8">
      <div className="surface-card p-6 sm:p-8">
        <h1 className="mb-1.5 text-2xl font-semibold tracking-tight text-ink">
          Forgot password
        </h1>
        <p className="mb-8 text-sm text-ink-muted">
          Enter your account email and we&apos;ll send you a link to reset your password.
        </p>

        {submitted ? (
          <div className="flex flex-col gap-4">
            <p className="rounded-lg border border-border bg-surface-2 px-3 py-2.5 text-sm text-ink-muted">
              If that email is registered, a password reset link has been sent.
            </p>
            {devResetLink && (
              <div className="rounded-lg border border-warning/30 bg-warning-soft px-3 py-2.5 text-sm text-warning">
                <p className="mb-1.5 font-medium">
                  Dev mode: no email provider is configured yet, so here&apos;s your link directly.
                </p>
                <a href={devResetLink} className="break-all underline">
                  {devResetLink}
                </a>
              </div>
            )}
          </div>
        ) : (
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

            {error && (
              <p className="rounded-lg border border-danger/30 bg-danger-soft px-3 py-2 text-sm text-danger">
                {error}
              </p>
            )}

            <button type="submit" disabled={isSubmitting} className="btn btn-primary mt-2 w-full">
              {isSubmitting ? 'Sending...' : 'Send reset link'}
            </button>
          </form>
        )}
      </div>

      <p className="mt-6 text-center text-sm text-ink-muted">
        <Link to="/login" className="font-medium text-accent hover:text-accent-hover">
          Back to log in
        </Link>
      </p>
    </div>
  )
}

export default ForgotPasswordPage
