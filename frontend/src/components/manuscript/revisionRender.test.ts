import { describe, expect, it } from 'vitest'
import { buildParagraphSegments, diffCorrection } from './revisionRender'
import type { LocalAnnotation, LocalCorrection } from '../../stores/manuscript'

describe('revisionRender', () => {
  it('buildParagraphSegments renders annotation ranges inline without losing plain text', () => {
    const annotations: LocalAnnotation[] = [
      { id: 'a1', paragraphIndex: 0, startOffset: 2, endOffset: 4, selectedText: '过树', comment: '这里太平' },
    ]

    const segments = buildParagraphSegments('风吹过树林。', annotations)

    expect(segments).toEqual([
      { type: 'text', text: '风吹' },
      { type: 'annotation', text: '过树', annotation: annotations[0] },
      { type: 'text', text: '林。' },
    ])
  })

  it('buildParagraphSegments handles overlapping annotations conservatively', () => {
    const annotations: LocalAnnotation[] = [
      { id: 'a1', paragraphIndex: 0, startOffset: 0, endOffset: 2, selectedText: '风吹', comment: '一' },
      { id: 'a2', paragraphIndex: 0, startOffset: 1, endOffset: 3, selectedText: '吹过', comment: '二' },
    ]

    const segments = buildParagraphSegments('风吹过', annotations)

    expect(segments).toEqual([
      { type: 'annotation', text: '风吹', annotation: annotations[0] },
      { type: 'text', text: '过' },
    ])
  })

  it('diffCorrection returns shared prefix/suffix and changed middle', () => {
    const correction: LocalCorrection = {
      id: 'c1',
      paragraphIndex: 0,
      originalText: '她推开门，寒风凛冽。',
      correctedText: '她推开门，夜风微凉。',
    }

    expect(diffCorrection(correction)).toEqual({
      prefix: '她推开门，',
      originalMiddle: '寒风凛冽',
      correctedMiddle: '夜风微凉',
      suffix: '。',
    })
  })
})
