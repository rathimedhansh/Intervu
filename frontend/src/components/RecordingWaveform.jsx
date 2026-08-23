// Animated bar waveform — a recording-state indicator, not a live audio
// analyzer (the mic pipeline in hooks/useDictation.js and
// hooks/useSpeechAnalysis.js doesn't expose amplitude data, and this
// component intentionally doesn't touch that pipeline). Bars only animate
// while `active` is true, so it always honestly reflects real recording
// state even though bar heights themselves are decorative.
const BAR_COUNT = 24

function barStyle(index, active) {
  const duration = 0.6 + ((index * 37) % 5) / 10 // 0.6s-1.1s, deterministic per bar
  const delay = ((index * 53) % 12) / 10 // 0s-1.1s stagger
  return active
    ? {
        animationDuration: `${duration}s`,
        animationDelay: `${delay}s`,
      }
    : undefined
}

function RecordingWaveform({ active = false, className = '' }) {
  return (
    <div
      className={`flex h-12 items-center justify-center gap-[3px] ${className}`}
      role="img"
      aria-label={active ? 'Recording audio' : 'Microphone idle'}
    >
      {Array.from({ length: BAR_COUNT }).map((_, i) => (
        <span
          key={i}
          style={barStyle(i, active)}
          className={`w-[3px] rounded-full ${
            active
              ? 'h-full origin-center animate-waveform-bar bg-accent'
              : 'h-1.5 bg-border-strong'
          }`}
        />
      ))}
    </div>
  )
}

export default RecordingWaveform
