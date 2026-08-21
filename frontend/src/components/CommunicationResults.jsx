import StatTile from './StatTile'

function scoreTone(score) {
  if (score >= 80) return { text: 'text-emerald-700', bg: 'bg-emerald-50', bar: 'bg-emerald-500', ring: 'border-emerald-200' }
  if (score >= 55) return { text: 'text-amber-700', bg: 'bg-amber-50', bar: 'bg-amber-500', ring: 'border-amber-200' }
  return { text: 'text-rose-700', bg: 'bg-rose-50', bar: 'bg-rose-500', ring: 'border-rose-200' }
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
    <div className={`mb-6 flex items-center gap-4 rounded-lg border p-4 ${tone.bg} ${tone.ring}`}>
      <span className={`text-4xl font-semibold ${tone.text}`}>
        {score}
        <span className="text-lg font-normal opacity-60">/100</span>
      </span>
      <div>
        <p className={`text-sm font-medium ${tone.text}`}>Communication Score</p>
        <p className="text-xs text-slate-500">
          A transparent score built only from measurements below — not a judgment of your ideas or answers.
        </p>
      </div>
    </div>
  )
}

function CategoryBar({ category }) {
  const tone = scoreTone(category.score)
  return (
    <div className="rounded-lg border border-slate-200 p-3">
      <div className="mb-1 flex items-center justify-between">
        <span className="text-sm font-medium text-slate-800">{category.label}</span>
        <span className={`text-sm font-semibold ${tone.text}`}>{category.score}</span>
      </div>
      <div className="mb-2 h-1.5 w-full overflow-hidden rounded-full bg-slate-200">
        <div className={`h-full rounded-full ${tone.bar}`} style={{ width: `${category.score}%` }} />
      </div>
      <p className="text-xs text-slate-500">{category.description}</p>
    </div>
  )
}

function ChipList({ items, tone = 'bg-slate-100 text-slate-600' }) {
  if (!items.length) return null
  return (
    <div className="flex flex-wrap gap-1.5">
      {items.map((item, i) => (
        <span key={i} className={`rounded-full px-2 py-0.5 text-xs ${tone}`}>
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
      <ul className="list-disc space-y-1 pl-5 text-sm text-slate-600">
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
    <div className="mb-8 rounded-lg border border-slate-200 bg-white p-4">
      <h2 className="mb-1 text-sm font-semibold text-slate-900">Communication &amp; Presentation</h2>
      <p className="mb-4 text-xs text-slate-500">
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
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
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
              <p className="mb-1 text-xs font-medium text-slate-600">Filler words used</p>
              <ChipList
                items={Object.entries(speech.filler_word_breakdown).map(
                  ([word, count]) => `"${word}" × ${count}`,
                )}
              />
            </div>
          )}

          <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
            <p className="mb-1 text-xs font-medium text-slate-600">
              Estimated repetition / stutter-like patterns
              <span className="ml-1.5 rounded-full bg-slate-200 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-slate-500">
                Heuristic
              </span>
            </p>
            <p className="mb-2 text-sm text-slate-700">
              {speech.estimated_repetition_count} repeated word/phrase pattern(s) detected
            </p>
            {speech.repeated_examples.length > 0 && (
              <ChipList
                items={speech.repeated_examples.map((example) => `"${example}"`)}
                tone="bg-white border border-slate-200 text-slate-500"
              />
            )}
            <p className="mt-2 text-xs italic text-slate-400">
              An estimated, heuristic signal only — not a medical diagnosis or definitive speech assessment.
            </p>
          </div>
        </div>
      )}

      {camera && (
        <div className="mb-6">
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
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
          <p className="mt-2 text-xs italic text-slate-400">
            "Gaze toward camera" is a geometric proxy for eye contact (nose position relative to
            your face), not a reading of attention, confidence, or emotion.
          </p>
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2">
        <BulletList title="Strengths" items={report.strengths} tone="text-emerald-700" />
        <BulletList title="Areas to improve" items={report.improvements} tone="text-amber-700" />
      </div>

      {report.recommendations.length > 0 && (
        <div className="mt-4">
          <h4 className="mb-1 text-xs font-semibold uppercase tracking-wide text-indigo-700">
            Recommendations
          </h4>
          <ul className="list-disc space-y-1 pl-5 text-sm text-slate-600">
            {report.recommendations.map((item, i) => (
              <li key={i}>{item}</li>
            ))}
          </ul>
        </div>
      )}

      <p className="mt-4 border-t border-slate-100 pt-3 text-xs text-slate-400">{report.note}</p>
    </div>
  )
}

export default CommunicationResults
