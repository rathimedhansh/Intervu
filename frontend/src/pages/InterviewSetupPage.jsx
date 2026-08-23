import { useEffect, useRef, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { createInterview } from '../api/interviews'
import { listResumes, uploadResume } from '../api/resumes'
import CommunicationConsent from '../components/CommunicationConsent'
import { MAX_FOCUS_CATEGORIES, RUBRIC_CATEGORIES } from '../constants/rubricCategories'
import {
  IconCheck,
  IconChevronLeft,
  IconChevronRight,
  IconFileText,
} from '../components/icons'

// Kept in sync with backend/app/services/question_generation/bank.py ROLES.
// The backend accepts any non-blank role string (not just this list) — see
// OTHER_ROLE_VALUE below for the custom-role escape hatch.
const ROLES = [
  'Software Engineer',
  'Frontend Engineer',
  'Backend Engineer',
  'Full Stack Engineer',
  'Mobile Developer',
  'DevOps Engineer',
  'Cloud Engineer',
  'Data Engineer',
  'ML Engineer',
  'AI Engineer',
  'Cybersecurity Engineer',
  'QA/Automation Engineer',
  'Data Scientist',
  'Data Analyst',
  'AI Researcher',
  'Product Manager',
  'Business Analyst',
  'Project Manager',
  'UX/UI Designer',
]

// Sentinel dropdown value that reveals a free-text input instead of being
// sent to the backend as-is — the typed text becomes the actual role.
const OTHER_ROLE_VALUE = 'Other'
const MAX_ROLE_LENGTH = 100

// The AI interviewer keeps interviews bounded between 5 and 10 questions
// (see backend/app/services/interview_flow) — the backend clamps into that
// range regardless, but only offering valid values avoids a confusing
// silent adjustment. Time estimates assume ~2-3 min per question (reading,
// answering, and the occasional follow-up) — this doubles as the "interview
// length / duration" control since there's no separate duration field.
const QUESTION_COUNT_OPTIONS = [
  { value: 5, label: '5 questions', time: '~10–15 min' },
  { value: 7, label: '7 questions', time: '~15–20 min' },
  { value: 10, label: '10 questions', time: '~20–30 min' },
]

const DIFFICULTY_OPTIONS = [
  { value: 'easy', label: 'Easy', description: 'Foundational questions, gentler follow-ups.' },
  { value: 'medium', label: 'Medium', description: 'Standard interview pace and depth.' },
  { value: 'hard', label: 'Hard', description: 'Deeper technical and behavioral probing.' },
]

const MAX_RESUME_SIZE_BYTES = 5 * 1024 * 1024

const STEPS = [
  { number: '01', label: 'Role & Focus' },
  { number: '02', label: 'Interview Preferences' },
  { number: '03', label: 'Review & Start' },
]

function formatDate(dateString) {
  return new Date(dateString).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

function StepIndicator({ step }) {
  return (
    <ol className="mb-8 flex flex-col gap-2 sm:flex-row sm:items-center sm:gap-0">
      {STEPS.map((item, index) => {
        const stepNumber = index + 1
        const isActive = stepNumber === step
        const isDone = stepNumber < step
        return (
          <li key={item.number} className="flex flex-1 items-center">
            <div className="flex items-center gap-2.5">
              <span
                className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-semibold transition-colors ${
                  isActive
                    ? 'bg-accent text-white'
                    : isDone
                      ? 'bg-accent-soft text-accent'
                      : 'bg-surface-2 text-ink-faint'
                }`}
              >
                {isDone ? <IconCheck className="h-3.5 w-3.5" /> : item.number}
              </span>
              <span className={`text-sm font-medium ${isActive ? 'text-ink' : 'text-ink-faint'}`}>
                {item.label}
              </span>
            </div>
            {stepNumber < STEPS.length && (
              <span className="mx-3 hidden h-px flex-1 bg-border sm:block" aria-hidden="true" />
            )}
          </li>
        )
      })}
    </ol>
  )
}

function PreviousResumePicker({ resumes, onSelect }) {
  if (resumes.length === 0) return null
  return (
    <div className="mb-3">
      <p className="mb-1.5 text-xs font-medium text-ink-muted">Use a previous resume</p>
      <div className="flex flex-col gap-1.5">
        {resumes.map((r) => (
          <button
            type="button"
            key={r.id}
            onClick={() => onSelect(r)}
            className="flex items-center justify-between gap-3 rounded-lg border border-border px-3 py-2 text-left text-sm transition-colors hover:border-accent-border hover:bg-accent-soft"
          >
            <span className="truncate font-medium text-ink">{r.original_filename}</span>
            <span className="shrink-0 text-xs text-ink-faint">{formatDate(r.created_at)}</span>
          </button>
        ))}
      </div>
      <p className="mt-2 text-xs text-ink-faint">or upload a new one below</p>
    </div>
  )
}

function ResumeSummary({ resume, onRemove }) {
  const { analysis } = resume
  return (
    <div className="rounded-xl border border-success/25 bg-success-soft p-4">
      <div className="mb-2 flex items-start justify-between gap-3">
        <p className="flex items-center gap-1.5 text-sm font-medium text-ink">
          <IconFileText className="h-3.5 w-3.5 text-success" />
          {resume.original_filename}
        </p>
        <button
          type="button"
          onClick={onRemove}
          className="shrink-0 text-xs font-medium text-success underline hover:text-ink"
        >
          Remove
        </button>
      </div>
      <p className="mb-3 text-sm text-ink-muted">{analysis.summary}</p>
      <div className="grid gap-3 sm:grid-cols-2">
        {analysis.strong_areas.length > 0 && (
          <div>
            <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-success">
              Strong areas
            </h3>
            <ul className="list-disc space-y-0.5 pl-4 text-xs text-ink-muted">
              {analysis.strong_areas.map((item, i) => (
                <li key={i}>{item}</li>
              ))}
            </ul>
          </div>
        )}
        {analysis.key_technologies.length > 0 && (
          <div>
            <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-success">
              Key technologies
            </h3>
            <div className="flex flex-wrap gap-1">
              {analysis.key_technologies.map((tech, i) => (
                <span key={i} className="badge bg-surface-2 text-ink-muted">
                  {tech}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function SectionHeading({ title, hint, aside }) {
  return (
    <div className="mb-4 flex items-start justify-between gap-3">
      <div>
        <h2 className="text-base font-semibold text-ink">{title}</h2>
        {hint && <p className="mt-0.5 text-xs text-ink-muted">{hint}</p>}
      </div>
      {aside && <span className="shrink-0 text-xs font-medium text-ink-faint">{aside}</span>}
    </div>
  )
}

function OptionCard({ selected, onSelect, label, description }) {
  return (
    <button
      type="button"
      onClick={onSelect}
      aria-pressed={selected}
      className={`rounded-xl border px-3.5 py-3 text-left transition-colors ${
        selected
          ? 'border-accent-border bg-accent-soft ring-1 ring-accent'
          : 'border-border hover:border-border-strong hover:bg-surface-hover'
      }`}
    >
      <span className="block text-sm font-medium text-ink">{label}</span>
      <span className="block text-xs text-ink-muted">{description}</span>
    </button>
  )
}

function FocusChip({ selected, disabled, onToggle, label, title }) {
  return (
    <button
      type="button"
      onClick={onToggle}
      disabled={disabled}
      title={title}
      aria-pressed={selected}
      className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-40 ${
        selected
          ? 'border-accent bg-accent text-white'
          : 'border-border text-ink-muted hover:border-border-strong hover:bg-surface-hover'
      }`}
    >
      {selected && <IconCheck className="h-3 w-3" />}
      {label}
    </button>
  )
}

const FOCUSABLE_CATEGORY_KEYS = new Set(RUBRIC_CATEGORIES.map((c) => c.key))

function InterviewSetupPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const fileInputRef = useRef(null)
  const [step, setStep] = useState(1)
  const [role, setRole] = useState(ROLES[0])
  const [customRole, setCustomRole] = useState('')
  const [difficulty, setDifficulty] = useState('medium')
  const [questionCount, setQuestionCount] = useState(5)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState(null)

  // Prefilled by the dashboard's "Practice weak areas" CTA (see
  // DashboardPage.jsx), which navigates here with router state carrying
  // the user's weakest rubric category keys. Filtered/capped defensively
  // since this is just router state, not validated input.
  const [focusCategories, setFocusCategories] = useState(() => {
    const incoming = location.state?.focusCategories
    if (!Array.isArray(incoming)) return []
    return incoming.filter((key) => FOCUSABLE_CATEGORY_KEYS.has(key)).slice(0, MAX_FOCUS_CATEGORIES)
  })
  const arrivedWithPrefilledFocus = focusCategories.length > 0

  function toggleFocusCategory(key) {
    setFocusCategories((current) =>
      current.includes(key)
        ? current.filter((c) => c !== key)
        : current.length >= MAX_FOCUS_CATEGORIES
          ? current
          : [...current, key],
    )
  }

  const [resume, setResume] = useState(null)
  const [isUploadingResume, setIsUploadingResume] = useState(false)
  const [resumeError, setResumeError] = useState(null)
  const [previousResumes, setPreviousResumes] = useState([])

  const [speechEnabled, setSpeechEnabled] = useState(false)
  const [cameraEnabled, setCameraEnabled] = useState(false)

  // Best-effort — offering "use a previous resume" is a convenience, not
  // essential to setting up an interview, so a failure here never blocks
  // the rest of the form (same philosophy as CommunicationPanel).
  useEffect(() => {
    listResumes()
      .then(setPreviousResumes)
      .catch(() => {})
  }, [])

  const isCustomRole = role === OTHER_ROLE_VALUE
  const effectiveRole = (isCustomRole ? customRole : role).trim()
  const roleIsValid = effectiveRole.length > 0 && effectiveRole.length <= MAX_ROLE_LENGTH
  const canSubmit = roleIsValid && !isSubmitting && !isUploadingResume
  const selectedQuestionOption =
    QUESTION_COUNT_OPTIONS.find((option) => option.value === questionCount) ??
    QUESTION_COUNT_OPTIONS[0]
  const selectedDifficultyOption = DIFFICULTY_OPTIONS.find((option) => option.value === difficulty)

  async function handleResumeChange(event) {
    const file = event.target.files?.[0]
    if (!file) return

    setResumeError(null)

    if (file.type !== 'application/pdf') {
      setResumeError('Only PDF files are supported.')
      event.target.value = ''
      return
    }
    if (file.size > MAX_RESUME_SIZE_BYTES) {
      setResumeError('Resume exceeds the 5MB size limit.')
      event.target.value = ''
      return
    }

    setIsUploadingResume(true)
    try {
      const uploaded = await uploadResume(file)
      setResume(uploaded)
      setPreviousResumes((current) => [uploaded, ...current])
    } catch (err) {
      setResumeError(err.message)
    } finally {
      setIsUploadingResume(false)
      event.target.value = ''
    }
  }

  function handleRemoveResume() {
    setResume(null)
    setResumeError(null)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  async function handleSubmit(event) {
    event.preventDefault()
    // The wizard shares one <form>, so pressing Enter on step 1/2 (e.g.
    // after typing a custom role) fires this same handler — treat that as
    // "advance to the next step" instead of creating the interview early.
    if (step !== STEPS.length) {
      if (step === 1 && !roleIsValid) return
      goNext()
      return
    }
    if (!canSubmit) return
    setError(null)

    setIsSubmitting(true)
    try {
      const interview = await createInterview(
        effectiveRole,
        difficulty,
        questionCount,
        resume?.id,
        focusCategories,
      )
      navigate(`/interview/${interview.id}`, { state: { speechEnabled, cameraEnabled } })
    } catch (err) {
      setError(err.message)
      setIsSubmitting(false)
    }
  }

  function goNext() {
    setStep((current) => Math.min(STEPS.length, current + 1))
  }

  function goBack() {
    setStep((current) => Math.max(1, current - 1))
  }

  return (
    <div className="mx-auto max-w-[1100px]">
      <button
        type="button"
        onClick={() => navigate('/dashboard')}
        className="mb-3 inline-flex items-center gap-1 text-xs font-medium text-ink-faint transition-colors hover:text-ink"
      >
        <IconChevronLeft className="h-3.5 w-3.5" />
        Dashboard
      </button>

      <h1 className="mb-1 text-[28px] font-semibold tracking-tight text-ink">New Interview</h1>
      <p className="mb-6 text-sm text-ink-muted">
        Customize your interview and get AI-generated questions tailored to you.
      </p>

      <StepIndicator step={step} />

      <form onSubmit={handleSubmit} className="flex flex-col gap-5">
        {step === 1 && (
          <div className="surface-card p-5 sm:p-6">
            <div className="mb-5">
              <h2 className="text-lg font-semibold text-ink">Let's create your interview</h2>
              <p className="mt-1 text-sm text-ink-muted">
                Choose what you're preparing for and what you want to improve.
              </p>
            </div>

            <div className="mb-6">
              <label htmlFor="role" className="mb-1.5 block text-sm font-medium text-ink-muted">
                Target role
              </label>
              <div className="relative">
                <select
                  id="role"
                  value={role}
                  onChange={(event) => setRole(event.target.value)}
                  className="input-field appearance-none pr-9"
                >
                  {ROLES.map((option) => (
                    <option key={option} value={option}>
                      {option}
                    </option>
                  ))}
                  <option value={OTHER_ROLE_VALUE}>Other / Custom Role</option>
                </select>
                <IconChevronRight className="pointer-events-none absolute right-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 rotate-90 text-ink-faint" />
              </div>

              {isCustomRole && (
                <div className="mt-2">
                  <input
                    type="text"
                    value={customRole}
                    onChange={(event) => setCustomRole(event.target.value)}
                    placeholder="Enter the role you want to practice for"
                    maxLength={MAX_ROLE_LENGTH}
                    className="input-field"
                  />
                  <div className="mt-1 flex items-center justify-between">
                    <p className="text-xs text-ink-faint">
                      {customRole.trim().length === 0 && 'Enter a role to continue.'}
                    </p>
                    <p className="text-xs text-ink-faint">
                      {customRole.length}/{MAX_ROLE_LENGTH}
                    </p>
                  </div>
                </div>
              )}
            </div>

            <div>
              <SectionHeading
                title="Focus areas"
                hint="Choose up to 3 areas you'd like the interview to emphasize."
                aside={`${focusCategories.length} / ${MAX_FOCUS_CATEGORIES} selected`}
              />
              {arrivedWithPrefilledFocus && (
                <p className="mb-2 text-xs text-accent">
                  Prefilled from your dashboard's weakest areas — adjust anytime.
                </p>
              )}
              <div className="flex flex-wrap gap-1.5">
                {RUBRIC_CATEGORIES.map((category) => {
                  const isSelected = focusCategories.includes(category.key)
                  const disabled = !isSelected && focusCategories.length >= MAX_FOCUS_CATEGORIES
                  return (
                    <FocusChip
                      key={category.key}
                      selected={isSelected}
                      disabled={disabled}
                      onToggle={() => toggleFocusCategory(category.key)}
                      label={category.label}
                      title={category.description}
                    />
                  )
                })}
              </div>
              <p className="mt-2 text-xs text-ink-faint">
                {focusCategories.length === 0 && 'None selected — questions will cover a natural mix, same as before.'}
              </p>
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="flex flex-col gap-4">
            <div className="surface-card p-5">
              <SectionHeading title="Difficulty" hint="Choose the difficulty level." />
              <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
                {DIFFICULTY_OPTIONS.map((option) => (
                  <OptionCard
                    key={option.value}
                    selected={difficulty === option.value}
                    onSelect={() => setDifficulty(option.value)}
                    label={option.label}
                    description={option.description}
                  />
                ))}
              </div>
            </div>

            <div className="surface-card p-5">
              <SectionHeading
                title="Interview length"
                hint="The AI may ask a follow-up on an interesting answer — this is the target number of main questions."
              />
              <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
                {QUESTION_COUNT_OPTIONS.map((option) => (
                  <OptionCard
                    key={option.value}
                    selected={questionCount === option.value}
                    onSelect={() => setQuestionCount(option.value)}
                    label={option.label}
                    description={option.time}
                  />
                ))}
              </div>
            </div>

            <div className="surface-card p-5">
              <SectionHeading
                title="Resume"
                hint="Optional. PDF only, up to 5MB. Questions will reference your projects, technologies, and experience."
              />
              {resume ? (
                <ResumeSummary resume={resume} onRemove={handleRemoveResume} />
              ) : (
                <>
                  <PreviousResumePicker resumes={previousResumes} onSelect={setResume} />
                  <input
                    id="resume"
                    ref={fileInputRef}
                    type="file"
                    accept="application/pdf"
                    onChange={handleResumeChange}
                    disabled={isUploadingResume}
                    className="w-full rounded-lg border border-dashed border-border px-3 py-2 text-sm text-ink-muted file:mr-3 file:rounded-md file:border-0 file:bg-accent-soft file:px-3 file:py-1.5 file:text-sm file:font-medium file:text-accent hover:file:bg-accent/20"
                  />
                </>
              )}

              {isUploadingResume && (
                <p className="mt-2 text-sm text-ink-muted">Uploading and analyzing resume...</p>
              )}
              {resumeError && <p className="mt-2 text-sm text-danger">{resumeError}</p>}
            </div>

            <CommunicationConsent
              speechEnabled={speechEnabled}
              onSpeechChange={setSpeechEnabled}
              cameraEnabled={cameraEnabled}
              onCameraChange={setCameraEnabled}
            />
          </div>
        )}

        {step === 3 && (
          <div className="surface-card p-5 sm:p-6">
            <SectionHeading title="Interview summary" hint="Review your setup before starting." />

            <div className="rounded-xl border border-border bg-surface-2/60 p-4">
              <p className="text-base font-semibold text-ink">
                {effectiveRole || <span className="text-ink-faint">Not set</span>}
              </p>
              <p className="mt-1 text-sm text-ink-muted">
                {selectedDifficultyOption?.label} difficulty · {selectedQuestionOption.label} (
                {selectedQuestionOption.time})
              </p>

              <dl className="mt-4 grid gap-3 border-t border-border pt-4 sm:grid-cols-2">
                <div>
                  <dt className="text-xs uppercase tracking-wide text-ink-faint">Resume</dt>
                  <dd className="mt-0.5 text-sm text-ink">{resume ? 'Attached' : 'Not attached'}</dd>
                </div>
                <div>
                  <dt className="text-xs uppercase tracking-wide text-ink-faint">Speech analysis</dt>
                  <dd className="mt-0.5 text-sm text-ink">{speechEnabled ? 'On' : 'Off'}</dd>
                </div>
                <div>
                  <dt className="text-xs uppercase tracking-wide text-ink-faint">Camera analysis</dt>
                  <dd className="mt-0.5 text-sm text-ink">{cameraEnabled ? 'On' : 'Off'}</dd>
                </div>
                <div>
                  <dt className="text-xs uppercase tracking-wide text-ink-faint">Focus</dt>
                  <dd className="mt-0.5 text-sm text-ink">
                    {focusCategories.length > 0
                      ? focusCategories
                          .map((key) => RUBRIC_CATEGORIES.find((c) => c.key === key)?.label ?? key)
                          .join(' · ')
                      : 'None selected'}
                  </dd>
                </div>
              </dl>
            </div>

            {error && <p className="mt-4 text-sm text-danger">{error}</p>}
          </div>
        )}

        <div className="flex items-center justify-between">
          {step > 1 ? (
            <button type="button" onClick={goBack} className="btn btn-secondary">
              <IconChevronLeft className="h-4 w-4" />
              Back
            </button>
          ) : (
            <span />
          )}

          {step < STEPS.length ? (
            <button
              type="button"
              onClick={goNext}
              disabled={step === 1 && !roleIsValid}
              className="btn btn-primary"
            >
              Continue
              <IconChevronRight className="h-4 w-4" />
            </button>
          ) : (
            <button type="submit" disabled={!canSubmit} className="btn btn-primary">
              {isSubmitting ? 'Starting...' : 'Start Interview'}
              <IconChevronRight className="h-4 w-4" />
            </button>
          )}
        </div>
      </form>
    </div>
  )
}

export default InterviewSetupPage
