import { useEffect, useRef, useState } from 'react'

// Animates a number counting up to `value` on mount/change — used for the
// large score displays so they feel alive without pulling in a heavier
// animation dependency for a single numeric tween. Skips the animation
// entirely for null/undefined so "no data yet" states never flash a 0.
export function useCountUp(value, durationMs = 700) {
  const [display, setDisplay] = useState(value ?? 0)
  const frameRef = useRef(null)

  useEffect(() => {
    if (value == null) {
      setDisplay(0)
      return undefined
    }
    const start = performance.now()
    const from = 0
    const to = value

    function tick(now) {
      const elapsed = now - start
      const progress = Math.min(1, elapsed / durationMs)
      // ease-out cubic
      const eased = 1 - Math.pow(1 - progress, 3)
      setDisplay(Math.round(from + (to - from) * eased))
      if (progress < 1) {
        frameRef.current = requestAnimationFrame(tick)
      }
    }

    frameRef.current = requestAnimationFrame(tick)
    return () => {
      if (frameRef.current) cancelAnimationFrame(frameRef.current)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value, durationMs])

  return display
}
