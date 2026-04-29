import { describe, expect, it } from 'vitest'
import {
  createProjectWorkspaceState,
  enterProject,
  markDirty,
  rememberManuscriptChapter,
} from './projectWorkspace'

describe('project workspace session', () => {
  it('resets dirty state only when entering a different project', () => {
    const state = createProjectWorkspaceState()

    enterProject(state, 'p1')
    markDirty(state, ['content', 'versions'])
    enterProject(state, 'p1')
    expect([...state.dirtyTargets]).toEqual(['content', 'versions'])
    enterProject(state, 'p2')
    expect([...state.dirtyTargets]).toEqual([])
  })

  it('remembers manuscript chapter by project', () => {
    const state = createProjectWorkspaceState()

    rememberManuscriptChapter(state, 'p1', 3)

    expect(state.lastManuscriptChapterByProject.p1).toBe(3)
  })
})
