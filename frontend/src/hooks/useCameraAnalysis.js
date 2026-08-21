import { useEffect, useRef, useState } from 'react'
import { CameraAnalyzer, isCameraAnalysisSupported } from '../services/cameraAnalysis'

// Interview-level camera metrics for the whole session. Starts once (if
// enabled) when the interview page mounts and stops on unmount/completion;
// snapshot() reads the running aggregate right before the interview is
// completed.
export function useCameraAnalysis(enabled) {
  const analyzerRef = useRef(null)
  const [status, setStatus] = useState('idle') // idle | active | unsupported | denied | error

  useEffect(() => {
    if (!enabled) {
      setStatus('idle')
      return undefined
    }

    if (!isCameraAnalysisSupported()) {
      setStatus('unsupported')
      return undefined
    }

    const analyzer = new CameraAnalyzer()
    analyzerRef.current = analyzer
    let cancelled = false

    analyzer
      .start()
      .then(() => {
        if (!cancelled) setStatus('active')
      })
      .catch((err) => {
        if (cancelled) return
        setStatus(err?.name === 'NotAllowedError' ? 'denied' : 'error')
      })

    return () => {
      cancelled = true
      analyzer.stop()
      analyzerRef.current = null
    }
  }, [enabled])

  function snapshot() {
    return analyzerRef.current?.getMetrics() ?? null
  }

  return { status, snapshot }
}
