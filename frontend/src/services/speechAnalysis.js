// Local, browser-only speech analysis. Raw audio is never recorded,
// buffered, or uploaded — this reads live amplitude levels and (if the
// browser supports it) live transcript text, discarding each sample as
// soon as it's processed. Only the aggregate counts/durations returned by
// getMetrics() ever leave this module.
//
// Metrics describe observable speech patterns only. They are never used to
// infer emotion, confidence, honesty, or personality, and repeated words /
// pauses are never labeled as a medical condition (e.g. stuttering).
//
// Framework-agnostic on purpose — swap the internals later without
// touching the React hook that wraps it.

const FILLER_WORDS = ['um', 'uh', 'like', 'you know', 'basically']
const SILENCE_RMS_THRESHOLD = 0.02
const PAUSE_MIN_SECONDS = 1.5
const LONG_PAUSE_MIN_SECONDS = 4
const AMPLITUDE_POLL_MS = 100

function getSpeechRecognitionCtor() {
  return window.SpeechRecognition || window.webkitSpeechRecognition || null
}

export function isSpeechAnalysisSupported() {
  return Boolean(navigator.mediaDevices?.getUserMedia)
}

export function isTranscriptionSupported() {
  return Boolean(getSpeechRecognitionCtor())
}

function countFillerWords(text) {
  const counts = {}
  let total = 0
  const lower = text.toLowerCase()
  for (const phrase of FILLER_WORDS) {
    const escaped = phrase.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
    const matches = lower.match(new RegExp(`\\b${escaped}\\b`, 'g'))
    if (matches?.length) {
      counts[phrase] = matches.length
      total += matches.length
    }
  }
  return { counts, total }
}

function countRepeatedWords(text) {
  const tokens = text
    .toLowerCase()
    .replace(/[^a-z0-9'\s]/g, '')
    .split(/\s+/)
    .filter(Boolean)
  let repeats = 0
  for (let i = 1; i < tokens.length; i++) {
    if (tokens[i] === tokens[i - 1]) repeats += 1
  }
  return repeats
}

export class SpeechAnalyzer {
  constructor() {
    this._stream = null
    this._audioContext = null
    this._analyser = null
    this._pollTimer = null
    this._recognition = null
    this._transcriptAvailable = false
    this._transcript = ''
    this._startedAt = null
    this._speechStartedAt = null
    this._silenceStartedAt = null
    this._pauseCount = 0
    this._longPauseCount = 0
    this._active = false
    // SpeechRecognitionAlternative.confidence on each final result, when
    // the engine actually reports one — many engines report 0/omit it, so
    // those are excluded rather than dragging the average down with a
    // value that was never really measured.
    this._confidenceSum = 0
    this._confidenceSamples = 0
    // Optional subscriber for the running transcript, set via
    // onTranscriptChange(). Lets a dictation UI reuse this analyzer's
    // already-running recognition session instead of starting a second,
    // conflicting SpeechRecognition instance (only one can be active at a
    // time in Chromium browsers).
    this._onTranscriptChange = null
  }

  // Registers (or clears, with null) a callback invoked with the running
  // transcript string every time it changes. Purely additive — existing
  // consumers that never call this are unaffected.
  onTranscriptChange(callback) {
    this._onTranscriptChange = callback
  }

  static isSupported() {
    return isSpeechAnalysisSupported()
  }

  async start() {
    if (this._active) return
    this._stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    this._startedAt = Date.now()
    this._active = true

    this._audioContext = new (window.AudioContext || window.webkitAudioContext)()
    const source = this._audioContext.createMediaStreamSource(this._stream)
    this._analyser = this._audioContext.createAnalyser()
    this._analyser.fftSize = 2048
    source.connect(this._analyser)

    const buffer = new Uint8Array(this._analyser.fftSize)
    this._pollTimer = setInterval(() => {
      this._analyser.getByteTimeDomainData(buffer)
      let sumSquares = 0
      for (let i = 0; i < buffer.length; i++) {
        const normalized = (buffer[i] - 128) / 128
        sumSquares += normalized * normalized
      }
      this._onAmplitudeSample(Math.sqrt(sumSquares / buffer.length))
    }, AMPLITUDE_POLL_MS)

    this._startRecognition()
  }

  _startRecognition() {
    const RecognitionCtor = getSpeechRecognitionCtor()
    if (!RecognitionCtor) return

    try {
      const recognition = new RecognitionCtor()
      recognition.continuous = true
      recognition.interimResults = true
      recognition.lang = 'en-US'
      recognition.onstart = () => {
        this._transcriptAvailable = true
      }
      recognition.onresult = (event) => {
        let finalText = ''
        let interim = ''
        for (let i = event.resultIndex; i < event.results.length; i++) {
          if (event.results[i].isFinal) {
            finalText += event.results[i][0].transcript + ' '
            const confidence = event.results[i][0].confidence
            if (typeof confidence === 'number' && confidence > 0) {
              this._confidenceSum += confidence
              this._confidenceSamples += 1
            }
          } else {
            interim += event.results[i][0].transcript
          }
        }
        if (finalText) this._transcript += finalText
        this._onTranscriptChange?.(`${this._transcript}${interim}`.trim())
      }
      recognition.onend = () => {
        // Some browsers auto-stop recognition after a period of silence;
        // restart while the analyzer is still active so a long answer with
        // pauses doesn't silently lose transcription.
        if (this._active) {
          try {
            recognition.start()
          } catch {
            // Already starting/stopping — ignore, next poll will retry.
          }
        }
      }
      recognition.onerror = () => {
        // Duration/pause metrics keep working independently of transcription.
      }
      recognition.start()
      this._recognition = recognition
    } catch {
      this._recognition = null
    }
  }

  _onAmplitudeSample(rms) {
    const now = Date.now()
    const isSilent = rms < SILENCE_RMS_THRESHOLD

    if (!isSilent) {
      if (this._speechStartedAt === null) this._speechStartedAt = now
      if (this._silenceStartedAt !== null) {
        const silenceSeconds = (now - this._silenceStartedAt) / 1000
        if (silenceSeconds >= PAUSE_MIN_SECONDS) {
          this._pauseCount += 1
          if (silenceSeconds >= LONG_PAUSE_MIN_SECONDS) this._longPauseCount += 1
        }
        this._silenceStartedAt = null
      }
    } else if (this._speechStartedAt !== null && this._silenceStartedAt === null) {
      this._silenceStartedAt = now
    }
  }

  // Zeroes per-answer counters without tearing down the mic stream or
  // restarting recognition, so a single permission grant / stream can be
  // reused across every question in an interview while still producing
  // independent metrics per answer.
  reset() {
    this._transcript = ''
    this._onTranscriptChange?.('')
    this._pauseCount = 0
    this._longPauseCount = 0
    this._speechStartedAt = null
    this._silenceStartedAt = null
    this._startedAt = Date.now()
    this._confidenceSum = 0
    this._confidenceSamples = 0
  }

  stop() {
    if (this._pollTimer) clearInterval(this._pollTimer)
    this._pollTimer = null

    if (this._recognition) {
      const recognition = this._recognition
      this._recognition = null
      recognition.onend = null
      try {
        recognition.stop()
      } catch {
        // Already stopped.
      }
    }

    if (this._audioContext) {
      this._audioContext.close().catch(() => {})
      this._audioContext = null
    }

    if (this._stream) {
      this._stream.getTracks().forEach((track) => track.stop())
      this._stream = null
    }

    this._active = false
  }

  getMetrics() {
    const durationSeconds = this._startedAt ? (Date.now() - this._startedAt) / 1000 : 0
    const transcript = this._transcript.trim()
    const transcriptWordCount = transcript ? transcript.split(/\s+/).filter(Boolean).length : 0
    const { counts: fillerWords, total: fillerWordCount } = this._transcriptAvailable
      ? countFillerWords(transcript)
      : { counts: {}, total: 0 }
    const repeatedWordCount = this._transcriptAvailable ? countRepeatedWords(transcript) : 0
    const wordsPerMinute =
      this._transcriptAvailable && durationSeconds > 0
        ? Math.round((transcriptWordCount / durationSeconds) * 60)
        : null

    return {
      duration_seconds: Number(durationSeconds.toFixed(1)),
      words_per_minute: wordsPerMinute,
      pause_count: this._pauseCount,
      long_pause_count: this._longPauseCount,
      filler_word_count: fillerWordCount,
      filler_words: fillerWords,
      repeated_word_count: repeatedWordCount,
      transcript_word_count: this._transcriptAvailable ? transcriptWordCount : null,
      transcript_available: this._transcriptAvailable,
      transcript_confidence: this._confidenceSamples
        ? Number((this._confidenceSum / this._confidenceSamples).toFixed(2))
        : null,
    }
  }
}
