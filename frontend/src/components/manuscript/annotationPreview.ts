const ANNOTATION_SELECTION_PREVIEW_LENGTH = 24

export function annotationSelectionPreview(selectedText: string) {
  const normalizedText = selectedText.trim().replace(/\s+/g, ' ')
  if (normalizedText.length <= ANNOTATION_SELECTION_PREVIEW_LENGTH) return normalizedText
  const preview = normalizedText.slice(0, ANNOTATION_SELECTION_PREVIEW_LENGTH)
  const punctuationIndex = Math.max(preview.lastIndexOf('，'), preview.lastIndexOf(','), preview.lastIndexOf('。'), preview.lastIndexOf('；'), preview.lastIndexOf(';'))
  if (punctuationIndex >= ANNOTATION_SELECTION_PREVIEW_LENGTH / 2) return `${preview.slice(0, punctuationIndex)}…`
  return `${preview}…`
}
