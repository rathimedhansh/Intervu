import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { SpeechAnalyzer } from '../speechAnalysis'
import {
  FakeSpeechRecognition,
  buildResultEvent,
  installFakeSpeechRecognition,
  latestInstance,
  uninstallFakeSpeechRecognition,
} from '../../hooks/__tests__/fakeSpeechRecognition'

// Exercises the SpeechAnalyzer's recognition.onerror/onend handling — the
// shared (communication-analysis) mic path used whenever "communication
// analysis" is enabled in interview setup. This class's onerror used to be
// a complete no-op, so a fatally broken recognition session (permission
// revoked, mic lost, speech service blocked) left `status` stuck at
// 'active' forever with no way for InterviewPage to fall back to the
// standalone dictation mic — the transcript would just never update again,
// and Submit Answer stayed disabled with zero explanation.

class FakeMediaStream {
  getTracks() {
    return []
  }
  getAudioTracks() {
    return [{ label: 'fake mic', readyState: 'live', enabled: true, muted: false }]
  }
}

class FakeAnalyserNode {
  constructor() {
    this.fftSize = 2048
  }
  getByteTimeDomainData(buffer) {
    buffer.fill(128) // silence
  }
}

class FakeAudioContext {
  createMediaStreamSource() {
    return { connect() {} }
  }
  createAnalyser() {
    return new FakeAnalyserNode()
  }
  close() {
    return Promise.resolve()
  }
}

function installFakeAudioPipeline() {
  vi.stubGlobal('navigator', {
    ...globalThis.navigator,
    mediaDevices: { getUserMedia: vi.fn().mockResolvedValue(new FakeMediaStream()) },
  })
  window.AudioContext = FakeAudioContext
}

function uninstallFakeAudioPipeline() {
  vi.unstubAllGlobals()
  delete window.AudioContext
}

describe('SpeechAnalyzer', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    installFakeSpeechRecognition()
    installFakeAudioPipeline()
  })

  afterEach(() => {
    vi.useRealTimers()
    uninstallFakeSpeechRecognition()
    uninstallFakeAudioPipeline()
  })

  it('a fatal error (not-allowed) is reported and stops the engine from restarting', async () => {
    const analyzer = new SpeechAnalyzer()
    const onFatalError = vi.fn()
    analyzer.onFatalError(onFatalError)
    await analyzer.start()

    const recognition = latestInstance()
    recognition.onerror({ error: 'not-allowed' })
    expect(onFatalError).toHaveBeenCalledWith('not-allowed')

    // The browser also fires onend right after onerror — must NOT restart.
    const countBefore = FakeSpeechRecognition.instances.length
    recognition.onend()
    expect(FakeSpeechRecognition.instances.length).toBe(countBefore)

    analyzer.stop()
  })

  it.each(['service-not-allowed', 'audio-capture'])(
    'treats %s as fatal too',
    async (code) => {
      const analyzer = new SpeechAnalyzer()
      const onFatalError = vi.fn()
      analyzer.onFatalError(onFatalError)
      await analyzer.start()

      const recognition = latestInstance()
      recognition.onerror({ error: code })
      expect(onFatalError).toHaveBeenCalledWith(code)

      analyzer.stop()
    },
  )

  it.each(['no-speech', 'aborted', 'network'])(
    '%s is recoverable — no fatal callback, and onend still restarts the engine',
    async (code) => {
      const analyzer = new SpeechAnalyzer()
      const onFatalError = vi.fn()
      analyzer.onFatalError(onFatalError)
      await analyzer.start()

      const recognition = latestInstance()
      recognition.onerror({ error: code })
      expect(onFatalError).not.toHaveBeenCalled()

      const countBefore = FakeSpeechRecognition.instances.length
      recognition.onend()
      expect(recognition.startCount).toBeGreaterThanOrEqual(2)
      expect(FakeSpeechRecognition.instances.length).toBe(countBefore) // same instance reused

      analyzer.stop()
    },
  )

  it('the final transcript is never cleared by onend restarting the engine', async () => {
    const analyzer = new SpeechAnalyzer()
    const onTranscriptChange = vi.fn()
    analyzer.onTranscriptChange(onTranscriptChange)
    await analyzer.start()

    const recognition = latestInstance()
    recognition.onresult(buildResultEvent(0, [{ transcript: 'hello world', isFinal: true }]))
    expect(onTranscriptChange).toHaveBeenLastCalledWith('hello world')

    // Browser silently ends the session mid-answer (common after a pause).
    recognition.onend()
    expect(onTranscriptChange).toHaveBeenLastCalledWith('hello world')

    // More speech after the transparent restart appends, doesn't replace.
    recognition.onresult(buildResultEvent(0, [{ transcript: ' second sentence', isFinal: true }]))
    expect(onTranscriptChange).toHaveBeenLastCalledWith('hello world  second sentence')

    analyzer.stop()
  })

  it('a fatal error does not discard the transcript already captured', async () => {
    const analyzer = new SpeechAnalyzer()
    analyzer.onFatalError(() => {})
    await analyzer.start()

    const recognition = latestInstance()
    recognition.onstart()
    recognition.onresult(buildResultEvent(0, [{ transcript: 'partial answer', isFinal: true }]))
    recognition.onerror({ error: 'audio-capture' })

    // getMetrics() reads from the same internal _transcript the recognition
    // handlers write to above — this proves it survived the fatal error.
    expect(analyzer.getMetrics().transcript_word_count).toBe(2)

    analyzer.stop()
  })
})
