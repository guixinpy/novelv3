// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import NarrativeWorkbench from './NarrativeWorkbench.vue'
import type { AthenaEvolutionPlan, ChapterSummary } from '../../api/types'

const plan = {
  outline: {
    id: 'outline-1',
    status: 'generated',
    total_chapters: 2,
    chapters: [
      {
        chapter_index: 1,
        title: '异常信号',
        summary: '潮汐门出现异常读数。',
        scenes: ['主控室读数', '档案室文件'],
        characters: ['林深', '老周'],
        purpose: '引入核心谜团',
      },
    ],
    plotlines: [],
  },
  storyline: {
    id: 'storyline-1',
    status: 'generated',
    plotlines: [
      {
        name: '主线：潮汐根源',
        type: 'main',
        milestones: [
          { chapter_index: 1, title: '发现异常', summary: '读数指向旧计划。' },
        ],
      },
    ],
    foreshadowing: [
      {
        hint: '普罗米修斯-意识锚点文件',
        planted_chapter: 1,
        resolved_chapter: 5,
        status: 'resolved',
      },
    ],
  },
} as unknown as AthenaEvolutionPlan

const chapters: ChapterSummary[] = [
  { id: 'chapter-1', chapter_index: 1, title: '异常信号', word_count: 1200, status: 'draft' },
]

describe('NarrativeWorkbench', () => {
  it('shows loading state before narrative plan data resolves', () => {
    const wrapper = mount(NarrativeWorkbench, {
      props: {
        plan: null,
        chapters,
        view: 'storyline',
        loading: true,
      },
    })

    expect(wrapper.text()).toContain('正在读取叙事规划')
    expect(wrapper.text()).not.toContain('尚未生成叙事规划')
  })

  it('renders storyline milestones', () => {
    const wrapper = mount(NarrativeWorkbench, { props: { plan, chapters, view: 'storyline' } })

    expect(wrapper.text()).toContain('主线：潮汐根源')
    expect(wrapper.text()).toContain('第1章')
    expect(wrapper.text()).toContain('发现异常')
  })

  it('renders storyline as a collapsible tree', async () => {
    const wrapper = mount(NarrativeWorkbench, { props: { plan, chapters, view: 'storyline' } })

    expect(wrapper.find('[data-testid="storyline-tree"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="storyline-branch"]').exists()).toBe(true)
    expect(wrapper.get('[data-testid="storyline-toggle"]').attributes('aria-expanded')).toBe('true')
    expect(wrapper.text()).toContain('发现异常')

    await wrapper.get('[data-testid="storyline-toggle"]').trigger('click')

    expect(wrapper.get('[data-testid="storyline-toggle"]').attributes('aria-expanded')).toBe('false')
    expect(wrapper.text()).not.toContain('发现异常')
  })

  it('accepts chapter field and avoids duplicate milestone copy', () => {
    const wrapper = mount(NarrativeWorkbench, {
      props: {
        plan: {
          storyline: {
            plotlines: [
              {
                name: '副线',
                type: 'subplot',
                milestones: [
                  { chapter: 5, event: '第一次看到灯塔' },
                ],
              },
            ],
          },
        } as unknown as AthenaEvolutionPlan,
        chapters,
        view: 'storyline',
      },
    })

    expect(wrapper.text()).toContain('第5章')
    expect(wrapper.findAll('.narrative-workbench__milestone p')).toHaveLength(0)
  })

  it('renders chapter planning against actual chapter status', () => {
    const wrapper = mount(NarrativeWorkbench, { props: { plan, chapters, view: 'chapters' } })

    expect(wrapper.text()).toContain('异常信号')
    expect(wrapper.text()).toContain('草稿')
    expect(wrapper.text()).toContain('引入核心谜团')
  })

  it('filters chapters and supports quick jump selection', async () => {
    const wrapper = mount(NarrativeWorkbench, {
      props: {
        plan: {
          outline: {
            chapters: [
              { chapter_index: 1, title: '雾锁灯塔', summary: '灯塔区集体失忆。' },
              { chapter_index: 2, title: '黑市交易', summary: '记忆黑市浮出水面。' },
            ],
          },
        } as unknown as AthenaEvolutionPlan,
        chapters: [
          { id: 'chapter-1', chapter_index: 1, title: '雾锁灯塔', word_count: 1200, status: 'draft' },
          { id: 'chapter-2', chapter_index: 2, title: '黑市交易', word_count: 1800, status: 'generated' },
        ],
        view: 'chapters',
      },
    })

    await wrapper.get('[data-testid="chapter-search"]').setValue('黑市')

    expect(wrapper.find('[data-testid="chapter-2"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="chapter-1"]').exists()).toBe(false)

    await wrapper.get('[data-testid="chapter-jump"]').setValue('1')

    expect(wrapper.text()).toContain('雾锁灯塔')
    expect(wrapper.get('[data-testid="chapter-1"]').classes()).toContain('narrative-workbench__chapter--active')
  })

  it('renders foreshadowing lifecycle', () => {
    const wrapper = mount(NarrativeWorkbench, { props: { plan, chapters, view: 'foreshadowing' } })

    expect(wrapper.text()).toContain('已回收')
    expect(wrapper.text()).toContain('普罗米修斯-意识锚点文件')
  })
})
