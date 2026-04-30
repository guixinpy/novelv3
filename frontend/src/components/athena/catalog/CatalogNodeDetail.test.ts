// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import CatalogNodeDetail from './CatalogNodeDetail.vue'
import type { CatalogNode } from './catalogNodeModel'

const node: CatalogNode = {
  ref: 'char.linche',
  id: 'char.linche',
  type: 'characters',
  label: '林澈',
  aliases: ['守夜人'],
  raw: {
    role_type: '主角',
    core_drives: ['查清旧案'],
    core_fears: ['记忆被潮汐吞没'],
    base_capabilities: ['读取潮痕残响'],
    hidden_truths: ['父亲失踪与潮汐门有关'],
  },
  facts: { identity: '旧灯塔守夜人' },
  presence: { location_ref: 'loc.lighthouse', presence_status: 'active' },
  relationCount: 2,
  factCount: 1,
  pendingCount: 1,
}

describe('CatalogNodeDetail', () => {
  it('renders complete layered node information', () => {
    const wrapper = mount(CatalogNodeDetail, { props: { node } })

    expect(wrapper.text()).toContain('林澈')
    expect(wrapper.text()).toContain('守夜人')
    expect(wrapper.text()).toContain('创作理解')
    expect(wrapper.text()).toContain('查清旧案')
    expect(wrapper.text()).toContain('事实账本')
    expect(wrapper.text()).toContain('identity')
    expect(wrapper.text()).toContain('待审 1')
  })
})
