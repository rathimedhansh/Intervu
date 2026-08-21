function CommunicationConsent({ speechEnabled, onSpeechChange, cameraEnabled, onCameraChange }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <h2 className="mb-1 text-sm font-semibold text-slate-900">
        Communication analysis is optional.
      </h2>
      <p className="mb-4 text-xs text-slate-500">
        Both options run entirely in your browser. Raw audio and video are
        never stored or uploaded — only the summary metrics below are saved
        with your results.
      </p>

      <label className="mb-3 flex items-start gap-3">
        <input
          type="checkbox"
          checked={speechEnabled}
          onChange={(event) => onSpeechChange(event.target.checked)}
          className="mt-0.5 h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
        />
        <span>
          <span className="block text-sm font-medium text-slate-700">
            Analyze my speech
          </span>
          <span className="block text-xs text-slate-500">
            Uses your microphone to measure speaking pace, pauses, filler
            words, and answer duration. No audio is stored.
          </span>
        </span>
      </label>

      <label className="flex items-start gap-3">
        <input
          type="checkbox"
          checked={cameraEnabled}
          onChange={(event) => onCameraChange(event.target.checked)}
          className="mt-0.5 h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
        />
        <span>
          <span className="block text-sm font-medium text-slate-700">
            Analyze my camera
          </span>
          <span className="block text-xs text-slate-500">
            Uses your webcam to estimate how often your face is visible and
            facing the camera. No video or images are stored.
          </span>
        </span>
      </label>
    </div>
  )
}

export default CommunicationConsent
