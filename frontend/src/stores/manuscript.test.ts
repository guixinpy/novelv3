import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useManuscriptStore } from './manuscript'
import { api } from '../api/client'
import type { ChapterRevision } from '../api/types'

vi.mock('../api/client', () => ({
  api: {
    getChapter: vi.fn(),
    getActiveRevision: vi.fn(),
    updateRevisionDraft: vi.fn(),
    submitRevision: vi.fn(),
    submitRevisionDraft: vi.fn(),
  },
}))

function mockChapter(chapterIndex = 1) {
  vi.mocked(api.getChapter).mockResolvedValue({
    id: `chapter-${chapterIndex}`,
    project_id: 'project-1',
    chapter_index: chapterIndex,
    title: `第${chapterIndex}章`,
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
}

function mockRevision(status = 'draft'): ChapterRevision {
  return {
    id: 'revision-1',
    project_id: 'project-1',
    chapter_id: 'chapter-1',
    chapter_index: 1,
    revision_index: 1,
    status,
    submitted_at: status === 'draft' ? null : '2026-04-24T00:00:00Z',
    completed_at: null,
    base_version_id: status === 'draft' ? null : 'version-base',
    result_version_id: null,
    annotations: [
      {
        id: 'annotation-1',
        revision_id: 'revision-1',
        paragraph_index: 0,
        start_offset: 0,
        end_offset: 2,
        selected_text: '开头',
        comment: '节奏太慢',
      },
    ],
    corrections: [
      {
        id: 'correction-1',
        revision_id: 'revision-1',
        paragraph_index: 1,
        original_text: '寒风凛冽',
        corrected_text: '夜风微凉',
      },
    ],
  }
}

describe('manuscript store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    vi.mocked(api.getActiveRevision).mockResolvedValue(null)
  })

  it('loads chapter and splits content into paragraphs', async () => {
    mockChapter()
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

  it('restores pending feedback from backend active revision after a page refresh', async () => {
    mockChapter()
    vi.mocked(api.getActiveRevision).mockResolvedValue(mockRevision())

    setActivePinia(createPinia())
    const reloadedStore = useManuscriptStore()
    await reloadedStore.loadChapter('project-1', 1)

    expect(reloadedStore.annotations).toMatchObject([
      { paragraphIndex: 0, startOffset: 0, endOffset: 2, selectedText: '开头', comment: '节奏太慢' },
    ])
    expect(reloadedStore.corrections).toMatchObject([
      { paragraphIndex: 1, originalText: '寒风凛冽', correctedText: '夜风微凉' },
    ])
    expect(reloadedStore.hasPendingFeedback).toBe(true)
  })

  it('saves annotation and correction changes to backend draft', async () => {
    mockChapter()
    const draftRevision = mockRevision()
    vi.mocked(api.updateRevisionDraft).mockResolvedValue(draftRevision)
    const store = useManuscriptStore()
    await store.loadChapter('project-1', 1)

    await store.addAnnotation({ paragraphIndex: 0, startOffset: 0, endOffset: 2, selectedText: '开头', comment: '节奏太慢' })
    await store.addCorrection({ paragraphIndex: 1, originalText: '寒风凛冽', correctedText: '夜风微凉' })

    expect(api.updateRevisionDraft).toHaveBeenLastCalledWith('project-1', 1, {
      annotations: [{ paragraph_index: 0, start_offset: 0, end_offset: 2, selected_text: '开头', comment: '节奏太慢' }],
      corrections: [{ paragraph_index: 1, original_text: '寒风凛冽', corrected_text: '夜风微凉' }],
    })
    expect(store.activeRevision?.id).toBe('revision-1')
  })

  it('removes an existing correction when the paragraph is restored to original text', async () => {
    mockChapter()
    const initialRevision = mockRevision()
    const clearedRevision: ChapterRevision = { ...initialRevision, corrections: [] }
    vi.mocked(api.getActiveRevision).mockResolvedValue(initialRevision)
    vi.mocked(api.updateRevisionDraft).mockResolvedValue(clearedRevision)
    const store = useManuscriptStore()
    await store.loadChapter('project-1', 1)

    await store.addCorrection({ paragraphIndex: 1, originalText: '寒风凛冽', correctedText: '寒风凛冽' })

    expect(api.updateRevisionDraft).toHaveBeenLastCalledWith('project-1', 1, {
      annotations: [{ paragraph_index: 0, start_offset: 0, end_offset: 2, selected_text: '开头', comment: '节奏太慢' }],
      corrections: [],
    })
    expect(store.corrections).toEqual([])
  })

  it('persists removal of the last annotation and clears the active draft', async () => {
    mockChapter()
    const initialRevision: ChapterRevision = { ...mockRevision(), corrections: [] }
    vi.mocked(api.getActiveRevision).mockResolvedValue(initialRevision)
    vi.mocked(api.updateRevisionDraft).mockResolvedValue(null)
    const store = useManuscriptStore()
    await store.loadChapter('project-1', 1)

    await store.removeAnnotation('annotation-1')

    expect(api.updateRevisionDraft).toHaveBeenLastCalledWith('project-1', 1, {
      annotations: [],
      corrections: [],
    })
    expect(store.annotations).toEqual([])
    expect(store.corrections).toEqual([])
    expect(store.activeRevision).toBeNull()
  })

  it('persists removal of the last correction and clears the active draft', async () => {
    mockChapter()
    const initialRevision: ChapterRevision = { ...mockRevision(), annotations: [] }
    vi.mocked(api.getActiveRevision).mockResolvedValue(initialRevision)
    vi.mocked(api.updateRevisionDraft).mockResolvedValue(null)
    const store = useManuscriptStore()
    await store.loadChapter('project-1', 1)

    await store.removeCorrection('correction-1')

    expect(api.updateRevisionDraft).toHaveBeenLastCalledWith('project-1', 1, {
      annotations: [],
      corrections: [],
    })
    expect(store.annotations).toEqual([])
    expect(store.corrections).toEqual([])
    expect(store.activeRevision).toBeNull()
  })

  it('submits backend draft without clearing feedback before regeneration completes', async () => {
    mockChapter()
    vi.mocked(api.getActiveRevision).mockResolvedValue(mockRevision())
    vi.mocked(api.updateRevisionDraft).mockResolvedValue(mockRevision())
    vi.mocked(api.submitRevisionDraft).mockResolvedValue(mockRevision('submitted'))
    const store = useManuscriptStore()
    await store.loadChapter('project-1', 1)

    await store.submitRevision('project-1', 1)

    expect(api.updateRevisionDraft).toHaveBeenCalledWith('project-1', 1, {
      annotations: [{ paragraph_index: 0, start_offset: 0, end_offset: 2, selected_text: '开头', comment: '节奏太慢' }],
      corrections: [{ paragraph_index: 1, original_text: '寒风凛冽', corrected_text: '夜风微凉' }],
    })
    expect(api.submitRevisionDraft).toHaveBeenCalledWith('project-1', 'revision-1')
    expect(store.activeRevision?.status).toBe('submitted')
    expect(store.hasPendingFeedback).toBe(true)
    expect(store.annotations).toHaveLength(1)
  })

  it('flushes the latest local feedback before submitting an existing backend draft', async () => {
    mockChapter()
    const draftRevision = mockRevision()
    const updatedDraft: ChapterRevision = {
      ...draftRevision,
      annotations: [{ ...draftRevision.annotations[0], comment: '最后一秒修改' }],
    }
    vi.mocked(api.getActiveRevision).mockResolvedValue(draftRevision)
    vi.mocked(api.updateRevisionDraft).mockResolvedValue(updatedDraft)
    vi.mocked(api.submitRevisionDraft).mockResolvedValue({ ...updatedDraft, status: 'submitted' })
    const store = useManuscriptStore()
    await store.loadChapter('project-1', 1)
    store.annotations[0].comment = '最后一秒修改'

    await store.submitRevision('project-1', 1)

    expect(api.updateRevisionDraft).toHaveBeenCalledWith('project-1', 1, {
      annotations: [{ paragraph_index: 0, start_offset: 0, end_offset: 2, selected_text: '开头', comment: '最后一秒修改' }],
      corrections: [{ paragraph_index: 1, original_text: '寒风凛冽', corrected_text: '夜风微凉' }],
    })
    expect(vi.mocked(api.updateRevisionDraft).mock.invocationCallOrder[0]).toBeLessThan(
      vi.mocked(api.submitRevisionDraft).mock.invocationCallOrder[0],
    )
  })

  it('clears feedback only after backend active revision is gone', async () => {
    mockChapter()
    vi.mocked(api.getActiveRevision).mockResolvedValueOnce(mockRevision('submitted')).mockResolvedValueOnce(null)
    const store = useManuscriptStore()

    await store.loadChapter('project-1', 1)
    expect(store.hasPendingFeedback).toBe(true)
    await store.loadChapter('project-1', 1)

    expect(store.annotations).toEqual([])
    expect(store.corrections).toEqual([])
    expect(store.activeRevision).toBeNull()
  })
})
