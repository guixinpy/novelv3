import type { LocalAnnotation, LocalCorrection } from '../../stores/manuscript'

export type ParagraphSegment =
  | { type: 'text'; text: string }
  | { type: 'annotation'; text: string; annotation: LocalAnnotation }

export interface CorrectionDiff {
  prefix: string
  originalMiddle: string
  correctedMiddle: string
  suffix: string
}

export function buildParagraphSegments(text: string, annotations: LocalAnnotation[]): ParagraphSegment[] {
  const sorted = [...annotations]
    .filter((item) => item.startOffset >= 0 && item.endOffset > item.startOffset && item.startOffset < text.length)
    .sort((a, b) => a.startOffset - b.startOffset || a.endOffset - b.endOffset)

  const segments: ParagraphSegment[] = []
  let cursor = 0
  for (const annotation of sorted) {
    if (annotation.startOffset < cursor) continue
    const start = Math.min(annotation.startOffset, text.length)
    const end = Math.min(annotation.endOffset, text.length)
    if (start > cursor) segments.push({ type: 'text', text: text.slice(cursor, start) })
    segments.push({ type: 'annotation', text: text.slice(start, end), annotation })
    cursor = end
  }
  if (cursor < text.length) segments.push({ type: 'text', text: text.slice(cursor) })
  return segments.length ? segments : [{ type: 'text', text }]
}

export function diffCorrection(correction: LocalCorrection): CorrectionDiff {
  const { originalText, correctedText } = correction
  let prefixLength = 0
  const maxPrefixLength = Math.min(originalText.length, correctedText.length)
  while (prefixLength < maxPrefixLength && originalText[prefixLength] === correctedText[prefixLength]) {
    prefixLength += 1
  }

  let suffixLength = 0
  const maxSuffixLength = Math.min(originalText.length - prefixLength, correctedText.length - prefixLength)
  while (
    suffixLength < maxSuffixLength
    && originalText[originalText.length - 1 - suffixLength] === correctedText[correctedText.length - 1 - suffixLength]
  ) {
    suffixLength += 1
  }

  const originalEnd = suffixLength ? originalText.length - suffixLength : originalText.length
  const correctedEnd = suffixLength ? correctedText.length - suffixLength : correctedText.length
  return {
    prefix: originalText.slice(0, prefixLength),
    originalMiddle: originalText.slice(prefixLength, originalEnd),
    correctedMiddle: correctedText.slice(prefixLength, correctedEnd),
    suffix: originalText.slice(originalEnd),
  }
}
