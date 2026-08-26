import { act, renderHook, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useSpeechAnalysis } from '../useSpeechAnalysis'
import {
  installFakeSpeechRecognition,
  latestInstance,
  uninstallFakeSpeechRecognition,
} from './fakeSpeechRecognition'

// Drives the ACTUAL useSpeechAnalysis.js hook (the "communication analysis"
// mic InterviewPage falls back away from via
// `speechAnalysisFailed = ['unsupported', 'denied', 'error'].includes(speech.status)`
// whenever it's broken). Before the fix, a fatal SpeechRecognition error
// after start() had already resolved left `status` stuck at 'active'
// forever — InterviewPage never knew to switch to the standalone dictation
// mic, so the mic looked "live" while silently producing nothing.

class FakeMediaStream {
  getTracks() {
    return []
  }
  getAudioTracks() {
    return [{ label: 'fake mic', readyState: 'live', enabled: true, muted: false }]
  }
}

class FakeAudioContext {
  createMediaStreamSource() {
    return { connect() {} }
  }
  createAnalyser() {
    return { fftSize: 2048, getByteTimeDomainData: (buffer) => buffer.fill(128) }
  }
  close() {
    return Promise.resolve()
  }
}

describe('useSpeechAnalysis', () => {
  beforeEach(() => {
    installFakeSpeechRecognition()
    vi.stubGlobal('navigator', {
      ...globalThis.navigator,
      mediaDevices: { getUserMedia: vi.fn().mockResolvedValue(new FakeMediaStream()) },
    })
    window.AudioContext = FakeAudioContext
  })

  afterEach(() => {
    uninstallFakeSpeechRecognition()
    vi.unstubAllGlobals()
    delete window.AudioContext
  })

  it('a fatal recognition error flips status away from "active" so InterviewPage falls back to dictation', async () => {
    const { result } = renderHook(() => useSpeechAnalysis(true))

    await waitFor(() => expect(result.current.status).toBe('active'))

    const recognition = latestInstance()
    act(() => {
      recognition.onerror({ error: 'not-allowed' })
    })

    expect(result.current.status).toBe('denied')
  })

  it('audio-capture is also treated as fatal and reported as "error"', async () => {
    const { result } = renderHook(() => useSpeechAnalysis(true))

    await waitFor(() => expect(result.current.status).toBe('active'))

    const recognition = latestInstance()
    act(() => {
      recognition.onerror({ error: 'audio-capture' })
    })

    expect(result.current.status).toBe('error')
  })

  it('a recoverable error (no-speech) leaves status as "active" — no fallback triggered', async () => {
    const { result } = renderHook(() => useSpeechAnalysis(true))

    await waitFor(() => expect(result.current.status).toBe('active'))

    const recognition = latestInstance()
    act(() => {
      recognition.onerror({ error: 'no-speech' })
    })

    expect(result.current.status).toBe('active')
  })

  it('liveTranscript already captured survives a fatal error (not wiped)', async () => {
    const { result } = renderHook(() => useSpeechAnalysis(true))

    await waitFor(() => expect(result.current.status).toBe('active'))

    const recognition = latestInstance()
    act(() => {
      recognition.onresult({
        resultIndex: 0,
        results: Object.assign(
          [Object.assign([{ transcript: 'partial answer', confidence: 0.9 }], { isFinal: true })],
          { length: 1 },
        ),
      })
    })
    expect(result.current.liveTranscript).toBe('partial answer')

    act(() => {
      recognition.onerror({ error: 'service-not-allowed' })
    })

    expect(result.current.status).toBe('denied')
    expect(result.current.liveTranscript).toBe('partial answer')
  })
})
