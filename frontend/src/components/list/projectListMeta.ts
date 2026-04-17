export type ProjectListProject = {
  id: string
  name: string
  description?: string
  genre?: string
  target_word_count?: number
  current_word_count?: number
  status?: string
  current_phase?: string
  created_at?: string
  updated_at?: string
}

export type ProjectInsight = {
  phaseLabel: string
  phaseCaption: string
  nextStepLabel: string
  nextStepDetail: string
  readinessTone: 'warming' | 'ready' | 'urgent'
  progressValue: number
  progressLabel: string
  urgencyScore: number
}

export type ProjectPortfolioSummary = {
  totalProjects: number
  activeProjects: number
  writingProjects: number
  totalWords: number
  pendingProjects: number
  pendingLabel: string
}

const PHASE_PROGRESS: Record<string, number> = {
  setup: 18,
  storyline: 44,
  outline: 71,
}

function toNumber(value: number | undefined) {
  return Number.isFinite(value) ? Number(value) : 0
}

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value))
}

function hoursSince(updatedAt?: string) {
  if (!updatedAt) return 72
  const timestamp = new Date(updatedAt).getTime()
  if (Number.isNaN(timestamp)) return 72
  const diff = Date.now() - timestamp
  return clamp(diff / (1000 * 60 * 60), 0, 72)
}

export function buildProjectInsight(project: ProjectListProject): ProjectInsight {
  const phase = project.current_phase || 'setup'
  const status = project.status || 'draft'
  const currentWords = toNumber(project.current_word_count)
  const targetWords = toNumber(project.target_word_count)
  const isWriting = status === 'writing'

  if (isWriting) {
    const ratio = targetWords > 0 ? clamp(Math.round((currentWords / targetWords) * 100), 0, 100) : 76
    return {
      phaseLabel: '正文推进',
      phaseCaption: currentWords > 0 ? '已经进入正文生产区' : '正文刚起笔，继续往前推',
      nextStepLabel: '继续推进正文，准备下一章',
      nextStepDetail: '优先保持写作连续性，再回头补修设定或大纲细节。',
      readinessTone: ratio >= 65 ? 'urgent' : 'ready',
      progressValue: ratio,
      progressLabel: targetWords > 0 ? `${currentWords} / ${targetWords} 字` : `${currentWords} 字`,
      urgencyScore: 96 + ratio / 20,
    }
  }

  if (phase === 'outline') {
    return {
      phaseLabel: '章节大纲',
      phaseCaption: '结构已成形，离正文只差最后一推',
      nextStepLabel: '确认大纲，进入正文写作',
      nextStepDetail: '把章节节奏和关键转折钉牢，打开工作区即可开写。',
      readinessTone: 'urgent',
      progressValue: PHASE_PROGRESS.outline,
      progressLabel: '大纲阶段',
      urgencyScore: 78,
    }
  }

  if (phase === 'storyline') {
    return {
      phaseLabel: '故事脉络',
      phaseCaption: '冲突和走向正在收束成主线',
      nextStepLabel: '确认故事线，准备展开大纲',
      nextStepDetail: '把人物目标、主冲突和关键转折串起来，再展开章节层级。',
      readinessTone: 'ready',
      progressValue: PHASE_PROGRESS.storyline,
      progressLabel: '故事线阶段',
      urgencyScore: 58,
    }
  }

  return {
    phaseLabel: '世界设定',
    phaseCaption: '项目还在铺底，先把世界和人物立住',
    nextStepLabel: '补齐设定，再进入故事线',
    nextStepDetail: '设定越虚，后面越容易返工，先把基底夯实。',
    readinessTone: 'warming',
    progressValue: PHASE_PROGRESS.setup,
    progressLabel: '设定阶段',
    urgencyScore: 36,
  }
}

export function pickFocusProject(projects: ProjectListProject[]) {
  const rankedProjects = [...projects]
    .sort((left, right) => {
      const leftInsight = buildProjectInsight(left)
      const rightInsight = buildProjectInsight(right)
      const leftScore = leftInsight.urgencyScore - hoursSince(left.updated_at) * 0.35
      const rightScore = rightInsight.urgencyScore - hoursSince(right.updated_at) * 0.35
      if (rightScore !== leftScore) return rightScore - leftScore
      return new Date(right.updated_at || 0).getTime() - new Date(left.updated_at || 0).getTime()
    })

  return rankedProjects[0]
}

export function buildProjectPortfolioSummary(projects: ProjectListProject[]): ProjectPortfolioSummary {
  const totalProjects = projects.length
  const writingProjects = projects.filter((project) => (project.status || '') === 'writing').length
  const totalWords = projects.reduce((sum, project) => sum + toNumber(project.current_word_count), 0)
  const activeProjects = projects.filter((project) => (project.status || '') !== 'archived').length
  const pendingProjects = projects.filter((project) => (project.status || '') !== 'writing').length

  return {
    totalProjects,
    activeProjects,
    writingProjects,
    totalWords,
    pendingProjects,
    pendingLabel: pendingProjects > 0 ? `${pendingProjects} 个项目待推进` : '全部项目都在正文推进中',
  }
}
