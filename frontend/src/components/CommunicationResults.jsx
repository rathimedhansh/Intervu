import StatTile from './StatTile'

function scoreTone(score) {
  if (score >= 80) return { text: 'text-success', bg: 'bg-success-soft', bar: 'bg-success', ring: 'border-success/25' }
  if (score >= 55) return { text: 'text-warning', bg: 'bg-warning-soft', bar: 'bg-warning', ring: 'border-warning/25' }
  return { text: 'text-danger', bg: 'bg-danger-soft', bar: 'bg-danger', ring: 'border-danger/25' }
}

function formatDuration(seconds) {
  const mins = Math.floor(seconds / 60)
  const secs = Math.round(seconds % 60)
  return mins > 0 ? `${mins}m ${secs}s` : `${secs}s`
}

function OverallScore({ score }) {
  if (score == null) return null
  const tone = scoreTone(score)
  return (
    <div className={`mb-6 flex items-center gap-4 rounded-xl border p-4 ${tone.bg} ${tone.ring}`}>
      <span className={`text-4xl font-semibold tracking-tight ${tone.text}`}>
        {score}
        <span className="text-lg font-normal opacity-60">/100</span>
      </span>
      <div>
        <p className={`text-sm font-medium ${tone.text}`}>Communication Score</p>
        <p className="text-xs text-ink-faint">
          A transparent score built only from measurements below — not a judgment of your ideas or answers.
        </p>
      </div>
    </div>
  )
}

function CategoryBar({ category }) {
  const tone = scoreTone(category.score)
  return (
    <div className="rounded-xl border border-border p-3">
      <div className="mb-1 flex items-center justify-between">
        <span className="text-sm font-medium text-ink">{category.label}</span>
        <span className={`text-sm font-semibold ${tone.text}`}>{category.score}</span>
      </div>
      <div className="mb-2 h-1.5 w-full overflow-hidden rounded-full bg-surface-2">
        <div className={`h-full rounded-full ${tone.bar}`} style={{ width: `${category.score}%` }} />
      </div>
      <p className="text-xs text-ink-faint">{category.description}</p>
    </div>
  )
}

function ChipList({ items, tone = 'bg-surface-2 text-ink-muted' }) {
  if (!items.length) return null
  return (
    <div className="flex flex-wrap gap-1.5">
      {items.map((item, i) => (
        <span key={i} className={`badge ${tone}`}>
          {item}
        </span>
      ))}
    </div>
  )
}

function BulletList({ title, items, tone }) {
  if (!items?.length) return null
  return (
    <div>
      <h4 className={`mb-1 text-xs font-semibold uppercase tracking-wide ${tone}`}>{title}</h4>
      <ul className="list-disc space-y-1 pl-5 text-sm text-ink-muted">
        {items.map((item, i) => (
          <li key={i}>{item}</li>
        ))}
      </ul>
    </div>
  )
}

// Opt-in only: renders nothing unless the interview actually opted into
// speech and/or camera analysis. Consumes the backend's communication_report
// (see app.services.communication_feedback.report) — a computed field
// derived entirely from speech_metrics/camera_metrics already stored per
// answer/interview, recomputed fresh on every read.
function CommunicationResults({ interview }) {
  const report = interview.communication_report
  if (!report) return null

  const { speech_summary: speech, camera_summary: camera } = report

  return (
    <div className="surface-card mb-8 p-5">
      <h2 className="mb-1 text-sm font-semibold text-ink">Communication &amp; Presentation</h2>
      <p className="mb-4 text-xs text-ink-faint">
        Locally-observed speech and presentation patterns from this session.
      </p>

      <OverallScore score={report.overall_score} />

      {report.categories.length > 0 && (
        <div className="mb-6 grid gap-3 sm:grid-cols-2">
          {report.categories.map((category) => (
            <CategoryBar key={category.key} category={category} />
          ))}
        </div>
      )}

      {speech && (
        <div className="mb-6">
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-faint">
            Speech statistics
          </h3>
          <div className="mb-3 grid grid-cols-2 gap-3 sm:grid-cols-3">
            <StatTile
              label="Speaking pace"
              value={speech.average_words_per_minute ?? '—'}
              suffix={speech.average_words_per_minute != null ? 'wpm' : undefined}
            />
            <StatTile label="Total speaking time" value={formatDuration(speech.total_duration_seconds)} />
            <StatTile label="Words spoken" value={speech.total_words_spoken ?? '—'} />
            <StatTile label="Filler words" value={speech.filler_word_count} />
            <StatTile label="Pauses" value={speech.pause_count} />
            <StatTile label="Long pauses (4s+)" value={speech.long_pause_count} />
          </div>

          {Object.keys(speech.filler_word_breakdown).length > 0 && (
            <div className="mb-3">
              <p className="mb-1 text-xs font-medium text-ink-muted">Filler words used</p>
              <ChipList
                items={Object.entries(speech.filler_word_breakdown).map(
                  ([word, count]) => `"${word}" × ${count}`,
                )}
              />
            </div>
          )}

          <div className="rounded-xl border border-border bg-surface-2/60 p-3">
            <p className="mb-1 text-xs font-medium text-ink-muted">
              Estimated repetition / stutter-like patterns
              <span className="badge ml-1.5 bg-surface-2 text-[10px] uppercase tracking-wide text-ink-faint">
                Heuristic
              </span>
            </p>
            <p className="mb-2 text-sm text-ink">
              {speech.estimated_repetition_count} repeated word/phrase pattern(s) detected
            </p>
            {speech.repeated_examples.length > 0 && (
              <ChipList
                items={speech.repeated_examples.map((example) => `"${example}"`)}
                tone="border border-border bg-surface text-ink-faint"
              />
            )}
            <p className="mt-2 text-xs italic text-ink-faint">
              An estimated, heuristic signal only — not a medical diagnosis or definitive speech assessment.
            </p>
          </div>
        </div>
      )}

      {camera && (
        <div className="mb-6">
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-ink-faint">
            Presentation
          </h3>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            <StatTile label="Face visibility" value={camera.face_visible_percentage} suffix="%" />
            <StatTile
              label="Gaze toward camera"
              value={camera.camera_attention_percentage}
              suffix="%"
            />
            <StatTile label="Head movement" value={camera.head_movement_score} />
            {camera.look_away_count != null && (
              <StatTile label="Times looked away" value={camera.look_away_count} />
            )}
            {camera.multiple_faces_percentage != null && camera.multiple_faces_percentage > 0 && (
              <StatTile label="Multiple faces detected" value={camera.multiple_faces_percentage} suffix="%" />
            )}
          </div>
          <p className="mt-2 text-xs italic text-ink-faint">
            "Gaze toward camera" is a geometric proxy for eye contact (nose position relative to
            your face), not a reading of attention, confidence, or emotion.
          </p>
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2">
        <BulletList title="Strengths" items={report.strengths} tone="text-success" />
        <BulletList title="Areas to improve" items={report.improvements} tone="text-warning" />
      </div>

      {report.recommendations.length > 0 && (
        <div className="mt-4">
          <h4 className="mb-1 text-xs font-semibold uppercase tracking-wide text-accent">
            Recommendations
          </h4>
          <ul className="list-disc space-y-1 pl-5 text-sm text-ink-muted">
            {report.recommendations.map((item, i) => (
              <li key={i}>{item}</li>
            ))}
          </ul>
        </div>
      )}

      <p className="mt-4 border-t border-border pt-3 text-xs text-ink-faint">{report.note}</p>
    </div>
  )
}

export default CommunicationResults
