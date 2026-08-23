import { NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { NAV_GROUPS } from './navItems'
import { IconLogout, IconSparkle } from './icons'

function initials(name, email) {
  const source = (name || email || '?').trim()
  if (!source) return '?'
  const parts = source.split(/\s+/)
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase()
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
}

// Fixed sidebar for the authenticated app shell — visible from md upward
// (tablet + desktop); MobileNav's drawer takes over only below that. ~240px
// wide, kept visually subtle per the redesign brief. Purely presentational;
// all data comes from AuthContext (already the single source of truth for
// the logged-in user).
function Sidebar() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  function handleLogout() {
    logout()
    navigate('/login')
  }

  return (
    <aside className="fixed inset-y-0 left-0 z-30 hidden w-60 shrink-0 flex-col border-r border-border bg-canvas-raised md:flex">
      <div className="flex items-center gap-2 px-5 py-5">
        <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-accent-soft text-accent">
          <IconSparkle className="h-4 w-4" />
        </span>
        <span className="text-sm font-semibold tracking-tight text-ink">
          Mock Interviewer
        </span>
      </div>

      <nav className="styled-scrollbar flex-1 overflow-y-auto px-3 py-2">
        {NAV_GROUPS.map((group) => (
          <div key={group.label} className="mb-4 last:mb-0">
            <p className="mb-1.5 px-3 text-[10px] font-semibold uppercase tracking-wider text-ink-faint">
              {group.label}
            </p>
            <ul className="flex flex-col gap-0.5">
              {group.items.map((item) => (
                <li key={item.to}>
                  <NavLink
                    to={item.to}
                    end={item.end}
                    className={({ isActive }) =>
                      `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                        isActive
                          ? 'bg-accent-soft text-ink'
                          : 'text-ink-muted hover:bg-surface-hover hover:text-ink'
                      }`
                    }
                  >
                    {({ isActive }) => (
                      <>
                        <item.icon
                          className={`h-4 w-4 shrink-0 ${isActive ? 'text-accent' : 'text-ink-faint'}`}
                        />
                        {item.label}
                      </>
                    )}
                  </NavLink>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </nav>

      <div className="border-t border-border p-3">
        <div className="flex items-center gap-2.5 rounded-lg px-2 py-2">
          <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-surface-2 text-xs font-semibold text-ink">
            {initials(user?.name, user?.email)}
          </span>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium text-ink">
              {user?.name || 'Account'}
            </p>
            <p className="truncate text-xs text-ink-faint">{user?.email}</p>
          </div>
          <button
            type="button"
            onClick={handleLogout}
            title="Log out"
            className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md text-ink-faint transition-colors hover:bg-surface-2 hover:text-ink"
          >
            <IconLogout className="h-4 w-4" />
          </button>
        </div>
      </div>
    </aside>
  )
}

export default Sidebar
