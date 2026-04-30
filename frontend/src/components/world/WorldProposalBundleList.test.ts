// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import WorldProposalBundleList from './WorldProposalBundleList.vue'
import type { ProposalBundle } from '../../api/types'

describe('WorldProposalBundleList', () => {
  function createBundle(overrides: Partial<ProposalBundle> = {}): ProposalBundle {
    return {
      id: 'bundle-1',
      project_id: 'project-1',
      project_profile_version_id: 'profile-1',
      profile_version: 1,
      parent_bundle_id: null,
      bundle_status: 'pending',
      title: '第1章事实候选',
      summary: '',
      created_by: 'athena.chapter_analyzer',
      created_at: '2026-04-29T00:00:00Z',
      updated_at: '2026-04-29T00:00:00Z',
      ...overrides,
    }
  }

  it('uses localized labels for proposal filters and statuses', () => {
    const wrapper = mount(WorldProposalBundleList, {
      props: {
        bundles: [createBundle()],
        selectedBundleId: null,
        total: 1,
        filters: {},
      },
    })

    expect(wrapper.text()).toContain('提案包')
    expect(wrapper.text()).toContain('待审')
    expect(wrapper.text()).not.toContain('Proposal Bundles')
    expect(wrapper.text()).not.toContain('pending')
  })
})
