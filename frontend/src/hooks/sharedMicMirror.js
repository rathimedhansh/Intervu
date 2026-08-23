// Pure decision logic for mirroring the communication-analysis mic's live
// transcript into the answer box while "Start Answer"/"Stop Answer" merely
// gate a shared, always-running SpeechRecognition session rather than
// starting/stopping one of their own (see useDictation.js's module comment
// for why only one recognition session may run at a time).
//
// Kept side-effect-free and exported on its own so the exact commit
// decision — including the tail commit for a final transcript that lands
// after "Stop Answer" was already clicked — can be unit tested without
// mounting the full InterviewPage tree.
export function computeSharedMicMirror({ canCaptureShared, sharedCapturing, tailArmed, liveTranscript, lastMirrored }) {
  if (!canCaptureShared) {
    return { commit: false, tailArmed }
  }

  let nextTailArmed = tailArmed
  if (sharedCapturing) {
    nextTailArmed = true
  } else if (!nextTailArmed) {
    return { commit: false, tailArmed: nextTailArmed }
  }

  if (liveTranscript === lastMirrored) {
    return { commit: false, tailArmed: nextTailArmed }
  }

  if (!sharedCapturing) nextTailArmed = false
  return { commit: true, tailArmed: nextTailArmed, text: liveTranscript }
}
