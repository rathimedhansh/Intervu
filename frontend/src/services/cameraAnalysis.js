// Local, browser-only camera analysis using face-api.js's tiny face
// detector + 68-point landmarks. Each frame is drawn onto an offscreen
// canvas, analyzed, and the canvas is cleared before the next frame —
// pixel data is never serialized, stored, or sent anywhere. Only three
// aggregate numbers (see getMetrics) ever leave this module.
//
// Detection is purely geometric (is a face present, where roughly is it
// pointing, how much did it move). No identity, emotion, confidence, or
// attractiveness inference of any kind.
//
// Framework-agnostic on purpose — swap the detector later without
// touching the React hook that wraps it.

const SAMPLE_INTERVAL_MS = 500
const MODEL_URL = '/models'
const CAPTURE_WIDTH = 320
const CAPTURE_HEIGHT = 240
// Fraction of face width the nose centroid can drift from the face's
// horizontal center before we treat the frame as "looking away".
const GAZE_YAW_THRESHOLD = 0.18

let modelsLoadedPromise = null

async function ensureModelsLoaded() {
  if (!modelsLoadedPromise) {
    modelsLoadedPromise = (async () => {
      const faceapi = await import('face-api.js')
      await faceapi.nets.tinyFaceDetector.loadFromUri(MODEL_URL)
      await faceapi.nets.faceLandmark68Net.loadFromUri(MODEL_URL)
      return faceapi
    })()
  }
  return modelsLoadedPromise
}

export function isCameraAnalysisSupported() {
  return Boolean(navigator.mediaDevices?.getUserMedia)
}

function noseCentroid(landmarks) {
  const nosePoints = landmarks.getNose()
  const x = nosePoints.reduce((sum, p) => sum + p.x, 0) / nosePoints.length
  const y = nosePoints.reduce((sum, p) => sum + p.y, 0) / nosePoints.length
  return { x, y }
}

export class CameraAnalyzer {
  constructor() {
    this._stream = null
    this._video = null
    this._canvas = null
    this._faceapi = null
    this._detectorOptions = null
    this._timer = null
    this._active = false
    this._sampling = false

    this._tickCount = 0
    this._faceVisibleCount = 0
    this._attentiveCount = 0
    this._movementSum = 0
    this._movementSamples = 0
    this._lastNose = null
    this._multiFaceCount = 0
    // Counts transitions from "looking toward the camera" to "looking
    // away", not just away ticks — a frequency (how often gaze left the
    // camera), distinct from camera_attention_percentage (how much of the
    // time it was away).
    this._lookAwayCount = 0
    this._wasAttentive = true
  }

  static isSupported() {
    return isCameraAnalysisSupported()
  }

  async start() {
    if (this._active) return

    this._faceapi = await ensureModelsLoaded()
    this._detectorOptions = new this._faceapi.TinyFaceDetectorOptions({
      inputSize: 224,
      scoreThreshold: 0.5,
    })

    this._stream = await navigator.mediaDevices.getUserMedia({
      video: { width: CAPTURE_WIDTH, height: CAPTURE_HEIGHT },
    })

    this._video = document.createElement('video')
    this._video.muted = true
    this._video.playsInline = true
    this._video.srcObject = this._stream
    await this._video.play()

    this._canvas = document.createElement('canvas')
    this._canvas.width = CAPTURE_WIDTH
    this._canvas.height = CAPTURE_HEIGHT

    this._active = true
    this._timer = setInterval(() => this._sample(), SAMPLE_INTERVAL_MS)
  }

  async _sample() {
    if (!this._active || this._sampling || !this._video || this._video.readyState < 2) return
    this._sampling = true

    try {
      const ctx = this._canvas.getContext('2d')
      ctx.drawImage(this._video, 0, 0, this._canvas.width, this._canvas.height)

      this._tickCount += 1

      // detectAllFaces (not detectSingleFace) so a second face in frame is
      // actually observable rather than silently ignored — gaze/movement
      // still track the largest/primary detection.
      const detections = await this._faceapi
        .detectAllFaces(this._canvas, this._detectorOptions)
        .withFaceLandmarks()

      // The frame is discarded immediately after analysis regardless of
      // outcome — never read out, exported, or persisted.
      ctx.clearRect(0, 0, this._canvas.width, this._canvas.height)

      if (!detections || detections.length === 0) {
        this._lastNose = null
        this._wasAttentive = true
        return
      }

      this._faceVisibleCount += 1
      if (detections.length > 1) this._multiFaceCount += 1

      const primary = detections[0]
      const box = primary.detection.box
      const nose = noseCentroid(primary.landmarks)
      const faceWidth = box.width || 1
      const faceCenterX = box.x + box.width / 2
      const yawFraction = Math.abs(nose.x - faceCenterX) / faceWidth
      const isAttentive = yawFraction <= GAZE_YAW_THRESHOLD
      if (isAttentive) {
        this._attentiveCount += 1
      } else if (this._wasAttentive) {
        this._lookAwayCount += 1
      }
      this._wasAttentive = isAttentive

      if (this._lastNose) {
        const dx = nose.x - this._lastNose.x
        const dy = nose.y - this._lastNose.y
        this._movementSum += Math.sqrt(dx * dx + dy * dy) / faceWidth
        this._movementSamples += 1
      }
      this._lastNose = nose
    } finally {
      this._sampling = false
    }
  }

  stop() {
    if (this._timer) clearInterval(this._timer)
    this._timer = null

    if (this._video) {
      this._video.pause()
      this._video.srcObject = null
      this._video = null
    }

    if (this._stream) {
      this._stream.getTracks().forEach((track) => track.stop())
      this._stream = null
    }

    this._canvas = null
    this._active = false
  }

  getMetrics() {
    const faceVisiblePercentage = this._tickCount
      ? Math.round((this._faceVisibleCount / this._tickCount) * 100)
      : 0
    const cameraAttentionPercentage = this._faceVisibleCount
      ? Math.round((this._attentiveCount / this._faceVisibleCount) * 100)
      : 0
    const avgMovement = this._movementSamples ? this._movementSum / this._movementSamples : 0
    const headMovementScore = Math.min(100, Math.round(avgMovement * 1000))
    const multipleFacesPercentage = this._tickCount
      ? Math.round((this._multiFaceCount / this._tickCount) * 100)
      : 0

    return {
      face_visible_percentage: faceVisiblePercentage,
      camera_attention_percentage: cameraAttentionPercentage,
      head_movement_score: headMovementScore,
      look_away_count: this._lookAwayCount,
      multiple_faces_percentage: multipleFacesPercentage,
    }
  }
}
