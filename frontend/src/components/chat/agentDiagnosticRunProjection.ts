import type { ActionResultView } from '../../api/types'

export const DIAGNOSTIC_AGENT_RUN_ACTION_TYPES = [
  'inspect_agent_trace_audit',
  'inspect_agent_job_projection',
  'inspect_agent_health_projection',
  'inspect_agent_command_contracts',
  'inspect_agent_control_plane_readiness',
  'inspect_agent_memory_route',
  'inspect_agent_memory_tree',
  'inspect_agent_knowledge_base_route',
] as const

export type DiagnosticAgentRunActionType = typeof DIAGNOSTIC_AGENT_RUN_ACTION_TYPES[number]

export interface DiagnosticAgentRunActionDescriptor {
  type: DiagnosticAgentRunActionType
  buildView: (actionResult: Record<string, unknown>, status: string) => ActionResultView
}

export const DIAGNOSTIC_AGENT_RUN_ACTION_DESCRIPTORS: Record<DiagnosticAgentRunActionType, DiagnosticAgentRunActionDescriptor> = {
  inspect_agent_trace_audit: {
    type: 'inspect_agent_trace_audit',
    buildView: buildTraceAuditActionResultView,
  },
  inspect_agent_job_projection: {
    type: 'inspect_agent_job_projection',
    buildView: buildJobProjectionActionResultView,
  },
  inspect_agent_health_projection: {
    type: 'inspect_agent_health_projection',
    buildView: buildAgentHealthProjectionActionResultView,
  },
  inspect_agent_command_contracts: {
    type: 'inspect_agent_command_contracts',
    buildView: buildCommandContractDiagnosticsActionResultView,
  },
  inspect_agent_control_plane_readiness: {
    type: 'inspect_agent_control_plane_readiness',
    buildView: buildControlPlaneReadinessActionResultView,
  },
  inspect_agent_memory_route: {
    type: 'inspect_agent_memory_route',
    buildView: buildMemoryRouteActionResultView,
  },
  inspect_agent_memory_tree: {
    type: 'inspect_agent_memory_tree',
    buildView: buildMemoryTreeActionResultView,
  },
  inspect_agent_knowledge_base_route: {
    type: 'inspect_agent_knowledge_base_route',
    buildView: buildKnowledgeBaseRouteActionResultView,
  },
}

function buildTraceAuditActionResultView(actionResult: Record<string, unknown>, status: string): ActionResultView {
  const detailItems = traceAuditDetailItems(recordValue(actionResult.data))
  return {
    type: 'inspect_agent_trace_audit',
    status,
    label: traceAuditLabel(status),
    variant: statusVariant(status),
    ...(detailItems.length ? { detail_items: detailItems } : {}),
  }
}

function buildJobProjectionActionResultView(actionResult: Record<string, unknown>, status: string): ActionResultView {
  const detailItems = jobProjectionDetailItems(recordValue(actionResult.data))
  return {
    type: 'inspect_agent_job_projection',
    status,
    label: jobProjectionLabel(status),
    variant: statusVariant(status),
    ...(detailItems.length ? { detail_items: detailItems } : {}),
  }
}

function buildAgentHealthProjectionActionResultView(actionResult: Record<string, unknown>, status: string): ActionResultView {
  const detailItems = agentHealthProjectionDetailItems(recordValue(actionResult.data))
  return {
    type: 'inspect_agent_health_projection',
    status,
    label: agentHealthProjectionLabel(status),
    variant: statusVariant(status),
    ...(detailItems.length ? { detail_items: detailItems } : {}),
  }
}

function buildCommandContractDiagnosticsActionResultView(actionResult: Record<string, unknown>, status: string): ActionResultView {
  const detailItems = commandContractDiagnosticsDetailItems(recordValue(actionResult.data))
  return {
    type: 'inspect_agent_command_contracts',
    status,
    label: commandContractDiagnosticsLabel(status),
    variant: statusVariant(status),
    ...(detailItems.length ? { detail_items: detailItems } : {}),
  }
}

function buildControlPlaneReadinessActionResultView(actionResult: Record<string, unknown>, status: string): ActionResultView {
  const detailItems = controlPlaneReadinessDiagnosticsDetailItems(recordValue(actionResult.data))
  return {
    type: 'inspect_agent_control_plane_readiness',
    status,
    label: controlPlaneReadinessDiagnosticsLabel(status),
    variant: statusVariant(status),
    ...(detailItems.length ? { detail_items: detailItems } : {}),
  }
}

function buildMemoryRouteActionResultView(actionResult: Record<string, unknown>, status: string): ActionResultView {
  const detailItems = memoryRouteDetailItems(recordValue(actionResult.data))
  return {
    type: 'inspect_agent_memory_route',
    status,
    label: memoryRouteLabel(status),
    variant: statusVariant(status),
    ...(detailItems.length ? { detail_items: detailItems } : {}),
  }
}

function buildMemoryTreeActionResultView(actionResult: Record<string, unknown>, status: string): ActionResultView {
  const detailItems = memoryTreeDetailItems(recordValue(actionResult.data))
  return {
    type: 'inspect_agent_memory_tree',
    status,
    label: memoryTreeLabel(status),
    variant: statusVariant(status),
    ...(detailItems.length ? { detail_items: detailItems } : {}),
  }
}

function buildKnowledgeBaseRouteActionResultView(actionResult: Record<string, unknown>, status: string): ActionResultView {
  const detailItems = knowledgeBaseRouteDetailItems(recordValue(actionResult.data))
  return {
    type: 'inspect_agent_knowledge_base_route',
    status,
    label: knowledgeBaseRouteLabel(status),
    variant: statusVariant(status),
    ...(detailItems.length ? { detail_items: detailItems } : {}),
  }
}

function traceAuditLabel(status: string) {
  if (status === 'success' || status === 'completed') return 'Trace 审计已生成'
  if (status === 'failed') return 'Trace 审计失败'
  if (status === 'running') return 'Trace 审计中'
  return `Trace 审计: ${status || '未知状态'}`
}

function jobProjectionLabel(status: string) {
  if (status === 'success' || status === 'completed') return '任务队列投影已生成'
  if (status === 'failed') return '任务队列投影失败'
  if (status === 'running') return '任务队列投影中'
  return `任务队列投影: ${status || '未知状态'}`
}

function agentHealthProjectionLabel(status: string) {
  if (status === 'success' || status === 'completed') return 'Agent 健康投影已生成'
  if (status === 'failed') return 'Agent 健康投影失败'
  if (status === 'running') return 'Agent 健康投影中'
  return `Agent 健康投影: ${status || '未知状态'}`
}

function commandContractDiagnosticsLabel(status: string) {
  if (status === 'success' || status === 'completed') return '命令契约诊断已生成'
  if (status === 'failed') return '命令契约诊断失败'
  if (status === 'running') return '命令契约诊断中'
  return `命令契约诊断: ${status || '未知状态'}`
}

function controlPlaneReadinessDiagnosticsLabel(status: string) {
  if (status === 'success' || status === 'completed') return '控制平面诊断已生成'
  if (status === 'failed') return '控制平面诊断失败'
  if (status === 'running') return '控制平面诊断中'
  return `控制平面诊断: ${status || '未知状态'}`
}

function memoryRouteLabel(status: string) {
  if (status === 'success' || status === 'completed') return '记忆路由诊断已生成'
  if (status === 'failed') return '记忆路由诊断失败'
  if (status === 'running') return '记忆路由诊断中'
  return `记忆路由诊断: ${status || '未知状态'}`
}

function memoryTreeLabel(status: string) {
  if (status === 'success' || status === 'completed') return '记忆树投影已生成'
  if (status === 'failed') return '记忆树投影失败'
  if (status === 'running') return '记忆树投影中'
  return `记忆树投影: ${status || '未知状态'}`
}

function knowledgeBaseRouteLabel(status: string) {
  if (status === 'success' || status === 'completed') return '知识库路由诊断已生成'
  if (status === 'failed') return '知识库路由诊断失败'
  if (status === 'running') return '知识库路由诊断中'
  return `知识库路由诊断: ${status || '未知状态'}`
}

function traceAuditDetailItems(data: Record<string, unknown>) {
  const items: Array<{ label: string; value: string }> = []
  const run = recordValue(data.run)
  const runStatus = stringValue(run.status)
  if (runStatus) {
    items.push({ label: '运行状态', value: runStatusLabel(runStatus) })
  }

  const audit = recordValue(data.audit)
  const stepCount = numberValue(audit.step_count)
  if (stepCount !== null) {
    items.push({ label: '工具步骤', value: `${stepCount} 个` })
  }
  const traceCount = numberValue(audit.trace_count)
  if (traceCount !== null) {
    items.push({ label: 'Trace', value: `${traceCount} 条` })
  }

  const failure = recordValue(data.failure)
  const reasonCode = stringValue(failure.reason_code)
  if (reasonCode) {
    items.push({ label: '失败原因', value: reasonCode })
  }

  const recommendedActions = Array.isArray(data.recommended_actions) ? data.recommended_actions : []
  if (recommendedActions.length) {
    items.push({ label: '建议动作', value: `${recommendedActions.length} 个` })
  }
  items.push(...commandContractDetailItems(recordValue(data.command_contracts)))
  return items
}

function jobProjectionDetailItems(data: Record<string, unknown>) {
  const items: Array<{ label: string; value: string }> = []
  const queue = recordValue(data.queue)
  const depth = numberValue(queue.depth)
  if (depth !== null) {
    items.push({ label: '队列深度', value: `${depth} 个` })
  }
  const active = numberValue(queue.active)
  if (active !== null) {
    items.push({ label: '活跃任务', value: `${active} 个` })
  }

  const selectedTask = recordValue(data.selected_task)
  const taskStatus = stringValue(selectedTask.status)
  if (taskStatus) {
    items.push({ label: '任务状态', value: runStatusLabel(taskStatus) })
  }
  const progress = recordValue(selectedTask.progress)
  const nextChapterIndex = numberValue(progress.next_chapter_index)
  if (nextChapterIndex !== null) {
    items.push({ label: '下一章', value: `第${nextChapterIndex}章` })
  }
  const agentRuns = Array.isArray(selectedTask.agent_runs) ? selectedTask.agent_runs : []
  if (agentRuns.length) {
    items.push({ label: '关联运行', value: `${agentRuns.length} 个` })
  }
  items.push(...controlPlaneReadinessDetailItems(recordValue(selectedTask.control_plane_readiness)))
  items.push(...commandContractDetailItems(recordValue(selectedTask.command_contracts)))

  const recommendedTools = Array.isArray(data.recommended_tools) ? data.recommended_tools : []
  if (recommendedTools.length) {
    items.push({ label: '推荐工具', value: `${recommendedTools.length} 个` })
  }
  return items
}

function agentHealthProjectionDetailItems(data: Record<string, unknown>) {
  const items: Array<{ label: string; value: string }> = []
  const healthStatus = stringValue(data.status)
  if (healthStatus) {
    items.push({ label: '健康状态', value: agentControlPlaneStatusLabel(healthStatus) })
  }
  items.push(...controlPlaneReadinessDetailItems(recordValue(data.control_plane_readiness)))
  items.push(...commandContractDetailItems(recordValue(data.command_contracts)))

  const profilePolicy = recordValue(data.profile_policy)
  const profilePolicyStatus = stringValue(profilePolicy.status)
  if (profilePolicyStatus) {
    items.push({ label: 'Profile 策略', value: agentControlPlaneStatusLabel(profilePolicyStatus) })
  }
  const profilePolicySummary = recordValue(profilePolicy.summary)
  const profilePolicyIssueCount = numberValue(profilePolicySummary.issues)
  if (profilePolicyIssueCount !== null) {
    items.push({ label: '策略问题', value: `${profilePolicyIssueCount} 个` })
  }
  items.push(...workerRouteRegistryDetailItems(recordValue(data.agent_worker_route_registry)))

  const diagnostics = Array.isArray(data.diagnostics) ? data.diagnostics : []
  if (diagnostics.length) {
    items.push({ label: '诊断项', value: `${diagnostics.length} 个` })
  }
  const recommendedTools = Array.isArray(data.recommended_tools) ? data.recommended_tools : []
  if (recommendedTools.length) {
    items.push({ label: '推荐工具', value: `${recommendedTools.length} 个` })
  }
  return items
}

function commandContractDiagnosticsDetailItems(data: Record<string, unknown>) {
  const items = commandContractDetailItems(data)
  const recommendedTools = Array.isArray(data.recommended_next_tools) ? data.recommended_next_tools : []
  if (recommendedTools.length) {
    items.push({ label: '推荐工具', value: `${recommendedTools.length} 个` })
  }
  return items
}

function controlPlaneReadinessDiagnosticsDetailItems(data: Record<string, unknown>) {
  return controlPlaneReadinessDetailItems(data)
}

function memoryRouteDetailItems(data: Record<string, unknown>) {
  const items: Array<{ label: string; value: string }> = []
  const route = recordValue(data.route)
  const routeStatus = stringValue(route.status)
  if (routeStatus) {
    items.push({ label: '路由状态', value: routeStatusLabel(routeStatus) })
  }
  const longformMemory = recordValue(data.longform_memory)
  const chapterCount = numberValue(longformMemory.chapter_count)
  if (chapterCount !== null) {
    items.push({ label: '章节记忆', value: `${chapterCount} 章` })
  }
  const totalMemories = numberValue(longformMemory.total_memories)
  if (totalMemories !== null) {
    items.push({ label: '长篇记忆', value: `${totalMemories} 条` })
  }
  const retrieval = recordValue(data.retrieval)
  const retrievalDocuments = numberValue(retrieval.total_documents)
  if (retrievalDocuments !== null) {
    items.push({ label: '检索文档', value: `${retrievalDocuments} 个` })
  }
  items.push(...memoryProvenanceDetailItems(recordValue(data.memory_provenance)))
  items.push(...diagnosticAndRecommendationItems(data, route))
  return items
}

function memoryTreeDetailItems(data: Record<string, unknown>) {
  const items: Array<{ label: string; value: string }> = []
  const projectionStatus = stringValue(data.status)
  if (projectionStatus) {
    items.push({ label: '投影状态', value: routeStatusLabel(projectionStatus) })
  }

  const levels = Array.isArray(data.levels) ? data.levels : []
  if (levels.length) {
    items.push({ label: '层级', value: `${levels.length} 层` })
  }
  const roots = Array.isArray(data.roots) ? data.roots : []
  if (roots.length) {
    items.push({ label: '根节点', value: `${roots.length} 个` })
  }
  const nodes = Array.isArray(data.nodes) ? data.nodes : []
  if (nodes.length) {
    items.push({ label: '返回节点', value: `${nodes.length} 个` })
  }

  const summary = recordValue(data.summary)
  const volumeNodes = numberValue(summary.volume_nodes)
  if (volumeNodes !== null) {
    items.push({ label: '卷', value: `${volumeNodes} 个` })
  }
  const chapterNodes = numberValue(summary.chapter_nodes)
  if (chapterNodes !== null) {
    items.push({ label: '章节', value: `${chapterNodes} 个` })
  }
  const sceneNodes = numberValue(summary.scene_nodes)
  if (sceneNodes !== null) {
    items.push({ label: '场景', value: `${sceneNodes} 个` })
  }
  const beatNodes = numberValue(summary.beat_nodes)
  if (beatNodes !== null) {
    items.push({ label: '节拍', value: `${beatNodes} 个` })
  }

  const filters = recordValue(data.filters)
  const filterLevel = stringValue(filters.level)
  if (filterLevel) {
    items.push({ label: '筛选层级', value: memoryTreeLevelLabel(filterLevel) })
  }
  const filterNodeId = stringValue(filters.node_id)
  if (filterNodeId) {
    items.push({ label: '筛选节点', value: filterNodeId })
  }
  const filterChapterIndex = numberValue(filters.chapter_index)
  if (filterChapterIndex !== null) {
    items.push({ label: '筛选章节', value: `第${filterChapterIndex}章` })
  }
  const filterQuery = stringValue(filters.query)
  if (filterQuery) {
    items.push({ label: '查询', value: filterQuery })
  }

  const trace = recordValue(data.trace)
  const sourceTables = Array.isArray(trace.source_tables) ? trace.source_tables : []
  if (sourceTables.length) {
    items.push({ label: '来源表', value: `${sourceTables.length} 个` })
  }
  return items
}

function knowledgeBaseRouteDetailItems(data: Record<string, unknown>) {
  const items: Array<{ label: string; value: string }> = []
  const route = recordValue(data.route)
  const routeStatus = stringValue(route.status)
  if (routeStatus) {
    items.push({ label: '路由状态', value: routeStatusLabel(routeStatus) })
  }
  const authorPreferences = recordValue(data.author_preferences)
  const authorPreferenceStatus = stringValue(authorPreferences.status)
  if (authorPreferenceStatus) {
    items.push({ label: '作者偏好', value: routeStatusLabel(authorPreferenceStatus) })
  }
  const learnedRules = recordValue(data.learned_rules)
  const learnedRuleTotal = numberValue(learnedRules.total)
  if (learnedRuleTotal !== null) {
    items.push({ label: '学习规则', value: `${learnedRuleTotal} 条` })
  }
  const learnedRuleReturned = numberValue(learnedRules.returned)
  if (learnedRuleReturned !== null) {
    items.push({ label: '本次返回', value: `${learnedRuleReturned} 条` })
  }
  const knowledgeCandidates = recordValue(data.knowledge_candidates)
  const candidateTotal = numberValue(knowledgeCandidates.total)
  if (candidateTotal !== null) {
    items.push({ label: '知识候选', value: `${candidateTotal} 条` })
  }
  items.push(...memoryProvenanceDetailItems(recordValue(data.memory_provenance)))
  items.push(...diagnosticAndRecommendationItems(data, route))
  return items
}

function memoryProvenanceDetailItems(provenance: Record<string, unknown>) {
  const items: Array<{ label: string; value: string }> = []
  const status = stringValue(provenance.status)
  if (status) {
    items.push({ label: '记忆溯源', value: routeStatusLabel(status) })
  }
  const sourceCount = numberValue(provenance.source_count)
  if (sourceCount !== null) {
    items.push({ label: '来源数量', value: `${sourceCount} 个` })
  }
  return items
}

function diagnosticAndRecommendationItems(data: Record<string, unknown>, route: Record<string, unknown>) {
  const items: Array<{ label: string; value: string }> = []
  const diagnostics = Array.isArray(data.diagnostics) ? data.diagnostics : []
  if (diagnostics.length) {
    items.push({ label: '诊断项', value: `${diagnostics.length} 个` })
  }
  const recommendedTools = Array.isArray(route.recommended_tools) ? route.recommended_tools : []
  if (recommendedTools.length) {
    items.push({ label: '推荐工具', value: `${recommendedTools.length} 个` })
  }
  return items
}

function commandContractDetailItems(contracts: Record<string, unknown>) {
  const summary = recordValue(contracts.summary)
  const items: Array<{ label: string; value: string }> = []
  if (!Object.keys(summary).length) return items

  items.push({ label: '命令契约', value: '已投影' })
  const controlCommands = numberValue(summary.agent_control_commands)
  if (controlCommands !== null) {
    items.push({ label: '控制命令', value: `${controlCommands} 个` })
  }
  const gapCount = numberValue(summary.gap_count)
  if (gapCount !== null) {
    items.push({ label: '契约缺口', value: `${gapCount} 个` })
  }
  return items
}

function controlPlaneReadinessDetailItems(readiness: Record<string, unknown>) {
  const summary = recordValue(readiness.summary)
  const items: Array<{ label: string; value: string }> = []
  if (!Object.keys(summary).length) return items

  items.push({ label: '控制平面', value: agentControlPlaneStatusLabel(stringValue(readiness.status)) })
  const totalGapCount = numberValue(summary.total_gap_count)
  if (totalGapCount !== null) {
    items.push({ label: '控制面缺口', value: `${totalGapCount} 个` })
  }
  const toolGapCount = numberValue(summary.tool_gap_count)
  if (toolGapCount !== null) {
    items.push({ label: '工具缺口', value: `${toolGapCount} 个` })
  }
  const commandGapCount = numberValue(summary.command_gap_count)
  if (commandGapCount !== null) {
    items.push({ label: '命令缺口', value: `${commandGapCount} 个` })
  }
  const recommendedNextTools = Array.isArray(readiness.recommended_next_tools)
    ? readiness.recommended_next_tools
    : []
  if (recommendedNextTools.length) {
    items.push({ label: '建议检查', value: `${recommendedNextTools.length} 项` })
  }
  return items
}

function workerRouteRegistryDetailItems(registry: Record<string, unknown>) {
  const summary = recordValue(registry.summary)
  const items: Array<{ label: string; value: string }> = []
  const status = stringValue(registry.status)
  if (status) {
    items.push({ label: '路由审计', value: routeRegistryStatusLabel(status) })
  }
  const unroutedAllowedTools = numberValue(summary.unrouted_allowed_tools)
  if (unroutedAllowedTools !== null) {
    items.push({ label: '未路由工具', value: `${unroutedAllowedTools} 个` })
  }
  const issueCount = numberValue(summary.issues)
  if (issueCount !== null && issueCount > 0) {
    items.push({ label: '路由问题', value: `${issueCount} 个` })
  }
  return items
}

function agentControlPlaneStatusLabel(status: string) {
  if (status === 'ready') return '可继续编排'
  if (status === 'degraded') return '需检查'
  if (status === 'needs_attention') return '需处理'
  return status || '未知'
}

function routeRegistryStatusLabel(status: string) {
  if (status === 'passed') return '通过'
  if (status === 'needs_attention') return '需处理'
  return status || '未知'
}

function runStatusLabel(status: string) {
  if (status === 'success') return '成功'
  if (status === 'failed') return '失败'
  if (status === 'running') return '运行中'
  if (status === 'blocked') return '已阻止'
  return status
}

function routeStatusLabel(status: string) {
  if (status === 'ready') return '可用'
  if (status === 'available') return '可用'
  if (status === 'configured') return '已配置'
  if (status === 'empty') return '空'
  if (status === 'sparse') return '稀疏'
  if (status === 'degraded') return '需检查'
  if (status === 'needs_attention') return '需处理'
  if (status === 'blocked') return '已阻塞'
  return status || '未知'
}

function memoryTreeLevelLabel(level: string) {
  if (level === 'volume') return '卷'
  if (level === 'chapter') return '章节'
  if (level === 'scene') return '场景'
  if (level === 'beat') return '节拍'
  return level
}

function statusVariant(status: string) {
  if (status === 'success' || status === 'completed') return 'success'
  if (status === 'failed') return 'error'
  return 'neutral'
}

function recordValue(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : {}
}

function stringValue(value: unknown) {
  return typeof value === 'string' ? value.trim() : ''
}

function numberValue(value: unknown) {
  return typeof value === 'number' && Number.isFinite(value) ? value : null
}
