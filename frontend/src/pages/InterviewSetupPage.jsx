import { useEffect, useRef, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { createInterview } from '../api/interviews'
import { listResumes, uploadResume } from '../api/resumes'
import CommunicationConsent from '../components/CommunicationConsent'
import { MAX_FOCUS_CATEGORIES, RUBRIC_CATEGORIES } from '../constants/rubricCategories'

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
// answering, and the occasional follow-up).
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

// Mirrors backend/app/services/answer_evaluation/rubrics.py — kept as
// plain labels (not the point values) since this is a "here's the shape
// of the feedback" preview, not a literal rubric reproduction.
const EVALUATION_CRITERIA = [
  {
    type: 'Behavioral questions',
    categories: ['Relevance', 'Clarity', 'Structure', 'Specificity / examples', 'Communication'],
  },
  {
    type: 'Technical questions',
    categories: ['Technical accuracy', 'Completeness', 'Reasoning', 'Clarity', 'Examples'],
  },
]

const MAX_RESUME_SIZE_BYTES = 5 * 1024 * 1024

function formatDate(dateString) {
  return new Date(dateString).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

function PreviousResumePicker({ resumes, onSelect }) {
  if (resumes.length === 0) return null
  return (
    <div className="mb-3">
      <p className="mb-1.5 text-xs font-medium text-slate-600">
        Use a previous resume
      </p>
      <div className="flex flex-col gap-1.5">
        {resumes.map((r) => (
          <button
            type="button"
            key={r.id}
            onClick={() => onSelect(r)}
            className="flex items-center justify-between gap-3 rounded-lg border border-slate-300 px-3 py-2 text-left text-sm transition-colors hover:border-indigo-400 hover:bg-indigo-50"
          >
            <span className="truncate font-medium text-slate-800">
              {r.original_filename}
            </span>
            <span className="shrink-0 text-xs text-slate-400">
              {formatDate(r.created_at)}
            </span>
          </button>
        ))}
      </div>
      <p className="mt-2 text-xs text-slate-400">or upload a new one below</p>
    </div>
  )
}

function ResumeSummary({ resume, onRemove }) {
  const { analysis } = resume
  return (
    <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4">
      <div className="mb-2 flex items-start justify-between gap-3">
        <p className="text-sm font-medium text-emerald-900">
          {resume.original_filename}
        </p>
        <button
          type="button"
          onClick={onRemove}
          className="shrink-0 text-xs font-medium text-emerald-700 underline hover:text-emerald-900"
        >
          Remove
        </button>
      </div>
      <p className="mb-3 text-sm text-emerald-800">{analysis.summary}</p>
      <div className="grid gap-3 sm:grid-cols-2">
        {analysis.strong_areas.length > 0 && (
          <div>
            <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-emerald-700">
              Strong areas
            </h3>
            <ul className="list-disc space-y-0.5 pl-4 text-xs text-emerald-800">
              {analysis.strong_areas.map((item, i) => (
                <li key={i}>{item}</li>
              ))}
            </ul>
          </div>
        )}
        {analysis.key_technologies.length > 0 && (
          <div>
            <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-emerald-700">
              Key technologies
            </h3>
            <div className="flex flex-wrap gap-1">
              {analysis.key_technologies.map((tech, i) => (
                <span
                  key={i}
                  className="rounded-full bg-emerald-100 px-2 py-0.5 text-xs text-emerald-800"
                >
                  {tech}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
      <p className="mt-3 text-xs text-emerald-700">
        Interview questions will be generated from this resume.
      </p>
    </div>
  )
}

function SectionCard({ step, title, hint, children }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-5">
      <div className="mb-3 flex items-baseline gap-2">
        <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-indigo-100 text-[11px] font-semibold text-indigo-700">
          {step}
        </span>
        <h2 className="text-sm font-semibold text-slate-900">{title}</h2>
      </div>
      {hint && <p className="mb-3 text-xs text-slate-500">{hint}</p>}
      {children}
    </div>
  )
}

function SegmentedOption({ selected, onSelect, label, description }) {
  return (
    <button
      type="button"
      onClick={onSelect}
      aria-pressed={selected}
      className={`rounded-lg border px-3 py-2.5 text-left transition-colors ${
        selected
          ? 'border-indigo-600 bg-indigo-50 ring-1 ring-indigo-600'
          : 'border-slate-300 hover:bg-slate-50'
      }`}
    >
      <span className="block text-sm font-medium text-slate-900">{label}</span>
      <span className="block text-xs text-slate-500">{description}</span>
    </button>
  )
}

function FocusCategoryPicker({ selected, onToggle, prefilled }) {
  const atLimit = selected.length >= MAX_FOCUS_CATEGORIES
  return (
    <div>
      {prefilled && selected.length > 0 && (
        <p className="mb-2 text-xs text-indigo-600">
          Prefilled from your dashboard's weakest areas — adjust anytime.
        </p>
      )}
      <div className="flex flex-wrap gap-1.5">
        {RUBRIC_CATEGORIES.map((category) => {
          const isSelected = selected.includes(category.key)
          const disabled = !isSelected && atLimit
          return (
            <button
              type="button"
              key={category.key}
              onClick={() => onToggle(category.key)}
              disabled={disabled}
              title={category.description}
              aria-pressed={isSelected}
              className={`rounded-full border px-3 py-1.5 text-xs font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-40 ${
                isSelected
                  ? 'border-indigo-600 bg-indigo-600 text-white'
                  : 'border-slate-300 text-slate-600 hover:bg-slate-50'
              }`}
            >
              {category.label}
            </button>
          )
        })}
      </div>
      <p className="mt-2 text-xs text-slate-400">
        {selected.length > 0
          ? `${selected.length}/${MAX_FOCUS_CATEGORIES} selected — questions will lean toward these.`
          : 'None selected — questions will cover a natural mix, same as before.'}
      </p>
    </div>
  )
}

function SummaryRow({ label, value }) {
  return (
    <div className="flex items-start justify-between gap-3 text-sm">
      <dt className="text-slate-500">{label}</dt>
      <dd className="text-right font-medium text-slate-900">{value}</dd>
    </div>
  )
}

const FOCUSABLE_CATEGORY_KEYS = new Set(RUBRIC_CATEGORIES.map((c) => c.key))

function InterviewSetupPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const fileInputRef = useRef(null)
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

  return (
    <div className="mx-auto max-w-4xl">
      <h1 className="mb-2 text-2xl font-semibold text-slate-900">
        Set up your interview
      </h1>
      <p className="mb-8 max-w-2xl text-slate-600">
        Pick a role, difficulty, and how many questions you want to practice.
        Questions adapt to your answers as you go, and difficulty adjusts
        gradually based on how you're doing.
      </p>

      <div className="grid gap-6 lg:grid-cols-[1fr_300px] lg:items-start">
        <form onSubmit={handleSubmit} className="flex flex-col gap-5">
          <SectionCard step={1} title="Target role">
            <select
              id="role"
              value={role}
              onChange={(event) => setRole(event.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 focus:border-indigo-500 focus:outline-none"
            >
              {ROLES.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
              <option value={OTHER_ROLE_VALUE}>Other / Custom Role</option>
            </select>

            {isCustomRole && (
              <div className="mt-2">
                <input
                  type="text"
                  value={customRole}
                  onChange={(event) => setCustomRole(event.target.value)}
                  placeholder="Enter the role you want to practice for"
                  maxLength={MAX_ROLE_LENGTH}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 focus:border-indigo-500 focus:outline-none"
                />
                <div className="mt-1 flex items-center justify-between">
                  <p className="text-xs text-slate-500">
                    {customRole.trim().length === 0 && 'Enter a role to continue.'}
                  </p>
                  <p className="text-xs text-slate-400">
                    {customRole.length}/{MAX_ROLE_LENGTH}
                  </p>
                </div>
              </div>
            )}
          </SectionCard>

          <SectionCard
            step={2}
            title="Focus areas (optional)"
            hint="Practicing weak areas? Pick up to 3 rubric categories and today's questions will lean toward exercising them."
          >
            <FocusCategoryPicker
              selected={focusCategories}
              onToggle={toggleFocusCategory}
              prefilled={arrivedWithPrefilledFocus}
            />
          </SectionCard>

          <SectionCard step={3} title="Difficulty">
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
              {DIFFICULTY_OPTIONS.map((option) => (
                <SegmentedOption
                  key={option.value}
                  selected={difficulty === option.value}
                  onSelect={() => setDifficulty(option.value)}
                  label={option.label}
                  description={option.description}
                />
              ))}
            </div>
          </SectionCard>

          <SectionCard
            step={4}
            title="Interview length"
            hint="The AI may ask a follow-up on an interesting answer — this is the target number of main questions."
          >
            <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
              {QUESTION_COUNT_OPTIONS.map((option) => (
                <SegmentedOption
                  key={option.value}
                  selected={questionCount === option.value}
                  onSelect={() => setQuestionCount(option.value)}
                  label={option.label}
                  description={option.time}
                />
              ))}
            </div>
          </SectionCard>

          <SectionCard
            step={5}
            title="Resume"
            hint="Optional. PDF only, up to 5MB. Questions will reference your projects, technologies, and experience."
          >
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
                  className="w-full rounded-lg border border-dashed border-slate-300 px-3 py-2 text-sm text-slate-600 file:mr-3 file:rounded-md file:border-0 file:bg-indigo-50 file:px-3 file:py-1.5 file:text-sm file:font-medium file:text-indigo-700 hover:file:bg-indigo-100"
                />
              </>
            )}

            {isUploadingResume && (
              <p className="mt-2 text-sm text-slate-500">
                Uploading and analyzing resume...
              </p>
            )}
            {resumeError && (
              <p className="mt-2 text-sm text-red-600">{resumeError}</p>
            )}
          </SectionCard>

          <SectionCard step={6} title="Communication analysis">
            <CommunicationConsent
              speechEnabled={speechEnabled}
              onSpeechChange={setSpeechEnabled}
              cameraEnabled={cameraEnabled}
              onCameraChange={setCameraEnabled}
            />
          </SectionCard>

          {error && <p className="text-sm text-red-600">{error}</p>}

          <button
            type="submit"
            disabled={!canSubmit}
            className="rounded-lg bg-indigo-600 px-6 py-3 font-medium text-white transition-colors hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isSubmitting ? 'Starting...' : 'Begin Interview'}
          </button>
        </form>

        <aside className="flex flex-col gap-6 lg:sticky lg:top-6">
          <div className="rounded-lg border border-slate-200 bg-white p-5">
            <h2 className="mb-3 text-sm font-semibold text-slate-900">
              Your setup
            </h2>
            <dl className="flex flex-col gap-2.5">
              <SummaryRow
                label="Role"
                value={effectiveRole || <span className="text-slate-400">Not set</span>}
              />
              <SummaryRow
                label="Focus areas"
                value={
                  focusCategories.length > 0
                    ? focusCategories
                        .map((key) => RUBRIC_CATEGORIES.find((c) => c.key === key)?.label ?? key)
                        .join(', ')
                    : <span className="text-slate-400">None selected</span>
                }
              />
              <SummaryRow
                label="Difficulty"
                value={difficulty[0].toUpperCase() + difficulty.slice(1)}
              />
              <SummaryRow
                label="Length"
                value={`${selectedQuestionOption.label} (${selectedQuestionOption.time})`}
              />
              <SummaryRow
                label="Resume"
                value={resume ? 'Attached' : 'Not attached'}
              />
              <SummaryRow label="Speech analysis" value={speechEnabled ? 'On' : 'Off'} />
              <SummaryRow label="Camera analysis" value={cameraEnabled ? 'On' : 'Off'} />
            </dl>
          </div>

          <div className="rounded-lg border border-slate-200 bg-white p-5">
            <h2 className="mb-1 text-sm font-semibold text-slate-900">
              What we'll evaluate
            </h2>
            <p className="mb-3 text-xs text-slate-500">
              Every answer is scored against a rubric matched to the question
              type, plus written feedback and a stronger-answer example.
            </p>
            <div className="flex flex-col gap-3">
              {EVALUATION_CRITERIA.map((group) => (
                <div key={group.type}>
                  <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
                    {group.type}
                  </h3>
                  <div className="flex flex-wrap gap-1">
                    {group.categories.map((category) => (
                      <span
                        key={category}
                        className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] text-slate-600"
                      >
                        {category}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
            <p className="mt-3 text-xs text-slate-500">
              Difficulty adapts as you go — strong answers gradually raise it,
              weaker ones ease it back.
            </p>
          </div>
        </aside>
      </div>
    </div>
  )
}

export default InterviewSetupPage
