// @vitest-environment jsdom
import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import ContextSourceList from './ContextSourceList.vue'

describe('ContextSourceList', () => {
  it('renders longform retrieval source labels and explanations in Chinese', () => {
    const wrapper = mount(ContextSourceList, {
      props: {
        sources: [
          {
            source_type: 'longform_memory',
            source_id: 'memory-1',
            label: '第1-20章',
            chapter_index: 20,
            source_ref: 'memory:arc:1-20',
            title: '第一剧情弧',
            metadata: {
              memory_type: 'arc',
              explanation: {
                source_label: '长篇记忆',
                chapter_range: '第1-20章',
                reason: '用户查询触发，关键词命中',
                score: 0.87,
              },
            },
          },
        ],
      },
    })

    const text = wrapper.text()
    expect(text).toContain('长篇记忆')
    expect(text).toContain('依据：用户查询触发，关键词命中')
    expect(text).toContain('范围：第1-20章')
    expect(text).toContain('得分：0.87')
    expect(text).not.toContain('longform_memory')
    expect(text).not.toContain('"explanation"')
  })
})
