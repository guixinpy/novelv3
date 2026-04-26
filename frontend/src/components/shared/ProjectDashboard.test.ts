// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import ProjectDashboard from './ProjectDashboard.vue'

describe('ProjectDashboard', () => {
  it('renders project overview, ai task status, and dashboard tool actions without chapter navigation', () => {
    const wrapper = mount(ProjectDashboard, {
      props: {
        setup: {
          id: 'setup-1',
          characters: [{ name: '林澈' }, { name: '许燃' }],
          world_building: { background: '火星城市', geography: '峡谷', society: '公司城', rules: '', atmosphere: '' },
          core_concept: { theme: '求生', premise: '气闸事故', hook: '', unique_selling_point: '' },
        },
        storyline: {
          id: 'storyline-1',
          plotlines: [{}, {}, {}],
          foreshadowing: [{}, {}, {}, {}, {}, {}, {}, {}],
        },
        outline: { total_chapters: 12, chapters: Array.from({ length: 12 }, (_, index) => ({ chapter_index: index + 1 })) },
        chapters: [
          { chapter_index: 1, word_count: 1200 },
          { chapter_index: 2, word_count: 1800 },
          { chapter_index: 3, word_count: 1800 },
          { chapter_index: 4, word_count: 1800 },
          { chapter_index: 5, word_count: 1800 },
          { chapter_index: 6, word_count: 1800 },
          { chapter_index: 7, word_count: 1800 },
          { chapter_index: 8, word_count: 1800 },
          { chapter_index: 9, word_count: 1800 },
          { chapter_index: 10, word_count: 1800 },
        ],
        totalWords: 55000,
        aiLoading: true,
        pendingAction: { id: 'action-1', type: 'generate_outline', description: '确认生成大纲', params: {}, requires_confirmation: true },
        latestActionLabel: '生成大纲',
        latestActionStatus: 'running',
        suggestedNextStep: '继续生成正文',
      },
    })

    expect(wrapper.text()).toContain('生产总览')
    expect(wrapper.findAll('.dashboard__stage-card')).toHaveLength(3)
    expect(wrapper.text()).toContain('角色 2')
    expect(wrapper.text()).toContain('世界观 3/5')
    expect(wrapper.text()).toContain('核心概念 2/4')
    expect(wrapper.text()).toContain('主线 3')
    expect(wrapper.text()).toContain('伏笔 8')
    expect(wrapper.text()).toContain('正文 10/12')
    expect(wrapper.text()).toContain('83%')
    expect(wrapper.text()).toContain('AI 任务')
    expect(wrapper.text()).toContain('待确认')
    expect(wrapper.text()).toContain('确认生成大纲')
    expect(wrapper.text()).toContain('Calliope')
    expect(wrapper.text()).not.toContain('查看 / 更新')
    expect(wrapper.find('.dashboard__chapter-list').exists()).toBe(false)
  })

  it('keeps production stage cards read-only and does not emit chat commands', async () => {
    const wrapper = mount(ProjectDashboard, {
      props: {
        setup: { characters: [{ name: '林澈' }], world_building: {}, core_concept: {} },
        storyline: { plotlines: [{}], foreshadowing: [] },
        outline: { total_chapters: 3, chapters: [{ chapter_index: 1 }, { chapter_index: 2 }, { chapter_index: 3 }] },
        chapters: [{ chapter_index: 1, word_count: 1200 }],
        totalWords: 1200,
      },
    })

    await wrapper.findAll('.dashboard__stage-card')[0].trigger('click')
    await wrapper.findAll('.dashboard__stage-card')[1].trigger('click')
    await wrapper.findAll('.dashboard__stage-card')[2].trigger('click')

    expect(wrapper.emitted('action')).toBeUndefined()
  })

  it('emits tool actions for Calliope, versions, and export', async () => {
    const wrapper = mount(ProjectDashboard, {
      props: {
        setup: null,
        storyline: null,
        outline: null,
        chapters: [],
        totalWords: 0,
      },
    })

    await wrapper.get('[data-testid="dashboard-tool-manuscript"]').trigger('click')
    await wrapper.get('[data-testid="dashboard-tool-versions"]').trigger('click')
    await wrapper.get('[data-testid="dashboard-tool-export"]').trigger('click')

    expect(wrapper.emitted('tool')).toEqual([['manuscript'], ['versions'], ['export']])
  })
})
