import { useAuth } from '../context/AuthContext'
import { IconUser } from '../components/icons'

function initials(name, email) {
  const source = (name || email || '?').trim()
  const parts = source.split(/\s+/)
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase()
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
}

// Read-only: the backend only exposes GET /auth/me (see api/auth.js) — no
// profile-update endpoint exists, so this deliberately doesn't offer editable
// fields that would silently do nothing.
function ProfilePage() {
  const { user } = useAuth()

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-6">
      <div>
        <h1 className="mb-1.5 text-2xl font-semibold tracking-tight text-ink">Profile</h1>
        <p className="text-sm text-ink-muted">Your account details.</p>
      </div>

      <div className="surface-card p-5">
        <div className="mb-6 flex items-center gap-4">
          <span className="flex h-14 w-14 shrink-0 items-center justify-center rounded-full bg-accent-soft text-base font-semibold text-accent">
            {initials(user?.name, user?.email)}
          </span>
          <div>
            <p className="text-base font-medium text-ink">{user?.name}</p>
            <p className="text-xs text-ink-faint">{user?.email}</p>
          </div>
        </div>

        <div className="grid gap-4 border-t border-border pt-4 sm:grid-cols-2">
          <div>
            <p className="mb-1 text-xs font-medium uppercase tracking-wide text-ink-faint">Name</p>
            <p className="flex items-center gap-2 text-sm text-ink">
              <IconUser className="h-3.5 w-3.5 text-ink-faint" />
              {user?.name}
            </p>
          </div>
          <div>
            <p className="mb-1 text-xs font-medium uppercase tracking-wide text-ink-faint">Email</p>
            <p className="text-sm text-ink">{user?.email}</p>
          </div>
          <div>
            <p className="mb-1 text-xs font-medium uppercase tracking-wide text-ink-faint">Member since</p>
            <p className="text-sm text-ink">
              {user?.created_at
                ? new Date(user.created_at).toLocaleDateString(undefined, {
                    year: 'numeric',
                    month: 'long',
                    day: 'numeric',
                  })
                : '—'}
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default ProfilePage
