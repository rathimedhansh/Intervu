import { useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { NAV_GROUPS } from './navItems'
import { IconClose, IconLogout, IconMenu, IconSparkle } from './icons'

// Compact top bar + slide-in drawer for the authenticated app shell on
// screens below md, where the fixed Sidebar is hidden.
function MobileNav() {
  const [open, setOpen] = useState(false)
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  function handleLogout() {
    setOpen(false)
    logout()
    navigate('/login')
  }

  return (
    <>
      <header className="glass sticky top-0 z-30 flex items-center justify-between border-b px-4 py-3 md:hidden">
        <div className="flex items-center gap-2">
          <span className="flex h-6 w-6 items-center justify-center rounded-md bg-accent-soft text-accent">
            <IconSparkle className="h-3.5 w-3.5" />
          </span>
          <span className="text-sm font-semibold text-ink">Intervu</span>
        </div>
        <button
          type="button"
          onClick={() => setOpen(true)}
          aria-label="Open navigation menu"
          className="flex h-8 w-8 items-center justify-center rounded-lg text-ink-muted transition-colors hover:bg-surface-hover hover:text-ink"
        >
          <IconMenu className="h-5 w-5" />
        </button>
      </header>

      <AnimatePresence>
        {open && (
          <>
            <motion.div
              key="backdrop"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.15 }}
              onClick={() => setOpen(false)}
              className="fixed inset-0 z-40 bg-black/60 md:hidden"
            />
            <motion.div
              key="drawer"
              initial={{ x: '-100%' }}
              animate={{ x: 0 }}
              exit={{ x: '-100%' }}
              transition={{ type: 'tween', duration: 0.2, ease: 'easeOut' }}
              className="fixed inset-y-0 left-0 z-50 flex w-72 max-w-[85vw] flex-col border-r border-border bg-canvas-raised md:hidden"
            >
              <div className="flex items-center justify-between px-5 py-5">
                <div className="flex items-center gap-2">
                  <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-accent-soft text-accent">
                    <IconSparkle className="h-4 w-4" />
                  </span>
                  <span className="text-sm font-semibold text-ink">Intervu</span>
                </div>
                <button
                  type="button"
                  onClick={() => setOpen(false)}
                  aria-label="Close navigation menu"
                  className="flex h-8 w-8 items-center justify-center rounded-lg text-ink-muted hover:bg-surface-hover hover:text-ink"
                >
                  <IconClose className="h-5 w-5" />
                </button>
              </div>

              <nav className="flex-1 overflow-y-auto px-3 py-2">
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
                            onClick={() => setOpen(false)}
                            className={({ isActive }) =>
                              `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors ${
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
                    {(user?.name || user?.email || '?').slice(0, 1).toUpperCase()}
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
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </>
  )
}

export default MobileNav
