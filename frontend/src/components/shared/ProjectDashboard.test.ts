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

  it('uses backend chapter totals when only the first chapter page is loaded', () => {
    const wrapper = mount(ProjectDashboard, {
      props: {
        setup: null,
        storyline: null,
        outline: { total_chapters: 1000, chapters: [] },
        chapters: Array.from({ length: 200 }, (_, index) => ({ chapter_index: index + 1, word_count: 1000 })),
        chaptersTotal: 1000,
        totalWords: 1000000,
      },
    })

    expect(wrapper.text()).toContain('正文 1000/1000')
    expect(wrapper.text()).toContain('100%')
    expect(wrapper.find('.dashboard__stat-value').text()).toBe('1000')
  })

  it('uses storyline count metadata when bootstrap returns partial storyline arrays', () => {
    const wrapper = mount(ProjectDashboard, {
      props: {
        setup: null,
        storyline: {
          id: 'storyline-partial',
          status: 'generated',
          plotlines: [],
          foreshadowing: [],
          plotlines_count: 24,
          foreshadowing_count: 120,
        },
        outline: null,
        chapters: [],
        totalWords: 0,
      },
    })

    expect(wrapper.text()).toContain('已生成')
    expect(wrapper.text()).toContain('主线 24')
    expect(wrapper.text()).toContain('伏笔 120')
  })

  it('uses generated setup status when bootstrap returns partial setup fields', () => {
    const wrapper = mount(ProjectDashboard, {
      props: {
        setup: {
          id: 'setup-partial',
          status: 'generated',
          world_building: {},
          characters: [],
          core_concept: {},
        },
        storyline: null,
        outline: null,
        chapters: [],
        totalWords: 0,
      },
    })

    expect(wrapper.text()).toContain('已生成')
    expect(wrapper.text()).not.toContain('待完善')
  })

  it('renders persisted writing progress from workspace bootstrap state', () => {
    const wrapper = mount(ProjectDashboard, {
      props: {
        setup: null,
        storyline: null,
        outline: { total_chapters: 100, chapters: [] },
        chapters: [],
        totalWords: 0,
        writingState: {
          project_id: 'project-1',
          current_chapter: 37,
          status: 'failed',
          last_error: '模型调用超时',
        },
      },
    })

    expect(wrapper.text()).toContain('写作进度')
    expect(wrapper.text()).toContain('第37章')
    expect(wrapper.text()).toContain('需处理')
    expect(wrapper.text()).toContain('模型调用超时')
  })

  it('renders writing task generation diagnostics as a compact Chinese summary', () => {
    const wrapper = mount(ProjectDashboard, {
      props: {
        setup: null,
        storyline: null,
        outline: { total_chapters: 100, chapters: [] },
        chapters: [],
        totalWords: 0,
        writingState: {
          project_id: 'project-1',
          current_chapter: 4,
          status: 'running',
          last_error: null,
        },
        writingTaskDiagnostics: {
          word_target: {
            under_count: 2,
            within_count: 1,
            over_count: 1,
            untracked_count: 0,
            under_chapter_indexes: [1, 2],
            over_chapter_indexes: [4],
          },
          post_generation_warning_count: 1,
          post_generation_warnings: [
            {
              chapter_index: 3,
              stage: 'longform_memory_refresh',
              error_type: 'RuntimeError',
              message: 'maintenance failed',
            },
          ],
        },
      },
    })

    expect(wrapper.text()).toContain('本轮诊断')
    expect(wrapper.text()).toContain('偏短 2')
    expect(wrapper.text()).toContain('偏长 1')
    expect(wrapper.text()).toContain('维护警告 1')
    expect(wrapper.text()).toContain('偏短章节：第1章、第2章')
    expect(wrapper.text()).toContain('偏长章节：第4章')
  })

  it('renders writing task range progress while continuous writing is running', () => {
    const wrapper = mount(ProjectDashboard, {
      props: {
        setup: null,
        storyline: null,
        outline: { total_chapters: 100, chapters: [] },
        chapters: [],
        totalWords: 0,
        writingState: {
          project_id: 'project-1',
          current_chapter: 12,
          status: 'running',
          last_error: null,
        },
        writingTaskProgress: {
          chapter_range: { start: 10, end: 20 },
          next_chapter_index: 13,
          completed_count: 3,
          total_count: 11,
          can_resume: true,
        },
      },
    })

    expect(wrapper.text()).toContain('本轮进度')
    expect(wrapper.text()).toContain('3/11')
    expect(wrapper.text()).toContain('27%')
    expect(wrapper.text()).toContain('下章第13章')
  })

  it('emits writing control actions from current writing status', async () => {
    const wrapper = mount(ProjectDashboard, {
      props: {
        setup: null,
        storyline: null,
        outline: null,
        chapters: [],
        totalWords: 0,
        writingState: {
          project_id: 'project-1',
          current_chapter: 37,
          status: 'idle',
          last_error: null,
        },
      },
    })

    expect(wrapper.get('[data-testid="dashboard-writing-control"]').text()).toContain('开始')
    await wrapper.get('[data-testid="dashboard-writing-control"]').trigger('click')

    await wrapper.setProps({
      writingState: {
        project_id: 'project-1',
        current_chapter: 37,
        status: 'running',
        last_error: null,
      },
    })
    expect(wrapper.get('[data-testid="dashboard-writing-control"]').text()).toContain('暂停')
    await wrapper.get('[data-testid="dashboard-writing-control"]').trigger('click')

    await wrapper.setProps({
      writingState: {
        project_id: 'project-1',
        current_chapter: 37,
        status: 'paused',
        last_error: null,
      },
    })
    expect(wrapper.get('[data-testid="dashboard-writing-control"]').text()).toContain('继续')
    await wrapper.get('[data-testid="dashboard-writing-control"]').trigger('click')

    await wrapper.setProps({
      writingState: {
        project_id: 'project-1',
        current_chapter: 37,
        status: 'failed',
        last_error: '模型调用超时',
      },
    })
    expect(wrapper.get('[data-testid="dashboard-writing-control"]').text()).toContain('重试')
    await wrapper.get('[data-testid="dashboard-writing-control"]').trigger('click')

    expect(wrapper.emitted('writing-control')).toEqual([
      ['start'],
      ['pause'],
      ['resume'],
      ['start'],
    ])
  })

  it('shows completed writing state without restart control', async () => {
    const wrapper = mount(ProjectDashboard, {
      props: {
        setup: null,
        storyline: null,
        outline: null,
        chapters: [],
        totalWords: 0,
        writingState: {
          project_id: 'project-1',
          current_chapter: 101,
          status: 'completed',
          last_error: null,
        },
      },
    })

    const control = wrapper.get('[data-testid="dashboard-writing-control"]')

    expect(wrapper.text()).toContain('已完成')
    expect(wrapper.get('.dashboard__writing .dashboard__task-title').text()).toContain('全部章节')
    expect(wrapper.get('.dashboard__writing .dashboard__task-title').text()).not.toContain('第101章')
    expect(control.text()).toContain('已完成')
    expect((control.element as HTMLButtonElement).disabled).toBe(true)

    await control.trigger('click')
    expect(wrapper.emitted('writing-control')).toBeUndefined()
  })
})
