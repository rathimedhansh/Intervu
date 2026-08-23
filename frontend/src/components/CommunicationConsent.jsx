function ConsentToggle({ checked, onChange, title, description }) {
  return (
    <label className="flex cursor-pointer items-start gap-3 rounded-xl border border-border p-3 transition-colors hover:border-border-strong">
      <span className="relative mt-0.5 inline-flex h-5 w-9 shrink-0 items-center">
        <input
          type="checkbox"
          checked={checked}
          onChange={(event) => onChange(event.target.checked)}
          className="peer sr-only"
        />
        <span className="absolute inset-0 rounded-full bg-surface-2 transition-colors peer-checked:bg-accent" />
        <span className="absolute left-0.5 h-4 w-4 rounded-full bg-ink transition-transform peer-checked:translate-x-4" />
      </span>
      <span>
        <span className="block text-sm font-medium text-ink">{title}</span>
        <span className="block text-xs text-ink-muted">{description}</span>
      </span>
    </label>
  )
}

function CommunicationConsent({ speechEnabled, onSpeechChange, cameraEnabled, onCameraChange }) {
  return (
    <div className="surface-card p-4">
      <h2 className="mb-1 text-sm font-semibold text-ink">Communication analysis is optional.</h2>
      <p className="mb-4 text-xs text-ink-faint">
        Both options run entirely in your browser. Raw audio and video are
        never stored or uploaded — only the summary metrics below are saved
        with your results.
      </p>

      <div className="flex flex-col gap-2.5">
        <ConsentToggle
          checked={speechEnabled}
          onChange={onSpeechChange}
          title="Analyze my speech"
          description="Uses your microphone to measure speaking pace, pauses, filler words, and answer duration. No audio is stored."
        />
        <ConsentToggle
          checked={cameraEnabled}
          onChange={onCameraChange}
          title="Analyze my camera"
          description="Uses your webcam to estimate how often your face is visible and facing the camera. No video or images are stored."
        />
      </div>
    </div>
  )
}

export default CommunicationConsent
