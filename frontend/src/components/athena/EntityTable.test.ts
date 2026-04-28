// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import EntityTable from './EntityTable.vue'

describe('EntityTable', () => {
  it('shows data provenance notice when provided', () => {
    const wrapper = mount(EntityTable, {
      props: {
        entityType: 'character',
        notice: 'Setup 草稿，尚未导入 world-model',
        entities: [{ id: 'setup-char-0', name: '林舟' }],
      },
    })

    expect(wrapper.text()).toContain('Setup 草稿，尚未导入 world-model')
    expect(wrapper.text()).toContain('林舟')
  })
})
