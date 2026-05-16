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

function windowedStorylinePlan(offset: number, limit: number, total: number) {
  return {
    outline: { chapters: [] },
    storyline: {
      plotlines: [
        {
          name: '主线：王朝崩塌',
          type: 'main',
          milestones: Array.from({ length: limit }, (_, index) => {
            const chapterIndex = offset + index + 1
            return {
              chapter_index: chapterIndex,
              title: `主线节点${chapterIndex}`,
            }
          }),
          milestones_total: total,
          milestones_offset: offset,
          milestones_limit: limit,
          milestones_has_more: offset + limit < total,
        },
      ],
      foreshadowing: [],
    },
  } as unknown as AthenaEvolutionPlan
}

function largeForeshadowingPlan(count: number) {
  return {
    outline: { chapters: [] },
    storyline: {
      plotlines: [],
      foreshadowing: Array.from({ length: count }, (_, index) => {
        const itemIndex = index + 1
        return {
          hint: `伏笔${itemIndex}`,
          planted_chapter: itemIndex,
          resolved_chapter: itemIndex + 10,
          status: itemIndex % 2 === 0 ? 'resolved' : 'pending',
        }
      }),
    },
  } as unknown as AthenaEvolutionPlan
}

function windowedPlanWithTotals() {
  return {
    outline: {
      chapters: Array.from({ length: 50 }, (_, index) => ({
        chapter_index: index + 101,
        title: `窗口章节${index + 101}`,
      })),
      plotlines: [],
      chapters_total: 1000,
    },
    storyline: {
      plotlines: [
        { name: '主线', type: 'main', milestones: [] },
        { name: '支线', type: 'sub', milestones: [] },
      ],
      foreshadowing: Array.from({ length: 100 }, (_, index) => ({
        hint: `窗口伏笔${index + 1}`,
        planted_chapter: index + 1,
        resolved_chapter: index + 50,
        status: 'pending',
      })),
      plotlines_total: 4,
      foreshadowing_total: 300,
    },
  } as unknown as AthenaEvolutionPlan
}

function windowedChapterPlan(offset: number, limit: number, total: number) {
  return {
    outline: {
      chapters: Array.from({ length: limit }, (_, index) => {
        const chapterIndex = offset + index + 1
        return {
          chapter_index: chapterIndex,
          title: `窗口章节${chapterIndex}`,
          summary: `第${chapterIndex}章摘要`,
        }
      }),
      chapters_total: total,
      chapters_offset: offset,
      chapters_limit: limit,
      chapters_has_more: offset + limit < total,
      plotlines: [],
    },
    storyline: null,
  } as unknown as AthenaEvolutionPlan
}

function windowedForeshadowingPlan(offset: number, limit: number, total: number) {
  return {
    outline: { chapters: [], plotlines: [] },
    storyline: {
      plotlines: [],
      foreshadowing: Array.from({ length: limit }, (_, index) => {
        const itemIndex = offset + index + 1
        return {
          hint: `窗口伏笔${itemIndex}`,
          planted_chapter: itemIndex,
          resolved_chapter: itemIndex + 10,
          status: 'pending',
        }
      }),
      foreshadowing_total: total,
      foreshadowing_offset: offset,
      foreshadowing_limit: limit,
      foreshadowing_has_more: offset + limit < total,
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

  it('windows large expanded storyline branches instead of rendering every milestone', async () => {
    const wrapper = mount(NarrativeWorkbench, {
      props: {
        plan: largeStorylinePlan(250, 0),
        chapters: [],
        view: 'storyline',
      },
    })

    expect(wrapper.findAll('.narrative-workbench__milestone')).toHaveLength(80)
    expect(wrapper.text()).toContain('当前显示 1-80 / 250 个节点')
    expect(wrapper.text()).toContain('主线节点80')
    expect(wrapper.text()).not.toContain('主线节点81')

    await wrapper.get('[data-testid="storyline-milestone-next"]').trigger('click')

    expect(wrapper.findAll('.narrative-workbench__milestone')).toHaveLength(80)
    expect(wrapper.text()).toContain('当前显示 81-160 / 250 个节点')
    expect(wrapper.findAll('.narrative-workbench__milestone')[0].text()).toContain('主线节点81')
    expect(wrapper.findAll('.narrative-workbench__milestone').some((item) => item.text() === '第1章主线节点1')).toBe(false)
  })

  it('emits milestone window requests for server-windowed storylines', async () => {
    const wrapper = mount(NarrativeWorkbench, {
      props: {
        plan: windowedStorylinePlan(80, 80, 250),
        chapters: [],
        view: 'storyline',
      },
    })

    expect(wrapper.text()).toContain('当前显示 81-160 / 250 个节点')

    await wrapper.get('[data-testid="storyline-milestone-next"]').trigger('click')
    await wrapper.get('[data-testid="storyline-milestone-prev"]').trigger('click')

    expect(wrapper.emitted('loadMilestoneWindow')).toEqual([
      [{ offset: 160, limit: 80 }],
      [{ offset: 0, limit: 80 }],
    ])
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

  it('uses narrative plan total metadata for windowed plan metrics', () => {
    const wrapper = mount(NarrativeWorkbench, {
      props: {
        plan: windowedPlanWithTotals(),
        chapters: [],
        view: 'chapters',
      },
    })
    const metricValues = wrapper.findAll('.narrative-workbench__metric strong').map((item) => item.text())

    expect(metricValues).toEqual(['1000', '4', '300'])
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

  it('emits chapter window requests for server-windowed chapter plans', async () => {
    const wrapper = mount(NarrativeWorkbench, {
      props: {
        plan: windowedChapterPlan(100, 50, 1000),
        chapters: [],
        view: 'chapters',
      },
    })

    expect(wrapper.text()).toContain('当前显示第101-150章 / 共1000章')

    await wrapper.get('[data-testid="chapter-next"]').trigger('click')
    await wrapper.get('[data-testid="chapter-prev"]').trigger('click')

    expect(wrapper.emitted('loadChapterWindow')).toEqual([
      [{ offset: 150, limit: 50 }],
      [{ offset: 50, limit: 50 }],
    ])
  })

  it('emits a direct chapter window request for distant server-windowed jumps', async () => {
    const wrapper = mount(NarrativeWorkbench, {
      props: {
        plan: windowedChapterPlan(100, 50, 1000),
        chapters: [],
        view: 'chapters',
      },
    })

    await wrapper.get('[data-testid="chapter-direct-jump"]').setValue('876')
    await wrapper.get('[data-testid="chapter-direct-jump-submit"]').trigger('click')

    expect(wrapper.emitted('loadChapterWindow')).toEqual([
      [{ offset: 875, limit: 50 }],
    ])
  })

  it('renders foreshadowing lifecycle', () => {
    const wrapper = mount(NarrativeWorkbench, { props: { plan, chapters, view: 'foreshadowing' } })

    expect(wrapper.text()).toContain('已回收')
    expect(wrapper.text()).toContain('普罗米修斯-意识锚点文件')
  })

  it('windows large foreshadowing lists instead of rendering every item', async () => {
    const wrapper = mount(NarrativeWorkbench, {
      props: {
        plan: largeForeshadowingPlan(250),
        chapters: [],
        view: 'foreshadowing',
      },
    })

    expect(wrapper.findAll('.narrative-workbench__hint')).toHaveLength(100)
    expect(wrapper.text()).toContain('当前显示 1-100 / 250 条伏笔')
    expect(wrapper.text()).toContain('伏笔100')
    expect(wrapper.text()).not.toContain('伏笔101')

    await wrapper.get('[data-testid="foreshadowing-next"]').trigger('click')

    expect(wrapper.findAll('.narrative-workbench__hint')).toHaveLength(100)
    expect(wrapper.text()).toContain('当前显示 101-200 / 250 条伏笔')
    expect(wrapper.findAll('.narrative-workbench__hint')[0].text()).toContain('伏笔101')
    expect(wrapper.findAll('.narrative-workbench__hint').some((item) => item.text() === '待回收第1章 → 第11章伏笔1')).toBe(false)
  })

  it('emits foreshadowing window requests for server-windowed foreshadowing plans', async () => {
    const wrapper = mount(NarrativeWorkbench, {
      props: {
        plan: windowedForeshadowingPlan(100, 100, 300),
        chapters: [],
        view: 'foreshadowing',
      },
    })

    expect(wrapper.text()).toContain('当前显示 101-200 / 300 条伏笔')

    await wrapper.get('[data-testid="foreshadowing-next"]').trigger('click')
    await wrapper.get('[data-testid="foreshadowing-prev"]').trigger('click')

    expect(wrapper.emitted('loadForeshadowingWindow')).toEqual([
      [{ offset: 200, limit: 100 }],
      [{ offset: 0, limit: 100 }],
    ])
  })
})
