import { describe, expect, it } from 'vitest'
import { getActionPanel, getActionRefreshTargets } from './workspaceMeta'

describe('workspaceMeta', () => {
  it('generate_chapter completion refreshes writing state with content', () => {
    expect(getActionRefreshTargets('generate_chapter', 'completed')).toEqual([
      'project',
      'content',
      'versions',
      'writing_state',
    ])
  })

  it('retry_chapter completion refreshes content and writing state', () => {
    expect(getActionPanel('retry_chapter')).toBe('content')
    expect(getActionRefreshTargets('retry_chapter', 'completed')).toEqual([
      'project',
      'content',
      'versions',
      'writing_state',
    ])
  })
})
