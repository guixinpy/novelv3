import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { api } from '../api/client'
import type { ChapterContent, ChapterRevision } from '../api/types'

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

export const useManuscriptStore = defineStore('manuscript', () => {
  const chapter = ref<ChapterContent | null>(null)
  const selectedChapterIndex = ref<number | null>(null)
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

  async function loadChapter(projectId: string, chapterIndex: number) {
    loading.value = true
    error.value = null
    try {
      chapter.value = await api.getChapter(projectId, chapterIndex)
      selectedChapterIndex.value = chapterIndex
      annotations.value = []
      corrections.value = []
    } catch (err) {
      error.value = toErrorMessage(err)
    } finally {
      loading.value = false
    }
  }

  function addAnnotation(draft: AnnotationDraft) {
    annotations.value.push({ id: createLocalId('annotation'), ...draft })
  }

  function updateAnnotation(id: string, comment: string) {
    const item = annotations.value.find((annotation) => annotation.id === id)
    if (item) item.comment = comment
  }

  function removeAnnotation(id: string) {
    annotations.value = annotations.value.filter((annotation) => annotation.id !== id)
  }

  function addCorrection(draft: CorrectionDraft) {
    corrections.value = [
      ...corrections.value.filter((correction) => correction.paragraphIndex !== draft.paragraphIndex),
      { id: createLocalId('correction'), ...draft },
    ]
  }

  function removeCorrection(id: string) {
    corrections.value = corrections.value.filter((correction) => correction.id !== id)
  }

  function clearFeedback() {
    annotations.value = []
    corrections.value = []
  }

  async function submitRevision(projectId: string, chapterIndex: number): Promise<ChapterRevision> {
    submitting.value = true
    error.value = null
    try {
      const revision = await api.submitRevision(projectId, {
        chapter_index: chapterIndex,
        annotations: annotations.value.map((item) => ({
          paragraph_index: item.paragraphIndex,
          start_offset: item.startOffset,
          end_offset: item.endOffset,
          selected_text: item.selectedText,
          comment: item.comment,
        })),
        corrections: corrections.value.map((item) => ({
          paragraph_index: item.paragraphIndex,
          original_text: item.originalText,
          corrected_text: item.correctedText,
        })),
      })
      clearFeedback()
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
    selectedChapterIndex.value = null
    clearFeedback()
    loading.value = false
    submitting.value = false
    error.value = null
  }

  return {
    chapter,
    selectedChapterIndex,
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
