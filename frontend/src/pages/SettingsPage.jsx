import { useNavigate } from 'react-router-dom'
import { useState } from 'react'
import { useAuth } from '../context/AuthContext'
import { getPreferences, savePreferences } from '../utils/preferences'
import { IconBell, IconLogout, IconSettings, IconTarget } from '../components/icons'

function SectionCard({ icon: Icon, title, description, children }) {
  return (
    <div className="surface-card p-5">
      <div className="mb-4 flex items-start gap-3">
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-accent-soft text-accent">
          <Icon className="h-4 w-4" />
        </span>
        <div>
          <h2 className="text-sm font-semibold text-ink">{title}</h2>
          {description && <p className="mt-0.5 text-xs text-ink-muted">{description}</p>}
        </div>
      </div>
      {children}
    </div>
  )
}

// Sections only show controls backed by something real: Account reads
// from the actual authenticated user (profile display/edit lives on its
// own page — see ProfilePage.jsx; there's no profile-update or
// password-change endpoint on the backend either way). Interview
// Preferences are genuine,
// functional client-side defaults (see utils/preferences.js) consumed by
// InterviewSetupPage. Notifications has nothing to back it yet — shown
// honestly as not-available rather than as working toggles that do
// nothing.
function SettingsPage() {
  const { logout } = useAuth()
  const navigate = useNavigate()
  const [prefs, setPrefs] = useState(getPreferences)
  const [saved, setSaved] = useState(false)

  function updatePref(partial) {
    const next = savePreferences(partial)
    setPrefs(next)
    setSaved(true)
    setTimeout(() => setSaved(false), 1500)
  }

  function handleLogout() {
    logout()
    navigate('/login')
  }

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-6">
      <div>
        <h1 className="mb-1.5 text-2xl font-semibold tracking-tight text-ink">Settings</h1>
        <p className="text-sm text-ink-muted">Manage your account and interview preferences.</p>
      </div>

      <SectionCard icon={IconSettings} title="Account" description="Session and sign-out.">
        <button type="button" onClick={handleLogout} className="btn btn-danger">
          <IconLogout className="h-4 w-4" />
          Log out
        </button>
      </SectionCard>

      <SectionCard
        icon={IconTarget}
        title="Interview preferences"
        description="Defaults applied the next time you set up a new interview. Saved on this device."
      >
        <div className="flex flex-col gap-4">
          <div>
            <p className="mb-2 text-xs font-medium text-ink-muted">Default difficulty</p>
            <div className="flex gap-2">
              {['easy', 'medium', 'hard'].map((level) => (
                <button
                  key={level}
                  type="button"
                  onClick={() => updatePref({ defaultDifficulty: level })}
                  className={`btn !px-3 !py-1.5 !text-xs capitalize ${
                    prefs.defaultDifficulty === level ? 'btn-primary' : 'btn-secondary'
                  }`}
                >
                  {level}
                </button>
              ))}
            </div>
          </div>

          <div>
            <p className="mb-2 text-xs font-medium text-ink-muted">Default question count</p>
            <div className="flex gap-2">
              {[5, 7, 10].map((count) => (
                <button
                  key={count}
                  type="button"
                  onClick={() => updatePref({ defaultQuestionCount: count })}
                  className={`btn !px-3 !py-1.5 !text-xs ${
                    prefs.defaultQuestionCount === count ? 'btn-primary' : 'btn-secondary'
                  }`}
                >
                  {count}
                </button>
              ))}
            </div>
          </div>

          {saved && <p className="text-xs text-success">Saved.</p>}
        </div>
      </SectionCard>

      <SectionCard
        icon={IconBell}
        title="Notifications"
        description="Email and in-app notifications aren't available yet — this app doesn't send any notifications today."
      >
        <p className="text-xs text-ink-faint">Nothing to configure here yet.</p>
      </SectionCard>
    </div>
  )
}

export default SettingsPage
