// Lightweight client-side interview preferences — there's no backend
// endpoint for user preferences (only signup/login/me exist), so these are
// real, functional local defaults (read by InterviewSetupPage, editable on
// SettingsPage) rather than a server-synced profile field. Deliberately not
// presented as "account settings" anywhere in the UI for that reason.
const STORAGE_KEY = 'interview_preferences'

const DEFAULTS = {
  defaultDifficulty: 'medium',
  defaultQuestionCount: 5,
  defaultSpeechEnabled: false,
  defaultCameraEnabled: false,
}

export function getPreferences() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return DEFAULTS
    return { ...DEFAULTS, ...JSON.parse(raw) }
  } catch {
    return DEFAULTS
  }
}

export function savePreferences(partial) {
  const next = { ...getPreferences(), ...partial }
  localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
  return next
}
