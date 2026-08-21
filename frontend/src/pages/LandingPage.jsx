import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

function LandingPage() {
  const navigate = useNavigate()
  const { user } = useAuth()

  return (
    <div className="flex flex-col items-center gap-6 py-16 text-center">
      <h1 className="text-4xl font-bold text-slate-900">
        Practice interviews with AI feedback
      </h1>
      <p className="max-w-xl text-slate-600">
        Run a realistic mock interview, get structured feedback, and track
        your progress over time.
      </p>

      {user ? (
        <div className="flex gap-3">
          <button
            onClick={() => navigate('/setup')}
            className="rounded-lg bg-indigo-600 px-6 py-3 font-medium text-white transition-colors hover:bg-indigo-700"
          >
            Start a Mock Interview
          </button>
          <button
            onClick={() => navigate('/dashboard')}
            className="rounded-lg border border-slate-300 px-6 py-3 font-medium text-slate-700 transition-colors hover:bg-slate-100"
          >
            Go to Dashboard
          </button>
        </div>
      ) : (
        <div className="flex gap-3">
          <button
            onClick={() => navigate('/signup')}
            className="rounded-lg bg-indigo-600 px-6 py-3 font-medium text-white transition-colors hover:bg-indigo-700"
          >
            Sign up to Get Started
          </button>
          <button
            onClick={() => navigate('/login')}
            className="rounded-lg border border-slate-300 px-6 py-3 font-medium text-slate-700 transition-colors hover:bg-slate-100"
          >
            Log in
          </button>
        </div>
      )}
    </div>
  )
}

export default LandingPage
