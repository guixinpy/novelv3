import { describe, expect, it } from 'vitest'
import { createActionReplayGuard } from './hermesActionReplay'

describe('Hermes action replay guard', () => {
  it('ignores the latest historical action fingerprint after initialization', () => {
    const guard = createActionReplayGuard()

    guard.markInitial('3:generate_chapter:success')

    expect(guard.shouldProcess('3:generate_chapter:success')).toBe(false)
    expect(guard.shouldProcess('4:generate_chapter:success')).toBe(true)
  })

  it('does not process fingerprints before the initial history is marked', () => {
    const guard = createActionReplayGuard()

    expect(guard.shouldProcess('1:generate_setup:success')).toBe(false)
  })
})
