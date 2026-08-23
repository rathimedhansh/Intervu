import { describe, expect, it } from 'vitest'
import { computeSharedMicMirror } from '../sharedMicMirror'

// computeSharedMicMirror is the exact decision logic InterviewPage.jsx runs
// on every change of canCaptureShared / sharedCapturing / speech.liveTranscript
// to mirror the communication-analysis mic's live transcript into the answer
// box. These tests drive it through the same "final result lands after Stop
// Answer" race as useDictation.test.js, but for the shared-mic path (case K).

describe('computeSharedMicMirror', () => {
  it('K/A: a final transcript that lands AFTER Stop Answer is still committed (tail commit)', () => {
    let tailArmed = false
    let lastMirrored = ''

    // Start Answer clicked; mic is live but nothing spoken yet.
    let decision = computeSharedMicMirror({
      canCaptureShared: true,
      sharedCapturing: true,
      tailArmed,
      liveTranscript: '',
      lastMirrored,
    })
    tailArmed = decision.tailArmed
    expect(decision.commit).toBe(false)
    expect(tailArmed).toBe(true)

    // User says "yes" and clicks Stop Answer before the analyzer's
    // recognition has delivered any result for it — liveTranscript is
    // still '' at the moment of the click.
    decision = computeSharedMicMirror({
      canCaptureShared: true,
      sharedCapturing: false,
      tailArmed,
      liveTranscript: '',
      lastMirrored,
    })
    tailArmed = decision.tailArmed
    expect(decision.commit).toBe(false) // no change yet, nothing to commit

    // The analyzer's shared recognition (which never stops) delivers the
    // final "yes" a moment later — this is the exact race useDictation.js's
    // module comment documents, replayed for the shared-mic path.
    decision = computeSharedMicMirror({
      canCaptureShared: true,
      sharedCapturing: false,
      tailArmed,
      liveTranscript: 'yes',
      lastMirrored,
    })
    expect(decision.commit).toBe(true)
    expect(decision.text).toBe('yes')
    expect(decision.tailArmed).toBe(false) // consumed, won't re-fire on stray audio
  })

  it('mirrors interim results live while capturing (not just on stop)', () => {
    let tailArmed = false
    let lastMirrored = ''

    for (const partial of ['y', 'ye', 'yes']) {
      const decision = computeSharedMicMirror({
        canCaptureShared: true,
        sharedCapturing: true,
        tailArmed,
        liveTranscript: partial,
        lastMirrored,
      })
      expect(decision.commit).toBe(true)
      expect(decision.text).toBe(partial)
      tailArmed = decision.tailArmed
      lastMirrored = decision.text
    }
  })

  it('does not mirror when the shared mic is not actually available', () => {
    const decision = computeSharedMicMirror({
      canCaptureShared: false,
      sharedCapturing: true,
      tailArmed: false,
      liveTranscript: 'yes',
      lastMirrored: '',
    })
    expect(decision.commit).toBe(false)
    expect(decision.tailArmed).toBe(false)
  })

  it('a manual edit (lastMirrored already matches) is not clobbered by a stray late update', () => {
    // After the tail was already consumed once, tailArmed is false, so an
    // unrelated ambient-audio transcript change while paused must not
    // overwrite a manual edit the user made in the meantime.
    const decision = computeSharedMicMirror({
      canCaptureShared: true,
      sharedCapturing: false,
      tailArmed: false,
      liveTranscript: 'yes and then some ambient noise',
      lastMirrored: 'yes',
    })
    expect(decision.commit).toBe(false)
  })

  it('stays armed across an equal-transcript re-render instead of disarming early', () => {
    // Regression guard: if the effect re-runs with an unchanged transcript
    // right after Stop Answer, the tail arm must survive so a still-pending
    // final result is not silently dropped.
    let decision = computeSharedMicMirror({
      canCaptureShared: true,
      sharedCapturing: false,
      tailArmed: true,
      liveTranscript: 'yes',
      lastMirrored: 'yes',
    })
    expect(decision.commit).toBe(false)
    expect(decision.tailArmed).toBe(true)

    decision = computeSharedMicMirror({
      canCaptureShared: true,
      sharedCapturing: false,
      tailArmed: decision.tailArmed,
      liveTranscript: 'yes.',
      lastMirrored: 'yes',
    })
    expect(decision.commit).toBe(true)
    expect(decision.text).toBe('yes.')
  })
})
