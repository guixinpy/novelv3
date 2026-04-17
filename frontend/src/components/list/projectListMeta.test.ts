import { describe, expect, it } from 'vitest'
import {
  buildProjectInsight,
  buildProjectPortfolioSummary,
  pickFocusProject,
} from './projectListMeta'
import { normalizeCreateProjectResult } from './projectMatrixHeroSubmit'

function makeProject(overrides: Record<string, unknown> = {}) {
  return {
    id: 'project-1',
    name: '雾港档案',
    description: '',
    genre: '悬疑',
    target_word_count: 120000,
    current_word_count: 0,
    style: '',
    complexity: 3,
    status: 'draft',
    current_phase: 'setup',
    ai_model: 'deepseek-chat',
    language: 'zh-CN',
    created_at: '2026-04-17T08:00:00Z',
    updated_at: '2026-04-17T10:00:00Z',
    ...overrides,
  }
}

describe('project list meta', () => {
  it('setup 阶段会提示先补齐世界设定', () => {
    const insight = buildProjectInsight(makeProject())

    expect(insight.phaseLabel).toBe('世界设定')
    expect(insight.nextStepLabel).toBe('补齐设定，再进入故事线')
    expect(insight.readinessTone).toBe('warming')
  })

  it('写作阶段会按目标字数给出正文推进建议', () => {
    const insight = buildProjectInsight(
      makeProject({
        current_phase: 'outline',
        status: 'writing',
        current_word_count: 56000,
        target_word_count: 100000,
      }),
    )

    expect(insight.phaseLabel).toBe('正文推进')
    expect(insight.nextStepLabel).toBe('继续推进正文，准备下一章')
    expect(insight.progressLabel).toBe('56000 / 100000 字')
    expect(insight.progressValue).toBe(56)
  })

  it('焦点项目优先选择接近完成且最近活跃的项目', () => {
    const setupProject = makeProject({
      id: 'setup',
      name: '旧街见闻',
      current_phase: 'setup',
      updated_at: '2026-04-17T11:00:00Z',
    })
    const outlineProject = makeProject({
      id: 'outline',
      name: '灰塔遗书',
      current_phase: 'outline',
      updated_at: '2026-04-17T10:30:00Z',
    })
    const writingProject = makeProject({
      id: 'writing',
      name: '星坠海沟',
      current_phase: 'outline',
      status: 'writing',
      current_word_count: 42000,
      target_word_count: 70000,
      updated_at: '2026-04-17T10:45:00Z',
    })

    expect(pickFocusProject([setupProject, outlineProject, writingProject])?.id).toBe('writing')
  })

  it('组合概况会统计活跃项目数和待推进项目数', () => {
    const summary = buildProjectPortfolioSummary([
      makeProject({ id: 'a', status: 'draft', current_phase: 'setup' }),
      makeProject({ id: 'b', current_phase: 'storyline', updated_at: '2026-04-16T10:00:00Z' }),
      makeProject({ id: 'c', status: 'writing', current_phase: 'outline', current_word_count: 30000 }),
    ])

    expect(summary.totalProjects).toBe(3)
    expect(summary.activeProjects).toBe(3)
    expect(summary.writingProjects).toBe(1)
    expect(summary.totalWords).toBe(30000)
    expect(summary.pendingLabel).toBe('2 个项目待推进')
  })

  it('空矩阵时返回专用概况文案', () => {
    const summary = buildProjectPortfolioSummary([])

    expect(summary.totalProjects).toBe(0)
    expect(summary.pendingLabel).toBe('还没有项目，先创建一个进入创作链路')
  })

  it('只有父层确认创建成功后才算创建成功', async () => {
    await expect(normalizeCreateProjectResult(async () => true, { name: '雾港档案', genre: '悬疑' })).resolves.toBe(true)
    await expect(normalizeCreateProjectResult(async () => false, { name: '雾港档案', genre: '悬疑' })).resolves.toBe(false)
    await expect(normalizeCreateProjectResult(async () => {
      throw new Error('boom')
    }, { name: '雾港档案', genre: '悬疑' })).resolves.toBe(false)
  })
})
