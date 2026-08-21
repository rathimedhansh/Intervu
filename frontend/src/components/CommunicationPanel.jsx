const STATUS_TEXT = {
  active: 'analyzing locally',
  unsupported: "isn't supported here — continuing without it",
  denied: 'permission denied — continuing without it',
  error: "couldn't start — continuing without it",
}

const STATUS_TONE = {
  active: 'bg-emerald-50 text-emerald-700',
  unsupported: 'bg-slate-100 text-slate-500',
  denied: 'bg-amber-50 text-amber-700',
  error: 'bg-amber-50 text-amber-700',
}

function StatusPill({ label, status }) {
  if (status === 'idle' || !status) return null
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ${
        STATUS_TONE[status] ?? 'bg-slate-100 text-slate-500'
      }`}
    >
      {status === 'active' && (
        <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-500" />
      )}
      {label}: {STATUS_TEXT[status] ?? status}
    </span>
  )
}

// Never blocks interview navigation — purely informational. Rendered only
// when at least one analysis type was opted into on the setup page.
function CommunicationPanel({ speechEnabled, speechStatus, cameraEnabled, cameraStatus }) {
  if (!speechEnabled && !cameraEnabled) return null

  return (
    <div className="mb-4 flex flex-wrap items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2">
      {speechEnabled && <StatusPill label="Speech" status={speechStatus} />}
      {cameraEnabled && <StatusPill label="Camera" status={cameraStatus} />}
    </div>
  )
}

export default CommunicationPanel
