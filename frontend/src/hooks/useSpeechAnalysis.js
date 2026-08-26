import { useEffect, useRef, useState } from 'react'
import { SpeechAnalyzer, isSpeechAnalysisSupported } from '../services/speechAnalysis'

// TEMPORARY MIC DIAGNOSTICS (2026-08-26, round 2 — Opera GX repro) —
// mirrors analyzer.onDiagnostic() events into state so InterviewPage can
// render the exact chronological event sequence and every error the native
// SpeechRecognition object produces for the shared (communication-analysis)
// mic path. Purely observational — never changes control flow. Do NOT
// remove until the real-browser root cause is confirmed and fixed.
const DIAG_DEFAULT = {
  log: [],
  ctorInfo: null,
  recognitionConfig: null,
  micTrack: null,
  lastError: null,
}
const DIAG_LOG_LIMIT = 100

// Answer-level speech metrics for the current interview. Starts the mic
// once (if enabled) and stays running for the whole interview so the user
// is only ever prompted for permission once; resetForQuestion() zeroes the
// per-answer counters at the start of each question and snapshot() reads
// them right before that answer is submitted.
export function useSpeechAnalysis(enabled) {
  const analyzerRef = useRef(null)
  const [status, setStatus] = useState('idle') // idle | active | unsupported | denied | error
  // Running transcript from this analyzer's own recognition session, live —
  // lets an answer-dictation UI reuse this mic instead of starting a second
  // SpeechRecognition instance (see hooks/useDictation.js).
  const [liveTranscript, setLiveTranscript] = useState('')
  const [diag, setDiag] = useState(DIAG_DEFAULT)

  useEffect(() => {
    if (!enabled) {
      setStatus('idle')
      setLiveTranscript('')
      return undefined
    }

    if (!isSpeechAnalysisSupported()) {
      setStatus('unsupported')
      return undefined
    }

    const analyzer = new SpeechAnalyzer()
    analyzer.onTranscriptChange(setLiveTranscript)
    setDiag(DIAG_DEFAULT)
    analyzer.onDiagnostic((event) => {
      setDiag((prev) => {
        const log = [...prev.log, { ...event, t: Date.now() }].slice(-DIAG_LOG_LIMIT)
        switch (event.type) {
          case 'recognition:constructor':
            return { ...prev, log, ctorInfo: event }
          case 'recognition:created':
            return { ...prev, log, recognitionConfig: event }
          case 'getUserMedia:success':
            return { ...prev, log, micTrack: event }
          case 'onerror':
            return { ...prev, log, lastError: { error: event.error, message: event.message } }
          default:
            return { ...prev, log }
        }
      })
    })
    // ROOT-CAUSE FIX (Submit Answer never enables when communication
    // analysis is on): this analyzer's recognition.onerror used to swallow
    // every error silently — including not-allowed/service-not-allowed/
    // audio-capture, which mean the recognition session is permanently
    // broken (e.g. permission revoked mid-interview, mic disconnected).
    // status stayed 'active' forever (it's only set once, after start()
    // resolves), so InterviewPage's fallback logic — which switches to the
    // standalone dictation mic whenever speech.status is
    // unsupported/denied/error — never triggered. The user saw a
    // permanently green "mic live" indicator with a transcript that could
    // never update, and Submit stayed disabled with no explanation.
    //
    // Fix: surface fatal errors as a real status transition, and stop this
    // analyzer's own (now-broken) recognition/mic session so it can't keep
    // occupying Chromium's single global SpeechRecognition slot — the
    // standalone dictation hook needs that slot free to take over. Don't
    // clear liveTranscript here: whatever was already transcribed before
    // the failure must remain visible/committed.
    analyzer.onFatalError((code) => {
      analyzer.stop()
      setStatus(code === 'not-allowed' || code === 'service-not-allowed' ? 'denied' : 'error')
    })
    analyzerRef.current = analyzer
    let cancelled = false

    analyzer
      .start()
      .then(() => {
        // ROOT-CAUSE FIX (transcript captured but Submit Answer never
        // enables): in dev, StrictMode mounts this effect, cleans it up,
        // then mounts it again — all synchronously. analyzer.start() only
        // creates the recognition session and marks itself active *after*
        // the awaited getUserMedia() call resolves, so the first mount's
        // cleanup (below) runs while that promise is still pending and its
        // analyzer.stop() has nothing to tear down yet (every field it
        // checks is still null). The first analyzer's mic/recognition
        // session then starts for real once getUserMedia resolves, orphaned
        // but still running — alongside the second (real) analyzer, both
        // wired to the same setLiveTranscript. Chromium allows only one
        // active SpeechRecognition session at a time (see
        // hooks/useDictation.js), so the two sessions continuously abort
        // and restart each other, feeding garbled/incomplete text into
        // liveTranscript — which is exactly why the transcript "appears/
        // partially appears" but never settles into the stable final value
        // InterviewPage's submit-eligibility logic is waiting to commit.
        //
        // Fix: if cleanup already fired (cancelled) by the time start()
        // resolves, immediately stop *this* analyzer instead of leaving it
        // running — same as the synchronous case, just deferred until
        // there's actually something to stop.
        if (cancelled) {
          analyzer.stop()
          return
        }
        setStatus('active')
      })
      .catch((err) => {
        if (cancelled) return
        setStatus(err?.name === 'NotAllowedError' ? 'denied' : 'error')
      })

    return () => {
      cancelled = true
      analyzer.stop()
      if (analyzerRef.current === analyzer) analyzerRef.current = null
      setLiveTranscript('')
    }
  }, [enabled])

  function resetForQuestion() {
    analyzerRef.current?.reset()
  }

  function snapshot() {
    return analyzerRef.current?.getMetrics() ?? null
  }

  return { status, liveTranscript, diag, resetForQuestion, snapshot }
}
