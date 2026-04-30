// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import RelationTable from './RelationTable.vue'

describe('RelationTable', () => {
  it('renders relation source and target refs from the Athena ontology API', () => {
    const wrapper = mount(RelationTable, {
      props: {
        relations: [
          {
            id: 'rel.hero.tower',
            source_ref: 'char.hero',
            target_ref: 'loc.tower',
            relation_type: 'located_at',
          },
        ],
      },
    })

    expect(wrapper.text()).toContain('char.hero')
    expect(wrapper.text()).toContain('loc.tower')
    expect(wrapper.text()).toContain('located_at')
  })
})
