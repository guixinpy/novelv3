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

function largePlan(chapterCount: number) {
  return {
    outline: {
      id: 'outline-large',
      status: 'generated',
      total_chapters: chapterCount,
      chapters: Array.from({ length: chapterCount }, (_, index) => {
        const chapterIndex = index + 1
        return {
          chapter_index: chapterIndex,
          title: `长篇章节${chapterIndex}`,
          summary: `第${chapterIndex}章摘要`,
        }
      }),
      plotlines: [],
    },
    storyline: null,
  } as unknown as AthenaEvolutionPlan
}

function largeStorylinePlan(mainCount: number, subCount: number) {
  return {
    outline: { chapters: [] },
    storyline: {
      plotlines: [
        {
          name: '主线：王朝崩塌',
          type: 'main',
          milestones: Array.from({ length: mainCount }, (_, index) => ({
            chapter_index: index + 1,
            title: `主线节点${index + 1}`,
          })),
        },
        {
          name: '支线：旧城密约',
          type: 'sub',
          milestones: Array.from({ length: subCount }, (_, index) => ({
            chapter_index: index + 1,
            title: `支线节点${index + 1}`,
          })),
        },
      ],
      foreshadowing: [],
    },
  } as unknown as AthenaEvolutionPlan
}

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

  it('keeps the main branch expanded and collapses side branches by default for large storylines', () => {
    const wrapper = mount(NarrativeWorkbench, {
      props: {
        plan: largeStorylinePlan(80, 80),
        chapters: [],
        view: 'storyline',
      },
    })
    const toggles = wrapper.findAll('[data-testid="storyline-toggle"]')

    expect(toggles[0].attributes('aria-expanded')).toBe('true')
    expect(toggles[1].attributes('aria-expanded')).toBe('false')
    expect(wrapper.text()).toContain('主线节点80')
    expect(wrapper.text()).not.toContain('支线节点1')
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

    await wrapper.get('[data-testid="chapter-search"]').setValue('')
    await wrapper.get('[data-testid="chapter-jump"]').setValue('1')

    expect(wrapper.text()).toContain('雾锁灯塔')
    expect(wrapper.get('[data-testid="chapter-1"]').classes()).toContain('narrative-workbench__chapter--active')
  })

  it('renders long chapter plans through bounded windows and jumps to later chapters', async () => {
    const wrapper = mount(NarrativeWorkbench, {
      props: {
        plan: largePlan(250),
        chapters: [],
        view: 'chapters',
      },
    })

    expect(wrapper.find('[data-testid="chapter-1"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="chapter-51"]').exists()).toBe(false)

    await wrapper.get('[data-testid="chapter-volume"]').setValue('201')
    await wrapper.get('[data-testid="chapter-jump"]').setValue('240')

    expect(wrapper.find('[data-testid="chapter-240"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="chapter-1"]').exists()).toBe(false)
  })

  it('keeps common chapter searches bounded for long plans', async () => {
    const wrapper = mount(NarrativeWorkbench, {
      props: {
        plan: largePlan(250),
        chapters: [],
        view: 'chapters',
      },
    })

    await wrapper.get('[data-testid="chapter-search"]').setValue('长篇')

    expect(wrapper.findAll('[data-narrative-chapter-index]')).toHaveLength(100)
    expect(wrapper.text()).toContain('搜索结果 100/250 章')
    expect(wrapper.text()).toContain('请缩小关键词')
  })

  it('bounds chapter jump options to the active volume for long plans', async () => {
    const wrapper = mount(NarrativeWorkbench, {
      props: {
        plan: largePlan(250),
        chapters: [],
        view: 'chapters',
      },
    })

    const initialJumpOptions = wrapper.get('[data-testid="chapter-jump"]').findAll('option')
    expect(initialJumpOptions).toHaveLength(101)
    expect(wrapper.get('[data-testid="chapter-jump"]').text()).toContain('第100章')
    expect(wrapper.get('[data-testid="chapter-jump"]').text()).not.toContain('第101章')

    await wrapper.get('[data-testid="chapter-volume"]').setValue('201')

    const laterJump = wrapper.get('[data-testid="chapter-jump"]')
    expect(laterJump.findAll('option')).toHaveLength(51)
    expect(laterJump.text()).toContain('第240章')
    expect(laterJump.text()).not.toContain('第200章')
  })

  it('renders foreshadowing lifecycle', () => {
    const wrapper = mount(NarrativeWorkbench, { props: { plan, chapters, view: 'foreshadowing' } })

    expect(wrapper.text()).toContain('已回收')
    expect(wrapper.text()).toContain('普罗米修斯-意识锚点文件')
  })
})
