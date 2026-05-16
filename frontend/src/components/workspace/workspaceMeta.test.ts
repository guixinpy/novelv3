import { describe, expect, it } from 'vitest'
import { getActionRefreshTargets } from './workspaceMeta'

describe('workspaceMeta', () => {
  it('generate_chapter completion refreshes writing state with content', () => {
    expect(getActionRefreshTargets('generate_chapter', 'completed')).toEqual([
      'project',
      'content',
      'versions',
      'writing_state',
    ])
  })
})
