import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { IconChartBar, IconMic, IconTarget } from '../components/icons'

const FEATURES = [
  {
    icon: IconMic,
    title: 'Adaptive AI questions',
    description:
      'Every follow-up question is generated live from your last answer, with difficulty that adjusts as you go.',
  },
  {
    icon: IconChartBar,
    title: 'Speech & presentation analysis',
    description:
      'Optional, on-device microphone and camera analysis for pace, filler words, and camera presence — nothing is ever uploaded.',
  },
  {
    icon: IconTarget,
    title: 'A practice plan that targets weak spots',
    description:
      'Your history is distilled into ranked, actionable practice areas — not just a score you have to interpret yourself.',
  },
]

function LandingPage() {
  const navigate = useNavigate()
  const { user } = useAuth()

  return (
    <div className="flex flex-col items-center gap-16 py-10 text-center">
      <div className="flex flex-col items-center gap-6">
        <span className="badge border border-border-strong bg-surface text-ink-muted">
          AI-driven mock interviews
        </span>
        <h1 className="max-w-2xl text-4xl font-bold tracking-tight text-ink sm:text-5xl">
          Practice interviews with AI feedback
        </h1>
        <p className="max-w-xl text-base text-ink-muted">
          Run a realistic mock interview, get structured feedback, and track
          your progress over time.
        </p>

        {user ? (
          <div className="flex flex-wrap justify-center gap-3">
            <button onClick={() => navigate('/setup')} className="btn btn-primary">
              Start a Mock Interview
            </button>
            <button onClick={() => navigate('/dashboard')} className="btn btn-secondary">
              Go to Dashboard
            </button>
          </div>
        ) : (
          <div className="flex flex-wrap justify-center gap-3">
            <button onClick={() => navigate('/signup')} className="btn btn-primary">
              Sign up to Get Started
            </button>
            <button onClick={() => navigate('/login')} className="btn btn-secondary">
              Log in
            </button>
          </div>
        )}
      </div>

      <div className="grid w-full gap-4 text-left sm:grid-cols-3">
        {FEATURES.map((feature) => (
          <div key={feature.title} className="surface-card p-5">
            <span className="mb-3 flex h-9 w-9 items-center justify-center rounded-lg bg-accent-soft text-accent">
              <feature.icon className="h-4 w-4" />
            </span>
            <h3 className="mb-1.5 text-sm font-semibold text-ink">{feature.title}</h3>
            <p className="text-sm text-ink-muted">{feature.description}</p>
          </div>
        ))}
      </div>
    </div>
  )
}

export default LandingPage
