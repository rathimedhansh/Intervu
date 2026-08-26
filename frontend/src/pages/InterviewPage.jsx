import { useCallback, useEffect, useRef, useState } from 'react'
import { useLocation, useNavigate, useParams } from 'react-router-dom'
import {
  completeInterview,
  getInterview,
  respondToQuestion,
} from '../api/interviews'
import CommunicationPanel from '../components/CommunicationPanel'
import ErrorState from '../components/ErrorState'
import { categoryLabel } from '../constants/rubricCategories'
import { useCameraAnalysis } from '../hooks/useCameraAnalysis'
import { useDictation } from '../hooks/useDictation'
import { computeSharedMicMirror } from '../hooks/sharedMicMirror'
import { useSpeechAnalysis } from '../hooks/useSpeechAnalysis'

const MAX_TEXTAREA_HEIGHT = 400

function capitalize(word) {
  return word ? word[0].toUpperCase() + word.slice(1) : word
}

function wordCount(text) {
  const trimmed = text.trim()
  return trimmed ? trimmed.split(/\s+/).length : 0
}

const PILL_TONE = {
  slate: 'bg-surface-2 text-ink-muted',
  emerald: 'bg-success-soft text-success',
  amber: 'bg-warning-soft text-warning',
}

const PILL_DOT_TONE = {
  slate: 'bg-ink-faint',
  emerald: 'bg-success',
  amber: 'bg-warning',
}

function StatusPill({ tone = 'slate', pulsing, children }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ${PILL_TONE[tone]}`}
    >
      {pulsing && (
        <span className={`h-1.5 w-1.5 animate-pulse rounded-full ${PILL_DOT_TONE[tone]}`} />
      )}
      {children}
    </span>
  )
}

// Shown while the AI evaluates the just-submitted answer and prepares the
// next question — the interview flow's single slowest, most "is this
// actually doing something?" moment, so it gets more than a line of text.
function ThinkingIndicator() {
  return (
    <div className="flex items-center gap-2.5 rounded-lg border border-accent-border bg-accent-soft px-3 py-2.5 text-sm text-accent">
      <span className="flex items-center gap-1" aria-hidden="true">
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-accent [animation-delay:-0.3s]" />
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-accent [animation-delay:-0.15s]" />
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-accent" />
      </span>
      <span>The AI is reviewing your answer and preparing the next question&hellip;</span>
    </div>
  )
}

// TEMPORARY MIC DIAGNOSTICS (2026-08-26, round 2 — Opera GX repro). The
// previous fix (fatal-error fallback in useSpeechAnalysis.js) did NOT
// resolve the reported failure: mic goes green, user speaks, no transcript
// appears anywhere, Submit stays disabled — reproduced with Communication
// Analysis enabled in Opera GX. This panel surfaces the ENTIRE browser
// SpeechRecognition pipeline for that (shared) path with nothing hidden —
// including errors previous code intentionally treated as "recoverable"
// (no-speech/aborted/network) — since a browser whose speech backend never
// works at all (e.g. a `network`/`service-not-allowed` error repeating
// forever) would look identical to those, and that fallback fix has no way
// to detect it: it only reacts to the FATAL codes. Do NOT remove until the
// real-browser root cause is confirmed and fixed.
function MicDiagnosticsPanel({
  speech,
  dictation,
  useOwnDictationMic,
  canCaptureShared,
  sharedCapturing,
  answerText,
  isSubmitting,
}) {
  const hasSpeechRecognition = Boolean(window.SpeechRecognition)
  const hasWebkitSpeechRecognition = Boolean(window.webkitSpeechRecognition)
  const submitEligible = !isSubmitting && Boolean(answerText.trim())
  const log = speech.diag.log
  const firstT = log[0]?.t ?? 0

  return (
    <div className="mb-4 rounded-lg border border-dashed border-warning/60 bg-warning-soft/30 p-3 font-mono text-[11px] leading-relaxed text-ink">
      <p className="mb-1.5 font-sans text-xs font-semibold text-warning">
        🔧 TEMP MIC DIAGNOSTICS (dev only, round 2 — do not remove until root cause confirmed)
      </p>

      <p className="font-sans font-semibold">Browser</p>
      <ul className="ml-4 list-disc break-all">
        <li>userAgent: {navigator.userAgent}</li>
        <li>window.SpeechRecognition supported: {String(hasSpeechRecognition)}</li>
        <li>window.webkitSpeechRecognition supported: {String(hasWebkitSpeechRecognition)}</li>
        <li>constructor chosen: {speech.diag.ctorInfo?.chosen ?? '(not yet reported)'}</li>
      </ul>

      <p className="mt-2 font-sans font-semibold">Microphone (getUserMedia)</p>
      <ul className="ml-4 list-disc">
        <li>track label: {speech.diag.micTrack?.trackLabel || '(not yet reported)'}</li>
        <li>track readyState: {speech.diag.micTrack?.trackReadyState ?? '(not yet reported)'}</li>
        <li>track enabled: {String(speech.diag.micTrack?.trackEnabled ?? '(not yet reported)')}</li>
        <li>track muted: {String(speech.diag.micTrack?.trackMuted ?? '(not yet reported)')}</li>
      </ul>

      <p className="mt-2 font-sans font-semibold">SpeechRecognition config actually applied</p>
      <ul className="ml-4 list-disc">
        <li>continuous: {String(speech.diag.recognitionConfig?.continuous ?? '(not yet reported)')}</li>
        <li>interimResults: {String(speech.diag.recognitionConfig?.interimResults ?? '(not yet reported)')}</li>
        <li>lang: {speech.diag.recognitionConfig?.lang ?? '(not yet reported)'}</li>
        <li>maxAlternatives: {speech.diag.recognitionConfig?.maxAlternatives ?? '(not yet reported)'}</li>
      </ul>

      <p className="mt-2 font-sans font-semibold">Latest error on the shared path (raw — never hidden)</p>
      <ul className="ml-4 list-disc">
        <li>error code: {speech.diag.lastError?.error ?? 'none yet'}</li>
        <li>message: {speech.diag.lastError?.message || '(none)'}</li>
      </ul>

      <p className="mt-2 font-sans font-semibold">
        Application state — active path:{' '}
        <strong>{useOwnDictationMic ? 'standalone dictation' : 'shared (communication-analysis)'}</strong>
      </p>
      <ul className="ml-4 list-disc">
        <li>speech.status: {speech.status}</li>
        <li>canCaptureShared: {String(canCaptureShared)}</li>
        <li>sharedCapturing: {String(sharedCapturing)}</li>
        <li>speech.liveTranscript: &quot;{speech.liveTranscript}&quot;</li>
        <li>dictation.supported: {String(dictation.supported)}</li>
        <li>dictation.isListening: {String(dictation.isListening)}</li>
        <li>answerText: &quot;{answerText}&quot;</li>
        <li>submit eligible: {String(submitEligible)}</li>
      </ul>

      <p className="mt-2 font-sans font-semibold">
        Exact chronological event sequence — oldest → newest, last {log.length} shown
      </p>
      <div className="mt-1 max-h-64 overflow-y-auto rounded border border-warning/40 bg-canvas/60 p-2">
        {log.length === 0 ? (
          <p className="font-sans italic text-ink-faint">(no events yet — click Start Answer and speak)</p>
        ) : (
          <ol className="ml-4 list-decimal">
            {log.map((entry, i) => (
              <li key={i}>
                <span className="text-ink-faint">+{entry.t - firstT}ms</span> <strong>{entry.type}</strong>
                {entry.error !== undefined && <> error=&quot;{String(entry.error)}&quot;</>}
                {entry.message ? <> msg=&quot;{entry.message}&quot;</> : null}
                {entry.isFinal !== undefined && <> isFinal={String(entry.isFinal)}</>}
                {entry.interim ? <> interim=&quot;{entry.interim}&quot;</> : null}
                {entry.finalTranscriptSoFar ? <> final=&quot;{entry.finalTranscriptSoFar}&quot;</> : null}
                {entry.chosen ? <> chosen={entry.chosen}</> : null}
                {entry.willRestart !== undefined && <> willRestart={String(entry.willRestart)}</>}
              </li>
            ))}
          </ol>
        )}
      </div>
    </div>
  )
}

function InterviewPage() {
  const { interviewId } = useParams()
  const navigate = useNavigate()
  const location = useLocation()

  const speechEnabled = Boolean(location.state?.speechEnabled)
  const cameraEnabled = Boolean(location.state?.cameraEnabled)
  const speech = useSpeechAnalysis(speechEnabled)
  const camera = useCameraAnalysis(cameraEnabled)

  // Chromium browsers only allow one active SpeechRecognition session at a
  // time. When communication analysis is running its own continuous
  // recognition, dictation must reuse its live transcript rather than
  // start a second, conflicting recognition instance. If communication
  // analysis was requested but actually failed to start (permission
  // denied, unsupported browser, etc.), fall back to the standalone
  // dictation mic instead of leaving the user with no speech input path.
  const speechAnalysisFailed = ['unsupported', 'denied', 'error'].includes(speech.status)
  const useOwnDictationMic = !speechEnabled || speechAnalysisFailed

  // Temporary diagnostic — remove once speech capture is confirmed working
  // reliably across browsers. Pinpoints which mic path is actually active,
  // since picking the wrong one silently produces no transcript.
  useEffect(() => {
    console.debug(
      '[dictation] mode:',
      useOwnDictationMic ? 'standalone (own SpeechRecognition instance)' : 'shared (reusing communication-analysis transcript)',
      '| speechEnabled:', speechEnabled,
      '| speech.status:', speech.status,
    )
  }, [useOwnDictationMic, speechEnabled, speech.status])

  const [interview, setInterview] = useState(null)
  const [currentQuestion, setCurrentQuestion] = useState(null)
  const [questionsAsked, setQuestionsAsked] = useState(0)
  const [questionCount, setQuestionCount] = useState(null)
  const [currentDifficulty, setCurrentDifficulty] = useState(null)
  // Separate from `notice` below: this is a low-priority, self-clearing
  // signal ("difficulty nudged up/down") that must never crowd out a more
  // important message (e.g. the state-recovery notice) sharing the same
  // screen real estate — see priority on keeping this "useful but subtle."
  const [difficultyNotice, setDifficultyNotice] = useState(null)
  const [answerText, setAnswerText] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isFinishing, setIsFinishing] = useState(false)
  const [error, setError] = useState(null)
  const [notice, setNotice] = useState(null)

  // Belt-and-suspenders alongside the `isSubmitting` state check: a ref is
  // read/written synchronously, so it closes the (tiny, but real) window
  // where two rapid clicks could both read a stale `isSubmitting=false`
  // before React commits the re-render that disables the button.
  const isSubmittingRef = useRef(false)
  const textareaRef = useRef(null)

  const dictation = useDictation(setAnswerText)

  // When communication analysis owns the mic, "Start Answer"/"Stop Answer"
  // can't start/stop a SpeechRecognition session (the analyzer's session
  // runs for the whole interview, and starting a second one would conflict
  // with it — see useDictation.js). Instead these buttons gate whether the
  // analyzer's already-running live transcript is mirrored into the answer
  // box, giving the same click-driven start/stop UX without ever creating a
  // second recognition instance.
  const [sharedCapturing, setSharedCapturing] = useState(false)
  const canCaptureShared = !useOwnDictationMic && speech.status === 'active'
  const isListening = dictation.isListening || (canCaptureShared && sharedCapturing)

  // BUG FIX (submit-button stuck disabled after stopping shared-mic
  // capture): the browser finalizes the last spoken phrase *after*
  // recognition already looks stopped — its final `onresult` can land after
  // the user clicks "Stop Answer". The old effect only mirrored
  // speech.liveTranscript into answerText while `sharedCapturing` was true,
  // so that trailing final result (sometimes the *only* result, for a very
  // short answer stopped right after speaking) never reached answerText —
  // the state Submit Answer's disabled check actually reads — and the
  // button stayed disabled even though a transcript existed.
  //
  // tailArmedRef stays "armed" for exactly one more real transcript change
  // after capturing turns off, so that trailing async result is still
  // committed; it's disarmed once consumed so unrelated mic audio picked up
  // later (the analyzer's recognition keeps running all interview) doesn't
  // keep overwriting manual edits to the answer box.
  const tailArmedRef = useRef(false)
  const lastMirroredTranscriptRef = useRef('')

  useEffect(() => {
    tailArmedRef.current = false
    lastMirroredTranscriptRef.current = ''
  }, [currentQuestion?.id])

  useEffect(() => {
    const decision = computeSharedMicMirror({
      canCaptureShared,
      sharedCapturing,
      tailArmed: tailArmedRef.current,
      liveTranscript: speech.liveTranscript,
      lastMirrored: lastMirroredTranscriptRef.current,
    })
    tailArmedRef.current = decision.tailArmed
    if (decision.commit) {
      lastMirroredTranscriptRef.current = decision.text
      setAnswerText(decision.text)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [canCaptureShared, sharedCapturing, speech.liveTranscript])

  // Temporary diagnostic — logs the exact value driving Submit Answer's
  // disabled state on every change, so a "text is visible but button won't
  // enable" report can be confirmed or ruled out from the console alone.
  useEffect(() => {
    console.debug(
      '[submit-eligibility] answerText:', JSON.stringify(answerText),
      '| trimmed empty:', !answerText.trim(),
      '| isSubmitting:', isSubmitting,
      '| disabled:', isSubmitting || !answerText.trim(),
    )
  }, [answerText, isSubmitting])

  // Auto-grows with content (up to a cap, then scrolls) so a long answer
  // never feels boxed into a cramped, fixed-height field.
  useEffect(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${el.scrollHeight}px`
  }, [answerText])

  useEffect(() => {
    getInterview(interviewId)
      .then((data) => {
        setInterview(data)
        setQuestionCount(data.question_count)
        setCurrentDifficulty(data.current_difficulty)
        if (data.status === 'completed') {
          navigate(`/results/${interviewId}`, { replace: true })
          return
        }
        const unanswered = data.questions.find((q) => !q.answer)
        if (unanswered) {
          setCurrentQuestion(unanswered)
          setQuestionsAsked(unanswered.order_index)
        } else {
          // Every generated question already has an answer but the
          // interview was never marked complete — e.g. the page was
          // refreshed right after the final answer, before /complete ran.
          setIsFinishing(true)
        }
      })
      .catch((err) => setError(err.message))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [interviewId])

  const finishInterview = useCallback(async () => {
    setError(null)
    try {
      const cameraMetrics = camera.snapshot()
      await completeInterview(interviewId, cameraMetrics)
      navigate(`/results/${interviewId}`)
    } catch (err) {
      setError(err.message)
      setIsFinishing(false)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [interviewId, navigate])

  useEffect(() => {
    if (isFinishing) finishInterview()
  }, [isFinishing, finishInterview])

  // Recovers from a 409 (question already answered / interview already
  // completed) by re-fetching the interview and resuming from whatever the
  // server actually has — the user is never just stuck on a dead question.
  async function recoverFromStateMismatch() {
    try {
      const data = await getInterview(interviewId)
      setInterview(data)
      setCurrentDifficulty(data.current_difficulty)
      if (data.status === 'completed') {
        navigate(`/results/${interviewId}`, { replace: true })
        return
      }
      const unanswered = data.questions.find((q) => !q.answer)
      if (unanswered) {
        setCurrentQuestion(unanswered)
        setQuestionsAsked(unanswered.order_index)
        setAnswerText('')
        setSharedCapturing(false)
        dictation.release()
        setNotice('Your progress was already saved — continuing from your current question.')
      } else {
        setIsFinishing(true)
      }
    } catch (err) {
      setError(err.message)
    }
  }

  async function handleSubmit() {
    console.debug('[submit-eligibility] handleSubmit() called with answerText:', JSON.stringify(answerText))
    if (!answerText.trim() || isSubmittingRef.current) return
    isSubmittingRef.current = true
    dictation.release()
    setSharedCapturing(false)
    setIsSubmitting(true)
    setError(null)
    setNotice(null)
    setDifficultyNotice(null)
    try {
      const speechMetrics = speech.snapshot()
      const result = await respondToQuestion(
        interviewId,
        currentQuestion.id,
        answerText.trim(),
        speechMetrics,
      )
      setCurrentDifficulty(result.current_difficulty)
      if (result.difficulty_changed) {
        setDifficultyNotice(
          `Difficulty ${result.difficulty_changed} to ${capitalize(result.current_difficulty)} based on your recent answers.`,
        )
      }
      if (result.is_complete) {
        setIsFinishing(true)
      } else {
        speech.resetForQuestion()
        setCurrentQuestion(result.next_question)
        setQuestionsAsked(result.questions_asked)
        setQuestionCount(result.question_count)
        setAnswerText('')
        setSharedCapturing(false)
      }
    } catch (err) {
      if (err.status === 409) {
        await recoverFromStateMismatch()
      } else {
        setError(err.message)
      }
    } finally {
      setIsSubmitting(false)
      isSubmittingRef.current = false
    }
  }

  function handleTextareaKeyDown(event) {
    if ((event.metaKey || event.ctrlKey) && event.key === 'Enter') {
      event.preventDefault()
      handleSubmit()
    }
  }

  if (error && !interview) {
    return <ErrorState message={error} />
  }

  if (!interview || isFinishing) {
    return (
      <div className="mx-auto flex max-w-2xl flex-col items-center gap-3 py-16 text-center">
        <span className="flex gap-1.5" aria-hidden="true">
          <span className="h-2 w-2 animate-bounce rounded-full bg-accent [animation-delay:-0.3s]" />
          <span className="h-2 w-2 animate-bounce rounded-full bg-accent [animation-delay:-0.15s]" />
          <span className="h-2 w-2 animate-bounce rounded-full bg-accent" />
        </span>
        <p className="text-ink-muted">
          {isFinishing ? 'Finishing up your interview...' : 'Loading interview...'}
        </p>
      </div>
    )
  }

  const progressPercent = questionCount
    ? ((questionsAsked + 1) / questionCount) * 100
    : 0

  return (
    <div className="mx-auto max-w-2xl">
      <h1 className="mb-1 text-2xl font-semibold text-ink">AI Interviewer</h1>
      <p className="mb-1 text-ink-muted">
        {interview.role} &middot; started at {capitalize(interview.difficulty)} difficulty
      </p>
      <p className="mb-4 text-xs font-medium text-accent">
        {interview.focus_categories?.length > 0 &&
          `Focused practice: ${interview.focus_categories.map(categoryLabel).join(', ')}`}
      </p>

      <div className="mb-6">
        <div className="mb-1.5 flex flex-wrap items-center justify-between gap-2">
          <span className="text-sm font-medium text-ink-muted">
            Question {questionsAsked + 1} of {questionCount ?? '—'}
          </span>
          <span className="flex items-center gap-1.5">
            {currentDifficulty && (
              <span
                title="Difficulty adapts to your recent answers"
                className="rounded-full bg-surface-2 px-2 py-0.5 text-[11px] font-medium uppercase tracking-wide text-ink-muted"
              >
                {capitalize(currentDifficulty)}
              </span>
            )}
            {currentQuestion?.is_followup && (
              <span className="rounded-full bg-accent-soft px-2 py-0.5 text-[11px] font-medium uppercase tracking-wide text-accent">
                Follow-up
              </span>
            )}
          </span>
        </div>
        <div className="h-2 w-full overflow-hidden rounded-full bg-surface-2">
          <div
            className="h-full rounded-full bg-accent transition-all duration-500 ease-out"
            style={{ width: `${progressPercent}%` }}
          />
        </div>
        {difficultyNotice && (
          <p className="mt-1.5 text-xs text-ink-faint">{difficultyNotice}</p>
        )}
      </div>

      <CommunicationPanel
        speechEnabled={speechEnabled}
        speechStatus={speech.status}
        cameraEnabled={cameraEnabled}
        cameraStatus={camera.status}
      />

      {import.meta.env.DEV && (
        <MicDiagnosticsPanel
          speech={speech}
          dictation={dictation}
          useOwnDictationMic={useOwnDictationMic}
          canCaptureShared={canCaptureShared}
          sharedCapturing={sharedCapturing}
          answerText={answerText}
          isSubmitting={isSubmitting}
        />
      )}

      <div key={currentQuestion?.id} className="surface-card animate-question-fade-in p-4">
        {currentQuestion?.source === 'resume' && (
          <span className="mb-2 inline-block rounded-full bg-accent-soft px-2 py-0.5 text-[11px] font-medium uppercase tracking-wide text-accent">
            From your resume
            {currentQuestion.resume_topic ? ` · ${currentQuestion.resume_topic}` : ''}
          </span>
        )}
        <p className="mb-3 text-lg font-medium leading-snug text-ink">
          {currentQuestion?.text}
        </p>

        {useOwnDictationMic && dictation.supported && (
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={dictation.isListening ? dictation.stop : dictation.start}
              disabled={isSubmitting}
              className={`rounded-lg border px-3 py-1.5 text-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${
                dictation.isListening
                  ? 'border-danger/30 bg-danger-soft text-danger hover:bg-danger-soft/70'
                  : 'border-border text-ink-muted hover:bg-surface-2'
              }`}
            >
              {dictation.isListening ? '⏹ Stop Answer' : '🎙 Start Answer'}
            </button>
            {dictation.status === 'requesting-mic' && (
              <StatusPill>Requesting microphone access&hellip;</StatusPill>
            )}
            {(dictation.status === 'listening' || dictation.status === 'speech-detected') && (
              <StatusPill tone="emerald" pulsing>
                {dictation.status === 'speech-detected' ? 'Speech detected' : 'Listening'}
              </StatusPill>
            )}
            {dictation.status === 'no-speech' && (
              <StatusPill tone="amber">
                Didn&apos;t catch that — try speaking again, closer to the mic
              </StatusPill>
            )}
            {dictation.errorMessage && (
              <span className="text-xs text-warning">{dictation.errorMessage}</span>
            )}
          </div>
        )}
        {canCaptureShared && (
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={() => setSharedCapturing((current) => !current)}
              disabled={isSubmitting}
              className={`rounded-lg border px-3 py-1.5 text-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${
                sharedCapturing
                  ? 'border-danger/30 bg-danger-soft text-danger hover:bg-danger-soft/70'
                  : 'border-border text-ink-muted hover:bg-surface-2'
              }`}
            >
              {sharedCapturing ? '⏹ Stop Answer' : '🎙 Start Answer'}
            </button>
            <StatusPill tone="emerald" pulsing={sharedCapturing}>
              {sharedCapturing
                ? 'Capturing your answer'
                : 'Mic live — click Start Answer to capture'}
            </StatusPill>
          </div>
        )}
        {!dictation.supported && useOwnDictationMic && (
          <p className="mb-2 text-xs text-ink-faint">
            Voice input isn&apos;t supported in this browser — type your answer below.
          </p>
        )}

        <textarea
          ref={textareaRef}
          rows={6}
          value={answerText}
          onChange={(event) => {
            // A manual edit after the mic was stopped should stick — don't
            // let an armed tail-commit (shared-mic effect above, or the
            // standalone dictation hook's own tail-arm) clobber it if a
            // stray transcript update arrives shortly after.
            tailArmedRef.current = false
            dictation.clearTail()
            setAnswerText(event.target.value)
          }}
          onKeyDown={handleTextareaKeyDown}
          placeholder={
            useOwnDictationMic
              ? 'Type your answer, or use Start Answer to speak it...'
              : 'Type your answer, or click Start Answer to capture your speech-analysis mic here...'
          }
          disabled={isSubmitting}
          className="input-field resize-none overflow-y-auto"
          style={{ maxHeight: MAX_TEXTAREA_HEIGHT }}
        />
        <div className="mt-1.5 flex items-center justify-between text-xs text-ink-faint">
          <span className="flex items-center gap-1.5">
            {isListening && (
              <>
                <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-danger" />
                Recording
              </>
            )}
          </span>
          <span>{wordCount(answerText)} word{wordCount(answerText) === 1 ? '' : 's'}</span>
        </div>
      </div>

      {notice && (
        <p className="mt-3 rounded-lg border border-accent-border bg-accent-soft px-3 py-2 text-sm text-accent">
          {notice}
        </p>
      )}
      {error && (
        <p className="mt-3 rounded-lg border border-danger/30 bg-danger-soft px-3 py-2 text-sm text-danger">
          {error}
        </p>
      )}

      <div className="mt-6 flex flex-col-reverse gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-h-[1.5rem]">{isSubmitting && <ThinkingIndicator />}</div>
        <button
          onClick={handleSubmit}
          disabled={isSubmitting || !answerText.trim()}
          className="btn btn-primary w-full shrink-0 sm:w-auto"
        >
          {isSubmitting ? 'Submitting...' : 'Submit Answer'}
        </button>
      </div>
      <p className="mt-2 hidden text-right text-xs text-ink-faint sm:block">
        Tip: Ctrl+Enter (Cmd+Enter on Mac) submits your answer.
      </p>
    </div>
  )
}

export default InterviewPage
