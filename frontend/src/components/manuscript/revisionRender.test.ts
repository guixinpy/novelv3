import { describe, expect, it } from 'vitest'
import { buildCorrectionRenderSegments, buildParagraphSegments, diffCorrection } from './revisionRender'
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

  it('diffCorrection treats paragraph breaks around unchanged text as structural layout', () => {
    const correction: LocalCorrection = {
      id: 'c1',
      paragraphIndex: 0,
      originalText: '地平线外，未改造的荒野',
      correctedText: '地平线外，\n\n未改\n\n造的荒野',
    }

    expect(diffCorrection(correction)).toEqual({
      prefix: '地平线外，',
      originalMiddle: '',
      correctedMiddle: '',
      suffix: '造的荒野',
      layoutMiddle: '\n\n未改\n\n',
      kind: 'paragraph_split',
    })
  })

  it('buildCorrectionRenderSegments renders unchanged split text as layout and real inserted text as correction', () => {
    const correction: LocalCorrection = {
      id: 'c1',
      paragraphIndex: 0,
      originalText: '稀薄的大气中蒸腾着红色的热浪',
      correctedText: '稀薄的\n\n大气中蒸腾\n\n着着\n\n红色的热浪',
    }

    expect(buildCorrectionRenderSegments(correction)).toEqual([
      { type: 'text', text: '稀薄的' },
      { type: 'layout', text: '\n\n大气中蒸腾\n\n着' },
      { type: 'correction', text: '着' },
      { type: 'layout', text: '\n\n' },
      { type: 'text', text: '红色的热浪' },
    ])
  })
})
