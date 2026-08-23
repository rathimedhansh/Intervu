// Deterministic stand-in for the browser's SpeechRecognition, driven
// manually from tests so we can reproduce exact event orderings (e.g. a
// final result arriving after the app has already "stopped" listening)
// that are otherwise timing-dependent and flaky in a real browser.

export function buildResultEvent(resultIndex, entries) {
  const results = entries.map(({ transcript, isFinal, confidence }) => {
    const alt = { transcript, confidence: confidence ?? 0.9 }
    const result = [alt]
    result.isFinal = isFinal
    return result
  })
  results.length = entries.length
  return { resultIndex, results }
}

export class FakeSpeechRecognition {
  constructor() {
    this.continuous = false
    this.interimResults = false
    this.lang = ''
    this.onstart = null
    this.onaudiostart = null
    this.onspeechstart = null
    this.onresult = null
    this.onerror = null
    this.onend = null
    this.startCount = 0
    this.stopped = false
    FakeSpeechRecognition.instances.push(this)
  }

  start() {
    this.startCount += 1
    this.stopped = false
  }

  stop() {
    this.stopped = true
  }

  abort() {
    this.stopped = true
  }
}
FakeSpeechRecognition.instances = []

export function installFakeSpeechRecognition() {
  FakeSpeechRecognition.instances = []
  window.SpeechRecognition = FakeSpeechRecognition
  window.webkitSpeechRecognition = FakeSpeechRecognition
  return FakeSpeechRecognition
}

export function uninstallFakeSpeechRecognition() {
  delete window.SpeechRecognition
  delete window.webkitSpeechRecognition
  FakeSpeechRecognition.instances = []
}

export function latestInstance() {
  return FakeSpeechRecognition.instances[FakeSpeechRecognition.instances.length - 1]
}
