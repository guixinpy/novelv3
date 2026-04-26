import type { LocalAnnotation, LocalCorrection } from '../../stores/manuscript'

export type ParagraphSegment =
  | { type: 'text'; text: string }
  | { type: 'annotation'; text: string; annotation: LocalAnnotation }

export interface CorrectionDiff {
  prefix: string
  originalMiddle: string
  correctedMiddle: string
  suffix: string
  layoutMiddle?: string
  kind?: 'paragraph_split'
}

function withoutLineBreaks(text: string) {
  return text.replace(/\n/g, '')
}

export type CorrectionRenderSegment =
  | { type: 'text'; text: string }
  | { type: 'original'; text: string }
  | { type: 'correction'; text: string }
  | { type: 'layout'; text: string }

function pushCorrectionSegment(segments: CorrectionRenderSegment[], segment: CorrectionRenderSegment) {
  if (!segment.text) return
  const last = segments[segments.length - 1]
  if (last?.type === segment.type) {
    last.text += segment.text
  } else {
    segments.push(segment)
  }
}

function buildLayoutAwareMiddleSegments(originalMiddle: string, correctedMiddle: string): CorrectionRenderSegment[] {
  const segments: CorrectionRenderSegment[] = []
  let originalIndex = 0
  let correctedIndex = 0

  while (correctedIndex < correctedMiddle.length) {
    if (correctedMiddle[correctedIndex] === '\n') {
      let breakEnd = correctedIndex
      while (breakEnd < correctedMiddle.length && correctedMiddle[breakEnd] === '\n') {
        breakEnd += 1
      }
      pushCorrectionSegment(segments, { type: 'layout', text: correctedMiddle.slice(correctedIndex, breakEnd) })
      correctedIndex = breakEnd
      continue
    }

    const character = correctedMiddle[correctedIndex]
    if (originalIndex < originalMiddle.length && character === originalMiddle[originalIndex]) {
      pushCorrectionSegment(segments, { type: 'layout', text: character })
      originalIndex += 1
    } else {
      pushCorrectionSegment(segments, { type: 'correction', text: character })
    }
    correctedIndex += 1
  }

  if (originalIndex < originalMiddle.length) {
    pushCorrectionSegment(segments, { type: 'original', text: originalMiddle.slice(originalIndex) })
  }

  return segments
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
  const originalMiddle = originalText.slice(prefixLength, originalEnd)
  const correctedMiddle = correctedText.slice(prefixLength, correctedEnd)

  if (correctedMiddle.includes('\n') && withoutLineBreaks(correctedMiddle) === originalMiddle) {
    return {
      prefix: originalText.slice(0, prefixLength),
      originalMiddle: '',
      correctedMiddle: '',
      suffix: originalText.slice(originalEnd),
      layoutMiddle: correctedMiddle,
      kind: 'paragraph_split',
    }
  }

  return {
    prefix: originalText.slice(0, prefixLength),
    originalMiddle,
    correctedMiddle,
    suffix: originalText.slice(originalEnd),
  }
}

export function buildCorrectionRenderSegments(correction: LocalCorrection): CorrectionRenderSegment[] {
  const diff = diffCorrection(correction)
  const segments: CorrectionRenderSegment[] = []

  pushCorrectionSegment(segments, { type: 'text', text: diff.prefix })

  if (diff.layoutMiddle !== undefined) {
    pushCorrectionSegment(segments, { type: 'layout', text: diff.layoutMiddle })
  } else if (diff.correctedMiddle.includes('\n')) {
    buildLayoutAwareMiddleSegments(diff.originalMiddle, diff.correctedMiddle).forEach((segment) => {
      pushCorrectionSegment(segments, segment)
    })
  } else {
    pushCorrectionSegment(segments, { type: 'original', text: diff.originalMiddle })
    if (diff.originalMiddle || diff.correctedMiddle) {
      segments.push({ type: 'correction', text: diff.correctedMiddle })
    }
  }

  pushCorrectionSegment(segments, { type: 'text', text: diff.suffix })
  return segments.length ? segments : [{ type: 'text', text: correction.correctedText }]
}
