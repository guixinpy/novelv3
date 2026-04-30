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

  it('localizes all backend bundle states and exposes them as filters', () => {
    const wrapper = mount(WorldProposalBundleList, {
      props: {
        bundles: [
          createBundle({ id: 'bundle-partial', bundle_status: 'partially_approved', title: '部分处理' }),
          createBundle({ id: 'bundle-uncertain', bundle_status: 'uncertain', title: '不确定处理' }),
          createBundle({ id: 'bundle-rolled-back', bundle_status: 'rolled_back', title: '回滚处理' }),
          createBundle({ id: 'bundle-split', bundle_status: 'split', title: '拆分处理' }),
        ],
        selectedBundleId: null,
        total: 4,
        filters: {},
      },
    })

    expect(wrapper.text()).toContain('部分通过')
    expect(wrapper.text()).toContain('不确定')
    expect(wrapper.text()).toContain('已回滚')
    expect(wrapper.text()).toContain('已拆分')
    expect(wrapper.text()).not.toContain('partially_approved')
    expect(wrapper.text()).not.toContain('rolled_back')
    const optionLabels = wrapper.findAll('option').map((option) => option.text())
    expect(optionLabels).toEqual(expect.arrayContaining([
      '部分通过',
      '不确定',
      '已回滚',
      '已拆分',
      '编辑后通过',
    ]))
  })

  it('disables load more while another page is loading', () => {
    const wrapper = mount(WorldProposalBundleList, {
      props: {
        bundles: [createBundle()],
        selectedBundleId: null,
        total: 2,
        filters: {},
        loadingMore: true,
      },
    })

    const loadMore = wrapper.get('button.bundle-list__load-more')

    expect(loadMore.attributes('disabled')).toBeDefined()
    expect(loadMore.text()).toContain('加载中')
  })
})
