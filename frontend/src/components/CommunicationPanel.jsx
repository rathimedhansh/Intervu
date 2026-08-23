const STATUS_TEXT = {
  active: 'analyzing locally',
  unsupported: "isn't supported here — continuing without it",
  denied: 'permission denied — continuing without it',
  error: "couldn't start — continuing without it",
}

const STATUS_TONE = {
  active: 'bg-success-soft text-success',
  unsupported: 'bg-surface-2 text-ink-faint',
  denied: 'bg-warning-soft text-warning',
  error: 'bg-warning-soft text-warning',
}

function StatusPill({ label, status }) {
  if (status === 'idle' || !status) return null
  return (
    <span className={`badge ${STATUS_TONE[status] ?? 'bg-surface-2 text-ink-faint'}`}>
      {status === 'active' && <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-success" />}
      {label}: {STATUS_TEXT[status] ?? status}
    </span>
  )
}

// Never blocks interview navigation — purely informational. Rendered only
// when at least one analysis type was opted into on the setup page.
function CommunicationPanel({ speechEnabled, speechStatus, cameraEnabled, cameraStatus }) {
  if (!speechEnabled && !cameraEnabled) return null

  return (
    <div className="mb-4 flex flex-wrap items-center gap-2 rounded-lg border border-border bg-surface-2/60 px-3 py-2">
      {speechEnabled && <StatusPill label="Speech" status={speechStatus} />}
      {cameraEnabled && <StatusPill label="Camera" status={cameraStatus} />}
    </div>
  )
}

export default CommunicationPanel
