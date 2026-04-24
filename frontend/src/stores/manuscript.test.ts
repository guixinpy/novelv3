import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useManuscriptStore } from './manuscript'
import { api } from '../api/client'

vi.mock('../api/client', () => ({
  api: {
    getChapter: vi.fn(),
    submitRevision: vi.fn(),
  },
}))

describe('manuscript store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('loads chapter and splits content into paragraphs', async () => {
    vi.mocked(api.getChapter).mockResolvedValue({
      id: 'chapter-1',
      project_id: 'project-1',
      chapter_index: 1,
      title: '第一章',
      content: '第一段。\n\n第二段。',
      word_count: 8,
      status: 'generated',
      model: '',
      prompt_tokens: 0,
      completion_tokens: 0,
      generation_time: 0,
      temperature: 0.7,
      created_at: '2026-04-24T00:00:00Z',
      updated_at: '2026-04-24T00:00:00Z',
    })
    const store = useManuscriptStore()

    await store.loadChapter('project-1', 1)

    expect(store.selectedChapterIndex).toBe(1)
    expect(store.paragraphs).toEqual(['第一段。', '第二段。'])
  })

  it('tracks local annotations and corrections as dirty state', () => {
    const store = useManuscriptStore()

    store.addAnnotation({ paragraphIndex: 0, startOffset: 0, endOffset: 2, selectedText: '开头', comment: '节奏太慢' })
    store.addCorrection({ paragraphIndex: 1, originalText: '寒风凛冽', correctedText: '夜风微凉' })

    expect(store.hasPendingFeedback).toBe(true)
    expect(store.annotations).toHaveLength(1)
    expect(store.corrections).toHaveLength(1)
  })

  it('submits feedback then clears local draft', async () => {
    vi.mocked(api.submitRevision).mockResolvedValue({
      id: 'revision-1',
      project_id: 'project-1',
      chapter_id: 'chapter-1',
      chapter_index: 1,
      revision_index: 1,
      status: 'submitted',
      submitted_at: '2026-04-24T00:00:00Z',
      completed_at: null,
      annotations: [],
      corrections: [],
    })
    const store = useManuscriptStore()
    store.addAnnotation({ paragraphIndex: 0, startOffset: 0, endOffset: 2, selectedText: '开头', comment: '节奏太慢' })

    const revision = await store.submitRevision('project-1', 1)

    expect(api.submitRevision).toHaveBeenCalledWith('project-1', {
      chapter_index: 1,
      annotations: [{ paragraph_index: 0, start_offset: 0, end_offset: 2, selected_text: '开头', comment: '节奏太慢' }],
      corrections: [],
    })
    expect(revision.id).toBe('revision-1')
    expect(store.hasPendingFeedback).toBe(false)
  })
})
