import { useCallback, useEffect, useRef, useState } from 'react'

// Standalone speech-to-text for dictating an answer. Deliberately separate
// from useSpeechAnalysis/SpeechAnalyzer (the opt-in communication-analysis
// feature) — different responsibility (filling the answer box vs.
// measuring speech patterns like pace/fillers/pauses).
//
// IMPORTANT: Chromium browsers (Chrome, Brave, Edge) only allow ONE active
// SpeechRecognition session at a time. When communication analysis is
// running its own continuous recognition, dictation must reuse its live
// transcript rather than start a second, conflicting recognition instance
// — see InterviewPage.jsx, which only uses this hook when communication
// analysis is not active.
//
// ROOT-CAUSE FIX (Submit Answer staying disabled after Stop Answer):
// Chrome's SpeechRecognition is network-backed. For a short utterance, the
// recognition request can still be in flight (not yet returned from the
// speech service) at the exact moment recognition.stop() is called — and
// Chrome's real-world behavior then is to drop that pending result
// entirely (delivered as onerror('aborted'), never onresult), instead of
// flushing it the way the spec implies. Calling stop() synchronously from
// the "Stop Answer" click therefore raced against — and could silently
// discard — the very transcript the user just spoke, especially for short
// answers stopped right after speaking.
//
// The fix: "Stop Answer" NEVER calls the native stop()/abort() anymore. It
// only pauses whether onresult commits into the answer box (isCapturingRef)
// — the underlying recognition engine keeps running continuously in the
// background for the whole question, exactly like the shared
// communication-analysis mic already does. That removes the race entirely:
// there's no click-triggered native stop() for an in-flight result to lose
// a race against. A tail-arm (tailArmedRef) still commits exactly one more
// result after pausing, for the case where the result for what was just
// said lands a moment after the click. The engine is only well and truly
// torn down via release() — on submit, question change, or unmount — never
// on a plain "Stop Answer" click.

const DEBUG_PREFIX = '[dictation]'

// Error codes that mean retrying won't help — the recognition service will
// keep failing the same way until the user (or their OS) changes something.
const FATAL_ERROR_CODES = new Set(['not-allowed', 'service-not-allowed', 'audio-capture'])

function getSpeechRecognitionCtor() {
  return window.SpeechRecognition || window.webkitSpeechRecognition || null
}

export function isDictationSupported() {
  return Boolean(getSpeechRecognitionCtor())
}

// Human-readable explanations for the standard Web Speech API error codes,
// shown directly in the UI so a user can self-diagnose without devtools.
const ERROR_MESSAGES = {
  'not-allowed': 'Microphone access was denied. Allow microphone access for this site and try again.',
  'service-not-allowed': 'Your browser blocked the speech recognition service (this is common in Brave — try enabling it in brave://settings/, or use Chrome).',
  network: 'No connection to the browser\'s speech recognition service. Check your network and try again.',
  'audio-capture': 'No microphone was found. Check that a microphone is connected and try again.',
  'start-failed': 'Could not start speech recognition in this browser.',
}

function describeError(code) {
  return ERROR_MESSAGES[code] || `Speech recognition error (${code}). You can still type your answer.`
}

// onTranscript(text) is called with the running transcript (final +
// interim) every time a result is actually committed (see isCapturingRef /
// tailArmedRef below).
export function useDictation(onTranscript) {
  const recognitionRef = useRef(null)
  // True for as long as the recognition engine itself should keep running
  // in the background for the current question (spans multiple Start/Stop
  // clicks) — distinguishes "the browser auto-ended the session, restart
  // it transparently" from "we're releasing for real" (submit / question
  // change / unmount), so onend knows whether to restart.
  const shouldEngineRunRef = useRef(false)
  // True only while "Stop Answer" hasn't been clicked (or has just been
  // resumed) — gates whether onresult commits into the answer box. This is
  // a pure in-memory flag, never tied to the native recognition object, so
  // pausing/resuming can never race against — or trigger — a native
  // stop()/start() call.
  const isCapturingRef = useRef(false)
  // Stays armed for exactly one more onresult after pausing, so the result
  // for speech that happened *before* the click (but is delivered slightly
  // after it) still lands in the answer — then disarms, so ambient audio
  // picked up later while paused doesn't keep overwriting the box (e.g.
  // after the user has started manually editing it).
  const tailArmedRef = useRef(false)
  const lastCommittedRef = useRef('')
  // Persists the finalized transcript across the whole question — across
  // pause/resume cycles *and* across the transparent auto-restarts below —
  // only reset by release().
  const finalTextRef = useRef('')

  const [isListening, setIsListening] = useState(false)
  // Temporary diagnostic status, surfaced in the UI: idle | requesting-mic
  // | listening | speech-detected | error
  const [status, setStatus] = useState('idle')
  const [error, setError] = useState(null)
  const supported = isDictationSupported()

  const commit = useCallback(
    (combined) => {
      lastCommittedRef.current = combined
      console.debug(DEBUG_PREFIX, 'commit ->', JSON.stringify(combined))
      onTranscript(combined)
    },
    [onTranscript],
  )

  // "Stop Answer": UI-level pause only. Deliberately does NOT touch the
  // native recognition object — see the module comment for why.
  const pause = useCallback(() => {
    console.debug(DEBUG_PREFIX, 'pause() — stop capturing into the answer box (engine keeps running)')
    isCapturingRef.current = false
    tailArmedRef.current = true
    setIsListening(false)
    setStatus('idle')
  }, [])

  // Full teardown: actually stops the recognition engine and releases the
  // mic. Only called when we're truly done with speech input for this
  // question — submit, question change/recovery, or unmount.
  const release = useCallback(() => {
    console.debug(DEBUG_PREFIX, 'release() — tearing down recognition instance for real')
    shouldEngineRunRef.current = false
    isCapturingRef.current = false
    tailArmedRef.current = false
    finalTextRef.current = ''
    lastCommittedRef.current = ''
    const recognition = recognitionRef.current
    if (recognition) {
      recognition.onend = null
      try {
        recognition.stop()
      } catch (err) {
        console.debug(DEBUG_PREFIX, 'release() stop() threw (already stopped)', err)
      }
      recognitionRef.current = null
    }
    setIsListening(false)
    setStatus('idle')
  }, [])

  // Discards an armed tail without waiting for it to fire — used when the
  // user manually edits the answer box, so a still-in-flight recognition
  // result from just before the edit can't clobber what they just typed.
  const clearTail = useCallback(() => {
    tailArmedRef.current = false
  }, [])

  const start = useCallback(() => {
    if (!supported) {
      console.warn(DEBUG_PREFIX, 'start() called but SpeechRecognition is not supported here')
      return
    }

    setError(null)
    isCapturingRef.current = true
    tailArmedRef.current = false
    setIsListening(true)

    if (recognitionRef.current) {
      // Engine is already running in the background from an earlier
      // Start/Stop cycle this question (see pause()) — resume committing
      // results, no new recognition session or mic-permission prompt
      // needed.
      console.debug(DEBUG_PREFIX, 'start() — engine already warm, resuming capture')
      setStatus('listening')
      return
    }

    console.debug(DEBUG_PREFIX, 'start() — spinning up a fresh recognition engine')
    setStatus('requesting-mic')
    shouldEngineRunRef.current = true

    const createAndStart = () => {
      const RecognitionCtor = getSpeechRecognitionCtor()
      const recognition = new RecognitionCtor()
      recognition.continuous = true
      recognition.interimResults = true
      recognition.lang = 'en-US'

      // Fires once the browser has actually granted mic access and the
      // recognition engine is running — the clearest signal that
      // permission was NOT the problem.
      recognition.onstart = () => {
        console.debug(DEBUG_PREFIX, 'onstart — recognition engine is running, mic access granted')
        if (isCapturingRef.current) setStatus('listening')
      }

      recognition.onaudiostart = () => {
        console.debug(DEBUG_PREFIX, 'onaudiostart — microphone audio capture began')
      }

      recognition.onspeechstart = () => {
        console.debug(DEBUG_PREFIX, 'onspeechstart — speech detected')
        if (isCapturingRef.current) setStatus('speech-detected')
      }

      recognition.onresult = (event) => {
        let interim = ''
        for (let i = event.resultIndex; i < event.results.length; i++) {
          const transcript = event.results[i][0].transcript
          if (event.results[i].isFinal) {
            finalTextRef.current += `${transcript} `
          } else {
            interim += transcript
          }
        }
        const combined = `${finalTextRef.current}${interim}`.trim()
        console.debug(DEBUG_PREFIX, 'onresult (raw):', JSON.stringify(combined), '| capturing:', isCapturingRef.current, '| tailArmed:', tailArmedRef.current)

        if (isCapturingRef.current) {
          commit(combined)
          return
        }
        if (tailArmedRef.current && combined !== lastCommittedRef.current) {
          console.debug(DEBUG_PREFIX, 'onresult — committing armed tail result after pause')
          tailArmedRef.current = false
          commit(combined)
        }
      }

      recognition.onerror = (event) => {
        console.warn(DEBUG_PREFIX, 'onerror:', event.error, event.message || '(no message)')
        // "no-speech"/"aborted" are routine (a brief pause, or a paused
        // engine being torn down) — only surface genuinely unexpected
        // failures.
        if (event.error !== 'no-speech' && event.error !== 'aborted') {
          setError(event.error || 'unknown-error')
          setStatus('error')
        }
        if (FATAL_ERROR_CODES.has(event.error)) {
          // Retrying won't help (e.g. permission denied) — let onend know
          // not to restart.
          shouldEngineRunRef.current = false
        }
      }

      recognition.onend = () => {
        console.debug(DEBUG_PREFIX, 'onend — recognition session ended')
        recognitionRef.current = null
        if (shouldEngineRunRef.current) {
          // The browser silently ends a session after a period of silence
          // even with continuous=true — most commonly while the user is
          // still reading the question before they start answering, or
          // while paused between Start/Stop clicks. Restart transparently
          // so the engine is still warm the next time capturing resumes.
          console.debug(DEBUG_PREFIX, 'engine should keep running — restarting transparently')
          try {
            createAndStart()
            return
          } catch (err) {
            console.warn(DEBUG_PREFIX, 'restart after onend failed:', err)
          }
        }
        setIsListening(false)
        setStatus((current) => (current === 'error' ? current : 'idle'))
      }

      recognition.start()
      recognitionRef.current = recognition
    }

    try {
      createAndStart()
    } catch (err) {
      console.warn(DEBUG_PREFIX, 'recognition.start() threw synchronously:', err)
      setError('start-failed')
      setStatus('error')
      shouldEngineRunRef.current = false
      isCapturingRef.current = false
      setIsListening(false)
    }
  }, [supported, commit])

  // Always release on unmount so a pending recognition session never
  // outlives the component (e.g. navigating away mid-answer).
  useEffect(() => release, [release])

  return {
    supported,
    isListening,
    status,
    error,
    errorMessage: error ? describeError(error) : null,
    start,
    stop: pause,
    release,
    clearTail,
  }
}
