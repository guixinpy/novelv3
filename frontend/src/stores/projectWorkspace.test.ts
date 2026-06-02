import { describe, expect, it } from 'vitest'
import {
  appendMemoryTreeHistory,
  clearMemoryTreeHistory,
  createProjectWorkspaceState,
  enterProject,
  markDirty,
  memoryTreeHistoryForProject,
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

  it('keeps bounded memory tree history by project', () => {
    const state = createProjectWorkspaceState()

    appendMemoryTreeHistory(state, 'p1', { key: 'run-1:search', label: '搜索：灯塔旧回声', runId: 'run-1' }, 2)
    appendMemoryTreeHistory(state, 'p1', { key: 'run-2:expand', label: '节点展开：第2章', runId: 'run-2' }, 2)
    appendMemoryTreeHistory(state, 'p1', { key: 'run-3:expand', label: '推荐展开：第3章', runId: 'run-3' }, 2)
    appendMemoryTreeHistory(state, 'p2', { key: 'run-4:search', label: '搜索：雨巷伏笔' }, 2)

    expect(memoryTreeHistoryForProject(state, 'p1')).toEqual([
      { key: 'run-2:expand', label: '节点展开：第2章', runId: 'run-2' },
      { key: 'run-3:expand', label: '推荐展开：第3章', runId: 'run-3' },
    ])
    expect(memoryTreeHistoryForProject(state, 'p2')).toEqual([
      { key: 'run-4:search', label: '搜索：雨巷伏笔' },
    ])
  })

  it('stores only safe memory tree history labels', () => {
    const state = createProjectWorkspaceState()

    appendMemoryTreeHistory(state, 'p1', { key: 'unsafe-node', label: '节点展开：scene:memory-3' })
    appendMemoryTreeHistory(state, 'p1', { key: 'unsafe-source', label: '搜索：chapter-content-2' })
    appendMemoryTreeHistory(state, 'p1', { key: 'safe', label: '节点展开：第2章' })

    expect(memoryTreeHistoryForProject(state, 'p1')).toEqual([
      { key: 'safe', label: '节点展开：第2章' },
    ])
  })

  it('clears memory tree history for one project without affecting another', () => {
    const state = createProjectWorkspaceState()

    appendMemoryTreeHistory(state, 'p1', { key: 'run-1:search', label: '搜索：灯塔旧回声' })
    appendMemoryTreeHistory(state, 'p2', { key: 'run-2:search', label: '搜索：雨巷伏笔' })
    clearMemoryTreeHistory(state, 'p1')

    expect(memoryTreeHistoryForProject(state, 'p1')).toEqual([])
    expect(memoryTreeHistoryForProject(state, 'p2')).toEqual([
      { key: 'run-2:search', label: '搜索：雨巷伏笔' },
    ])
  })
})
