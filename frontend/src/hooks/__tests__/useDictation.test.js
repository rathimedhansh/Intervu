import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useDictation } from '../useDictation'
import {
  FakeSpeechRecognition,
  buildResultEvent,
  installFakeSpeechRecognition,
  latestInstance,
  uninstallFakeSpeechRecognition,
} from './fakeSpeechRecognition'

// These tests drive the ACTUAL useDictation.js hook (not a re-implementation)
// through the exact SpeechRecognition event sequences that are timing-
// dependent in a real browser: a final result delivered after "Stop Answer"
// has already paused capture, the browser auto-ending a session mid-answer,
// and manual edits racing an in-flight result. Real microphone/browser
// verification is still required — see the final report — but this proves
// the state machine itself commits the final transcript into answer state
// (and therefore enables Submit) for every sequence below.

describe('useDictation', () => {
  beforeEach(() => {
    installFakeSpeechRecognition()
  })

  afterEach(() => {
    uninstallFakeSpeechRecognition()
  })

  it('A/C: final result arriving AFTER Stop Answer still reaches answer state', () => {
    const onTranscript = vi.fn()
    const { result } = renderHook(() => useDictation(onTranscript))

    act(() => result.current.start())
    const recognition = latestInstance()

    // User says "yes" and clicks Stop Answer before the network-backed
    // recognizer has delivered ANY result for it yet.
    act(() => result.current.stop())
    expect(result.current.isListening).toBe(false)

    // The final result for "yes" arrives late — this is the exact race the
    // module comment in useDictation.js documents.
    act(() => {
      recognition.onresult(buildResultEvent(0, [{ transcript: 'yes', isFinal: true }]))
    })

    expect(onTranscript).toHaveBeenCalledWith('yes')
  })

  it('B/F: a normal multi-sentence answer preserves the full final transcript', () => {
    const onTranscript = vi.fn()
    const { result } = renderHook(() => useDictation(onTranscript))

    act(() => result.current.start())
    const recognition = latestInstance()

    act(() => {
      recognition.onresult(buildResultEvent(0, [{ transcript: 'this is my answer', isFinal: false }]))
    })
    expect(onTranscript).toHaveBeenLastCalledWith('this is my answer')

    act(() => {
      recognition.onresult(
        buildResultEvent(0, [
          { transcript: 'this is my answer.', isFinal: true },
          { transcript: ' and a second sentence', isFinal: false },
        ]),
      )
    })
    expect(onTranscript).toHaveBeenLastCalledWith('this is my answer.  and a second sentence')

    act(() => result.current.stop())
    act(() => {
      recognition.onresult(
        buildResultEvent(0, [{ transcript: ' and a second sentence.', isFinal: true }]),
      )
    })
    expect(onTranscript).toHaveBeenLastCalledWith('this is my answer.  and a second sentence.')
  })

  it('D: speak, pause (silence), then stop — still commits once stopped', () => {
    const onTranscript = vi.fn()
    const { result } = renderHook(() => useDictation(onTranscript))

    act(() => result.current.start())
    const recognition = latestInstance()

    act(() => {
      recognition.onresult(buildResultEvent(0, [{ transcript: 'well', isFinal: false }]))
    })
    // Simulate a mid-answer pause: no events for a while, nothing to assert.
    act(() => result.current.stop())

    act(() => {
      recognition.onresult(buildResultEvent(0, [{ transcript: 'well, let me think', isFinal: true }]))
    })
    expect(onTranscript).toHaveBeenLastCalledWith('well, let me think')
  })

  it('E: Start -> Stop -> Start again reuses the warm engine and keeps accumulating', () => {
    const onTranscript = vi.fn()
    const { result } = renderHook(() => useDictation(onTranscript))

    act(() => result.current.start())
    const recognition = latestInstance()
    act(() => {
      recognition.onresult(buildResultEvent(0, [{ transcript: 'yes', isFinal: true }]))
    })
    act(() => result.current.stop())

    act(() => result.current.start())
    // No new SpeechRecognition instance should have been created — same
    // engine keeps running across a Start/Stop/Start cycle.
    expect(latestInstance()).toBe(recognition)

    act(() => {
      recognition.onresult(buildResultEvent(0, [{ transcript: ' and also no', isFinal: true }]))
    })
    expect(onTranscript).toHaveBeenLastCalledWith('yes  and also no')
  })

  it('G: manually editing the box after Stop discards a still-in-flight tail result', () => {
    const onTranscript = vi.fn()
    const { result } = renderHook(() => useDictation(onTranscript))

    act(() => result.current.start())
    const recognition = latestInstance()
    act(() => result.current.stop())

    // User types over the box before the late result arrives.
    act(() => result.current.clearTail())

    act(() => {
      recognition.onresult(buildResultEvent(0, [{ transcript: 'yes', isFinal: true }]))
    })
    expect(onTranscript).not.toHaveBeenCalled()
  })

  it('H: the browser ending the session naturally mid-answer still restarts and keeps capturing', () => {
    const onTranscript = vi.fn()
    const { result } = renderHook(() => useDictation(onTranscript))

    act(() => result.current.start())
    const first = latestInstance()

    // Browser silently ends the session (e.g. brief silence) while still
    // capturing — shouldEngineRunRef is true, so it must restart itself.
    act(() => {
      first.onend()
    })
    const second = latestInstance()
    expect(second).not.toBe(first)
    expect(result.current.isListening).toBe(true)

    act(() => {
      second.onresult(buildResultEvent(0, [{ transcript: 'restarted answer', isFinal: true }]))
    })
    expect(onTranscript).toHaveBeenLastCalledWith('restarted answer')
  })

  it('"no-speech" while capturing surfaces an actionable hint instead of silently doing nothing', () => {
    const onTranscript = vi.fn()
    const { result } = renderHook(() => useDictation(onTranscript))

    act(() => result.current.start())
    const recognition = latestInstance()

    // A short/quiet utterance (e.g. "yes") can make Chrome's recognizer
    // fire "no-speech" without ever emitting a result at all.
    act(() => {
      recognition.onerror({ error: 'no-speech' })
    })
    expect(result.current.status).toBe('no-speech')
    // Must not be treated as a hard error — capturing keeps running and
    // nothing is force-enabled or faked.
    expect(result.current.error).toBe(null)
    expect(result.current.isListening).toBe(true)

    // Once real speech is detected, the hint clears.
    act(() => {
      recognition.onspeechstart()
    })
    expect(result.current.status).toBe('speech-detected')
  })

  it('I: a non-fatal recognition error does not brick the answer/submit state', () => {
    const onTranscript = vi.fn()
    const { result } = renderHook(() => useDictation(onTranscript))

    act(() => result.current.start())
    const recognition = latestInstance()

    act(() => {
      recognition.onerror({ error: 'network' })
    })
    expect(result.current.error).toBe('network')
    expect(result.current.errorMessage).toMatch(/network/i)

    // Still able to receive and commit a transcript afterwards.
    act(() => {
      recognition.onresult(buildResultEvent(0, [{ transcript: 'still works', isFinal: true }]))
    })
    expect(onTranscript).toHaveBeenCalledWith('still works')
  })

  it('J: permission denied surfaces a clear, non-retrying error state', () => {
    const onTranscript = vi.fn()
    const { result } = renderHook(() => useDictation(onTranscript))

    act(() => result.current.start())
    const recognition = latestInstance()

    act(() => {
      recognition.onerror({ error: 'not-allowed' })
    })
    expect(result.current.error).toBe('not-allowed')
    expect(result.current.errorMessage).toMatch(/microphone access was denied/i)

    // Fatal error: onend must NOT transparently restart the engine.
    const countBefore = FakeSpeechRecognition.instances.length
    act(() => {
      recognition.onend()
    })
    expect(FakeSpeechRecognition.instances.length).toBe(countBefore)
    expect(result.current.isListening).toBe(false)
  })
})
