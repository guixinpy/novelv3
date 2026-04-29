import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useAthenaStore } from './athena'
import { api } from '../api/client'

vi.mock('../api/client', () => ({
  api: {
    getAthenaOntology: vi.fn(),
    getAthenaMessages: vi.fn(),
  },
}))

function ontology(version = 1) {
  return {
    entities: { characters: [{ id: `char-${version}`, name: `角色 ${version}` }] },
    relations: [],
    rules: [],
    setup_summary: null,
    profile_version: version,
  }
}

function message(id: string) {
  return {
    id,
    role: 'assistant' as const,
    content: id,
    message_type: null,
    meta: null,
    pending_action: null,
    diagnosis: null,
    action_result: null,
    trace_id: null,
    created_at: '2026-04-29T00:00:00Z',
  }
}

describe('athena project scope', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('同项目激活不会清掉已加载的 ontology 和 messages', () => {
    const store = useAthenaStore()

    expect(store.ensureProject('project-1')).toBe(true)
    store.ontology = ontology()
    store.messages = [message('history')]

    expect(store.ensureProject('project-1')).toBe(false)

    expect(store.ontology).toEqual(ontology())
    expect(store.messages).toEqual([message('history')])
  })

  it('切换项目会清掉 Athena 项目作用域状态', () => {
    const store = useAthenaStore()

    store.ensureProject('project-1')
    store.ontology = ontology()
    store.messages = [message('history')]
    store.projection = { project_id: 'project-1' } as any

    expect(store.ensureProject('project-2')).toBe(true)

    expect(store.ontology).toBeNull()
    expect(store.messages).toEqual([])
    expect(store.projection).toBeNull()
  })

  it('同项目 fresh 的 ontology 和 messages 再次加载不会重复请求', async () => {
    vi.mocked(api.getAthenaOntology).mockResolvedValue(ontology())
    vi.mocked(api.getAthenaMessages).mockResolvedValue([message('history')])
    const store = useAthenaStore()

    await store.loadOntology('project-1')
    await store.loadMessages('project-1')
    await store.loadOntology('project-1')
    await store.loadMessages('project-1')

    expect(api.getAthenaOntology).toHaveBeenCalledTimes(1)
    expect(api.getAthenaMessages).toHaveBeenCalledTimes(1)
    expect(store.ontology).toEqual(ontology())
    expect(store.messages).toEqual([message('history')])
  })
})
