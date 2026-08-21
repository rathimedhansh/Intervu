import { NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

const links = [
  { to: '/', label: 'Home', end: true },
  { to: '/setup', label: 'New Interview' },
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/history', label: 'History' },
]

function Navbar() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  function handleLogout() {
    logout()
    navigate('/login')
  }

  return (
    <nav className="border-b border-slate-200 bg-white">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
        <span className="text-lg font-semibold text-slate-900">
          AI Mock Interviewer
        </span>
        <div className="flex items-center gap-6">
          {links.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.end}
              className={({ isActive }) =>
                `text-sm font-medium transition-colors ${
                  isActive
                    ? 'text-indigo-600'
                    : 'text-slate-600 hover:text-slate-900'
                }`
              }
            >
              {link.label}
            </NavLink>
          ))}

          {user ? (
            <div className="flex items-center gap-3 border-l border-slate-200 pl-6">
              <span className="text-sm text-slate-600">
                {user.name || user.email}
              </span>
              <button
                onClick={handleLogout}
                className="text-sm font-medium text-slate-600 transition-colors hover:text-slate-900"
              >
                Log out
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-4 border-l border-slate-200 pl-6">
              <NavLink
                to="/login"
                className="text-sm font-medium text-slate-600 transition-colors hover:text-slate-900"
              >
                Log in
              </NavLink>
              <NavLink
                to="/signup"
                className="rounded-lg bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white transition-colors hover:bg-indigo-700"
              >
                Sign up
              </NavLink>
            </div>
          )}
        </div>
      </div>
    </nav>
  )
}

export default Navbar
