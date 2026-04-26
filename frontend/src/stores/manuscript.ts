import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { api } from '../api/client'
import type { ChapterContent, ChapterRevision, RevisionAnnotationPayload, RevisionCorrectionPayload } from '../api/types'

export interface LocalAnnotation {
  id: string
  paragraphIndex: number
  startOffset: number
  endOffset: number
  selectedText: string
  comment: string
}

export interface LocalCorrection {
  id: string
  paragraphIndex: number
  originalText: string
  correctedText: string
}

export type AnnotationDraft = Omit<LocalAnnotation, 'id'>
export type CorrectionDraft = Omit<LocalCorrection, 'id'>

function createLocalId(prefix: string) {
  return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}`
}

function toErrorMessage(err: unknown): string {
  return err instanceof Error ? err.message : String(err)
}

function toLocalAnnotation(item: ChapterRevision['annotations'][number]): LocalAnnotation {
  return {
    id: item.id,
    paragraphIndex: item.paragraph_index,
    startOffset: item.start_offset,
    endOffset: item.end_offset,
    selectedText: item.selected_text,
    comment: item.comment,
  }
}

function toLocalCorrection(item: ChapterRevision['corrections'][number]): LocalCorrection {
  return {
    id: item.id,
    paragraphIndex: item.paragraph_index,
    originalText: item.original_text,
    correctedText: item.corrected_text,
  }
}

function toAnnotationPayload(item: LocalAnnotation): RevisionAnnotationPayload {
  return {
    paragraph_index: item.paragraphIndex,
    start_offset: item.startOffset,
    end_offset: item.endOffset,
    selected_text: item.selectedText,
    comment: item.comment,
  }
}

function toCorrectionPayload(item: LocalCorrection): RevisionCorrectionPayload {
  return {
    paragraph_index: item.paragraphIndex,
    original_text: item.originalText,
    corrected_text: item.correctedText,
  }
}

export const useManuscriptStore = defineStore('manuscript', () => {
  const chapter = ref<ChapterContent | null>(null)
  const selectedProjectId = ref<string | null>(null)
  const selectedChapterIndex = ref<number | null>(null)
  const activeRevision = ref<ChapterRevision | null>(null)
  const annotations = ref<LocalAnnotation[]>([])
  const corrections = ref<LocalCorrection[]>([])
  const loading = ref(false)
  const submitting = ref(false)
  const error = ref<string | null>(null)

  const paragraphs = computed(() => {
    if (!chapter.value?.content) return []
    return chapter.value.content.split(/\n{2,}/).map((item) => item.trim()).filter(Boolean)
  })
  const hasPendingFeedback = computed(() => annotations.value.length > 0 || corrections.value.length > 0)

  function buildDraftPayload() {
    return {
      annotations: annotations.value.map(toAnnotationPayload),
      corrections: corrections.value.map(toCorrectionPayload),
    }
  }

  function applyRevisionFeedback(revision: ChapterRevision | null) {
    activeRevision.value = revision
    annotations.value = revision ? revision.annotations.map(toLocalAnnotation) : []
    corrections.value = revision ? revision.corrections.map(toLocalCorrection) : []
  }

  async function persistCurrentDraft() {
    if (!selectedProjectId.value || selectedChapterIndex.value === null) return
    try {
      const revision = await api.updateRevisionDraft(selectedProjectId.value, selectedChapterIndex.value, buildDraftPayload())
      applyRevisionFeedback(revision)
    } catch (err) {
      error.value = toErrorMessage(err)
    }
  }

  async function loadChapter(projectId: string, chapterIndex: number) {
    loading.value = true
    error.value = null
    try {
      const [nextChapter, revision] = await Promise.all([
        api.getChapter(projectId, chapterIndex),
        api.getActiveRevision(projectId, chapterIndex),
      ])
      chapter.value = nextChapter
      selectedProjectId.value = projectId
      selectedChapterIndex.value = chapterIndex
      applyRevisionFeedback(revision)
    } catch (err) {
      error.value = toErrorMessage(err)
    } finally {
      loading.value = false
    }
  }

  async function addAnnotation(draft: AnnotationDraft) {
    annotations.value.push({ id: createLocalId('annotation'), ...draft })
    await persistCurrentDraft()
  }

  async function updateAnnotation(id: string, comment: string) {
    const item = annotations.value.find((annotation) => annotation.id === id)
    if (item) item.comment = comment
    await persistCurrentDraft()
  }

  async function removeAnnotation(id: string) {
    annotations.value = annotations.value.filter((annotation) => annotation.id !== id)
    await persistCurrentDraft()
  }

  async function addCorrection(draft: CorrectionDraft) {
    if (draft.correctedText === draft.originalText) {
      corrections.value = corrections.value.filter((correction) => correction.paragraphIndex !== draft.paragraphIndex)
    } else {
      corrections.value = [
        ...corrections.value.filter((correction) => correction.paragraphIndex !== draft.paragraphIndex),
        { id: createLocalId('correction'), ...draft },
      ]
    }
    await persistCurrentDraft()
  }

  async function removeCorrection(id: string) {
    corrections.value = corrections.value.filter((correction) => correction.id !== id)
    await persistCurrentDraft()
  }

  async function clearFeedback() {
    annotations.value = []
    corrections.value = []
    await persistCurrentDraft()
  }

  async function submitRevision(projectId: string, chapterIndex: number): Promise<ChapterRevision> {
    submitting.value = true
    error.value = null
    try {
      let revision = activeRevision.value
      if (!revision) {
        revision = await api.submitRevision(projectId, {
          chapter_index: chapterIndex,
          ...buildDraftPayload(),
        })
      } else {
        revision = await api.updateRevisionDraft(projectId, chapterIndex, buildDraftPayload())
        if (!revision) throw new Error('revision feedback cannot be empty')
        revision = await api.submitRevisionDraft(projectId, revision.id)
      }
      applyRevisionFeedback(revision)
      return revision
    } catch (err) {
      error.value = toErrorMessage(err)
      throw err
    } finally {
      submitting.value = false
    }
  }

  function reset() {
    chapter.value = null
    selectedProjectId.value = null
    selectedChapterIndex.value = null
    activeRevision.value = null
    annotations.value = []
    corrections.value = []
    loading.value = false
    submitting.value = false
    error.value = null
  }

  return {
    chapter,
    selectedProjectId,
    selectedChapterIndex,
    activeRevision,
    annotations,
    corrections,
    loading,
    submitting,
    error,
    paragraphs,
    hasPendingFeedback,
    loadChapter,
    addAnnotation,
    updateAnnotation,
    removeAnnotation,
    addCorrection,
    removeCorrection,
    clearFeedback,
    submitRevision,
    reset,
  }
})
