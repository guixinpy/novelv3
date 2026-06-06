<script setup lang="ts">
import { computed, ref } from 'vue'
import BaseModal from '../base/BaseModal.vue'
import AgentRunChapterConflictRecoveryPanel from './AgentRunChapterConflictRecoveryPanel.vue'
import AgentRunContextCompressionPanel from './AgentRunContextCompressionPanel.vue'
import AgentRunEventProjectionPanel from './AgentRunEventProjectionPanel.vue'
import AgentRunJobProjectionPanel from './AgentRunJobProjectionPanel.vue'
import AgentRunKnowledgeBaseRoutePanel from './AgentRunKnowledgeBaseRoutePanel.vue'
import AgentRunLongformContextPanel from './AgentRunLongformContextPanel.vue'
import AgentRunMemoryActivationPanel from './AgentRunMemoryActivationPanel.vue'
import AgentRunMemoryRoutePanel from './AgentRunMemoryRoutePanel.vue'
import AgentRunPostChapterMemoryPanel from './AgentRunPostChapterMemoryPanel.vue'
import AgentRunPreflightContextBudgetPanel from './AgentRunPreflightContextBudgetPanel.vue'
import AgentRunReferenceAlignmentPanel from './AgentRunReferenceAlignmentPanel.vue'
import AgentRunRetrievalContextPanel from './AgentRunRetrievalContextPanel.vue'
import AgentRunRetrievalPrefetchPanel from './AgentRunRetrievalPrefetchPanel.vue'
import AgentRunRetrievalStrategyPanel from './AgentRunRetrievalStrategyPanel.vue'
import AgentRunRetrievalStrategyQualityPanel from './AgentRunRetrievalStrategyQualityPanel.vue'
import AgentRunWorkerDispatchPanel from './AgentRunWorkerDispatchPanel.vue'
import AgentRunWorldModelRoutePanel from './AgentRunWorldModelRoutePanel.vue'
import AgentRunWriteGateCoveragePanel from './AgentRunWriteGateCoveragePanel.vue'
import type { WritingAgentRunDetail } from '../../api/types'

type PlannerPlanExecutePayload = {
  sourceRunId: string
  sourcePlanId: string
  goal: string
  tools: Array<Record<string, unknown>>
  planner: Record<string, unknown>
  approvalContractHash?: string
  approvalContract?: Record<string, unknown>
}

type PlannerContinuationAction = {
  key: string
  label: string
  payload: PlannerPlanExecutePayload
}

type MemoryTreeDrilldownAction = PlannerContinuationAction
type KnowledgeBaseCandidateRouteAction = PlannerContinuationAction

type MemoryTreeNavigationHistoryItem = {
  key: string
  label: string
}

const props = defineProps<{
  open: boolean
  loading: boolean
  error: string
  run: WritingAgentRunDetail | null
  pendingActionId?: string | null
  memoryTreeHistory?: MemoryTreeNavigationHistoryItem[]
}>()

const emit = defineEmits<{
  close: []
  refresh: []
  executeRecovery: [payload: { sourceRunId: string; planHash: string }]
  executeRecommendedFollowups: [payload: { sourceRunId: string; planHash: string }]
  executePlannerPlan: [payload: PlannerPlanExecutePayload]
  applyRouteUpgrade: [payload: {
    sourceRunId: string
    pendingActionId: string
    approvalContractHash: string
    approvalContract: Record<string, unknown>
  }]
}>()

const memoryTreeSearchQueryInput = ref('')
const steps = computed(() => props.run?.steps || [])
const runInput = computed(() => (isRecord(props.run?.input) ? props.run.input : {}))
const inputPlannerOutput = computed(() => recordValue(runInput.value.planner))
const plannerPreviewOutput = computed(() => {
  for (let index = steps.value.length - 1; index >= 0; index -= 1) {
    const step = steps.value[index]
    if (step?.tool_name !== 'plan_writing_agent_run' && step?.tool_name !== 'plan_dialog_intent_agent_run') continue
    const output = recordValue(step.output)
    const nestedPlan = recordValue(output.plan)
    return Object.keys(nestedPlan).length ? nestedPlan : output
  }
  return {}
})
const plannerSourceIsPreview = computed(() => (
  Object.keys(inputPlannerOutput.value).length === 0 && Object.keys(plannerPreviewOutput.value).length > 0
))
const plannerOutput = computed(() => (
  Object.keys(inputPlannerOutput.value).length ? inputPlannerOutput.value : plannerPreviewOutput.value
))
const nestedPlannerOutput = computed(() => recordValue(plannerOutput.value.planner))
const nestedPlanOutput = computed(() => recordValue(plannerOutput.value.plan))
const directPlannerTrace = computed(() => recordValue(plannerOutput.value.trace))
const nestedPlanTrace = computed(() => recordValue(nestedPlanOutput.value.trace))
const plannerTrace = computed(() => (
  Object.keys(directPlannerTrace.value).length ? directPlannerTrace.value : nestedPlanTrace.value
))
const plannerSummary = computed(() => (
  Object.keys(nestedPlannerOutput.value).length ? nestedPlannerOutput.value : plannerOutput.value
))
const plannerStatus = computed(() => (
  stringValue(plannerOutput.value.status) || stringValue(nestedPlanOutput.value.status)
))
const plannerIntentClass = computed(() => (
  stringValue(plannerSummary.value.intent_class) ||
  stringValue(nestedPlanOutput.value.intent_class) ||
  stringValue(plannerTrace.value.intent_class)
))
const plannerVersion = computed(() => (
  stringValue(plannerSummary.value.planner_version) ||
  stringValue(nestedPlanOutput.value.planner_version) ||
  stringValue(plannerTrace.value.planner_version)
))
const plannerChapterIndex = computed(() => (
  numberValue(plannerSummary.value.chapter_index) ??
  numberValue(nestedPlanOutput.value.chapter_index)
))
const plannerPlanId = computed(() => (
  stringValue(plannerTrace.value.plan_id) ||
  stringValue(plannerSummary.value.plan_id) ||
  stringValue(nestedPlanTrace.value.plan_id)
))
const plannerToolRequests = computed(() => {
  const direct = toolRequestList(plannerOutput.value.tools)
  if (direct.length) return direct
  const nested = toolRequestList(nestedPlanOutput.value.tools)
  return nested
})
const executionPlanTools = computed(() => {
  const inputTools = toolRequestList(runInput.value.tools)
  if (inputTools.length) return inputTools
  return plannerToolRequests.value
})
const executionPlanToolCount = computed(() => executionPlanTools.value.length)
const executionPlanExecutedCount = computed(() => (
  executionPlanToolCount.value > 0 ? Math.min(steps.value.length, executionPlanToolCount.value) : steps.value.length
))
const executionPlanCompletedCount = computed(() => (
  steps.value.filter((step) => ['success', 'completed'].includes(stringValue(step.status))).length
))
const executionPlanRunningCount = computed(() => (
  steps.value.filter((step) => stringValue(step.status) === 'running').length
))
const executionPlanNextTool = computed(() => {
  if (!executionPlanTools.value.length) return ''
  const next = executionPlanTools.value[executionPlanExecutedCount.value]
  return stringValue(next?.tool_name)
})
const executionPlanToolRows = computed(() => (
  executionPlanTools.value.map((tool, index) => {
    const step = steps.value[index]
    const status = stringValue(step?.status) || 'pending'
    return {
      key: `${stringValue(tool.tool_name) || 'tool'}:${index}`,
      toolName: stringValue(tool.tool_name),
      status,
      statusLabel: executionPlanToolStatusLabel(status),
    }
  })
))
const hasExecutionPlanProgress = computed(() => (
  executionPlanToolCount.value > 0 || steps.value.length > 0
))
const plannerSelectedTools = computed(() => {
  const traced = uniqueStrings(toolNameList(plannerTrace.value.selected_tools))
  if (traced.length) return traced
  const direct = uniqueStrings(toolNameList(plannerToolRequests.value))
  if (direct.length) return direct
  return uniqueStrings(toolNameList(plannerOutput.value.steps))
})
const plannerRiskFlags = computed(() => stringList(plannerTrace.value.risk_flags))
const plannerMissingDependencies = computed(() => dependencyList(plannerTrace.value.missing_dependencies))
const plannerApprovalContract = computed(() => {
  const direct = recordValue(plannerOutput.value.approval_contract)
  if (Object.keys(direct).length) return direct
  return recordValue(nestedPlanOutput.value.approval_contract)
})
const plannerApprovalStatus = computed(() => stringValue(plannerApprovalContract.value.status))
const plannerApprovalHash = computed(() => (
  stringValue(recordValue(plannerApprovalContract.value.approval).approval_contract_hash)
))
const plannerReferencePatterns = computed(() => {
  const traced = referencePatternList(plannerTrace.value.reference_patterns)
  if (traced.length) return traced
  const nested = referencePatternList(nestedPlanTrace.value.reference_patterns)
  if (nested.length) return nested
  for (const step of steps.value) {
    const outputTrace = recordValue(recordValue(step.output).trace)
    const patterns = referencePatternList(outputTrace.reference_patterns)
    if (patterns.length) return patterns
  }
  return []
})
const plannerReferencePatternVersion = computed(() => {
  if (plannerReferencePatterns.value.length === 0) return ''
  if (stringValue(plannerTrace.value.reference_pattern_version)) return stringValue(plannerTrace.value.reference_pattern_version)
  if (stringValue(nestedPlanTrace.value.reference_pattern_version)) return stringValue(nestedPlanTrace.value.reference_pattern_version)
  for (const step of steps.value) {
    const outputTrace = recordValue(recordValue(step.output).trace)
    const version = stringValue(outputTrace.reference_pattern_version)
    if (version) return version
  }
  return ''
})
const hasPlannerProjection = computed(() => Boolean(
  Object.keys(plannerOutput.value).length &&
  (
    plannerStatus.value ||
    plannerIntentClass.value ||
    plannerVersion.value ||
    plannerSelectedTools.value.length ||
    plannerApprovalStatus.value ||
    plannerRiskFlags.value.length ||
    plannerMissingDependencies.value.length ||
    plannerReferencePatterns.value.length
  ),
))
const plannerExecutePayload = computed<PlannerPlanExecutePayload | null>(() => {
  if (!plannerSourceIsPreview.value || props.run?.status !== 'success') return null
  const approvalReady = (
    plannerApprovalStatus.value === 'requires_confirmation' &&
    Boolean(plannerApprovalHash.value) &&
    Object.keys(plannerApprovalContract.value).length > 0
  )
  if (plannerApprovalStatus.value !== 'not_required' && !approvalReady) return null
  if (!props.run?.id || !plannerPlanId.value || !plannerToolRequests.value.length) return null
  return {
    sourceRunId: props.run.id,
    sourcePlanId: plannerPlanId.value,
    goal: `执行规划工具链：${plannerIntentLabel(plannerIntentClass.value)}`,
    tools: plannerToolRequests.value,
    planner: plannerOutput.value,
    ...(approvalReady
      ? {
          approvalContractHash: plannerApprovalHash.value,
          approvalContract: plannerApprovalContract.value,
        }
      : {}),
  }
})
const agentProfileDefinition = computed(() => recordValue(props.run?.agent_profile_definition))
const agentProfileScope = computed(() => recordValue(props.run?.agent_profile_scope))
const agentToolDiscovery = computed(() => recordValue(props.run?.agent_tool_discovery))
const agentProfilePolicyAudit = computed(() => recordValue(props.run?.agent_profile_policy_audit))
const agentCommandContracts = computed(() => recordValue(props.run?.agent_command_contracts))
const agentCommandContractSummary = computed(() => recordValue(agentCommandContracts.value.summary))
const hasAgentCommandContracts = computed(() => Object.keys(agentCommandContractSummary.value).length > 0)
const agentControlCommandCount = computed(() => numberValue(agentCommandContractSummary.value.agent_control_commands))
const agentCommandContractGapCount = computed(() => numberValue(agentCommandContractSummary.value.gap_count))
const agentControlPlaneReadiness = computed(() => recordValue(props.run?.agent_control_plane_readiness))
const agentControlPlaneSummary = computed(() => recordValue(agentControlPlaneReadiness.value.summary))
const hasAgentControlPlaneReadiness = computed(() => Object.keys(agentControlPlaneSummary.value).length > 0)
const agentControlPlaneStatus = computed(() => stringValue(agentControlPlaneReadiness.value.status))
const agentControlPlaneTotalGapCount = computed(() => numberValue(agentControlPlaneSummary.value.total_gap_count))
const agentControlPlaneToolGapCount = computed(() => numberValue(agentControlPlaneSummary.value.tool_gap_count))
const agentControlPlaneCommandGapCount = computed(() => numberValue(agentControlPlaneSummary.value.command_gap_count))
const agentControlPlaneRecommendedCheckCount = computed(() => (
  Array.isArray(agentControlPlaneReadiness.value.recommended_next_tools)
    ? agentControlPlaneReadiness.value.recommended_next_tools.length
    : 0
))
const agentWorkerRouteRegistry = computed(() => recordValue(props.run?.agent_worker_route_registry))
const agentWorkerRouteRegistrySummary = computed(() => recordValue(agentWorkerRouteRegistry.value.summary))
const agentWorkerRouteRegistryStatus = computed(() => stringValue(agentWorkerRouteRegistry.value.status))
const agentWorkerRouteUnroutedToolCount = computed(() => (
  numberValue(agentWorkerRouteRegistrySummary.value.unrouted_allowed_tools)
))
const agentWorkerRouteIssueCount = computed(() => numberValue(agentWorkerRouteRegistrySummary.value.issues))
const agentDogfoodEvidence = computed(() => recordValue(props.run?.agent_dogfood_evidence))
const agentDogfoodEvidenceSummary = computed(() => recordValue(agentDogfoodEvidence.value.summary))
const agentDogfoodEvidenceStatus = computed(() => stringValue(agentDogfoodEvidence.value.status))
const agentDogfoodCoveredCapabilityCount = computed(() => (
  numberValue(agentDogfoodEvidenceSummary.value.covered_capability_count)
))
const agentDogfoodRequiredCapabilityCount = computed(() => (
  numberValue(agentDogfoodEvidenceSummary.value.required_capability_count)
))
const agentDogfoodGeneratedChapterCount = computed(() => (
  numberValue(agentDogfoodEvidenceSummary.value.generated_chapter_count)
))
const agentDogfoodMissingSourceCount = computed(() => (
  numberValue(agentDogfoodEvidenceSummary.value.missing_source_count)
))
const referenceAlignmentOutput = computed(() => latestToolOutput('inspect_agent_reference_alignment'))
const writeGateCoverageOutput = computed(() => latestToolOutput('inspect_agent_write_gate_coverage'))
const eventProjectionOutput = computed(() => latestToolOutput('inspect_agent_event_projection'))
const jobProjectionOutput = computed(() => latestToolOutput('inspect_agent_job_projection'))
const chapterConflictRecoveryOutput = computed(() => latestToolOutput('plan_chapter_conflict_recovery'))
const workerDispatchOutput = computed(() => latestToolOutput('inspect_agent_worker_dispatch'))
const agentProfile = computed(() => (
  stringValue(props.run?.agent_profile) ||
  stringValue(agentProfileDefinition.value.profile) ||
  stringValue(agentToolDiscovery.value.effective_profile) ||
  stringValue(agentProfileScope.value.agent_profile)
))
const agentProfileTier = computed(() => stringValue(agentProfileDefinition.value.tier))
const agentProfileDelegationAllowed = computed(() => (
  typeof agentProfileDefinition.value.delegation_allowed === 'boolean'
    ? agentProfileDefinition.value.delegation_allowed
    : null
))
const agentProfileDelegateTargetCount = computed(() => {
  const targets = agentProfileDefinition.value.delegate_to_profiles
  if (agentProfileDefinition.value.delegation_allowed !== true || !Array.isArray(targets)) {
    return 0
  }
  return targets.length
})
const hasAgentProfileProjection = computed(() => Boolean(
  agentProfile.value ||
  Object.keys(agentProfileDefinition.value).length ||
  Object.keys(agentToolDiscovery.value).length ||
  Object.keys(agentProfileScope.value).length,
))
const toolDiscoveryStatus = computed(() => (
  stringValue(agentToolDiscovery.value.status) ||
  (agentToolDiscovery.value.scope_applied === true ? 'applied' : '') ||
  stringValue(agentProfileScope.value.status)
))
const allowedVisibleToolCount = computed(() => (
  numberValue(agentToolDiscovery.value.visible_tool_count) ??
  numberValue(agentProfileScope.value.allowed_visible_tool_count)
))
const profileFilteredVisibleToolCount = computed(() => (
  numberValue(agentToolDiscovery.value.filtered_by_profile_count) ??
  numberValue(agentProfileScope.value.profile_filtered_visible_tool_count)
))
const agentProfilePolicyAuditLabel = computed(() => profilePolicyAuditLabel(agentProfilePolicyAudit.value))
const recoveryPreview = computed(() => {
  const step = steps.value.find((item) => item.tool_name === 'plan_recovery_tools')
  return isRecord(step?.output) ? step.output : null
})
const isRecoveryExecutionRun = computed(() => (
  props.run?.entrypoint === 'ui_recovery_execute' ||
  runInput.value.execute_recovery === true
))
const executionPolicy = computed(() => {
  const value = recoveryPreview.value?.execution_policy
  return isRecord(value) ? value : null
})
const guardrails = computed(() => {
  const value = recoveryPreview.value?.guardrails
  return isRecord(value) ? value : null
})
const guardrailBlockers = computed(() => {
  const blockers = guardrails.value?.blockers
  return Array.isArray(blockers) ? blockers.filter(isRecord) : []
})
const recoveryTools = computed(() => {
  const tools = recoveryPreview.value?.tools
  return Array.isArray(tools) ? tools.filter(isRecord) : []
})
const hasRecoveryPolicy = computed(() => Boolean(executionPolicy.value || guardrails.value || recoveryTools.value.length))
const recommendedFollowupPreview = computed(() => {
  const step = steps.value.find((item) => item.tool_name === 'plan_recommended_followups')
  return isRecord(step?.output) ? step.output : null
})
const recommendedFollowupState = computed(() => recordValue(recommendedFollowupPreview.value?.recommended_followups))
const recommendedFollowupTools = computed(() => {
  const tools = recommendedFollowupPreview.value?.tools
  return Array.isArray(tools) ? tools.filter(isRecord) : []
})
const recommendedFollowupExecutionPolicy = computed(() => recordValue(recommendedFollowupPreview.value?.execution_policy))
const recommendedFollowupWorkerDispatch = computed(() => recordValue(recommendedFollowupPreview.value?.worker_dispatch))
const recommendedFollowupWorkerDispatchSummary = computed(() => (
  recordValue(recommendedFollowupWorkerDispatch.value.summary)
))
const recommendedFollowupRouteRegistry = computed(() => (
  recordValue(recommendedFollowupWorkerDispatch.value.route_registry)
))
const recommendedFollowupRouteRegistrySummary = computed(() => (
  recordValue(recommendedFollowupRouteRegistry.value.summary)
))
const recommendedFollowupWorkerDispatches = computed(() => (
  recordList(recommendedFollowupWorkerDispatch.value.worker_dispatches)
))
const recommendedFollowupWorkerCount = computed(() => (
  numberValue(recommendedFollowupWorkerDispatchSummary.value.workers)
))
const recommendedFollowupPlannedTaskCount = computed(() => (
  numberValue(recommendedFollowupWorkerDispatchSummary.value.planned_tasks)
))
const recommendedFollowupRouteRegistryStatus = computed(() => (
  stringValue(recommendedFollowupRouteRegistry.value.status)
))
const recommendedFollowupUnroutedToolCount = computed(() => (
  numberValue(recommendedFollowupRouteRegistrySummary.value.unrouted_allowed_tools)
))
const recommendedFollowupRouteIssueCount = computed(() => (
  numberValue(recommendedFollowupRouteRegistrySummary.value.issues)
))
const recommendedFollowupWriteTools = computed(() => {
  const tools = recommendedFollowupState.value.provenance_write_tools
  return Array.isArray(tools) ? tools.filter(isRecord) : []
})
const recommendedFollowupContinuationTools = computed(() => {
  const tools = recommendedFollowupState.value.post_approval_continuation_tools
  return Array.isArray(tools) ? tools.filter(isRecord) : []
})
const memoryActivationOutput = computed(() => {
  const directOutput = latestToolOutput('inspect_agent_memory_activation_plan')
  if (directOutput) return directOutput
  const generationOutput = latestToolOutput('generate_chapter')
  const nestedOutput = recordValue(generationOutput?.agent_memory_activation)
  return Object.keys(nestedOutput).length ? nestedOutput : null
})
const memoryActivationStatus = computed(() => stringValue(memoryActivationOutput.value?.status))
const memoryActivationCounts = computed(() => {
  const coverage = recordValue(memoryActivationOutput.value?.coverage)
  const coveredCounts = recordValue(coverage.activated_counts)
  if (Object.keys(coveredCounts).length) return coveredCounts
  return recordValue(memoryActivationOutput.value?.activated_counts)
})
const memoryActivationLongformCount = computed(() => numberValue(memoryActivationCounts.value.longform))
const memoryActivationKnowledgeBaseCount = computed(() => numberValue(memoryActivationCounts.value.knowledge_base))
const retrievalContextOutput = computed(() => latestToolOutput('search_agent_retrieval_context'))
const retrievalStrategyOutput = computed(() => latestToolOutput('inspect_agent_retrieval_strategy'))
const retrievalStrategyQualityOutput = computed(() => latestToolOutput('inspect_agent_retrieval_strategy_quality'))
const retrievalPrefetchOutput = computed(() => latestToolOutput('inspect_agent_retrieval_prefetch_plan'))
const retrievalContextSummary = computed(() => recordValue(retrievalContextOutput.value?.summary))
const retrievalContextItems = computed(() => recordList(retrievalContextOutput.value?.items))
const retrievalContextCoverageLabel = computed(() => {
  const returned = numberValue(retrievalContextSummary.value.returned)
  const total = numberValue(retrievalContextSummary.value.total)
  if (returned !== null && total !== null) return `返回 ${returned} / 共 ${total}`
  if (returned !== null) return `返回 ${returned}`
  if (total !== null) return `共 ${total}`
  return ''
})
const retrievalPrimarySourceLabel = computed(() => {
  const item = retrievalContextItems.value[0]
  if (!item) return ''
  const title = safeRetrievalContextSummaryText(item.title) || safeRetrievalContextSummaryText(item.source_ref)
  const chapter = chapterIndexLabel(item.chapter_index)
  const sourceType = retrievalSourceTypeLabel(stringValue(item.source_type))
  return [title, chapter || sourceType].filter(Boolean).join(' · ')
})
const retrievalRecommendedTools = computed(() => stringList(retrievalContextOutput.value?.recommended_next_tools))
const longformContextOutput = computed(() => latestToolOutput('summarize_longform_context'))
const contextCompressionOutput = computed(() => latestToolOutput('inspect_agent_context_compression_projection'))
const preflightBudgetStep = computed(() => latestToolStep('preflight_writing'))
const memoryRouteOutput = computed(() => latestToolOutput('inspect_agent_memory_route'))
const knowledgeBaseRouteOutput = computed(() => latestToolOutput('inspect_agent_knowledge_base_route'))
const worldModelRouteOutput = computed(() => latestToolOutput('inspect_agent_world_model_route'))
const worldModelSemanticCheckOutput = computed(() => latestToolOutput('inspect_agent_world_model_semantic_check'))
const worldModelSemanticCheck = computed(() => recordValue(worldModelSemanticCheckOutput.value?.semantic_check))
const worldModelSemanticFactWindow = computed(() => recordValue(worldModelSemanticCheckOutput.value?.fact_window))
const worldModelSemanticRecommendedTools = computed(() => stringList(worldModelSemanticCheckOutput.value?.recommended_next_tools))
const worldModelSemanticChapterLabel = computed(() => chapterIndexLabel(worldModelSemanticCheckOutput.value?.chapter_index))
const worldModelSemanticSubject = computed(() => safeWorldModelSemanticText(worldModelSemanticCheckOutput.value?.subject_ref))
const worldModelSemanticReturnedFacts = computed(() => numberValue(worldModelSemanticFactWindow.value.returned_facts))
const worldModelSemanticTotalFacts = computed(() => numberValue(worldModelSemanticFactWindow.value.total_confirmed_facts))
const worldModelSemanticFactLimit = computed(() => numberValue(worldModelSemanticFactWindow.value.limit))
const worldModelSemanticIssueCount = computed(() => (
  numberValue(worldModelSemanticCheck.value.issue_count) ?? recordList(worldModelSemanticCheckOutput.value?.issues).length
))
const worldModelSemanticIssueRows = computed(() => (
  recordList(worldModelSemanticCheckOutput.value?.issues)
    .slice(0, 5)
    .map((issue, index) => ({
      key: `world-model-semantic-issue:${index}`,
      code: safeWorldModelSemanticText(issue.code),
      severity: worldModelSemanticSeverityLabel(issue.severity),
      subject: safeWorldModelSemanticText(issue.subject_ref),
      predicate: safeWorldModelSemanticText(issue.predicate),
      message: safeWorldModelSemanticText(issue.message),
      evidence: safeWorldModelSemanticText(issue.evidence_excerpt),
    }))
    .filter((row) => Boolean(row.code || row.message || row.evidence))
))
const worldModelProposalReviewOutput = computed(() => latestToolOutput('review_world_model_proposals'))
const worldModelProposalReviewRiskCounts = computed(() => recordValue(worldModelProposalReviewOutput.value?.risk_counts))
const worldModelProposalReviewModeCounts = computed(() => recordValue(worldModelProposalReviewOutput.value?.review_mode_counts))
const worldModelProposalReviewRecommendedActions = computed(() => stringList(worldModelProposalReviewOutput.value?.recommended_actions))
const worldModelProposalReviewReturned = computed(() => numberValue(worldModelProposalReviewOutput.value?.returned_items))
const worldModelProposalReviewTotal = computed(() => numberValue(worldModelProposalReviewOutput.value?.total_items))
const worldModelProposalReviewHighRiskCount = computed(() => numberValue(worldModelProposalReviewRiskCounts.value.high))
const worldModelProposalReviewMediumRiskCount = computed(() => numberValue(worldModelProposalReviewRiskCounts.value.medium))
const worldModelProposalReviewLowRiskCount = computed(() => numberValue(worldModelProposalReviewRiskCounts.value.low))
const worldModelProposalReviewIndividualCount = computed(() => numberValue(worldModelProposalReviewModeCounts.value.individual))
const worldModelProposalReviewBatchCount = computed(() => numberValue(worldModelProposalReviewModeCounts.value.batch))
const worldModelProposalReviewGenerationLabel = computed(() => (
  worldModelProposalReviewOutput.value?.should_generate_next_chapter === true ? '可继续生成' : '不可继续生成'
))
const worldModelProposalReviewHasMoreLabel = computed(() => {
  if (worldModelProposalReviewOutput.value?.has_more === true) return '有更多'
  if (worldModelProposalReviewOutput.value?.has_more === false) return '无更多'
  return ''
})
const worldModelProposalReviewClusterRows = computed(() => (
  recordList(worldModelProposalReviewOutput.value?.clusters)
    .map((cluster, index) => {
      const subjects = stringList(cluster.subject_refs)
        .map((subject) => safeWorldModelRouteText(subject))
        .filter(Boolean)
      const candidateCount = numberValue(cluster.candidate_count)
      return {
        key: `world-model-proposal-review-cluster:${index}`,
        title: [subjects.join(', '), safeWorldModelRouteText(cluster.predicate)].filter(Boolean).join(' · ') || '待审提案',
        meta: [
          worldModelRiskLabel(cluster.risk_level),
          worldModelReviewModeLabel(cluster.review_mode),
          candidateCount !== null ? `${candidateCount} 个候选` : '',
          worldModelChapterRangeLabel(cluster.chapter_range),
        ].filter(Boolean).join(' · '),
        reason: safeWorldModelRouteText(cluster.reason),
      }
    })
    .filter((row) => Boolean(row.title || row.meta || row.reason))
))
const worldModelResolutionPlanOutput = computed(() => latestToolOutput('plan_world_model_proposal_resolution'))
const worldModelResolutionRiskCounts = computed(() => recordValue(worldModelResolutionPlanOutput.value?.risk_counts))
const worldModelResolutionModeCounts = computed(() => recordValue(worldModelResolutionPlanOutput.value?.review_mode_counts))
const worldModelResolutionReturned = computed(() => numberValue(worldModelResolutionPlanOutput.value?.returned_items))
const worldModelResolutionTotal = computed(() => numberValue(worldModelResolutionPlanOutput.value?.total_items))
const worldModelResolutionHighRiskCount = computed(() => numberValue(worldModelResolutionRiskCounts.value.high))
const worldModelResolutionMediumRiskCount = computed(() => numberValue(worldModelResolutionRiskCounts.value.medium))
const worldModelResolutionLowRiskCount = computed(() => numberValue(worldModelResolutionRiskCounts.value.low))
const worldModelResolutionIndividualCount = computed(() => numberValue(worldModelResolutionModeCounts.value.individual))
const worldModelResolutionBatchCount = computed(() => numberValue(worldModelResolutionModeCounts.value.batch))
const worldModelResolutionHighPriorityStepCount = computed(() => numberValue(worldModelResolutionPlanOutput.value?.high_priority_step_count))
const worldModelResolutionBatchStepCount = computed(() => numberValue(worldModelResolutionPlanOutput.value?.batch_step_count))
const worldModelResolutionConfirmationLabel = computed(() => (
  worldModelResolutionPlanOutput.value?.requires_human_confirmation === true ? '需要人工确认' : '无需人工确认'
))
const worldModelResolutionAutoApplyLabel = computed(() => (
  worldModelResolutionPlanOutput.value?.can_auto_apply === true ? '可自动应用' : '不可自动应用'
))
const worldModelResolutionGenerationLabel = computed(() => (
  worldModelResolutionPlanOutput.value?.should_generate_next_chapter === true ? '可继续生成' : '不可继续生成'
))
const worldModelResolutionRecommendedItems = computed(() => (
  [
    ...stringList(worldModelResolutionPlanOutput.value?.recommended_actions),
    ...stringList(worldModelResolutionPlanOutput.value?.recommended_next_tools),
  ]
))
const worldModelResolutionStepRows = computed(() => (
  recordList(worldModelResolutionPlanOutput.value?.resolution_steps)
    .slice(0, 5)
    .map((step, index) => {
      const stepIndex = numberValue(step.step_index)
      const subjects = stringList(step.subject_refs)
        .map((subject) => safeWorldModelRouteText(subject))
        .filter(Boolean)
      const candidateCount = numberValue(step.candidate_count)
      return {
        key: `world-model-resolution-step:${stepIndex ?? index}`,
        title: [
          stepIndex !== null ? `#${stepIndex}` : '',
          [subjects.join(', '), safeWorldModelRouteText(step.predicate)].filter(Boolean).join(' · '),
        ].filter(Boolean).join(' ') || '解决步骤',
        meta: [
          worldModelResolutionActionTypeLabel(step.action_type),
          worldModelRecommendedResolutionLabel(step.recommended_resolution),
          worldModelRiskLabel(step.risk_level),
          candidateCount !== null ? `${candidateCount} 个候选` : '',
          worldModelChapterRangeLabel(step.chapter_range),
        ].filter(Boolean).join(' · '),
        reason: safeWorldModelRouteText(step.reason),
      }
    })
    .filter((row) => Boolean(row.title || row.meta || row.reason))
))
const traceAuditOutput = computed(() => latestToolOutput('inspect_agent_trace_audit'))
const traceAnomalyTrendsOutput = computed(() => latestToolOutput('inspect_agent_trace_anomaly_trends'))
const traceAnomalyLongRunSamplesOutput = computed(() => (
  latestToolOutput('inspect_agent_trace_anomaly_long_run_samples')
))
const traceAnomalyThresholdReviewOutput = computed(() => (
  latestToolOutput('inspect_agent_trace_anomaly_threshold_review')
))
const traceAudit = computed(() => recordValue(traceAuditOutput.value?.audit))
const traceAuditRun = computed(() => recordValue(traceAuditOutput.value?.run))
const traceAuditFailure = computed(() => recordValue(traceAuditOutput.value?.failure))
const traceAuditContext = computed(() => recordValue(traceAuditOutput.value?.context))
const traceAuditIntentChain = computed(() => recordValue(traceAuditOutput.value?.intent_chain))
const traceAuditEndToEndChain = computed(() => recordValue(traceAuditOutput.value?.end_to_end_chain))
const traceAuditAnomalySummary = computed(() => recordValue(traceAuditOutput.value?.anomaly_summary))
const traceAuditSteps = computed(() => recordList(traceAuditOutput.value?.steps))
const traceAuditTraces = computed(() => recordList(traceAuditOutput.value?.traces))
const traceAuditEventChain = computed(() => recordList(traceAuditOutput.value?.event_chain))
const traceAuditRecommendedActions = computed(() => recordList(traceAuditOutput.value?.recommended_actions))
const traceAnomalyTrend = computed(() => recordValue(traceAnomalyTrendsOutput.value?.trend))
const traceAnomalyTrendBaseline = computed(() => recordValue(traceAnomalyTrendsOutput.value?.baseline))
const traceAnomalyTrendComparison = computed(() => recordValue(traceAnomalyTrendsOutput.value?.comparison))
const traceAnomalyTrendFilters = computed(() => recordValue(traceAnomalyTrendsOutput.value?.filters))
const traceAnomalyTrendIssueCounts = computed(() => recordValue(traceAnomalyTrend.value.issue_counts))
const traceAnomalyTrendSeverityCounts = computed(() => recordValue(traceAnomalyTrend.value.severity_counts))
const traceAnomalyTrendThresholdSignals = computed(() => recordList(traceAnomalyTrendsOutput.value?.threshold_signals))
const traceAnomalyTrendThresholdConfig = computed(() => recordValue(traceAnomalyTrendsOutput.value?.threshold_config))
const traceAnomalyTrendCalibration = computed(() => recordValue(traceAnomalyTrendsOutput.value?.calibration))
const traceAnomalyTrendCalibrationSample = computed(() => recordValue(traceAnomalyTrendCalibration.value.sample))
const traceAnomalyTrendCalibrationSuggestedThresholds = computed(() => (
  recordValue(traceAnomalyTrendCalibration.value.suggested_thresholds)
))
const traceAnomalyTrendCalibrationFalseNegativeGuard = computed(() => (
  recordValue(traceAnomalyTrendCalibration.value.false_negative_guard)
))
const traceAnomalyTrendCalibrationFalsePositiveGuard = computed(() => (
  recordValue(traceAnomalyTrendCalibration.value.false_positive_guard)
))
const traceAnomalyTrendCalibrationPolicy = computed(() => recordValue(traceAnomalyTrendCalibration.value.policy))
const traceAnomalyTrendRecommendedTools = computed(() => stringList(traceAnomalyTrendsOutput.value?.recommended_next_tools))
const traceAnomalyLongRunSampleCollection = computed(() => (
  recordValue(traceAnomalyLongRunSamplesOutput.value?.sample_collection)
))
const traceAnomalyLongRunReviewWindow = computed(() => (
  recordValue(traceAnomalyLongRunSamplesOutput.value?.review_window)
))
const traceAnomalyLongRunStatus = computed(() => stringValue(traceAnomalyLongRunSamplesOutput.value?.status))
const traceAnomalyLongRunCollectionStatusLabel = computed(() => (
  traceAnomalyLongRunSampleStatusLabel(traceAnomalyLongRunSampleCollection.value.status)
))
const traceAnomalyLongRunCandidateCount = computed(() => (
  numberValue(traceAnomalyLongRunSampleCollection.value.candidate_run_count)
))
const traceAnomalyLongRunMinimumReviewCount = computed(() => (
  numberValue(traceAnomalyLongRunSampleCollection.value.minimum_review_run_count)
))
const traceAnomalyLongRunMissingCount = computed(() => (
  numberValue(traceAnomalyLongRunSampleCollection.value.missing_run_count)
))
const traceAnomalyLongRunStepCount = computed(() => (
  numberValue(traceAnomalyLongRunSampleCollection.value.step_count)
))
const traceAnomalyLongRunChapterLabels = computed(() => (
  Array.isArray(traceAnomalyLongRunSampleCollection.value.chapter_indexes)
    ? traceAnomalyLongRunSampleCollection.value.chapter_indexes
      .map((value) => chapterIndexLabel(value))
      .filter(Boolean)
    : []
))
const traceAnomalyLongRunReviewLimit = computed(() => numberValue(traceAnomalyLongRunReviewWindow.value.limit))
const traceAnomalyLongRunReviewBaselineLimit = computed(() => (
  numberValue(traceAnomalyLongRunReviewWindow.value.baseline_limit)
))
const traceAnomalyLongRunReviewChapterLabel = computed(() => (
  chapterIndexLabel(traceAnomalyLongRunReviewWindow.value.chapter_index)
))
const traceAnomalyLongRunStatusRows = computed(() => (
  Object.entries(recordValue(traceAnomalyLongRunSampleCollection.value.status_counts))
    .map(([status, count]) => ({
      key: `trace-anomaly-long-run-status:${status}`,
      label: traceAnomalyRunStatusCountLabel(status),
      count: numberValue(count),
    }))
    .filter((row) => Boolean(row.label && row.count !== null))
    .sort((left, right) => left.label.localeCompare(right.label))
))
const traceAnomalyLongRunRecommendedTools = computed(() => (
  stringList(traceAnomalyLongRunSamplesOutput.value?.recommended_next_tools)
))
const traceAnomalyThresholdReview = computed(() => (
  recordValue(traceAnomalyThresholdReviewOutput.value?.review)
))
const traceAnomalyThresholdReviewSample = computed(() => (
  recordValue(traceAnomalyThresholdReview.value.sample)
))
const traceAnomalyThresholdCandidate = computed(() => (
  recordValue(traceAnomalyThresholdReviewOutput.value?.threshold_candidate)
))
const traceAnomalyThresholdReviewSideEffects = computed(() => (
  recordValue(traceAnomalyThresholdReviewOutput.value?.side_effects)
))
const traceAnomalyThresholdReviewStatus = computed(() => (
  stringValue(traceAnomalyThresholdReviewOutput.value?.status)
))
const traceAnomalyThresholdReviewStateLabel = computed(() => (
  traceAnomalyThresholdReviewStatusLabel(traceAnomalyThresholdReview.value.status)
))
const traceAnomalyThresholdReviewPolicyDecisionLabel = computed(() => (
  traceAnomalyThresholdReviewDecisionLabel(traceAnomalyThresholdReview.value.policy_decision)
))
const traceAnomalyThresholdReviewRecentRunCount = computed(() => (
  numberValue(traceAnomalyThresholdReviewSample.value.recent_run_count)
))
const traceAnomalyThresholdReviewBaselineRunCount = computed(() => (
  numberValue(traceAnomalyThresholdReviewSample.value.baseline_run_count)
))
const traceAnomalyThresholdReviewReviewedRunCount = computed(() => (
  numberValue(traceAnomalyThresholdReviewSample.value.reviewed_run_count)
))
const traceAnomalyThresholdReviewMinimumRunCount = computed(() => (
  numberValue(traceAnomalyThresholdReviewSample.value.minimum_review_run_count)
))
const traceAnomalyThresholdReviewSignalCount = computed(() => (
  numberValue(traceAnomalyThresholdReview.value.signal_count)
))
const traceAnomalyThresholdReviewAffectedThresholdLabel = computed(() => (
  percentLabel(traceAnomalyThresholdCandidate.value.affected_run_rate_delta)
))
const traceAnomalyThresholdReviewCriticalThresholdLabel = computed(() => (
  percentLabel(traceAnomalyThresholdCandidate.value.critical_issue_rate_delta)
))
const traceAnomalyThresholdReviewSkippedDirectWrite = computed(() => (
  stringList(traceAnomalyThresholdReviewSideEffects.value.skipped)
    .includes('record_agent_trace_anomaly_threshold_config')
))
const traceAnomalyThresholdReviewRecommendedTools = computed(() => (
  stringList(traceAnomalyThresholdReviewOutput.value?.recommended_next_tools)
))
const traceAuditRunGoal = computed(() => safeTraceAuditText(traceAuditRun.value.goal))
const traceAuditStepCount = computed(() => numberValue(traceAudit.value.step_count))
const traceAuditTraceCount = computed(() => numberValue(traceAudit.value.trace_count))
const traceAuditEventCount = computed(() => numberValue(traceAudit.value.event_chain_count))
const traceAuditContextBlockCount = computed(() => numberValue(traceAudit.value.context_block_count))
const traceAuditControlPlaneGapCount = computed(() => numberValue(traceAudit.value.control_plane_gap_count))
const traceAuditIntentChainStatus = computed(() => stringValue(traceAuditIntentChain.value.status))
const traceAuditIntentChainRuleId = computed(() => safeTraceAuditText(traceAuditIntentChain.value.rule_id))
const traceAuditIntentChainClass = computed(() => safeTraceAuditText(traceAuditIntentChain.value.intent_class))
const traceAuditIntentChainChapterLabel = computed(() => chapterIndexLabel(traceAuditIntentChain.value.chapter_index))
const traceAuditIntentChainPlannedCount = computed(() => numberValue(traceAuditIntentChain.value.planned_tool_count))
const traceAuditIntentChainExecutedCount = computed(() => numberValue(traceAuditIntentChain.value.executed_tool_count))
const traceAuditIntentChainMatchedCount = computed(() => numberValue(traceAuditIntentChain.value.matched_tool_count))
const traceAuditEndToEndStatus = computed(() => stringValue(traceAuditEndToEndChain.value.status))
const traceAuditEndToEndPlannedCount = computed(() => numberValue(traceAuditEndToEndChain.value.planned_tool_count))
const traceAuditEndToEndToolStepCount = computed(() => numberValue(traceAuditEndToEndChain.value.tool_step_count))
const traceAuditEndToEndModelTraceCount = computed(() => numberValue(traceAuditEndToEndChain.value.model_trace_count))
const traceAuditEndToEndResultMessage = computed(() => recordValue(traceAuditEndToEndChain.value.result_message))
const traceAuditEndToEndResultActionType = computed(() => (
  safeTraceAuditText(traceAuditEndToEndResultMessage.value.action_type)
))
const traceAuditEndToEndResultStatusLabel = computed(() => (
  traceAuditActionStatusLabel(traceAuditEndToEndResultMessage.value.action_status)
))
const traceAuditAnomalyStatus = computed(() => stringValue(traceAuditAnomalySummary.value.status))
const traceAuditAnomalyIssueCount = computed(() => numberValue(traceAuditAnomalySummary.value.issue_count))
const traceAuditAnomalySeverityCounts = computed(() => recordValue(traceAuditAnomalySummary.value.severity_counts))
const traceAuditAnomalyCriticalCount = computed(() => numberValue(traceAuditAnomalySeverityCounts.value.critical))
const traceAuditAnomalyWarningCount = computed(() => numberValue(traceAuditAnomalySeverityCounts.value.warning))
const traceAuditAnomalyInfoCount = computed(() => numberValue(traceAuditAnomalySeverityCounts.value.info))
const traceAuditAnomalyFailedStepCount = computed(() => numberValue(traceAuditAnomalySummary.value.failed_step_count))
const traceAuditAnomalyFailedTraceCount = computed(() => numberValue(traceAuditAnomalySummary.value.failed_trace_count))
const traceAuditAnomalyMissingTraceCount = computed(() => (
  numberValue(traceAuditAnomalySummary.value.missing_trace_binding_count)
))
const traceAuditAnomalyUnmatchedPlanCount = computed(() => (
  numberValue(traceAuditAnomalySummary.value.unmatched_planned_tool_count)
))
const traceAuditAnomalyMissingResultMessage = computed(() => traceAuditAnomalySummary.value.missing_result_message === true)
const traceAuditAnomalyTruncatedContextCount = computed(() => (
  numberValue(traceAuditAnomalySummary.value.truncated_context_block_count)
))
const traceAnomalyTrendStatus = computed(() => stringValue(traceAnomalyTrend.value.status))
const traceAnomalyTrendChapterLabel = computed(() => chapterIndexLabel(traceAnomalyTrendFilters.value.chapter_index))
const traceAnomalyTrendRunCount = computed(() => numberValue(traceAnomalyTrend.value.run_count))
const traceAnomalyTrendAffectedRunCount = computed(() => numberValue(traceAnomalyTrend.value.affected_run_count))
const traceAnomalyTrendIssueCount = computed(() => numberValue(traceAnomalyTrend.value.issue_count))
const traceAnomalyTrendCriticalCount = computed(() => numberValue(traceAnomalyTrendSeverityCounts.value.critical))
const traceAnomalyTrendWarningCount = computed(() => numberValue(traceAnomalyTrendSeverityCounts.value.warning))
const traceAnomalyTrendInfoCount = computed(() => numberValue(traceAnomalyTrendSeverityCounts.value.info))
const traceAnomalyTrendDominantIssueLabel = computed(() => (
  traceAuditAnomalyCodeLabel(traceAnomalyTrend.value.dominant_issue_code)
))
const traceAnomalyTrendBaselineRunCount = computed(() => numberValue(traceAnomalyTrendBaseline.value.run_count))
const traceAnomalyTrendBaselineAffectedRunCount = computed(() => (
  numberValue(traceAnomalyTrendBaseline.value.affected_run_count)
))
const traceAnomalyTrendAffectedRunRateDeltaLabel = computed(() => (
  signedPercentLabel(traceAnomalyTrendComparison.value.affected_run_rate_delta)
))
const traceAnomalyTrendIssueRateDeltaLabel = computed(() => (
  signedPercentLabel(traceAnomalyTrendComparison.value.issue_rate_delta)
))
const traceAnomalyTrendThresholdConfigLabel = computed(() => (
  traceAnomalyThresholdConfigLabel(traceAnomalyTrendThresholdConfig.value.status)
))
const traceAnomalyTrendCalibrationStatusLabel = computed(() => (
  traceAnomalyCalibrationStatusLabel(traceAnomalyTrendCalibration.value.status)
))
const traceAnomalyTrendCalibrationRecentRunCount = computed(() => (
  numberValue(traceAnomalyTrendCalibrationSample.value.recent_run_count)
))
const traceAnomalyTrendCalibrationBaselineRunCount = computed(() => (
  numberValue(traceAnomalyTrendCalibrationSample.value.baseline_run_count)
))
const traceAnomalyTrendCalibrationCurrentSignalCount = computed(() => (
  numberValue(traceAnomalyTrendCalibration.value.current_signal_count)
))
const traceAnomalyTrendCalibrationSuggestedAffectedThresholdLabel = computed(() => (
  percentLabel(traceAnomalyTrendCalibrationSuggestedThresholds.value.affected_run_rate_delta)
))
const traceAnomalyTrendCalibrationSuggestedCriticalThresholdLabel = computed(() => (
  percentLabel(traceAnomalyTrendCalibrationSuggestedThresholds.value.critical_issue_rate_delta)
))
const traceAnomalyTrendCalibrationPolicyStatusLabel = computed(() => (
  traceAnomalyPolicyStatusLabel(traceAnomalyTrendCalibrationPolicy.value.status)
))
const traceAnomalyTrendCalibrationPolicyDecisionLabel = computed(() => (
  traceAnomalyPolicyDecisionLabel(traceAnomalyTrendCalibrationPolicy.value.decision)
))
const traceAnomalyTrendCalibrationPolicyReviewedRunCount = computed(() => (
  numberValue(traceAnomalyTrendCalibrationPolicy.value.reviewed_run_count)
))
const traceAnomalyTrendCalibrationPolicyMinimumRunCount = computed(() => (
  numberValue(traceAnomalyTrendCalibrationPolicy.value.minimum_review_run_count)
))
const traceAnomalyTrendCalibrationPolicyPromotionLabel = computed(() => (
  traceAnomalyPolicyPromotionLabel(traceAnomalyTrendCalibrationPolicy.value.promotion_candidate)
))
const traceAuditFailureTool = computed(() => safeTraceAuditText(traceAuditFailure.value.tool_name))
const traceAuditFailureReason = computed(() => safeTraceAuditText(traceAuditFailure.value.reason_code))
const traceAuditFailureMessage = computed(() => safeTraceAuditText(traceAuditFailure.value.message))
const traceAuditIntentChainRows = computed(() => (
  recordList(traceAuditIntentChain.value.planned_tools)
    .map((tool, index) => {
      const stepIndex = numberValue(tool.step_index)
      return {
        key: `trace-audit-intent-tool:${index}`,
        toolName: safeTraceAuditText(tool.tool_name) || '计划工具',
        statusLabel: traceAuditStatusLabel(tool.status),
        stepLabel: stepIndex !== null ? `#${stepIndex}` : '',
      }
    })
    .filter((row) => Boolean(row.toolName || row.statusLabel || row.stepLabel))
))
const traceAuditEndToEndSegmentRows = computed(() => (
  recordList(traceAuditEndToEndChain.value.segments)
    .map((segment, index) => {
      const count = numberValue(segment.count)
      const chapterLabel = chapterIndexLabel(segment.chapter_index)
      const status = stringValue(segment.status)
      const actionStatus = stringValue(segment.action_status)
      return {
        key: `trace-audit-e2e:${index}`,
        stageLabel: traceAuditEndToEndStageLabel(segment.stage),
        statusLabel: traceAuditAvailabilityLabel(status),
        meta: [
          count !== null ? `${count}` : '',
          chapterLabel,
          safeTraceAuditText(segment.intent_class),
          safeTraceAuditText(segment.action_type),
          actionStatus ? traceAuditActionStatusLabel(actionStatus) : '',
        ].filter(Boolean).join(' · '),
      }
    })
    .filter((row) => Boolean(row.stageLabel || row.statusLabel || row.meta))
))
const traceAuditAnomalyIssueRows = computed(() => (
  recordList(traceAuditAnomalySummary.value.issues)
    .slice(0, 8)
    .map((issue, index) => {
      const stepIndex = numberValue(issue.step_index)
      const charCount = numberValue(issue.char_count)
      const sourceCount = numberValue(issue.source_count)
      return {
        key: `trace-audit-anomaly:${index}`,
        label: traceAuditAnomalyCodeLabel(issue.code),
        severityLabel: traceAuditAnomalySeverityLabel(issue.severity),
        meta: [
          safeTraceAuditText(issue.tool_name),
          safeTraceAuditText(issue.trace_type),
          traceAuditEndToEndStageLabel(issue.stage),
          safeTraceAuditText(issue.kind),
          traceAuditStatusLabel(issue.status),
          stepIndex !== null ? `#${stepIndex}` : '',
          chapterIndexLabel(issue.chapter_index),
          issue.error_recorded === true ? '已记录错误' : '',
          charCount !== null ? `${charCount} 字` : '',
          sourceCount !== null ? `来源 ${sourceCount}` : '',
        ].filter(Boolean).join(' · '),
        title: safeTraceAuditText(issue.title),
      }
    })
    .filter((row) => Boolean(row.label || row.severityLabel || row.meta || row.title))
))
const traceAnomalyTrendIssueRows = computed(() => (
  Object.entries(traceAnomalyTrendIssueCounts.value)
    .map(([code, count]) => ({
      key: `trace-anomaly-trend-issue:${code}`,
      label: traceAuditAnomalyCodeLabel(code),
      count: numberValue(count),
    }))
    .filter((row) => Boolean(row.label && row.count !== null))
    .sort((left, right) => (right.count ?? 0) - (left.count ?? 0) || left.label.localeCompare(right.label))
))
const traceAnomalyTrendRunRows = computed(() => (
  recordList(traceAnomalyTrendsOutput.value?.runs)
    .slice(0, 6)
    .map((run, index) => {
      const runIndex = numberValue(run.run_index)
      const issueCount = numberValue(run.issue_count)
      const criticalCount = numberValue(run.critical_issue_count)
      const warningCount = numberValue(run.warning_issue_count)
      const infoCount = numberValue(run.info_issue_count)
      const topIssues = stringList(run.top_issue_codes)
        .map((code) => traceAuditAnomalyCodeLabel(code))
        .filter(Boolean)
      return {
        key: `trace-anomaly-trend-run:${runIndex ?? index}`,
        title: [runIndex !== null ? `#${runIndex}` : '', safeTraceAuditText(run.goal) || 'Agent run']
          .filter(Boolean)
          .join(' '),
        statusLabel: traceAuditAnomalyStatusLabel(run.anomaly_status),
        meta: [
          chapterIndexLabel(run.chapter_index),
          issueCount !== null ? `问题 ${issueCount}` : '',
          criticalCount !== null ? `严重 ${criticalCount}` : '',
          warningCount !== null ? `警告 ${warningCount}` : '',
          infoCount !== null ? `提示 ${infoCount}` : '',
          safeTraceAuditText(run.entrypoint),
          traceAuditStatusLabel(run.status),
        ].filter(Boolean).join(' · '),
        issueLabel: topIssues.join(' · '),
      }
    })
    .filter((row) => Boolean(row.title || row.statusLabel || row.meta || row.issueLabel))
))
const traceAnomalyTrendThresholdSignalRows = computed(() => (
  traceAnomalyTrendThresholdSignals.value
    .slice(0, 5)
    .map((signal, index) => {
      const delta = signedPercentLabel(signal.delta)
      const threshold = percentLabel(signal.threshold)
      const recent = percentLabel(signal.recent_value)
      const baseline = percentLabel(signal.baseline_value)
      return {
        key: `trace-anomaly-threshold-signal:${index}`,
        title: safeTraceAuditText(signal.title) || traceAnomalyThresholdSignalLabel(signal.code),
        severityLabel: traceAuditAnomalySeverityLabel(signal.severity),
        meta: [
          delta ? `变化 ${delta}` : '',
          threshold ? `阈值 ${threshold}` : '',
          recent ? `当前 ${recent}` : '',
          baseline ? `基线 ${baseline}` : '',
        ].filter(Boolean).join(' · '),
      }
    })
    .filter((row) => Boolean(row.title || row.severityLabel || row.meta))
))
const traceAnomalyTrendCalibrationGuardRows = computed(() => (
  [
    {
      key: 'trace-anomaly-calibration-fn',
      title: '漏报 guard',
      statusLabel: traceAnomalyCalibrationGuardStatusLabel(
        traceAnomalyTrendCalibrationFalseNegativeGuard.value.status,
      ),
      meta: [
        traceAnomalyCalibrationGuardReasonLabel(traceAnomalyTrendCalibrationFalseNegativeGuard.value.reason),
        numberValue(traceAnomalyTrendCalibrationFalseNegativeGuard.value.missed_affected_run_count) !== null
          ? `漏过运行 ${numberValue(traceAnomalyTrendCalibrationFalseNegativeGuard.value.missed_affected_run_count)}`
          : '',
        numberValue(traceAnomalyTrendCalibrationFalseNegativeGuard.value.missed_issue_count) !== null
          ? `漏过问题 ${numberValue(traceAnomalyTrendCalibrationFalseNegativeGuard.value.missed_issue_count)}`
          : '',
      ].filter(Boolean).join(' · '),
    },
    {
      key: 'trace-anomaly-calibration-fp',
      title: '误报 guard',
      statusLabel: traceAnomalyCalibrationGuardStatusLabel(
        traceAnomalyTrendCalibrationFalsePositiveGuard.value.status,
      ),
      meta: [
        traceAnomalyCalibrationGuardReasonLabel(traceAnomalyTrendCalibrationFalsePositiveGuard.value.reason),
        numberValue(traceAnomalyTrendCalibrationFalsePositiveGuard.value.info_only_signal_count) !== null
          ? `提示信号 ${numberValue(traceAnomalyTrendCalibrationFalsePositiveGuard.value.info_only_signal_count)}`
          : '',
      ].filter(Boolean).join(' · '),
    },
  ].filter((row) => Boolean(row.statusLabel || row.meta))
))
const traceAuditStepRows = computed(() => (
  traceAuditSteps.value
    .map((step, index) => {
      const stepIndex = numberValue(step.step_index)
      const toolName = safeTraceAuditText(step.tool_name)
      return {
        key: `trace-audit-step:${stepIndex ?? index}`,
        label: [stepIndex !== null ? `#${stepIndex}` : '', toolName].filter(Boolean).join(' '),
        statusLabel: traceAuditStatusLabel(step.status),
        chapterLabel: chapterIndexLabel(step.chapter_index),
      }
    })
    .filter((row) => Boolean(row.label || row.statusLabel || row.chapterLabel))
))
const traceAuditTraceRows = computed(() => (
  traceAuditTraces.value
    .map((trace, index) => {
      const promptTokens = numberValue(trace.prompt_tokens)
      const completionTokens = numberValue(trace.completion_tokens)
      const latencyMs = numberValue(trace.latency_ms)
      const contextBlockCount = numberValue(trace.context_block_count)
      const contextCharCount = numberValue(trace.context_char_count)
      const meta = [
        safeTraceAuditText(trace.model),
        promptTokens !== null ? `prompt ${promptTokens}` : '',
        completionTokens !== null ? `completion ${completionTokens}` : '',
        latencyMs !== null ? `${latencyMs}ms` : '',
        contextBlockCount !== null ? `上下文块 ${contextBlockCount}` : '',
        contextCharCount !== null ? `${contextCharCount} 字` : '',
      ].filter(Boolean).join(' · ')
      return {
        key: `trace-audit-trace:${index}`,
        label: safeTraceAuditText(trace.trace_type) || '模型 Trace',
        statusLabel: traceAuditStatusLabel(trace.status),
        meta,
        error: safeTraceAuditText(trace.error_message),
      }
    })
    .filter((row) => Boolean(row.label || row.statusLabel || row.meta || row.error))
))
const traceAuditEventRows = computed(() => (
  traceAuditEventChain.value
    .slice(0, 6)
    .map((event, index) => ({
      key: `trace-audit-event:${index}`,
      label: traceAuditEventLabel(event),
      detail: traceAuditEventDetail(event),
    }))
    .filter((row) => Boolean(row.label || row.detail))
))
const traceAuditContextRows = computed(() => (
  recordList(traceAuditContext.value.blocks)
    .map((block, index) => {
      const charCount = numberValue(block.char_count)
      const sourceCount = numberValue(block.source_count)
      return {
        key: `trace-audit-context:${index}`,
        title: safeTraceAuditText(block.title) || '上下文块',
        kind: safeTraceAuditText(block.kind),
        meta: [
          charCount !== null ? `${charCount} 字` : '',
          sourceCount !== null ? `来源 ${sourceCount}` : '',
          block.truncated === true ? '已截断' : '',
        ].filter(Boolean).join(' · '),
      }
    })
    .filter((row) => Boolean(row.title || row.meta))
))
const traceAuditRecommendedActionRows = computed(() => (
  traceAuditRecommendedActions.value
    .map((action, index) => {
      const sourceStepIndex = numberValue(action.source_step_index)
      return {
        key: `trace-audit-action:${index}`,
        toolName: safeTraceAuditText(action.tool_name) || '建议工具',
        reason: safeTraceAuditText(action.reason_code),
        sourceStepLabel: sourceStepIndex !== null ? `步骤 ${sourceStepIndex}` : '',
      }
    })
    .filter((row) => Boolean(row.toolName || row.reason || row.sourceStepLabel))
))
const postChapterMemoryOutput = computed(() => latestToolOutput('plan_post_chapter_memory_capture'))
const postChapterMemorySummary = computed(() => recordValue(postChapterMemoryOutput.value?.summary))
const postChapterMemoryChapterLabel = computed(() => chapterIndexLabel(postChapterMemoryOutput.value?.chapter_index))
const postChapterMemoryCaptureStatus = computed(() => stringValue(postChapterMemoryOutput.value?.capture_status))
const postChapterMemoryCandidateCount = computed(() => numberValue(postChapterMemorySummary.value.candidate_count))
const postChapterMemoryReviewStepCount = computed(() => numberValue(postChapterMemorySummary.value.review_step_count))
const postChapterMemoryRecommendedTools = computed(() => stringList(postChapterMemoryOutput.value?.recommended_next_tools))
const postChapterMemoryCandidates = computed(() => recordList(postChapterMemoryOutput.value?.candidates))
const knowledgeBaseCandidateExecutionOutput = computed(() => latestToolOutput('execute_record_agent_knowledge_base_candidate_with_approval'))
const knowledgeBaseCandidateExecutionCandidate = computed(() => recordValue(knowledgeBaseCandidateExecutionOutput.value?.candidate))
const knowledgeBaseCandidateExecutionTitle = computed(() => (
  safePostMemoryCandidateLabel(knowledgeBaseCandidateExecutionCandidate.value.title) || '知识库候选'
))
const knowledgeBaseCandidateExecutionType = computed(() => (
  knowledgeBaseCandidateTypeLabel(knowledgeBaseCandidateExecutionCandidate.value.memory_type)
))
const knowledgeBaseCandidateExecutionCount = computed(() => (
  numberValue(knowledgeBaseCandidateExecutionOutput.value?.candidate_count)
))
const knowledgeBaseCandidateExecutionChapterIndex = computed(() => (
  numberValue(knowledgeBaseCandidateExecutionCandidate.value.chapter_index) ??
  numberValue(knowledgeBaseCandidateExecutionOutput.value?.chapter_index)
))
const knowledgeBaseCandidateExecutionRecommendedTools = computed(() => (
  stringList(knowledgeBaseCandidateExecutionOutput.value?.recommended_next_tools)
))
const memoryTreeOutput = computed(() => latestToolOutput('inspect_agent_memory_tree'))
const memoryTreeSummary = computed(() => recordValue(memoryTreeOutput.value?.summary))
const memoryTreeSummaryLabel = computed(() => {
  const counts = [
    ['卷', numberValue(memoryTreeSummary.value.volume_nodes)],
    ['章节', numberValue(memoryTreeSummary.value.chapter_nodes)],
    ['场景', numberValue(memoryTreeSummary.value.scene_nodes)],
    ['节拍', numberValue(memoryTreeSummary.value.beat_nodes)],
  ]
  return counts
    .filter((item): item is [string, number] => item[1] !== null)
    .map(([label, count]) => `${label} ${count}`)
    .join(' / ')
})
const memoryTreeFilters = computed(() => recordValue(memoryTreeOutput.value?.filters))
const memoryTreeNavigation = computed(() => recordValue(memoryTreeOutput.value?.navigation))
const memoryTreeNodes = computed(() => recordList(memoryTreeOutput.value?.nodes))
const memoryTreeLevelCount = computed(() => (
  Array.isArray(memoryTreeOutput.value?.levels) ? memoryTreeOutput.value.levels.length : null
))
const memoryTreeNodeCount = computed(() => memoryTreeNodes.value.length)
const memoryTreeQuery = computed(() => stringValue(memoryTreeFilters.value.query))
const memoryTreeFilterLevel = computed(() => stringValue(memoryTreeFilters.value.level))
const memoryTreeRecommendedDrilldownCount = computed(() => (
  recordList(memoryTreeNavigation.value.recommended_drilldowns).length
))
const memoryTreeHistoryRows = computed(() => (
  (props.memoryTreeHistory || [])
    .map((item, index) => ({
      key: stringValue(item.key) || `memory-tree-history:${index}`,
      label: safeMemoryTreeDisplayLabel(item.label),
    }))
    .filter((item) => Boolean(item.label))
))
const memoryTreeNodeRows = computed(() => (
  memoryTreeNodes.value.map((node, index) => {
    const level = stringValue(node.level)
    const relevance = recordValue(node.relevance)
    const score = numberValue(relevance.score)
    return {
      key: `${stringValue(node.id) || level || 'node'}:${index}`,
      levelLabel: memoryTreeLevelLabel(level),
      title: stringValue(node.title) || '未命名节点',
      chapterLabel: chapterIndexLabel(node.chapter_index),
      summary: stringValue(node.summary),
      relevanceLabel: score !== null ? `相关度 ${score.toFixed(2)}` : '',
      depth: memoryTreeLevelDepth(level),
    }
  })
))
const memoryTreeNodesById = computed(() => {
  const nodesById: Record<string, Record<string, unknown>> = {}
  for (const node of memoryTreeNodes.value) {
    const nodeId = stringValue(node.id)
    if (nodeId) nodesById[nodeId] = node
  }
  return nodesById
})
const memoryTreeLlmCandidateOutput = computed(() => latestToolOutput('inspect_agent_memory_tree_llm_candidates'))
const memoryTreeLlmCandidateFilters = computed(() => recordValue(memoryTreeLlmCandidateOutput.value?.filters))
const memoryTreeLlmCandidateSummary = computed(() => recordValue(memoryTreeLlmCandidateOutput.value?.summary))
const memoryTreeLlmCandidateBatchOutput = computed(() => (
  latestToolOutput('prepare_record_agent_memory_tree_llm_candidate_summaries_batch')
))
const memoryTreeLlmCandidateBatchSummary = computed(() => recordValue(memoryTreeLlmCandidateBatchOutput.value?.summary))
const memoryTreeLlmCandidateBatchExecuteOutput = computed(() => (
  latestToolOutput('execute_record_agent_memory_tree_llm_candidate_summaries_batch_with_approval')
))
const memoryTreeLlmCandidateBatchExecuteSummary = computed(() => (
  recordValue(memoryTreeLlmCandidateBatchExecuteOutput.value?.summary)
))
const memoryTreeLlmCandidateRows = computed(() => (
  recordList(memoryTreeLlmCandidateOutput.value?.candidates)
    .map((candidateTrace, index) => {
      const candidate = recordValue(candidateTrace.candidate)
      const summaryTarget = recordValue(candidateTrace.summary_target)
      const chapterIndex = (
        numberValue(candidateTrace.chapter_index) ??
        numberValue(summaryTarget.chapter_index)
      )
      const salientTerms = stringList(candidate.salient_terms)
      const primaryTerm = salientTerms[0] || ''
      const sourceCount = numberValue(candidateTrace.source_count)
      const sourceChars = numberValue(candidateTrace.source_chars)
      const sourceLabel = sourceCount !== null || sourceChars !== null
        ? `来源 ${sourceCount ?? 0} / ${sourceChars ?? 0} 字`
        : ''
      const qualityLabel = memoryTreeLlmCandidateQualityLabel(candidateTrace.quality_precheck_status)
      const materialization = recordValue(candidateTrace.materialization)
      const materializationLabel = memoryTreeLlmCandidateMaterializationLabel(materialization.status)
      return {
        key: `memory-tree-llm-candidate:${index}`,
        label: [chapterIndexLabel(chapterIndex), primaryTerm].filter(Boolean).join(' ') || `候选 ${index + 1}`,
        summary: stringValue(candidate.summary),
        termsLabel: salientTerms.slice(0, 3).join(' / '),
        sourceLabel,
        qualityLabel: qualityLabel ? `质量预检：${qualityLabel}` : '',
        materializationLabel,
      }
    })
    .filter((row) => Boolean(row.summary || row.termsLabel))
))
const memoryTreeLlmCandidateSummaryLabel = computed(() => {
  const traceCount = numberValue(memoryTreeLlmCandidateSummary.value.candidate_traces)
  const readyCount = numberValue(memoryTreeLlmCandidateSummary.value.ready_candidates)
  const pendingCount = numberValue(memoryTreeLlmCandidateSummary.value.pending_candidates)
  const materializedCount = numberValue(memoryTreeLlmCandidateSummary.value.materialized_candidates)
  const parts = [
    `候选 ${traceCount ?? memoryTreeLlmCandidateRows.value.length}`,
    `可准备 ${pendingCount ?? readyCount ?? memoryTreeLlmCandidateRows.value.length}`,
  ]
  if (materializedCount !== null) parts.push(`已物化 ${materializedCount}`)
  return parts.join(' / ')
})
const memoryTreeLlmCandidateChapterLabel = computed(() => (
  chapterIndexLabel(memoryTreeLlmCandidateFilters.value.chapter_index)
))
const memoryTreeLlmCandidatePrepareCalls = computed(() => (
  toolRequestList(memoryTreeLlmCandidateOutput.value?.recommended_next_tool_calls)
    .filter((call) => stringValue(call.tool_name) === 'prepare_record_agent_memory_tree_llm_candidate_summary')
))
const memoryTreeLlmCandidateBatchPreparations = computed(() => (
  recordList(memoryTreeLlmCandidateBatchOutput.value?.candidate_preparations)
))
const memoryTreeLlmCandidateBatchRows = computed(() => (
  memoryTreeLlmCandidateBatchPreparations.value
    .map((preparation, index) => {
      const summaryPlan = recordValue(preparation.summary_plan)
      const chapterLabel = chapterIndexLabel(summaryPlan.chapter_index)
      const qualityQuery = stringValue(summaryPlan.quality_query)
      const executeCall = recordValue(preparation.recommended_next_tool_call)
      const executeToolLabel = preparedApprovalExecuteToolLabel(stringValue(executeCall.tool_name))
      return {
        key: `memory-tree-llm-candidate-batch:${index}`,
        label: [chapterLabel, qualityQuery].filter(Boolean).join(' ') || `候选 ${index + 1}`,
        chapterLabel,
        qualityQuery,
        executeToolLabel,
      }
    })
    .filter((row) => Boolean(row.label || row.executeToolLabel))
))
const memoryTreeLlmCandidateBatchSummaryLabel = computed(() => {
  const candidateTraces = numberValue(memoryTreeLlmCandidateBatchSummary.value.candidate_traces)
  const preparedCandidates = numberValue(memoryTreeLlmCandidateBatchSummary.value.prepared_candidates)
  const skippedCandidates = numberValue(memoryTreeLlmCandidateBatchSummary.value.skipped_candidates)
  return [
    `已准备 ${preparedCandidates ?? memoryTreeLlmCandidateBatchRows.value.length}`,
    `候选 ${candidateTraces ?? memoryTreeLlmCandidateBatchRows.value.length}`,
    `跳过 ${skippedCandidates ?? 0}`,
  ].join(' / ')
})
const memoryTreeLlmCandidateBatchExecuteRows = computed(() => (
  recordList(memoryTreeLlmCandidateBatchExecuteOutput.value?.candidate_results)
    .map((result, index) => {
      const materialization = recordValue(result.materialization)
      const materializationSummary = recordValue(materialization.summary)
      const nodes = recordList(materialization.nodes)
      const firstNode = recordValue(nodes[0])
      const quality = recordValue(result.post_materialization_quality)
      const createdNodes = numberValue(materializationSummary.created_nodes)
      const updatedNodes = numberValue(materializationSummary.updated_nodes)
      const chapterLabel = chapterIndexLabel(firstNode.chapter_index)
      const qualityLabel = memoryTreeLlmCandidateQualityLabel(quality.status)
      return {
        key: `memory-tree-llm-candidate-batch-execute:${index}`,
        label: chapterLabel || `候选 ${index + 1}`,
        statusLabel: memoryTreeStatusLabel(result.status),
        writeLabel: `创建 ${createdNodes ?? 0} / 更新 ${updatedNodes ?? 0}`,
        qualityLabel: qualityLabel ? `质量：${qualityLabel}` : '',
      }
    })
))
const memoryTreeLlmCandidateBatchExecuteSummaryLabel = computed(() => {
  const candidateExecutions = numberValue(memoryTreeLlmCandidateBatchExecuteSummary.value.candidate_executions)
  const succeededCandidates = numberValue(memoryTreeLlmCandidateBatchExecuteSummary.value.succeeded_candidates)
  const blockedCandidates = numberValue(memoryTreeLlmCandidateBatchExecuteSummary.value.blocked_candidates)
  return [
    `成功 ${succeededCandidates ?? 0}`,
    `阻塞 ${blockedCandidates ?? 0}`,
    `候选 ${candidateExecutions ?? memoryTreeLlmCandidateBatchExecuteRows.value.length}`,
  ].join(' / ')
})

function createMemoryTreeReadPayload(
  runId: string,
  planId: string,
  goal: string,
  params: Record<string, unknown>,
): PlannerPlanExecutePayload {
  const toolRequest: Record<string, unknown> = {
    tool_name: 'inspect_agent_memory_tree',
    params,
    planner: {
      step_id: planId,
      plan_id: planId,
      mutability: 'read',
      requires_confirmation: false,
    },
  }
  return {
    sourceRunId: runId,
    sourcePlanId: planId,
    goal,
    tools: [toolRequest],
    planner: {
      status: 'completed',
      intent_class: 'inspect_memory_tree',
      approval_contract: { status: 'not_required', write_steps: [] },
      trace: {
        plan_id: planId,
        selected_tools: ['inspect_agent_memory_tree'],
      },
      tools: [toolRequest],
    },
  }
}

function createMemoryTreeLlmCandidateBatchExecutePayload(
  runId: string,
  planId: string,
  goal: string,
  toolName: string,
  params: Record<string, unknown>,
  agentPlan: Record<string, unknown>,
  approvalContract: Record<string, unknown>,
  approvalContractHash: string,
  plannerVersion: string,
): PlannerPlanExecutePayload {
  const toolRequest: Record<string, unknown> = {
    tool_name: toolName,
    params,
    planner: {
      plan_id: planId,
      planner_version: plannerVersion,
      mutability: 'write',
      requires_confirmation: true,
      reason: '确认执行已准备的 Memory Tree LLM 候选摘要写入。',
    },
  }
  return {
    sourceRunId: runId,
    sourcePlanId: planId,
    goal,
    tools: [toolRequest],
    planner: {
      ...agentPlan,
      approval_contract: approvalContract,
    },
    approvalContractHash,
    approvalContract,
  }
}

function createMemoryTreeLlmCandidatePreparePayload(
  runId: string,
  planId: string,
  goal: string,
  params: Record<string, unknown>,
): PlannerPlanExecutePayload {
  const toolRequest: Record<string, unknown> = {
    tool_name: 'prepare_record_agent_memory_tree_llm_candidate_summary',
    params,
    planner: {
      step_id: planId,
      plan_id: planId,
      mutability: 'read',
      requires_confirmation: false,
      reason: '准备 Memory Tree LLM 候选摘要审批，不直接写入 LongformMemory。',
    },
  }
  return {
    sourceRunId: runId,
    sourcePlanId: planId,
    goal,
    tools: [toolRequest],
    planner: {
      status: 'completed',
      intent_class: 'prepare_memory_tree_llm_candidate_summary',
      approval_contract: { status: 'not_required', write_steps: [] },
      trace: {
        plan_id: planId,
        selected_tools: ['prepare_record_agent_memory_tree_llm_candidate_summary'],
      },
      tools: [toolRequest],
    },
  }
}

function createPostMemoryCandidatePreparePayload(
  runId: string,
  planId: string,
  goal: string,
  params: Record<string, unknown>,
): PlannerPlanExecutePayload {
  const toolRequest: Record<string, unknown> = {
    tool_name: 'prepare_record_agent_knowledge_base_candidate',
    params,
    planner: {
      step_id: planId,
      plan_id: planId,
      mutability: 'read',
      requires_confirmation: false,
      reason: '准备写后记忆候选审批，不直接写入知识库。',
    },
  }
  return {
    sourceRunId: runId,
    sourcePlanId: planId,
    goal,
    tools: [toolRequest],
    planner: {
      status: 'completed',
      intent_class: 'prepare_knowledge_base_candidate',
      approval_contract: { status: 'not_required', write_steps: [] },
      trace: {
        plan_id: planId,
        selected_tools: ['prepare_record_agent_knowledge_base_candidate'],
      },
      tools: [toolRequest],
    },
  }
}

function createKnowledgeBaseRouteReadPayload(
  runId: string,
  planId: string,
  goal: string,
  params: Record<string, unknown>,
): PlannerPlanExecutePayload {
  const toolRequest: Record<string, unknown> = {
    tool_name: 'inspect_agent_knowledge_base_route',
    params,
    planner: {
      step_id: planId,
      plan_id: planId,
      mutability: 'read',
      requires_confirmation: false,
    },
  }
  return {
    sourceRunId: runId,
    sourcePlanId: planId,
    goal,
    tools: [toolRequest],
    planner: {
      status: 'completed',
      intent_class: 'inspect_knowledge_base_route',
      approval_contract: { status: 'not_required', write_steps: [] },
      trace: {
        plan_id: planId,
        selected_tools: ['inspect_agent_knowledge_base_route'],
      },
      tools: [toolRequest],
    },
  }
}

const postChapterMemoryCandidatePrepareActions = computed<PlannerContinuationAction[]>(() => {
  const runId = props.run?.id
  if (!runId || props.run?.status !== 'success') return []
  const actions: PlannerContinuationAction[] = []
  for (const [index, candidate] of postChapterMemoryCandidates.value.entries()) {
    const nextToolCall = recordValue(candidate.next_tool_call)
    if (stringValue(nextToolCall.tool_name) !== 'prepare_record_agent_knowledge_base_candidate') continue
    const params = recordValue(nextToolCall.params)
    if (!Object.keys(params).length) continue
    const planId = `post-memory-candidate-prepare:${index}`
    const candidateLabel = (
      safePostMemoryCandidateLabel(candidate.title) ||
      safePostMemoryCandidateLabel(params.title) ||
      `候选 ${index + 1}`
    )
    actions.push({
      key: planId,
      label: `准备候选：${candidateLabel}`,
      payload: createPostMemoryCandidatePreparePayload(
        runId,
        planId,
        `准备写后记忆候选审批：${candidateLabel}`,
        params,
      ),
    })
  }
  return actions
})

const memoryTreeLlmCandidatePrepareActions = computed<PlannerContinuationAction[]>(() => {
  const runId = props.run?.id
  if (!runId || props.run?.status !== 'success') return []
  return memoryTreeLlmCandidatePrepareCalls.value.map((call, index) => {
    const params = recordValue(call.params)
    const row = memoryTreeLlmCandidateRows.value[index]
    const qualityQuery = stringValue(params.quality_query)
    const chapterLabel = chapterIndexLabel(params.quality_chapter_index) || memoryTreeLlmCandidateChapterLabel.value
    const candidateLabel = [chapterLabel, qualityQuery || row?.termsLabel || row?.label]
      .filter(Boolean)
      .join(' ')
    const planId = `memory-tree-llm-candidate-prepare:${index}`
    return {
      key: planId,
      label: `准备候选摘要：${qualityQuery || row?.label || `候选 ${index + 1}`}`,
      payload: createMemoryTreeLlmCandidatePreparePayload(
        runId,
        planId,
        `准备 Memory Tree 候选摘要审批：${candidateLabel || `候选 ${index + 1}`}`,
        params,
      ),
    }
  })
})

const memoryTreeLlmCandidateBatchExecuteActions = computed<PlannerContinuationAction[]>(() => {
  const runId = props.run?.id
  if (!runId || props.run?.status !== 'success') return []
  const actions: PlannerContinuationAction[] = []
  for (const [index, preparation] of memoryTreeLlmCandidateBatchPreparations.value.entries()) {
    const call = recordValue(preparation.recommended_next_tool_call)
    const toolName = stringValue(call.tool_name)
    if (toolName !== 'execute_record_agent_memory_tree_llm_candidate_summary_with_approval') continue
    const params = recordValue(call.params)
    if (!Object.keys(params).length) continue
    const agentPlan = recordValue(preparation.agent_plan)
    const approvalContract = recordValue(preparation.agent_plan_approval_contract)
    const approvalContractHash = (
      stringValue(preparation.agent_plan_approval_contract_hash) ||
      stringValue(params.approval_contract_hash)
    )
    if (!Object.keys(agentPlan).length || !Object.keys(approvalContract).length || !approvalContractHash) continue
    const planTrace = recordValue(agentPlan.trace)
    const planId = stringValue(planTrace.plan_id) || `memory-tree-llm-candidate-batch-execute:${index}`
    const plannerVersion = (
      stringValue(planTrace.planner_version) ||
      stringValue(memoryTreeLlmCandidateBatchOutput.value?.prepare_version)
    )
    const summaryPlan = recordValue(preparation.summary_plan)
    const chapterLabel = chapterIndexLabel(summaryPlan.chapter_index)
    const qualityQuery = stringValue(summaryPlan.quality_query) || stringValue(params.quality_query)
    const candidateLabel = [chapterLabel, qualityQuery].filter(Boolean).join(' ') || `候选 ${index + 1}`
    actions.push({
      key: `memory-tree-llm-candidate-batch-execute:${index}`,
      label: `确认候选摘要：${qualityQuery || candidateLabel}`,
      payload: createMemoryTreeLlmCandidateBatchExecutePayload(
        runId,
        planId,
        `执行 Memory Tree 候选摘要写入：${candidateLabel}`,
        toolName,
        params,
        agentPlan,
        approvalContract,
        approvalContractHash,
        plannerVersion,
      ),
    })
  }
  return actions
})

const knowledgeBaseCandidateRouteActions = computed<KnowledgeBaseCandidateRouteAction[]>(() => {
  const runId = props.run?.id
  if (!runId || props.run?.status !== 'success') return []
  if (!knowledgeBaseCandidateExecutionRecommendedTools.value.includes('inspect_agent_knowledge_base_route')) return []
  const title = knowledgeBaseCandidateExecutionTitle.value
  const params: Record<string, unknown> = {
    query: title,
    limit: 8,
  }
  const chapterIndex = knowledgeBaseCandidateExecutionChapterIndex.value
  if (chapterIndex !== null) params.chapter_index = chapterIndex
  const planId = 'knowledge-candidate-route:0'
  return [{
    key: planId,
    label: `检查知识库：${title}`,
    payload: createKnowledgeBaseRouteReadPayload(
      runId,
      planId,
      `检查知识库写入结果：${title}`,
      params,
    ),
  }]
})

function memoryTreeNodeActionLabel(node: Record<string, unknown>) {
  return stringValue(node.title) || chapterIndexLabel(node.chapter_index) || memoryTreeLevelLabel(node.level)
}

const memoryTreeNodeExpandActions = computed<MemoryTreeDrilldownAction[]>(() => {
  const runId = props.run?.id
  if (!runId || props.run?.status !== 'success') return []
  const actions: MemoryTreeDrilldownAction[] = []
  for (const [index, node] of memoryTreeNodes.value.entries()) {
    const expandNodeId = stringValue(node.id)
    const children = Array.isArray(node.children) ? node.children : []
    if (!expandNodeId || children.length === 0) continue
    const planId = `memory-tree-node-expand:${index}`
    const nodeLabel = memoryTreeNodeActionLabel(node)
    actions.push({
      key: planId,
      label: nodeLabel ? `展开节点：${nodeLabel}` : '展开节点',
      payload: createMemoryTreeReadPayload(
        runId,
        planId,
        `展开 Memory Tree：${nodeLabel || '节点'}`,
        {
          expand_node_id: expandNodeId,
          include_ancestors: true,
          max_depth: 1,
        },
      ),
    })
  }
  return actions
})

const memoryTreeDrilldownActions = computed<MemoryTreeDrilldownAction[]>(() => {
  const runId = props.run?.id
  if (!runId || props.run?.status !== 'success') return []
  const actions: MemoryTreeDrilldownAction[] = []
  for (const [index, drilldown] of recordList(memoryTreeNavigation.value.recommended_drilldowns).entries()) {
    const expandNodeId = stringValue(drilldown.expand_node_id) || stringValue(drilldown.node_id)
    if (!expandNodeId) continue
    const planId = `memory-tree-drilldown:${index}`
    const node = memoryTreeNodesById.value[expandNodeId] || {}
    const nodeLabel = memoryTreeNodeActionLabel(node)
    const params = {
      expand_node_id: expandNodeId,
      include_ancestors: true,
      max_depth: 1,
    }
    actions.push({
      key: planId,
      label: nodeLabel ? `展开推荐节点：${nodeLabel}` : '展开推荐节点',
      payload: createMemoryTreeReadPayload(runId, planId, `展开 Memory Tree：${nodeLabel || '推荐节点'}`, params),
    })
  }
  return actions
})
const memoryTreeSearchAction = computed<MemoryTreeDrilldownAction | null>(() => {
  const runId = props.run?.id
  const query = memoryTreeSearchQueryInput.value.trim()
  if (!runId || props.run?.status !== 'success' || !query) return null
  const planId = 'memory-tree-search:manual'
  return {
    key: planId,
    label: `搜索 Memory Tree：${query}`,
    payload: createMemoryTreeReadPayload(runId, planId, `搜索 Memory Tree：${query}`, {
      query,
      include_ancestors: true,
    }),
  }
})
const hasMemoryLoopProjection = computed(() => Boolean(
  memoryActivationOutput.value
  || retrievalStrategyOutput.value
  || retrievalStrategyQualityOutput.value
  || retrievalPrefetchOutput.value
  || retrievalContextOutput.value
  || postChapterMemoryOutput.value,
))
const hasWorldModelSemanticCheckProjection = computed(() => Boolean(worldModelSemanticCheckOutput.value))
const hasWorldModelProposalReviewProjection = computed(() => Boolean(worldModelProposalReviewOutput.value))
const hasWorldModelResolutionPlanProjection = computed(() => Boolean(worldModelResolutionPlanOutput.value))
const hasTraceAuditProjection = computed(() => Boolean(traceAuditOutput.value))
const hasTraceAuditIntentChain = computed(() => Boolean(
  traceAuditIntentChainStatus.value === 'available' ||
  traceAuditIntentChainRuleId.value ||
  traceAuditIntentChainClass.value ||
  traceAuditIntentChainChapterLabel.value ||
  traceAuditIntentChainRows.value.length,
))
const hasTraceAuditEndToEndChain = computed(() => Boolean(
  traceAuditEndToEndStatus.value ||
  traceAuditEndToEndPlannedCount.value !== null ||
  traceAuditEndToEndToolStepCount.value !== null ||
  traceAuditEndToEndModelTraceCount.value !== null ||
  traceAuditEndToEndResultActionType.value ||
  traceAuditEndToEndSegmentRows.value.length,
))
const hasTraceAuditAnomalySummary = computed(() => Boolean(
  traceAuditAnomalyStatus.value ||
  traceAuditAnomalyIssueCount.value !== null ||
  traceAuditAnomalyIssueRows.value.length,
))
const hasTraceAnomalyTrendsProjection = computed(() => Boolean(
  traceAnomalyTrendsOutput.value &&
  (
    traceAnomalyTrendStatus.value ||
    traceAnomalyTrendRunCount.value !== null ||
    traceAnomalyTrendBaselineRunCount.value !== null ||
    traceAnomalyTrendIssueRows.value.length ||
    traceAnomalyTrendRunRows.value.length ||
    traceAnomalyTrendThresholdSignalRows.value.length ||
    traceAnomalyTrendThresholdConfigLabel.value ||
    traceAnomalyTrendCalibrationStatusLabel.value ||
    traceAnomalyTrendCalibrationGuardRows.value.length ||
    traceAnomalyTrendCalibrationPolicyStatusLabel.value
  ),
))
const hasTraceAnomalyLongRunSamplesProjection = computed(() => Boolean(
  traceAnomalyLongRunSamplesOutput.value &&
  (
    traceAnomalyLongRunStatus.value ||
    traceAnomalyLongRunCollectionStatusLabel.value ||
    traceAnomalyLongRunCandidateCount.value !== null ||
    traceAnomalyLongRunStatusRows.value.length ||
    traceAnomalyLongRunReviewLimit.value !== null ||
    traceAnomalyLongRunRecommendedTools.value.length
  ),
))
const hasTraceAnomalyThresholdReviewProjection = computed(() => Boolean(
  traceAnomalyThresholdReviewOutput.value &&
  (
    traceAnomalyThresholdReviewStatus.value ||
    traceAnomalyThresholdReviewStateLabel.value ||
    traceAnomalyThresholdReviewPolicyDecisionLabel.value ||
    traceAnomalyThresholdReviewSignalCount.value !== null ||
    traceAnomalyThresholdReviewAffectedThresholdLabel.value ||
    traceAnomalyThresholdReviewRecommendedTools.value.length
  ),
))
const hasKnowledgeBaseCandidateExecutionProjection = computed(() => Boolean(knowledgeBaseCandidateExecutionOutput.value))
const hasMemoryTreeProjection = computed(() => Boolean(memoryTreeOutput.value))
const hasMemoryTreeLlmCandidateProjection = computed(() => Boolean(memoryTreeLlmCandidateOutput.value))
const hasMemoryTreeLlmCandidateBatchProjection = computed(() => Boolean(memoryTreeLlmCandidateBatchOutput.value))
const hasMemoryTreeLlmCandidateBatchExecuteProjection = computed(() => (
  Boolean(memoryTreeLlmCandidateBatchExecuteOutput.value)
))
const hasRecommendedFollowupPolicy = computed(() => Boolean(
  recommendedFollowupPreview.value &&
  (
    recommendedFollowupTools.value.length ||
    recommendedFollowupWriteTools.value.length ||
    recommendedFollowupWorkerDispatches.value.length ||
    Object.keys(recommendedFollowupRouteRegistry.value).length
  ),
))
const runKindLabel = computed(() => {
  if (isRecoveryExecutionRun.value) return '恢复执行'
  if (recoveryPreview.value) return '恢复预览'
  if (recommendedFollowupPreview.value) return '后继预览'
  if (props.run?.entrypoint === 'dialog_auto_plan') return '自动规划'
  return '普通运行'
})
const recoverySourceRunId = computed(() => (
  stringValue(runInput.value.recovery_run_id) || stringValue(recoveryPreview.value?.source_run_id)
))
const recoveryPlanHash = computed(() => (
  stringValue(runInput.value.recovery_plan_hash) || stringValue(recoveryPreview.value?.plan_hash)
))
const recoveryExecutePayload = computed(() => {
  const sourceRunId = stringValue(recoveryPreview.value?.source_run_id)
  const planHash = stringValue(recoveryPreview.value?.plan_hash)
  if (
    recoveryPreview.value?.can_execute === true &&
    executionPolicy.value?.status === 'ready' &&
    sourceRunId &&
    planHash
  ) {
    return { sourceRunId, planHash }
  }
  return null
})
const recommendedFollowupExecutePayload = computed(() => {
  const sourceRunId = stringValue(recommendedFollowupPreview.value?.source_run_id)
  const planHash = stringValue(recommendedFollowupPreview.value?.plan_hash)
  if (
    recommendedFollowupTools.value.length &&
    recommendedFollowupExecutionPolicy.value.requires_followup_run === true &&
    sourceRunId &&
    planHash
  ) {
    return { sourceRunId, planHash }
  }
  return null
})
const routeUpgradeContractOutput = computed(() => {
  for (let index = steps.value.length - 1; index >= 0; index -= 1) {
    const step = steps.value[index]
    if (step?.tool_name !== 'preview_pending_action_route_approval_opt_in_apply_contract') continue
    const output = recordValue(step.output)
    if (Object.keys(output).length) return output
  }
  return null
})
const preparedApprovalOutput = computed(() => {
  for (let index = steps.value.length - 1; index >= 0; index -= 1) {
    const output = recordValue(steps.value[index]?.output)
    if (stringValue(output.status) !== 'approval_required') continue
    if (!Object.keys(recordValue(output.agent_plan)).length) continue
    if (!Object.keys(recordValue(output.agent_plan_approval_contract)).length) continue
    if (!stringList(output.recommended_next_tools).length) continue
    return output
  }
  return null
})
const preparedApprovalAgentPlan = computed(() => recordValue(preparedApprovalOutput.value?.agent_plan))
const preparedApprovalContract = computed(() => recordValue(preparedApprovalOutput.value?.agent_plan_approval_contract))
const preparedApprovalContractHash = computed(() => (
  stringValue(preparedApprovalOutput.value?.agent_plan_approval_contract_hash) ||
  stringValue(recordValue(preparedApprovalContract.value.approval).approval_contract_hash)
))
const preparedApprovalNextTools = computed(() => stringList(preparedApprovalOutput.value?.recommended_next_tools))
const preparedApprovalExecuteTool = computed(() => (
  preparedApprovalNextTools.value.find((tool) => tool.endsWith('_with_approval')) || ''
))
const preparedApprovalPlanTrace = computed(() => recordValue(preparedApprovalAgentPlan.value.trace))
const preparedApprovalPlanId = computed(() => stringValue(preparedApprovalPlanTrace.value.plan_id))
const preparedApprovalPlannerVersion = computed(() => (
  stringValue(preparedApprovalPlanTrace.value.planner_version) ||
  stringValue(preparedApprovalOutput.value?.prepare_version)
))
const preparedApprovalPlanSteps = computed(() => recordList(preparedApprovalAgentPlan.value.steps))
const preparedApprovalPlanStep = computed(() => preparedApprovalPlanSteps.value[0] || {})
const preparedApprovalBaseParams = computed(() => recordValue(preparedApprovalPlanStep.value.params))
const preparedApprovalChapterIndex = computed(() => (
  numberValue(preparedApprovalOutput.value?.chapter_index) ??
  numberValue(preparedApprovalBaseParams.value.chapter_index)
))
const preparedApprovalTargetLabel = computed(() => {
  if (preparedApprovalExecuteTool.value === 'execute_record_agent_knowledge_base_candidate_with_approval') {
    return safePostMemoryCandidateLabel(preparedApprovalBaseParams.value.title) || '知识库候选'
  }
  const chapter = preparedApprovalChapterIndex.value
  if (chapter !== null) return `第${chapter}章`
  return preparedApprovalExecuteToolLabel(preparedApprovalExecuteTool.value)
})
const preparedApprovalExecutePayload = computed<PlannerPlanExecutePayload | null>(() => {
  if (props.run?.status !== 'success') return null
  if (!props.run?.id || !preparedApprovalPlanId.value || !preparedApprovalExecuteTool.value) return null
  if (!preparedApprovalContractHash.value || !Object.keys(preparedApprovalContract.value).length) return null
  if (!Object.keys(preparedApprovalAgentPlan.value).length) return null
  return {
    sourceRunId: props.run.id,
    sourcePlanId: preparedApprovalPlanId.value,
    goal: `执行已审批工具：${preparedApprovalExecuteToolLabel(preparedApprovalExecuteTool.value)}`,
    tools: [
      {
        tool_name: preparedApprovalExecuteTool.value,
        params: {
          ...preparedApprovalBaseParams.value,
          confirm_execute: true,
          approval_contract_hash: preparedApprovalContractHash.value,
          approval_contract: preparedApprovalContract.value,
        },
        planner: {
          plan_id: preparedApprovalPlanId.value,
          planner_version: preparedApprovalPlannerVersion.value,
          mutability: 'write',
          requires_confirmation: true,
          reason: '确认执行已准备的写入工具。',
        },
      },
    ],
    planner: {
      ...preparedApprovalAgentPlan.value,
      approval_contract: preparedApprovalContract.value,
    },
    approvalContractHash: preparedApprovalContractHash.value,
    approvalContract: preparedApprovalContract.value,
  }
})
const routeUpgradeStatus = computed(() => stringValue(routeUpgradeContractOutput.value?.status))
const routeUpgradeRequiredConfirmation = computed(() => routeUpgradeContractOutput.value?.required_confirmation === true)
const routeUpgradeContract = computed(() => recordValue(routeUpgradeContractOutput.value?.approval_contract))
const routeUpgradeContractHash = computed(() => stringValue(routeUpgradeContractOutput.value?.approval_contract_hash))
const routeUpgradePendingActionId = computed(() => {
  const output = routeUpgradeContractOutput.value
  const routePreview = recordValue(output?.route_apply_preview)
  const recommendedCall = firstRecommendedRouteApplyCall(output)
  const recommendedParams = recordValue(recommendedCall?.params)
  return (
    stringValue(output?.pending_action_id) ||
    stringValue(routePreview.pending_action_id) ||
    stringValue(recommendedParams.pending_action_id)
  )
})
const canApplyRouteUpgrade = computed(() => {
  const output = routeUpgradeContractOutput.value
  if (!props.run?.id || !output) return false
  if (props.run.entrypoint !== 'pending_action_safety_action') return false
  if (props.run.status !== 'success') return false
  if (routeUpgradeStatus.value !== 'requires_confirmation') return false
  if (!routeUpgradeRequiredConfirmation.value) return false
  if (!routeUpgradePendingActionId.value || !routeUpgradeContractHash.value || !Object.keys(routeUpgradeContract.value).length) return false
  if (String(props.pendingActionId || '').trim() !== routeUpgradePendingActionId.value) return false
  return hasRouteApplyRecommendation(output)
})

function close() {
  emit('close')
}

function refreshRun() {
  emit('refresh')
}

function executeRecovery() {
  if (!recoveryExecutePayload.value) return
  emit('executeRecovery', recoveryExecutePayload.value)
}

function executeRecommendedFollowups() {
  if (!recommendedFollowupExecutePayload.value) return
  emit('executeRecommendedFollowups', recommendedFollowupExecutePayload.value)
}

function executePlannerPlan() {
  if (!plannerExecutePayload.value) return
  emit('executePlannerPlan', plannerExecutePayload.value)
}

function applyRouteUpgrade() {
  if (!canApplyRouteUpgrade.value || !props.run?.id) return
  emit('applyRouteUpgrade', {
    sourceRunId: props.run.id,
    pendingActionId: routeUpgradePendingActionId.value,
    approvalContractHash: routeUpgradeContractHash.value,
    approvalContract: routeUpgradeContract.value,
  })
}

function executePreparedApproval() {
  if (!preparedApprovalExecutePayload.value) return
  emit('executePlannerPlan', preparedApprovalExecutePayload.value)
}

function executeMemoryTreeDrilldown(action: MemoryTreeDrilldownAction) {
  emit('executePlannerPlan', action.payload)
}

function executeMemoryTreeSearch() {
  if (!memoryTreeSearchAction.value) return
  emit('executePlannerPlan', memoryTreeSearchAction.value.payload)
}

function executeMemoryTreeLlmCandidatePrepare(action: PlannerContinuationAction) {
  emit('executePlannerPlan', action.payload)
}

function executeMemoryTreeLlmCandidateBatch(action: PlannerContinuationAction) {
  emit('executePlannerPlan', action.payload)
}

function executePostMemoryCandidatePrepare(action: PlannerContinuationAction) {
  emit('executePlannerPlan', action.payload)
}

function executeKnowledgeBaseCandidateRoute(action: KnowledgeBaseCandidateRouteAction) {
  emit('executePlannerPlan', action.payload)
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value && typeof value === 'object' && !Array.isArray(value))
}

function stringValue(value: unknown) {
  return typeof value === 'string' ? value : ''
}

function numberValue(value: unknown) {
  return typeof value === 'number' && Number.isFinite(value) ? value : null
}

function booleanLabel(value: unknown, trueLabel: string, falseLabel: string) {
  return value === true ? trueLabel : falseLabel
}

function percentLabel(value: unknown) {
  const numericValue = numberValue(value)
  if (numericValue === null) return ''
  return `${Math.round(numericValue * 100)}%`
}

function signedPercentLabel(value: unknown) {
  const numericValue = numberValue(value)
  if (numericValue === null) return ''
  const percent = Math.round(numericValue * 100)
  return `${percent > 0 ? '+' : ''}${percent}%`
}

function agentProfileLabel(profile: unknown) {
  const displayName = stringValue(agentProfileDefinition.value.display_name)
  if (displayName) return displayName
  return agentProfileNameLabel(profile)
}

function agentProfileNameLabel(profile: unknown) {
  const value = stringValue(profile)
  if (value === 'orchestrator') return '编排主控'
  if (value === 'drafting_worker') return '创作执行者'
  if (value === 'reviewer_worker') return '审稿执行者'
  if (value === 'memory_worker') return '记忆维护者'
  if (value === 'retrieval_worker') return '检索取证者'
  if (value === 'world_model_worker') return '世界模型执行者'
  if (value === 'revision_worker') return '修订执行者'
  if (value === 'recovery_worker') return '恢复维护者'
  return value || '未标注'
}

function agentProfileScopeStatusLabel(status: unknown) {
  const value = stringValue(status)
  if (value === 'applied') return '已按身份收窄'
  if (value === 'not_requested') return '未请求身份收窄'
  if (value === 'unknown_profile') return '未知身份，已拒绝工具面'
  return value || '未知'
}

function agentControlPlaneStatusLabel(status: unknown) {
  const value = stringValue(status)
  if (value === 'ready') return '可继续编排'
  if (value === 'degraded') return '需检查'
  if (value === 'needs_attention') return '需处理'
  return value || '未知'
}

function routeRegistryStatusLabel(status: unknown) {
  const value = stringValue(status)
  if (value === 'passed') return '通过'
  if (value === 'needs_attention') return '需处理'
  return value || '未知'
}

function dogfoodEvidenceStatusLabel(status: unknown) {
  const value = stringValue(status)
  if (value === 'ready') return '可用'
  if (value === 'degraded') return '需检查'
  return value || '未知'
}

function plannerIntentLabel(intent: unknown) {
  const value = stringValue(intent)
  if (value === 'setup_project') return '基础设定'
  if (value === 'build_storyline') return '故事线'
  if (value === 'build_outline') return '大纲'
  if (value === 'review_chapter') return '审稿章节'
  if (value === 'continue_next_chapter') return '续写章节'
  if (value === 'recover_blocked_run') return '恢复阻塞'
  if (value === 'inspect_tools') return '工具检查'
  return value || '未知'
}

function plannerStatusLabel(status: unknown) {
  const value = stringValue(status)
  if (value === 'completed') return '已完成'
  if (value === 'blocked') return '已阻塞'
  if (value === 'success') return '成功'
  if (value === 'failed') return '失败'
  return value || '未知'
}

function executionPlanToolStatusLabel(status: unknown) {
  const value = stringValue(status)
  if (value === 'success' || value === 'completed') return '已完成'
  if (value === 'running') return '进行中'
  if (value === 'failed') return '失败'
  if (value === 'blocked') return '已阻止'
  if (value === 'pending') return '待执行'
  return value || '待执行'
}

function plannerApprovalStatusLabel(status: unknown) {
  const value = stringValue(status)
  if (value === 'not_required') return '无需审批'
  if (value === 'requires_confirmation') return '需要审批'
  if (value === 'blocked') return '已阻止'
  return value || '未知'
}

function chapterIndexLabel(value: unknown) {
  const index = numberValue(value)
  return index !== null ? `第${index}章` : ''
}

function profilePolicyAuditLabel(audit: Record<string, unknown>) {
  const status = stringValue(audit.status)
  const summary = recordValue(audit.summary)
  const issueCount = numberValue(summary.issues)
  if (status === 'passed') return '通过'
  if (status === 'needs_attention') {
    return issueCount !== null ? `需关注：${issueCount} 个问题` : '需关注'
  }
  return status
}

function policyStatusLabel(status: unknown) {
  const value = stringValue(status)
  if (value === 'ready') return '可执行'
  if (value === 'requires_user_input') return '需要用户补充输入'
  if (value === 'confirmation_required') return '等待确认'
  if (value === 'repeat_failed_recovery') return '重复失败保护'
  if (value === 'blocked') return '已阻止'
  if (value === 'not_executable') return '不可执行'
  return value || '未知'
}

function guardrailStatusLabel(status: unknown) {
  const value = stringValue(status)
  if (value === 'ready') return '通过'
  if (value === 'blocked') return '已阻止'
  return value || '未知'
}

function routeUpgradeStatusLabel(status: unknown) {
  const value = stringValue(status)
  if (value === 'requires_confirmation') return '等待确认'
  if (value === 'blocked') return '已阻止'
  if (value === 'not_required') return '无需处理'
  if (value === 'success') return '成功'
  return value || '未知'
}

function preparedApprovalExecuteToolLabel(toolName: string) {
  if (toolName === 'execute_generate_chapter_with_approval') return '生成正文'
  if (toolName === 'execute_analyze_chapter_world_model_with_approval') return '分析世界模型'
  if (toolName === 'execute_record_agent_knowledge_base_candidate_with_approval') return '写入知识库候选'
  if (toolName === 'execute_record_agent_memory_tree_llm_candidate_summary_with_approval') return '写入 Memory Tree 候选摘要'
  if (toolName === 'execute_repair_longform_maintenance_with_approval') return '修复长篇维护'
  return toolName || '写入工具'
}

function knowledgeBaseCandidateTypeLabel(memoryType: unknown) {
  const value = stringValue(memoryType)
  if (value === 'writing_pattern') return '写法模式'
  if (value === 'self_optimization_lesson') return '自优化经验'
  if (value === 'author_preference') return '作者偏好'
  if (value === 'project_policy') return '项目策略'
  if (value === 'learned_rule') return '学习规则'
  return value || '知识库候选'
}

function postChapterMemoryCaptureStatusLabel(status: unknown) {
  const value = stringValue(status)
  if (value === 'ready') return '可写入候选'
  if (value === 'needs_review') return '需要审稿'
  if (value === 'missing_chapter') return '缺少章节'
  return value || '未知'
}

function memoryActivationStatusLabel(status: unknown) {
  const value = stringValue(status)
  if (value === 'ready') return '已激活'
  if (value === 'degraded') return '降级激活'
  if (value === 'blocked') return '已阻止'
  return value || '未知'
}

function memoryTreeStatusLabel(status: unknown) {
  const value = stringValue(status)
  if (value === 'ready') return '可用'
  if (value === 'success' || value === 'completed') return '已完成'
  if (value === 'running') return '生成中'
  if (value === 'failed') return '失败'
  if (value === 'blocked') return '已阻止'
  if (value === 'approval_required') return '等待确认'
  return value || '未知'
}

function memoryTreeLevelLabel(level: unknown) {
  const value = stringValue(level)
  if (value === 'volume') return '卷'
  if (value === 'chapter') return '章节'
  if (value === 'scene') return '场景'
  if (value === 'beat') return '节拍'
  return value || '节点'
}

function memoryTreeLevelDepth(level: unknown) {
  const value = stringValue(level)
  if (value === 'chapter') return 1
  if (value === 'scene') return 2
  if (value === 'beat') return 3
  return 0
}

function memoryTreeNavigationModeLabel(mode: unknown) {
  const value = stringValue(mode)
  if (value === 'semantic_search_with_ancestors') return '语义搜索 + 祖先'
  if (value === 'semantic_search') return '语义搜索'
  if (value === 'search_with_ancestors') return '搜索 + 祖先'
  if (value === 'expanded_subtree') return '展开子树'
  if (value === 'filtered') return '筛选'
  return value || '未知'
}

function memoryTreeLlmCandidateQualityLabel(status: unknown) {
  const value = stringValue(status)
  if (value === 'ready') return '通过'
  if (value === 'degraded') return '降级'
  if (value === 'blocked') return '已阻止'
  return value
}

function memoryTreeLlmCandidateMaterializationLabel(status: unknown) {
  const value = stringValue(status)
  if (value === 'pending') return '待物化'
  if (value === 'materialized') return '已物化'
  if (value === 'hash_mismatch') return '摘要冲突'
  if (value === 'not_ready') return '未就绪'
  return value
}

function safeMemoryTreeDisplayLabel(label: unknown) {
  const value = stringValue(label).replace(/\s+/g, ' ')
  if (!value) return ''
  if (/[A-Za-z_]+:[A-Za-z0-9_-]+/.test(value)) return ''
  if (/source_refs|source_id|approval_contract|approval:|chapter-content-\d+|memory-\d+/i.test(value)) return ''
  return value.slice(0, 64)
}

function safePostMemoryCandidateLabel(label: unknown) {
  const value = stringValue(label).replace(/\s+/g, ' ')
  if (!value) return ''
  if (/[A-Za-z_]+:[A-Za-z0-9_-]+/.test(value)) return ''
  if (/source_refs|source_id|approval_contract|approval:|chapter-content-\d+|writing_agent_step:/i.test(value)) return ''
  return value.slice(0, 64)
}

function safeRetrievalContextSummaryText(label: unknown) {
  const value = stringValue(label).replace(/\s+/g, ' ')
  if (!value) return ''
  if (/[A-Za-z_]+:[A-Za-z0-9_.:-]+/.test(value)) return ''
  if (/project-secret|candidate-secret|memory-secret|retrieval-secret|source_refs?|source_type|source_id|memory_id|candidate_id|retrieval_internal|retrieval-vector|query_vector_cache_key|memory_provenance|retrieval_items|phase\d+\.agent_retrieval_context/i.test(value)) return ''
  return value.slice(0, 120)
}

function safeWorldModelRouteText(label: unknown) {
  const value = stringValue(label).replace(/\s+/g, ' ')
  if (!value) return ''
  if (/[A-Za-z_]+:[A-Za-z0-9_.-]+/.test(value)) return ''
  if (/(project|profile|fact|cluster|item|bundle)-secret|source_refs?|source_id|evidence_refs?|approval_contract|approval:|world_profile:/i.test(value)) return ''
  return value.slice(0, 96)
}

function safeWorldModelSemanticText(label: unknown) {
  const value = stringValue(label).replace(/\s+/g, ' ')
  if (!value) return ''
  if (/[A-Za-z_]+:[A-Za-z0-9_.-]+/.test(value)) return ''
  if (/(project|profile|fact|claim|trace|prompt)-secret|source_refs?|source_id|evidence_refs?|claim_id|llm_prompt_contract|prompt_contract|template_hash|raw prompt|phase\d+\.world_model_semantic_check|world_profile:/i.test(value)) return ''
  return value.slice(0, 120)
}

function safeTraceAuditText(label: unknown) {
  const value = stringValue(label).replace(/\s+/g, ' ')
  if (!value) return ''
  if (/[A-Za-z_]+:[A-Za-z0-9_-]+/.test(value)) return ''
  if (/(run|step|trace|message|task|target|chapter-content|longform)-secret|source_refs?|source_id|approval_contract|approval:/i.test(value)) return ''
  return value.slice(0, 96)
}

function worldModelRouteStatusLabel(status: unknown) {
  const value = stringValue(status)
  if (value === 'ready') return '可用'
  if (value === 'blocked') return '已阻塞'
  if (value === 'completed' || value === 'success') return '已完成'
  if (value === 'missing_profile') return '缺少 Profile'
  return value || '未知'
}

function worldModelSemanticStatusLabel(status: unknown) {
  const value = stringValue(status)
  if (value === 'passed') return '通过'
  if (value === 'issues_found') return '已发现问题'
  if (value === 'blocked') return '已阻塞'
  if (value === 'failed') return '失败'
  if (value === 'completed' || value === 'success' || value === 'ready') return '已完成'
  return value || '未知'
}

function worldModelSemanticSeverityLabel(severity: unknown) {
  const value = stringValue(severity)
  if (value === 'error') return '错误'
  if (value === 'warning') return '警告'
  if (value === 'info') return '提示'
  return safeWorldModelSemanticText(value)
}

function worldModelRiskLabel(risk: unknown) {
  const value = stringValue(risk)
  if (value === 'high') return '高风险'
  if (value === 'medium') return '中风险'
  if (value === 'low') return '低风险'
  return value
}

function worldModelReviewModeLabel(mode: unknown) {
  const value = stringValue(mode)
  if (value === 'individual') return '逐项审阅'
  if (value === 'batch') return '批量审阅'
  return value
}

function worldModelResolutionActionTypeLabel(actionType: unknown) {
  const value = stringValue(actionType)
  if (value === 'review_individual') return '逐项审阅'
  if (value === 'review_batch') return '批量审阅'
  return value
}

function worldModelRecommendedResolutionLabel(resolution: unknown) {
  const value = stringValue(resolution)
  if (value === 'manual_individual_review') return '手动逐项审阅'
  if (value === 'batch_review') return '批量审阅'
  return value
}

function worldModelChapterRangeLabel(rangeValue: unknown) {
  const range = recordValue(rangeValue)
  const start = numberValue(range.start)
  const end = numberValue(range.end)
  if (start !== null && end !== null && start !== end) return `第${start}-${end}章`
  if (start !== null) return chapterIndexLabel(start)
  if (end !== null) return chapterIndexLabel(end)
  return ''
}

function traceAuditStatusLabel(status: unknown) {
  const value = stringValue(status)
  if (value === 'completed' || value === 'success' || value === 'ready' || value === 'passed') return '已完成'
  if (value === 'blocked') return '阻塞'
  if (value === 'failed') return '失败'
  if (value === 'running') return '运行中'
  if (value === 'executed') return '已执行'
  if (value === 'pending') return '等待中'
  if (value === 'cancelled') return '已取消'
  if (value === 'needs_attention') return '需处理'
  return value || '未知'
}

function traceAuditAnomalyStatusLabel(status: unknown) {
  const value = stringValue(status)
  if (value === 'clear') return '正常'
  if (value === 'informational') return '提示'
  if (value === 'needs_attention') return '需处理'
  return traceAuditStatusLabel(value)
}

function traceAuditAnomalySeverityLabel(severity: unknown) {
  const value = stringValue(severity)
  if (value === 'critical') return '严重'
  if (value === 'warning') return '警告'
  if (value === 'info') return '提示'
  return safeTraceAuditText(value)
}

function traceAuditEndToEndStatusLabel(status: unknown) {
  const value = stringValue(status)
  if (value === 'complete') return '完整'
  if (value === 'partial') return '部分'
  if (value === 'missing') return '缺失'
  return traceAuditStatusLabel(value)
}

function traceAuditAvailabilityLabel(status: unknown) {
  const value = stringValue(status)
  if (value === 'available') return '可用'
  if (value === 'missing') return '缺失'
  return traceAuditStatusLabel(value)
}

function traceAuditActionStatusLabel(status: unknown) {
  const value = stringValue(status)
  if (value === 'success' || value === 'completed') return '成功'
  if (value === 'ready') return '可用'
  if (value === 'failed') return '失败'
  if (value === 'blocked') return '阻塞'
  if (value === 'running') return '运行中'
  return value
}

function traceAuditEndToEndStageLabel(stage: unknown) {
  const value = stringValue(stage)
  if (!value) return ''
  if (value === 'intent') return '意图'
  if (value === 'planned_tools') return '计划工具'
  if (value === 'executed_tools') return '执行工具'
  if (value === 'model_traces') return '模型 Trace'
  if (value === 'result_message') return '结果消息'
  return safeTraceAuditText(value)
}

function traceAuditAnomalyCodeLabel(code: unknown) {
  const value = stringValue(code)
  if (value === 'failed_tool_step') return '工具步骤失败'
  if (value === 'failed_model_trace') return '模型 Trace 失败'
  if (value === 'missing_trace_binding') return '缺少 Trace 绑定'
  if (value === 'planned_tool_not_executed') return '计划工具未执行'
  if (value === 'missing_result_message') return '结果消息缺失'
  if (value === 'truncated_context_block') return '上下文块已截断'
  return safeTraceAuditText(value)
}

function traceAnomalyThresholdSignalLabel(code: unknown) {
  const value = stringValue(code)
  if (value === 'affected_run_rate_spike') return '受影响运行率升高'
  if (value === 'critical_issue_rate_spike') return '严重异常率升高'
  return safeTraceAuditText(value)
}

function traceAnomalyThresholdConfigLabel(status: unknown) {
  const value = stringValue(status)
  if (value === 'configured') return '项目配置'
  if (value === 'partial') return '部分配置'
  if (value === 'default') return '内置默认'
  return ''
}

function traceAnomalyCalibrationStatusLabel(status: unknown) {
  const value = stringValue(status)
  if (value === 'needs_tuning') return '需要调参'
  if (value === 'calibrated') return '已校准'
  if (value === 'insufficient_data') return '样本不足'
  return traceAuditStatusLabel(value)
}

function traceAnomalyCalibrationGuardStatusLabel(status: unknown) {
  const value = stringValue(status)
  if (value === 'triggered') return '触发'
  if (value === 'passed') return '通过'
  if (value === 'skipped') return '跳过'
  return traceAuditStatusLabel(value)
}

function traceAnomalyCalibrationGuardReasonLabel(reason: unknown) {
  const value = stringValue(reason)
  if (value === 'recent_anomalies_below_current_threshold') return '近期异常低于当前阈值'
  if (value === 'threshold_signal_has_only_info_anomalies') return '仅提示级异常触发'
  if (value === 'threshold_signal_present') return '阈值信号已触发'
  if (value === 'no_threshold_signal') return '无阈值信号'
  if (value === 'no_actionable_anomaly') return '无可行动异常'
  if (value === 'actionable_threshold_signal') return '可行动阈值信号'
  if (value === 'insufficient_window_data') return '样本不足'
  return ''
}

function traceAnomalyPolicyStatusLabel(status: unknown) {
  const value = stringValue(status)
  if (value === 'review_required') return '需复核'
  if (value === 'eligible_for_promotion') return '可固化'
  if (value === 'collecting_samples') return '收集样本'
  return traceAuditStatusLabel(value)
}

function traceAnomalyPolicyDecisionLabel(decision: unknown) {
  const value = stringValue(decision)
  if (value === 'lower_affected_run_rate_delta_threshold') return '降低异常阈值'
  if (value === 'raise_affected_run_rate_delta_threshold') return '提高异常阈值'
  if (value === 'keep_current_thresholds') return '保留当前阈值'
  if (value === 'collect_more_samples') return '继续收集样本'
  return ''
}

function traceAnomalyPolicyPromotionLabel(value: unknown) {
  if (value === true) return '可固化'
  if (value === false) return '不可固化'
  return ''
}

function traceAnomalyLongRunSampleStatusLabel(status: unknown) {
  const value = stringValue(status)
  if (value === 'ready_for_threshold_review') return '可复核'
  if (value === 'collecting_samples') return '收集样本'
  return traceAuditStatusLabel(value)
}

function traceAnomalyRunStatusCountLabel(status: unknown) {
  const value = stringValue(status)
  if (value === 'success') return '成功'
  if (value === 'blocked') return '已阻塞'
  if (value === 'failed') return '失败'
  if (value === 'running') return '运行中'
  if (value === 'pending') return '等待中'
  if (value === 'cancelled') return '已取消'
  return safeTraceAuditText(value)
}

function traceAnomalyThresholdReviewStatusLabel(status: unknown) {
  const value = stringValue(status)
  if (value === 'ready_for_manual_review') return '可人工复核'
  if (value === 'collecting_samples') return '收集样本'
  return traceAuditStatusLabel(value)
}

function traceAnomalyThresholdReviewDecisionLabel(decision: unknown) {
  const value = stringValue(decision)
  if (value === 'keep_current_thresholds') return '保持当前阈值'
  if (value === 'collect_more_samples') return '继续收集样本'
  if (value === 'raise_affected_run_rate_delta_threshold') return '提高异常阈值'
  if (value === 'lower_affected_run_rate_delta_threshold') return '降低异常阈值'
  return ''
}

function traceAuditEventLabel(event: Record<string, unknown>) {
  const eventType = stringValue(event.event_type)
  if (eventType === 'dialog_route_decision') {
    return safeTraceAuditText(event.selected_route_label) || '对话路由'
  }
  if (eventType === 'approval_decision') {
    return ['审批', safeTraceAuditText(event.decision_label)].filter(Boolean).join('：')
  }
  if (eventType === 'run_dispatched') {
    return ['运行派发', traceAuditStatusLabel(event.status)].filter(Boolean).join('：')
  }
  if (eventType === 'tool_step') {
    const stepIndex = numberValue(event.step_index)
    const toolName = safeTraceAuditText(event.tool_name)
    return ['工具步骤', stepIndex !== null ? `#${stepIndex}` : '', toolName].filter(Boolean).join(' ')
  }
  if (eventType === 'trace_attached') {
    return ['Trace', safeTraceAuditText(event.trace_type)].filter(Boolean).join(' ')
  }
  return safeTraceAuditText(eventType)
}

function traceAuditEventDetail(event: Record<string, unknown>) {
  const eventType = stringValue(event.event_type)
  if (eventType === 'dialog_route_decision') {
    return safeTraceAuditText(event.reason_label)
  }
  if (eventType === 'approval_decision') {
    return safeTraceAuditText(event.action_type)
  }
  if (eventType === 'run_dispatched') {
    return safeTraceAuditText(event.entrypoint)
  }
  if (eventType === 'tool_step' || eventType === 'trace_attached') {
    return traceAuditStatusLabel(event.status)
  }
  return ''
}

function countRangeLabel(returned: number | null, total: number | null) {
  if (returned !== null && total !== null) return `${returned} / ${total}`
  if (returned !== null) return `${returned}`
  if (total !== null) return `${total}`
  return ''
}

function retrievalSourceTypeLabel(sourceType: string) {
  if (sourceType === 'knowledge_base_candidate') return '知识库候选'
  if (sourceType === 'longform_memory') return '长篇记忆'
  if (sourceType === 'world_fact') return '世界事实'
  return ''
}

function recordValue(value: unknown): Record<string, unknown> {
  return isRecord(value) ? value : {}
}

function recordList(value: unknown) {
  if (!Array.isArray(value)) return []
  return value.filter(isRecord)
}

function latestToolStep(toolName: string) {
  for (let index = steps.value.length - 1; index >= 0; index -= 1) {
    const step = steps.value[index]
    if (step?.tool_name !== toolName) continue
    return step
  }
  return null
}

function latestToolOutput(toolName: string) {
  for (let index = steps.value.length - 1; index >= 0; index -= 1) {
    const step = steps.value[index]
    if (step?.tool_name !== toolName) continue
    const output = recordValue(step.output)
    if (Object.keys(output).length) return output
  }
  return null
}

function firstRecommendedRouteApplyCall(output: Record<string, unknown> | null | undefined) {
  const calls = Array.isArray(output?.recommended_next_tool_calls) ? output.recommended_next_tool_calls : []
  return calls
    .filter(isRecord)
    .find((call) => call.tool_name === 'apply_pending_action_route_approval_opt_in') || null
}

function hasRouteApplyRecommendation(output: Record<string, unknown>) {
  const tools = Array.isArray(output.recommended_next_tools) ? output.recommended_next_tools : []
  if (tools.includes('apply_pending_action_route_approval_opt_in')) return true
  return Boolean(firstRecommendedRouteApplyCall(output))
}

function stringList(value: unknown) {
  if (!Array.isArray(value)) return []
  return value
    .map((item) => stringValue(item))
    .filter(Boolean)
}

function toolNameList(value: unknown) {
  if (!Array.isArray(value)) return []
  return value
    .map((item) => {
      if (typeof item === 'string') return item.trim()
      return stringValue(recordValue(item).tool_name)
    })
    .filter(Boolean)
}

function toolRequestList(value: unknown) {
  if (!Array.isArray(value)) return []
  return value
    .filter(isRecord)
    .filter((item) => Boolean(stringValue(item.tool_name)))
}

function uniqueStrings(values: string[]) {
  return [...new Set(values)]
}

function dependencyList(value: unknown) {
  if (!Array.isArray(value)) return []
  return value
    .map((item) => {
      if (typeof item === 'string') return { code: item }
      return recordValue(item)
    })
    .filter((item) => Object.keys(item).length > 0)
}

function referencePatternList(value: unknown) {
  if (!Array.isArray(value)) return []
  return value.filter(isRecord)
}

function sourceLinesLabel(value: unknown) {
  const lines = stringList(value)
  return lines.length ? `lines ${lines.join(', ')}` : ''
}

function appliedPatternsLabel(value: unknown) {
  return stringList(value).join(', ')
}

function workerDispatchName(dispatch: Record<string, unknown>) {
  return agentProfileNameLabel(recordValue(dispatch.worker).name)
}

function workerDispatchTaskLabel(dispatch: Record<string, unknown>) {
  const summary = recordValue(dispatch.summary)
  const planned = numberValue(summary.planned_tasks)
  const blocked = numberValue(summary.blocked_tasks)
  const issues = numberValue(summary.issues)
  const parts = []
  if (planned !== null) parts.push(`${planned} 个任务`)
  if (blocked !== null && blocked > 0) parts.push(`${blocked} 个阻塞`)
  if (issues !== null && issues > 0) parts.push(`${issues} 个问题`)
  return parts.join(' · ')
}

function toolChapterLabel(tool: Record<string, unknown>) {
  const params = recordValue(tool.params)
  return chapterIndexLabel(params.chapter_index)
}

function missingDependencyCode(value: Record<string, unknown>) {
  return stringValue(value.code) || stringValue(value.reason) || 'unknown_dependency'
}

function missingDependencyTool(value: Record<string, unknown>) {
  return stringValue(value.tool_name)
}
</script>

<template>
  <BaseModal
    :open="open"
    title="Agent 运行详情"
    width="720px"
    test-id="agent-run-drawer"
    @close="close"
  >
    <div class="agent-run-drawer">
      <p v-if="loading" class="agent-run-drawer__state">正在加载 Agent 运行详情...</p>
      <p v-else-if="error" class="agent-run-drawer__state agent-run-drawer__state--error">{{ error }}</p>
      <p v-else-if="!run" class="agent-run-drawer__state">暂无运行详情。</p>
      <template v-else>
        <section class="agent-run-drawer__summary">
          <div class="agent-run-drawer__summary-head">
            <div>
              <span class="agent-run-drawer__eyebrow">目标</span>
              <h4>{{ run.goal }}</h4>
            </div>
            <button
              type="button"
              class="agent-run-drawer__ghost"
              data-testid="refresh-agent-run"
              @click="refreshRun"
            >
              刷新运行
            </button>
          </div>
          <dl>
            <div>
              <dt>状态</dt>
              <dd>{{ run.status }}</dd>
            </div>
            <div>
              <dt>入口</dt>
              <dd>{{ run.entrypoint }}</dd>
            </div>
            <div>
              <dt>运行 ID</dt>
              <dd>{{ run.id }}</dd>
            </div>
            <div>
              <dt>运行类型</dt>
              <dd>{{ runKindLabel }}</dd>
            </div>
            <div v-if="hasAgentProfileProjection">
              <dt>Agent 身份</dt>
              <dd>{{ agentProfileLabel(agentProfile) }}</dd>
            </div>
            <div v-if="agentProfileTier">
              <dt>编排层级</dt>
              <dd>{{ agentProfileTier }}</dd>
            </div>
            <div v-if="agentProfileDelegationAllowed !== null">
              <dt>委派</dt>
              <dd>{{ agentProfileDelegationAllowed ? '可委派' : '不可委派' }}</dd>
            </div>
            <div v-if="agentProfileDelegateTargetCount > 0">
              <dt>可委派目标</dt>
              <dd>{{ agentProfileDelegateTargetCount }} 个声明</dd>
            </div>
            <div v-if="toolDiscoveryStatus">
              <dt>工具面</dt>
              <dd>{{ agentProfileScopeStatusLabel(toolDiscoveryStatus) }}</dd>
            </div>
            <div v-if="allowedVisibleToolCount !== null">
              <dt>可见工具</dt>
              <dd>{{ allowedVisibleToolCount }}</dd>
            </div>
            <div v-if="profileFilteredVisibleToolCount !== null">
              <dt>已过滤</dt>
              <dd>{{ profileFilteredVisibleToolCount }}</dd>
            </div>
            <div v-if="agentProfilePolicyAuditLabel">
              <dt>策略审计</dt>
              <dd>{{ agentProfilePolicyAuditLabel }}</dd>
            </div>
            <div v-if="hasAgentCommandContracts">
              <dt>命令契约</dt>
              <dd>已投影</dd>
            </div>
            <div v-if="agentControlCommandCount !== null">
              <dt>控制命令</dt>
              <dd>{{ agentControlCommandCount }}</dd>
            </div>
            <div v-if="agentCommandContractGapCount !== null">
              <dt>契约缺口</dt>
              <dd>{{ agentCommandContractGapCount }}</dd>
            </div>
            <div v-if="hasAgentControlPlaneReadiness">
              <dt>控制平面</dt>
              <dd>{{ agentControlPlaneStatusLabel(agentControlPlaneStatus) }}</dd>
            </div>
            <div v-if="agentControlPlaneTotalGapCount !== null">
              <dt>控制面缺口</dt>
              <dd>{{ agentControlPlaneTotalGapCount }}</dd>
            </div>
            <div v-if="agentControlPlaneToolGapCount !== null">
              <dt>工具缺口</dt>
              <dd>{{ agentControlPlaneToolGapCount }}</dd>
            </div>
            <div v-if="agentControlPlaneCommandGapCount !== null">
              <dt>命令缺口</dt>
              <dd>{{ agentControlPlaneCommandGapCount }}</dd>
            </div>
            <div v-if="agentControlPlaneRecommendedCheckCount > 0">
              <dt>建议检查</dt>
              <dd>{{ agentControlPlaneRecommendedCheckCount }}</dd>
            </div>
            <div v-if="agentWorkerRouteRegistryStatus">
              <dt>Worker 路由</dt>
              <dd>{{ routeRegistryStatusLabel(agentWorkerRouteRegistryStatus) }}</dd>
            </div>
            <div v-if="agentWorkerRouteUnroutedToolCount !== null">
              <dt>未路由工具</dt>
              <dd>{{ agentWorkerRouteUnroutedToolCount }}</dd>
            </div>
            <div v-if="agentWorkerRouteIssueCount !== null && agentWorkerRouteIssueCount > 0">
              <dt>路由问题</dt>
              <dd>{{ agentWorkerRouteIssueCount }}</dd>
            </div>
            <div v-if="agentDogfoodEvidenceStatus">
              <dt>Dogfood 证据</dt>
              <dd>{{ dogfoodEvidenceStatusLabel(agentDogfoodEvidenceStatus) }}</dd>
            </div>
            <div v-if="agentDogfoodCoveredCapabilityCount !== null && agentDogfoodRequiredCapabilityCount !== null">
              <dt>能力覆盖</dt>
              <dd>{{ agentDogfoodCoveredCapabilityCount }} / {{ agentDogfoodRequiredCapabilityCount }}</dd>
            </div>
            <div v-if="agentDogfoodGeneratedChapterCount !== null">
              <dt>生成章节</dt>
              <dd>{{ agentDogfoodGeneratedChapterCount }}</dd>
            </div>
            <div v-if="agentDogfoodMissingSourceCount !== null">
              <dt>缺失来源</dt>
              <dd>{{ agentDogfoodMissingSourceCount }}</dd>
            </div>
            <div v-if="recoverySourceRunId">
              <dt>来源运行</dt>
              <dd>{{ recoverySourceRunId }}</dd>
            </div>
            <div v-if="recoveryPlanHash">
              <dt>计划哈希</dt>
              <dd>{{ recoveryPlanHash }}</dd>
            </div>
          </dl>
        </section>

        <AgentRunReferenceAlignmentPanel
          v-if="referenceAlignmentOutput"
          :output="referenceAlignmentOutput"
        />

        <AgentRunWriteGateCoveragePanel
          v-if="writeGateCoverageOutput"
          :output="writeGateCoverageOutput"
        />

        <AgentRunEventProjectionPanel
          v-if="eventProjectionOutput"
          :output="eventProjectionOutput"
        />

        <AgentRunJobProjectionPanel
          v-if="jobProjectionOutput"
          :output="jobProjectionOutput"
        />

        <AgentRunChapterConflictRecoveryPanel
          v-if="chapterConflictRecoveryOutput"
          :output="chapterConflictRecoveryOutput"
        />

        <AgentRunWorkerDispatchPanel
          v-if="workerDispatchOutput"
          :output="workerDispatchOutput"
        />

        <section
          v-if="hasExecutionPlanProgress"
          class="agent-run-drawer__execution-plan"
          aria-label="Agent execution plan progress"
        >
          <h4>执行计划</h4>
          <dl class="agent-run-drawer__facts">
            <div v-if="executionPlanToolCount > 0">
              <dt>计划工具</dt>
              <dd>{{ executionPlanToolCount }} 个</dd>
            </div>
            <div v-if="executionPlanToolCount > 0">
              <dt>已执行</dt>
              <dd>{{ executionPlanExecutedCount }} / {{ executionPlanToolCount }}</dd>
            </div>
            <div v-if="executionPlanCompletedCount > 0">
              <dt>已完成</dt>
              <dd>{{ executionPlanCompletedCount }} 个</dd>
            </div>
            <div v-if="executionPlanRunningCount > 0">
              <dt>进行中</dt>
              <dd>{{ executionPlanRunningCount }} 个</dd>
            </div>
            <div v-if="executionPlanNextTool">
              <dt>下一步</dt>
              <dd>{{ executionPlanNextTool }}</dd>
            </div>
          </dl>
          <ol
            v-if="executionPlanToolRows.length"
            class="agent-run-drawer__execution-tools"
          >
            <li
              v-for="row in executionPlanToolRows"
              :key="row.key"
              data-testid="execution-plan-tool"
            >
              <span>{{ row.toolName }}</span>
              <strong>{{ row.statusLabel }}</strong>
            </li>
          </ol>
        </section>

        <section
          v-if="hasPlannerProjection"
          class="agent-run-drawer__planner"
          aria-label="Agent planner projection"
        >
          <h4>Agent 规划投影</h4>
          <dl class="agent-run-drawer__facts">
            <div v-if="plannerIntentClass">
              <dt>意图</dt>
              <dd>{{ plannerIntentLabel(plannerIntentClass) }}</dd>
            </div>
            <div v-if="plannerStatus">
              <dt>规划状态</dt>
              <dd>{{ plannerStatusLabel(plannerStatus) }}</dd>
            </div>
            <div v-if="plannerChapterIndex !== null">
              <dt>章节</dt>
              <dd>{{ chapterIndexLabel(plannerChapterIndex) }}</dd>
            </div>
            <div v-if="plannerVersion">
              <dt>规划器</dt>
              <dd>{{ plannerVersion }}</dd>
            </div>
            <div v-if="plannerApprovalStatus">
              <dt>审批</dt>
              <dd>{{ plannerApprovalStatusLabel(plannerApprovalStatus) }}</dd>
            </div>
            <div v-if="plannerSelectedTools.length">
              <dt>工具链</dt>
              <dd>{{ plannerSelectedTools.length }} 个工具</dd>
            </div>
            <div v-if="plannerRiskFlags.length">
              <dt>风险</dt>
              <dd>{{ plannerRiskFlags.length }} 项</dd>
            </div>
            <div v-if="plannerMissingDependencies.length">
              <dt>缺依赖</dt>
              <dd>{{ plannerMissingDependencies.length }} 项</dd>
            </div>
            <div v-if="plannerReferencePatterns.length">
              <dt>参考模式</dt>
              <dd>{{ plannerReferencePatterns.length }} 个来源</dd>
            </div>
            <div v-if="plannerReferencePatternVersion">
              <dt>模式版本</dt>
              <dd>{{ plannerReferencePatternVersion }}</dd>
            </div>
          </dl>
          <ul
            v-if="plannerSelectedTools.length"
            class="agent-run-drawer__tools"
          >
            <li
              v-for="tool in plannerSelectedTools"
              :key="`planner-tool:${tool}`"
            >
              {{ tool }}
            </li>
          </ul>
          <ul
            v-if="plannerRiskFlags.length"
            class="agent-run-drawer__planner-signals"
          >
            <li
              v-for="flag in plannerRiskFlags"
              :key="`planner-risk:${flag}`"
            >
              {{ flag }}
            </li>
          </ul>
          <ul
            v-if="plannerMissingDependencies.length"
            class="agent-run-drawer__planner-signals"
          >
            <li
              v-for="(dependency, index) in plannerMissingDependencies"
              :key="`planner-dependency:${missingDependencyCode(dependency)}:${index}`"
            >
              <strong>{{ missingDependencyCode(dependency) }}</strong>
              <span v-if="missingDependencyTool(dependency)">{{ missingDependencyTool(dependency) }}</span>
            </li>
          </ul>
          <ul
            v-if="plannerReferencePatterns.length"
            class="agent-run-drawer__reference-patterns"
          >
            <li
              v-for="(pattern, index) in plannerReferencePatterns"
              :key="`reference-pattern:${pattern.source || index}`"
            >
              <div>
                <strong>{{ pattern.source || 'unknown-source' }}</strong>
                <span v-if="sourceLinesLabel(pattern.source_lines)">{{ sourceLinesLabel(pattern.source_lines) }}</span>
              </div>
              <p v-if="appliedPatternsLabel(pattern.applied_patterns)">{{ appliedPatternsLabel(pattern.applied_patterns) }}</p>
              <p v-if="pattern.decision">{{ pattern.decision }}</p>
            </li>
          </ul>
          <div v-if="plannerExecutePayload" class="agent-run-drawer__actions">
            <button
              type="button"
              class="agent-run-drawer__execute"
              data-testid="execute-planner-plan"
              @click="executePlannerPlan"
            >
              确认执行规划工具链
            </button>
          </div>
        </section>

        <section
          v-if="hasMemoryLoopProjection"
          class="agent-run-drawer__memory-loop"
          aria-label="Agent memory loop"
        >
          <h4>Agent 记忆闭环</h4>
          <dl class="agent-run-drawer__facts">
            <div v-if="memoryActivationOutput">
              <dt>写前激活</dt>
              <dd>{{ memoryActivationStatusLabel(memoryActivationStatus) }}</dd>
            </div>
            <div v-if="memoryActivationLongformCount !== null">
              <dt>长篇记忆</dt>
              <dd>长篇记忆 {{ memoryActivationLongformCount }}</dd>
            </div>
            <div v-if="memoryActivationKnowledgeBaseCount !== null">
              <dt>知识库经验</dt>
              <dd>知识库经验 {{ memoryActivationKnowledgeBaseCount }}</dd>
            </div>
            <div v-if="retrievalContextCoverageLabel">
              <dt>检索证据</dt>
              <dd>{{ retrievalContextCoverageLabel }}</dd>
            </div>
            <div v-if="retrievalPrimarySourceLabel">
              <dt>检索来源</dt>
              <dd>{{ retrievalPrimarySourceLabel }}</dd>
            </div>
            <div v-if="postChapterMemoryOutput">
              <dt>写后记忆</dt>
              <dd>{{ postChapterMemoryChapterLabel }} {{ postChapterMemoryCaptureStatusLabel(postChapterMemoryCaptureStatus) }}</dd>
            </div>
            <div v-if="postChapterMemoryCandidateCount !== null">
              <dt>候选</dt>
              <dd>候选 {{ postChapterMemoryCandidateCount }}</dd>
            </div>
            <div v-if="postChapterMemoryReviewStepCount !== null">
              <dt>审稿</dt>
              <dd>审稿证据 {{ postChapterMemoryReviewStepCount }}</dd>
            </div>
          </dl>
          <ul
            v-if="retrievalRecommendedTools.length"
            class="agent-run-drawer__tools"
          >
            <li
              v-for="tool in retrievalRecommendedTools"
              :key="`retrieval-next:${tool}`"
            >
              {{ tool }}
            </li>
          </ul>
          <ul
            v-if="postChapterMemoryRecommendedTools.length"
            class="agent-run-drawer__write-tools"
          >
            <li
              v-for="tool in postChapterMemoryRecommendedTools"
              :key="`post-memory-next:${tool}`"
            >
              {{ tool }}
            </li>
          </ul>
          <div
            v-if="postChapterMemoryCandidatePrepareActions.length"
            class="agent-run-drawer__actions"
          >
            <button
              v-for="action in postChapterMemoryCandidatePrepareActions"
              :key="action.key"
              type="button"
              class="agent-run-drawer__ghost"
              data-testid="post-memory-candidate-prepare"
              @click="executePostMemoryCandidatePrepare(action)"
            >
              {{ action.label }}
            </button>
          </div>
        </section>

        <AgentRunPostChapterMemoryPanel
          v-if="postChapterMemoryOutput"
          :output="postChapterMemoryOutput"
        />

        <AgentRunRetrievalStrategyPanel
          v-if="retrievalStrategyOutput"
          :output="retrievalStrategyOutput"
        />

        <AgentRunRetrievalStrategyQualityPanel
          v-if="retrievalStrategyQualityOutput"
          :output="retrievalStrategyQualityOutput"
        />

        <AgentRunRetrievalPrefetchPanel
          v-if="retrievalPrefetchOutput"
          :output="retrievalPrefetchOutput"
        />

        <AgentRunRetrievalContextPanel
          v-if="retrievalContextOutput"
          :output="retrievalContextOutput"
        />

        <AgentRunLongformContextPanel
          v-if="longformContextOutput"
          :output="longformContextOutput"
        />

        <AgentRunContextCompressionPanel
          v-if="contextCompressionOutput"
          :output="contextCompressionOutput"
        />

        <AgentRunPreflightContextBudgetPanel
          v-if="preflightBudgetStep"
          :step="preflightBudgetStep"
        />

        <AgentRunMemoryActivationPanel
          v-if="memoryActivationOutput"
          :output="memoryActivationOutput"
        />

        <AgentRunMemoryRoutePanel
          v-if="memoryRouteOutput"
          :output="memoryRouteOutput"
        />

        <AgentRunKnowledgeBaseRoutePanel
          v-if="knowledgeBaseRouteOutput"
          :output="knowledgeBaseRouteOutput"
        />

        <AgentRunWorldModelRoutePanel
          v-if="worldModelRouteOutput"
          :output="worldModelRouteOutput"
        />

        <section
          v-if="hasWorldModelSemanticCheckProjection"
          class="agent-run-drawer__world-semantic-check"
          aria-label="World model semantic check projection"
        >
          <h4>世界模型语义检查</h4>
          <dl class="agent-run-drawer__facts">
            <div>
              <dt>状态</dt>
              <dd>{{ worldModelSemanticStatusLabel(worldModelSemanticCheck.status) }}</dd>
            </div>
            <div v-if="worldModelSemanticIssueCount !== null">
              <dt>问题</dt>
              <dd>问题 {{ worldModelSemanticIssueCount }}</dd>
            </div>
            <div v-if="worldModelSemanticChapterLabel">
              <dt>章节</dt>
              <dd>{{ worldModelSemanticChapterLabel }}</dd>
            </div>
            <div v-if="worldModelSemanticSubject">
              <dt>主体</dt>
              <dd>{{ worldModelSemanticSubject }}</dd>
            </div>
            <div v-if="countRangeLabel(worldModelSemanticReturnedFacts, worldModelSemanticTotalFacts)">
              <dt>确认事实</dt>
              <dd>确认事实 {{ countRangeLabel(worldModelSemanticReturnedFacts, worldModelSemanticTotalFacts) }}</dd>
            </div>
            <div v-if="worldModelSemanticFactLimit !== null">
              <dt>事实上限</dt>
              <dd>检查事实上限 {{ worldModelSemanticFactLimit }}</dd>
            </div>
          </dl>
          <p v-if="safeWorldModelSemanticText(worldModelSemanticCheck.summary)">
            {{ safeWorldModelSemanticText(worldModelSemanticCheck.summary) }}
          </p>
          <ul
            v-if="worldModelSemanticRecommendedTools.length"
            class="agent-run-drawer__tools"
          >
            <li
              v-for="tool in worldModelSemanticRecommendedTools"
              :key="`world-semantic-tool:${tool}`"
            >
              {{ tool }}
            </li>
          </ul>
          <ul
            v-if="worldModelSemanticIssueRows.length"
            class="agent-run-drawer__planner-signals"
          >
            <li
              v-for="row in worldModelSemanticIssueRows"
              :key="row.key"
            >
              <strong>{{ [row.code, row.severity].filter(Boolean).join(' · ') || '语义问题' }}</strong>
              <span v-if="[row.subject, row.predicate].filter(Boolean).length">
                {{ [row.subject, row.predicate].filter(Boolean).join(' · ') }}
              </span>
              <span v-if="row.message">{{ row.message }}</span>
              <span v-if="row.evidence">{{ row.evidence }}</span>
            </li>
          </ul>
        </section>

        <section
          v-if="hasWorldModelProposalReviewProjection"
          class="agent-run-drawer__world-proposal-review"
          aria-label="World model proposal review projection"
        >
          <h4>世界模型提案队列</h4>
          <dl class="agent-run-drawer__facts">
            <div>
              <dt>状态</dt>
              <dd>{{ worldModelRouteStatusLabel(worldModelProposalReviewOutput?.status) }}</dd>
            </div>
            <div>
              <dt>生成</dt>
              <dd>{{ worldModelProposalReviewGenerationLabel }}</dd>
            </div>
            <div v-if="countRangeLabel(worldModelProposalReviewReturned, worldModelProposalReviewTotal)">
              <dt>返回</dt>
              <dd>返回 {{ countRangeLabel(worldModelProposalReviewReturned, worldModelProposalReviewTotal) }}</dd>
            </div>
            <div v-if="worldModelProposalReviewTotal !== null">
              <dt>待审</dt>
              <dd>待审 {{ worldModelProposalReviewTotal }}</dd>
            </div>
            <div v-if="worldModelProposalReviewHasMoreLabel">
              <dt>分页</dt>
              <dd>{{ worldModelProposalReviewHasMoreLabel }}</dd>
            </div>
            <div v-if="worldModelProposalReviewHighRiskCount !== null && worldModelProposalReviewHighRiskCount > 0">
              <dt>高风险</dt>
              <dd>高风险 {{ worldModelProposalReviewHighRiskCount }}</dd>
            </div>
            <div v-if="worldModelProposalReviewMediumRiskCount !== null && worldModelProposalReviewMediumRiskCount > 0">
              <dt>中风险</dt>
              <dd>中风险 {{ worldModelProposalReviewMediumRiskCount }}</dd>
            </div>
            <div v-if="worldModelProposalReviewLowRiskCount !== null && worldModelProposalReviewLowRiskCount > 0">
              <dt>低风险</dt>
              <dd>低风险 {{ worldModelProposalReviewLowRiskCount }}</dd>
            </div>
            <div v-if="worldModelProposalReviewIndividualCount !== null && worldModelProposalReviewIndividualCount > 0">
              <dt>逐项</dt>
              <dd>逐项审阅 {{ worldModelProposalReviewIndividualCount }}</dd>
            </div>
            <div v-if="worldModelProposalReviewBatchCount !== null && worldModelProposalReviewBatchCount > 0">
              <dt>批量</dt>
              <dd>批量审阅 {{ worldModelProposalReviewBatchCount }}</dd>
            </div>
          </dl>
          <ul
            v-if="worldModelProposalReviewRecommendedActions.length"
            class="agent-run-drawer__tools"
          >
            <li
              v-for="action in worldModelProposalReviewRecommendedActions"
              :key="`world-proposal-review-action:${action}`"
            >
              {{ action }}
            </li>
          </ul>
          <ul
            v-if="worldModelProposalReviewClusterRows.length"
            class="agent-run-drawer__planner-signals"
          >
            <li
              v-for="row in worldModelProposalReviewClusterRows"
              :key="row.key"
            >
              <strong>{{ row.title }}</strong>
              <span v-if="row.meta">{{ row.meta }}</span>
              <span v-if="row.reason">{{ row.reason }}</span>
            </li>
          </ul>
        </section>

        <section
          v-if="hasWorldModelResolutionPlanProjection"
          class="agent-run-drawer__world-proposal-resolution"
          aria-label="World model proposal resolution plan projection"
        >
          <h4>世界模型提案解决计划</h4>
          <dl class="agent-run-drawer__facts">
            <div>
              <dt>状态</dt>
              <dd>{{ worldModelRouteStatusLabel(worldModelResolutionPlanOutput?.status) }}</dd>
            </div>
            <div>
              <dt>确认</dt>
              <dd>{{ worldModelResolutionConfirmationLabel }}</dd>
            </div>
            <div>
              <dt>应用</dt>
              <dd>{{ worldModelResolutionAutoApplyLabel }}</dd>
            </div>
            <div>
              <dt>生成</dt>
              <dd>{{ worldModelResolutionGenerationLabel }}</dd>
            </div>
            <div v-if="countRangeLabel(worldModelResolutionReturned, worldModelResolutionTotal)">
              <dt>返回</dt>
              <dd>返回 {{ countRangeLabel(worldModelResolutionReturned, worldModelResolutionTotal) }}</dd>
            </div>
            <div v-if="worldModelResolutionHighPriorityStepCount !== null">
              <dt>高优先级</dt>
              <dd>高优先级步骤 {{ worldModelResolutionHighPriorityStepCount }}</dd>
            </div>
            <div v-if="worldModelResolutionBatchStepCount !== null">
              <dt>批量步骤</dt>
              <dd>批量步骤 {{ worldModelResolutionBatchStepCount }}</dd>
            </div>
            <div v-if="worldModelResolutionHighRiskCount !== null && worldModelResolutionHighRiskCount > 0">
              <dt>高风险</dt>
              <dd>高风险 {{ worldModelResolutionHighRiskCount }}</dd>
            </div>
            <div v-if="worldModelResolutionMediumRiskCount !== null && worldModelResolutionMediumRiskCount > 0">
              <dt>中风险</dt>
              <dd>中风险 {{ worldModelResolutionMediumRiskCount }}</dd>
            </div>
            <div v-if="worldModelResolutionLowRiskCount !== null && worldModelResolutionLowRiskCount > 0">
              <dt>低风险</dt>
              <dd>低风险 {{ worldModelResolutionLowRiskCount }}</dd>
            </div>
            <div v-if="worldModelResolutionIndividualCount !== null && worldModelResolutionIndividualCount > 0">
              <dt>逐项</dt>
              <dd>逐项审阅 {{ worldModelResolutionIndividualCount }}</dd>
            </div>
            <div v-if="worldModelResolutionBatchCount !== null && worldModelResolutionBatchCount > 0">
              <dt>批量</dt>
              <dd>批量审阅 {{ worldModelResolutionBatchCount }}</dd>
            </div>
          </dl>
          <ul
            v-if="worldModelResolutionRecommendedItems.length"
            class="agent-run-drawer__tools"
          >
            <li
              v-for="item in worldModelResolutionRecommendedItems"
              :key="`world-proposal-resolution-action:${item}`"
            >
              {{ item }}
            </li>
          </ul>
          <ul
            v-if="worldModelResolutionStepRows.length"
            class="agent-run-drawer__planner-signals"
          >
            <li
              v-for="row in worldModelResolutionStepRows"
              :key="row.key"
            >
              <strong>{{ row.title }}</strong>
              <span v-if="row.meta">{{ row.meta }}</span>
              <span v-if="row.reason">{{ row.reason }}</span>
            </li>
          </ul>
        </section>

        <section
          v-if="hasTraceAuditProjection"
          class="agent-run-drawer__trace-audit"
          aria-label="Agent trace audit projection"
        >
          <h4>Trace 审计</h4>
          <dl class="agent-run-drawer__facts">
            <div>
              <dt>状态</dt>
              <dd>{{ traceAuditStatusLabel(traceAudit.status) }}</dd>
            </div>
            <div v-if="traceAuditRunGoal">
              <dt>目标</dt>
              <dd>{{ traceAuditRunGoal }}</dd>
            </div>
            <div v-if="traceAuditStepCount !== null">
              <dt>步骤</dt>
              <dd>步骤 {{ traceAuditStepCount }}</dd>
            </div>
            <div v-if="traceAuditTraceCount !== null">
              <dt>Trace</dt>
              <dd>Trace {{ traceAuditTraceCount }}</dd>
            </div>
            <div v-if="traceAuditEventCount !== null">
              <dt>事件</dt>
              <dd>事件 {{ traceAuditEventCount }}</dd>
            </div>
            <div v-if="traceAuditContextBlockCount !== null">
              <dt>上下文</dt>
              <dd>上下文块 {{ traceAuditContextBlockCount }}</dd>
            </div>
            <div v-if="traceAuditControlPlaneGapCount !== null">
              <dt>控制面</dt>
              <dd>控制面缺口 {{ traceAuditControlPlaneGapCount }}</dd>
            </div>
          </dl>
          <div
            v-if="traceAuditFailureTool || traceAuditFailureReason || traceAuditFailureMessage"
            class="agent-run-drawer__trace-audit-failure"
          >
            <strong>{{ traceAuditFailureTool || '失败摘要' }}</strong>
            <span v-if="traceAuditFailureReason">{{ traceAuditFailureReason }}</span>
            <p v-if="traceAuditFailureMessage">{{ traceAuditFailureMessage }}</p>
          </div>
          <div
            v-if="hasTraceAuditAnomalySummary"
            class="agent-run-drawer__trace-audit-anomaly"
          >
            <strong>异常摘要</strong>
            <dl class="agent-run-drawer__facts">
              <div v-if="traceAuditAnomalyStatus">
                <dt>状态</dt>
                <dd>{{ traceAuditAnomalyStatusLabel(traceAuditAnomalyStatus) }}</dd>
              </div>
              <div v-if="traceAuditAnomalyIssueCount !== null">
                <dt>问题</dt>
                <dd>问题 {{ traceAuditAnomalyIssueCount }}</dd>
              </div>
              <div v-if="traceAuditAnomalyCriticalCount !== null">
                <dt>严重</dt>
                <dd>严重 {{ traceAuditAnomalyCriticalCount }}</dd>
              </div>
              <div v-if="traceAuditAnomalyWarningCount !== null">
                <dt>警告</dt>
                <dd>警告 {{ traceAuditAnomalyWarningCount }}</dd>
              </div>
              <div v-if="traceAuditAnomalyInfoCount !== null">
                <dt>提示</dt>
                <dd>提示 {{ traceAuditAnomalyInfoCount }}</dd>
              </div>
              <div v-if="traceAuditAnomalyFailedStepCount !== null">
                <dt>失败步骤</dt>
                <dd>失败步骤 {{ traceAuditAnomalyFailedStepCount }}</dd>
              </div>
              <div v-if="traceAuditAnomalyFailedTraceCount !== null">
                <dt>失败 Trace</dt>
                <dd>失败 Trace {{ traceAuditAnomalyFailedTraceCount }}</dd>
              </div>
              <div v-if="traceAuditAnomalyMissingTraceCount !== null">
                <dt>缺 Trace</dt>
                <dd>缺 Trace {{ traceAuditAnomalyMissingTraceCount }}</dd>
              </div>
              <div v-if="traceAuditAnomalyUnmatchedPlanCount !== null">
                <dt>未执行计划</dt>
                <dd>未执行计划 {{ traceAuditAnomalyUnmatchedPlanCount }}</dd>
              </div>
              <div v-if="traceAuditAnomalyMissingResultMessage">
                <dt>结果消息</dt>
                <dd>缺结果消息</dd>
              </div>
              <div v-if="traceAuditAnomalyTruncatedContextCount !== null">
                <dt>截断上下文</dt>
                <dd>截断上下文 {{ traceAuditAnomalyTruncatedContextCount }}</dd>
              </div>
            </dl>
            <ul
              v-if="traceAuditAnomalyIssueRows.length"
              class="agent-run-drawer__planner-signals"
            >
              <li
                v-for="row in traceAuditAnomalyIssueRows"
                :key="row.key"
              >
                <strong>{{ row.label }}</strong>
                <span v-if="row.severityLabel">{{ row.severityLabel }}</span>
                <span v-if="row.meta">{{ row.meta }}</span>
                <span v-if="row.title">{{ row.title }}</span>
              </li>
            </ul>
          </div>
          <div
            v-if="hasTraceAuditIntentChain"
            class="agent-run-drawer__trace-audit-intent"
          >
            <strong>意图链路</strong>
            <dl class="agent-run-drawer__facts">
              <div v-if="traceAuditIntentChainRuleId">
                <dt>规则</dt>
                <dd>{{ traceAuditIntentChainRuleId }}</dd>
              </div>
              <div v-if="traceAuditIntentChainClass">
                <dt>意图</dt>
                <dd>{{ traceAuditIntentChainClass }}</dd>
              </div>
              <div v-if="traceAuditIntentChainChapterLabel">
                <dt>章节</dt>
                <dd>{{ traceAuditIntentChainChapterLabel }}</dd>
              </div>
              <div v-if="traceAuditIntentChainPlannedCount !== null">
                <dt>计划工具</dt>
                <dd>计划工具 {{ traceAuditIntentChainPlannedCount }}</dd>
              </div>
              <div v-if="traceAuditIntentChainExecutedCount !== null">
                <dt>已执行</dt>
                <dd>已执行 {{ traceAuditIntentChainExecutedCount }}</dd>
              </div>
              <div v-if="traceAuditIntentChainMatchedCount !== null">
                <dt>已匹配</dt>
                <dd>已匹配 {{ traceAuditIntentChainMatchedCount }}</dd>
              </div>
            </dl>
            <ul
              v-if="traceAuditIntentChainRows.length"
              class="agent-run-drawer__execution-tools"
            >
              <li
                v-for="row in traceAuditIntentChainRows"
                :key="row.key"
              >
                <span>{{ row.toolName }}</span>
                <strong>{{ [row.stepLabel, row.statusLabel].filter(Boolean).join(' · ') }}</strong>
              </li>
            </ul>
          </div>
          <div
            v-if="hasTraceAuditEndToEndChain"
            class="agent-run-drawer__trace-audit-end-to-end"
          >
            <strong>端到端链路</strong>
            <dl class="agent-run-drawer__facts">
              <div v-if="traceAuditEndToEndStatus">
                <dt>状态</dt>
                <dd>{{ traceAuditEndToEndStatusLabel(traceAuditEndToEndStatus) }}</dd>
              </div>
              <div v-if="traceAuditEndToEndPlannedCount !== null">
                <dt>计划工具</dt>
                <dd>计划工具 {{ traceAuditEndToEndPlannedCount }}</dd>
              </div>
              <div v-if="traceAuditEndToEndToolStepCount !== null">
                <dt>执行步骤</dt>
                <dd>执行步骤 {{ traceAuditEndToEndToolStepCount }}</dd>
              </div>
              <div v-if="traceAuditEndToEndModelTraceCount !== null">
                <dt>模型 Trace</dt>
                <dd>模型 Trace {{ traceAuditEndToEndModelTraceCount }}</dd>
              </div>
              <div v-if="traceAuditEndToEndResultActionType || traceAuditEndToEndResultStatusLabel">
                <dt>结果消息</dt>
                <dd>
                  {{ [traceAuditEndToEndResultActionType, traceAuditEndToEndResultStatusLabel].filter(Boolean).join(' · ') }}
                </dd>
              </div>
            </dl>
            <ul
              v-if="traceAuditEndToEndSegmentRows.length"
              class="agent-run-drawer__execution-tools"
            >
              <li
                v-for="row in traceAuditEndToEndSegmentRows"
                :key="row.key"
              >
                <span>{{ row.stageLabel }}</span>
                <strong>{{ [row.statusLabel, row.meta].filter(Boolean).join(' · ') }}</strong>
              </li>
            </ul>
          </div>
          <ul
            v-if="traceAuditRecommendedActionRows.length"
            class="agent-run-drawer__tools"
          >
            <li
              v-for="row in traceAuditRecommendedActionRows"
              :key="row.key"
            >
              {{ row.toolName }}
              <span v-if="row.reason"> · {{ row.reason }}</span>
              <span v-if="row.sourceStepLabel"> · {{ row.sourceStepLabel }}</span>
            </li>
          </ul>
          <ul
            v-if="traceAuditEventRows.length"
            class="agent-run-drawer__planner-signals"
          >
            <li
              v-for="row in traceAuditEventRows"
              :key="row.key"
            >
              <strong>{{ row.label }}</strong>
              <span v-if="row.detail">{{ row.detail }}</span>
            </li>
          </ul>
          <ul
            v-if="traceAuditContextRows.length"
            class="agent-run-drawer__reference-patterns"
          >
            <li
              v-for="row in traceAuditContextRows"
              :key="row.key"
            >
              <div>
                <strong>{{ row.title }}</strong>
                <span v-if="row.kind">{{ row.kind }}</span>
              </div>
              <p v-if="row.meta">{{ row.meta }}</p>
            </li>
          </ul>
          <ul
            v-if="traceAuditStepRows.length"
            class="agent-run-drawer__execution-tools"
          >
            <li
              v-for="row in traceAuditStepRows"
              :key="row.key"
            >
              <span>{{ row.label || '工具步骤' }}</span>
              <strong>{{ [row.chapterLabel, row.statusLabel].filter(Boolean).join(' · ') }}</strong>
            </li>
          </ul>
          <ul
            v-if="traceAuditTraceRows.length"
            class="agent-run-drawer__reference-patterns"
          >
            <li
              v-for="row in traceAuditTraceRows"
              :key="row.key"
            >
              <div>
                <strong>{{ row.label }}</strong>
                <span>{{ row.statusLabel }}</span>
              </div>
              <p v-if="row.meta">{{ row.meta }}</p>
              <p v-if="row.error">{{ row.error }}</p>
            </li>
          </ul>
        </section>

        <section
          v-if="hasTraceAnomalyTrendsProjection"
          class="agent-run-drawer__trace-anomaly-trends"
          aria-label="Trace anomaly trends projection"
        >
          <h4>Trace 异常趋势</h4>
          <dl class="agent-run-drawer__facts">
            <div v-if="traceAnomalyTrendStatus">
              <dt>状态</dt>
              <dd>{{ traceAuditAnomalyStatusLabel(traceAnomalyTrendStatus) }}</dd>
            </div>
            <div v-if="traceAnomalyTrendChapterLabel">
              <dt>章节</dt>
              <dd>{{ traceAnomalyTrendChapterLabel }}</dd>
            </div>
            <div v-if="traceAnomalyTrendRunCount !== null">
              <dt>运行</dt>
              <dd>运行 {{ traceAnomalyTrendRunCount }}</dd>
            </div>
            <div v-if="traceAnomalyTrendAffectedRunCount !== null">
              <dt>受影响</dt>
              <dd>受影响 {{ traceAnomalyTrendAffectedRunCount }}</dd>
            </div>
            <div v-if="traceAnomalyTrendIssueCount !== null">
              <dt>问题</dt>
              <dd>问题 {{ traceAnomalyTrendIssueCount }}</dd>
            </div>
            <div v-if="traceAnomalyTrendCriticalCount !== null">
              <dt>严重</dt>
              <dd>严重 {{ traceAnomalyTrendCriticalCount }}</dd>
            </div>
            <div v-if="traceAnomalyTrendWarningCount !== null">
              <dt>警告</dt>
              <dd>警告 {{ traceAnomalyTrendWarningCount }}</dd>
            </div>
            <div v-if="traceAnomalyTrendInfoCount !== null">
              <dt>提示</dt>
              <dd>提示 {{ traceAnomalyTrendInfoCount }}</dd>
            </div>
            <div v-if="traceAnomalyTrendDominantIssueLabel">
              <dt>主要问题</dt>
              <dd>主要问题 {{ traceAnomalyTrendDominantIssueLabel }}</dd>
            </div>
            <div v-if="traceAnomalyTrendBaselineRunCount !== null">
              <dt>基线运行</dt>
              <dd>基线运行 {{ traceAnomalyTrendBaselineRunCount }}</dd>
            </div>
            <div v-if="traceAnomalyTrendBaselineAffectedRunCount !== null">
              <dt>基线受影响</dt>
              <dd>基线受影响 {{ traceAnomalyTrendBaselineAffectedRunCount }}</dd>
            </div>
            <div v-if="traceAnomalyTrendAffectedRunRateDeltaLabel">
              <dt>异常率</dt>
              <dd>异常率 {{ traceAnomalyTrendAffectedRunRateDeltaLabel }}</dd>
            </div>
            <div v-if="traceAnomalyTrendIssueRateDeltaLabel">
              <dt>问题率</dt>
              <dd>问题率 {{ traceAnomalyTrendIssueRateDeltaLabel }}</dd>
            </div>
            <div v-if="traceAnomalyTrendThresholdConfigLabel">
              <dt>阈值来源</dt>
              <dd>{{ traceAnomalyTrendThresholdConfigLabel }}</dd>
            </div>
          </dl>
          <ul
            v-if="traceAnomalyTrendThresholdSignalRows.length"
            class="agent-run-drawer__planner-signals"
          >
            <li
              v-for="row in traceAnomalyTrendThresholdSignalRows"
              :key="row.key"
            >
              <strong>{{ row.title }}</strong>
              <span>{{ [row.severityLabel, row.meta].filter(Boolean).join(' · ') }}</span>
            </li>
          </ul>
          <dl
            v-if="traceAnomalyTrendCalibrationStatusLabel || traceAnomalyTrendCalibrationCurrentSignalCount !== null"
            class="agent-run-drawer__facts"
          >
            <div v-if="traceAnomalyTrendCalibrationStatusLabel">
              <dt>校准</dt>
              <dd>{{ traceAnomalyTrendCalibrationStatusLabel }}</dd>
            </div>
            <div
              v-if="
                traceAnomalyTrendCalibrationRecentRunCount !== null &&
                traceAnomalyTrendCalibrationBaselineRunCount !== null
              "
            >
              <dt>样本</dt>
              <dd>样本 {{ traceAnomalyTrendCalibrationRecentRunCount }}/{{ traceAnomalyTrendCalibrationBaselineRunCount }}</dd>
            </div>
            <div v-if="traceAnomalyTrendCalibrationCurrentSignalCount !== null">
              <dt>当前信号</dt>
              <dd>当前信号 {{ traceAnomalyTrendCalibrationCurrentSignalCount }}</dd>
            </div>
            <div v-if="traceAnomalyTrendCalibrationSuggestedAffectedThresholdLabel">
              <dt>建议异常阈值</dt>
              <dd>建议异常阈值 {{ traceAnomalyTrendCalibrationSuggestedAffectedThresholdLabel }}</dd>
            </div>
            <div v-if="traceAnomalyTrendCalibrationSuggestedCriticalThresholdLabel">
              <dt>建议严重阈值</dt>
              <dd>建议严重阈值 {{ traceAnomalyTrendCalibrationSuggestedCriticalThresholdLabel }}</dd>
            </div>
            <div v-if="traceAnomalyTrendCalibrationPolicyStatusLabel">
              <dt>固化策略</dt>
              <dd>{{ traceAnomalyTrendCalibrationPolicyStatusLabel }}</dd>
            </div>
            <div v-if="traceAnomalyTrendCalibrationPolicyDecisionLabel">
              <dt>策略决策</dt>
              <dd>{{ traceAnomalyTrendCalibrationPolicyDecisionLabel }}</dd>
            </div>
            <div
              v-if="
                traceAnomalyTrendCalibrationPolicyReviewedRunCount !== null &&
                traceAnomalyTrendCalibrationPolicyMinimumRunCount !== null
              "
            >
              <dt>复核样本</dt>
              <dd>复核样本 {{ traceAnomalyTrendCalibrationPolicyReviewedRunCount }}/{{ traceAnomalyTrendCalibrationPolicyMinimumRunCount }}</dd>
            </div>
            <div v-if="traceAnomalyTrendCalibrationPolicyPromotionLabel">
              <dt>固化候选</dt>
              <dd>{{ traceAnomalyTrendCalibrationPolicyPromotionLabel }}</dd>
            </div>
          </dl>
          <ul
            v-if="traceAnomalyTrendCalibrationGuardRows.length"
            class="agent-run-drawer__planner-signals"
          >
            <li
              v-for="row in traceAnomalyTrendCalibrationGuardRows"
              :key="row.key"
            >
              <strong>{{ row.title }}</strong>
              <span>{{ [row.statusLabel, row.meta].filter(Boolean).join(' · ') }}</span>
            </li>
          </ul>
          <ul
            v-if="traceAnomalyTrendIssueRows.length"
            class="agent-run-drawer__execution-tools"
          >
            <li
              v-for="row in traceAnomalyTrendIssueRows"
              :key="row.key"
            >
              <span>{{ row.label }}</span>
              <strong>{{ row.count }}</strong>
            </li>
          </ul>
          <ul
            v-if="traceAnomalyTrendRunRows.length"
            class="agent-run-drawer__planner-signals"
          >
            <li
              v-for="row in traceAnomalyTrendRunRows"
              :key="row.key"
            >
              <strong>{{ row.title }}</strong>
              <span>{{ [row.statusLabel, row.meta].filter(Boolean).join(' · ') }}</span>
              <span v-if="row.issueLabel">{{ row.issueLabel }}</span>
            </li>
          </ul>
          <ul
            v-if="traceAnomalyTrendRecommendedTools.length"
            class="agent-run-drawer__tools"
          >
            <li
              v-for="toolName in traceAnomalyTrendRecommendedTools"
              :key="toolName"
            >
              {{ toolName }}
            </li>
          </ul>
        </section>

        <section
          v-if="hasTraceAnomalyLongRunSamplesProjection"
          class="agent-run-drawer__trace-anomaly-long-run"
          aria-label="Trace anomaly long run samples projection"
        >
          <h4>Trace 长跑样本</h4>
          <dl class="agent-run-drawer__facts">
            <div v-if="traceAnomalyLongRunStatus">
              <dt>状态</dt>
              <dd>{{ traceAuditStatusLabel(traceAnomalyLongRunStatus) }}</dd>
            </div>
            <div v-if="traceAnomalyLongRunCollectionStatusLabel">
              <dt>采样状态</dt>
              <dd>{{ traceAnomalyLongRunCollectionStatusLabel }}</dd>
            </div>
            <div v-if="traceAnomalyLongRunCandidateCount !== null">
              <dt>候选运行</dt>
              <dd>{{ traceAnomalyLongRunCandidateCount }}</dd>
            </div>
            <div v-if="traceAnomalyLongRunMinimumReviewCount !== null">
              <dt>最低样本</dt>
              <dd>{{ traceAnomalyLongRunMinimumReviewCount }}</dd>
            </div>
            <div v-if="traceAnomalyLongRunMissingCount !== null">
              <dt>缺失样本</dt>
              <dd>{{ traceAnomalyLongRunMissingCount }}</dd>
            </div>
            <div v-if="traceAnomalyLongRunStepCount !== null">
              <dt>工具步骤</dt>
              <dd>{{ traceAnomalyLongRunStepCount }}</dd>
            </div>
            <div v-if="traceAnomalyLongRunChapterLabels.length">
              <dt>章节</dt>
              <dd>{{ traceAnomalyLongRunChapterLabels.join(' / ') }}</dd>
            </div>
            <div
              v-if="
                traceAnomalyLongRunReviewLimit !== null &&
                traceAnomalyLongRunReviewBaselineLimit !== null
              "
            >
              <dt>复核窗口</dt>
              <dd>
                {{ ['最近 ' + traceAnomalyLongRunReviewLimit + ' / 基线 ' + traceAnomalyLongRunReviewBaselineLimit, traceAnomalyLongRunReviewChapterLabel].filter(Boolean).join(' · ') }}
              </dd>
            </div>
          </dl>
          <ul
            v-if="traceAnomalyLongRunStatusRows.length"
            class="agent-run-drawer__execution-tools"
          >
            <li
              v-for="row in traceAnomalyLongRunStatusRows"
              :key="row.key"
            >
              <span>{{ row.label }} {{ row.count }}</span>
            </li>
          </ul>
          <ul
            v-if="traceAnomalyLongRunRecommendedTools.length"
            class="agent-run-drawer__tools"
          >
            <li
              v-for="toolName in traceAnomalyLongRunRecommendedTools"
              :key="`trace-long-run-next:${toolName}`"
            >
              {{ toolName }}
            </li>
          </ul>
        </section>

        <section
          v-if="hasTraceAnomalyThresholdReviewProjection"
          class="agent-run-drawer__trace-threshold-review"
          aria-label="Trace anomaly threshold review projection"
        >
          <h4>Trace 阈值复核</h4>
          <dl class="agent-run-drawer__facts">
            <div v-if="traceAnomalyThresholdReviewStatus">
              <dt>状态</dt>
              <dd>{{ traceAuditStatusLabel(traceAnomalyThresholdReviewStatus) }}</dd>
            </div>
            <div v-if="traceAnomalyThresholdReviewStateLabel">
              <dt>复核状态</dt>
              <dd>{{ traceAnomalyThresholdReviewStateLabel }}</dd>
            </div>
            <div v-if="traceAnomalyThresholdReviewPolicyDecisionLabel">
              <dt>策略决策</dt>
              <dd>{{ traceAnomalyThresholdReviewPolicyDecisionLabel }}</dd>
            </div>
            <div
              v-if="
                traceAnomalyThresholdReviewRecentRunCount !== null &&
                traceAnomalyThresholdReviewBaselineRunCount !== null
              "
            >
              <dt>样本</dt>
              <dd>样本 {{ traceAnomalyThresholdReviewRecentRunCount }}/{{ traceAnomalyThresholdReviewBaselineRunCount }}</dd>
            </div>
            <div
              v-if="
                traceAnomalyThresholdReviewReviewedRunCount !== null &&
                traceAnomalyThresholdReviewMinimumRunCount !== null
              "
            >
              <dt>已复核</dt>
              <dd>已复核 {{ traceAnomalyThresholdReviewReviewedRunCount }}/{{ traceAnomalyThresholdReviewMinimumRunCount }}</dd>
            </div>
            <div v-if="traceAnomalyThresholdReviewSignalCount !== null">
              <dt>阈值信号</dt>
              <dd>阈值信号 {{ traceAnomalyThresholdReviewSignalCount }}</dd>
            </div>
            <div v-if="traceAnomalyThresholdReviewAffectedThresholdLabel">
              <dt>异常阈值</dt>
              <dd>异常阈值 {{ traceAnomalyThresholdReviewAffectedThresholdLabel }}</dd>
            </div>
            <div v-if="traceAnomalyThresholdReviewCriticalThresholdLabel">
              <dt>严重阈值</dt>
              <dd>严重阈值 {{ traceAnomalyThresholdReviewCriticalThresholdLabel }}</dd>
            </div>
            <div v-if="traceAnomalyThresholdReviewRecommendedTools.includes('prepare_record_agent_trace_anomaly_threshold_config')">
              <dt>配置准备</dt>
              <dd>配置准备</dd>
            </div>
            <div v-if="traceAnomalyThresholdReviewSkippedDirectWrite">
              <dt>直接写入</dt>
              <dd>已跳过直接写入</dd>
            </div>
          </dl>
          <ul
            v-if="traceAnomalyThresholdReviewRecommendedTools.length"
            class="agent-run-drawer__tools"
          >
            <li
              v-for="toolName in traceAnomalyThresholdReviewRecommendedTools"
              :key="`trace-threshold-review-next:${toolName}`"
            >
              {{ toolName }}
            </li>
          </ul>
        </section>

        <section
          v-if="hasKnowledgeBaseCandidateExecutionProjection"
          class="agent-run-drawer__knowledge-candidate"
          aria-label="Knowledge base candidate execution"
        >
          <h4>知识库候选写入</h4>
          <dl class="agent-run-drawer__facts">
            <div>
              <dt>候选</dt>
              <dd>{{ knowledgeBaseCandidateExecutionTitle }}</dd>
            </div>
            <div>
              <dt>类型</dt>
              <dd>{{ knowledgeBaseCandidateExecutionType }}</dd>
            </div>
            <div v-if="knowledgeBaseCandidateExecutionCount !== null">
              <dt>数量</dt>
              <dd>候选 {{ knowledgeBaseCandidateExecutionCount }}</dd>
            </div>
          </dl>
          <ul
            v-if="knowledgeBaseCandidateExecutionRecommendedTools.length"
            class="agent-run-drawer__tools"
          >
            <li
              v-for="tool in knowledgeBaseCandidateExecutionRecommendedTools"
              :key="`knowledge-candidate-next:${tool}`"
            >
              {{ tool }}
            </li>
          </ul>
          <div
            v-if="knowledgeBaseCandidateRouteActions.length"
            class="agent-run-drawer__actions"
          >
            <button
              v-for="action in knowledgeBaseCandidateRouteActions"
              :key="action.key"
              type="button"
              class="agent-run-drawer__ghost"
              data-testid="knowledge-candidate-route"
              @click="executeKnowledgeBaseCandidateRoute(action)"
            >
              {{ action.label }}
            </button>
          </div>
        </section>

        <section
          v-if="hasMemoryTreeProjection"
          class="agent-run-drawer__memory-tree"
          aria-label="Agent memory tree projection"
        >
          <h4>Memory Tree 投影</h4>
          <dl class="agent-run-drawer__facts">
            <div>
              <dt>状态</dt>
              <dd>{{ memoryTreeStatusLabel(memoryTreeOutput?.status) }}</dd>
            </div>
            <div v-if="memoryTreeLevelCount !== null">
              <dt>层级</dt>
              <dd>{{ memoryTreeLevelCount }} 层</dd>
            </div>
            <div>
              <dt>返回节点</dt>
              <dd>返回 {{ memoryTreeNodeCount }} 个</dd>
            </div>
            <div v-if="memoryTreeSummaryLabel">
              <dt>节点概况</dt>
              <dd>{{ memoryTreeSummaryLabel }}</dd>
            </div>
            <div v-if="memoryTreeFilterLevel">
              <dt>筛选层级</dt>
              <dd>{{ memoryTreeLevelLabel(memoryTreeFilterLevel) }}</dd>
            </div>
            <div v-if="memoryTreeQuery">
              <dt>查询</dt>
              <dd>{{ memoryTreeQuery }}</dd>
            </div>
            <div v-if="memoryTreeNavigation.mode">
              <dt>导航模式</dt>
              <dd>{{ memoryTreeNavigationModeLabel(memoryTreeNavigation.mode) }}</dd>
            </div>
            <div v-if="memoryTreeRecommendedDrilldownCount">
              <dt>推荐展开</dt>
              <dd>推荐展开 {{ memoryTreeRecommendedDrilldownCount }}</dd>
            </div>
          </dl>
          <div
            v-if="memoryTreeHistoryRows.length"
            class="agent-run-drawer__memory-tree-history"
          >
            <span>浏览历史</span>
            <ol>
              <li
                v-for="item in memoryTreeHistoryRows"
                :key="item.key"
                data-testid="memory-tree-history-item"
              >
                {{ item.label }}
              </li>
            </ol>
          </div>
          <ol
            v-if="memoryTreeNodeRows.length"
            class="agent-run-drawer__memory-tree-nodes"
          >
            <li
              v-for="row in memoryTreeNodeRows"
              :key="row.key"
              :style="{ paddingInlineStart: `${8 + row.depth * 12}px` }"
              data-testid="memory-tree-node"
            >
              <span class="agent-run-drawer__memory-tree-level">{{ row.levelLabel }}</span>
              <div class="agent-run-drawer__memory-tree-content">
                <div class="agent-run-drawer__memory-tree-title">
                  <strong>{{ row.title }}</strong>
                  <span v-if="row.chapterLabel">{{ row.chapterLabel }}</span>
                  <span v-if="row.relevanceLabel">{{ row.relevanceLabel }}</span>
                </div>
                <p v-if="row.summary">{{ row.summary }}</p>
              </div>
            </li>
          </ol>
          <div
            v-if="memoryTreeNodeExpandActions.length"
            class="agent-run-drawer__actions"
          >
            <button
              v-for="action in memoryTreeNodeExpandActions"
              :key="action.key"
              type="button"
              class="agent-run-drawer__ghost"
              data-testid="memory-tree-node-expand"
              @click="executeMemoryTreeDrilldown(action)"
            >
              {{ action.label }}
            </button>
          </div>
          <div
            v-if="memoryTreeDrilldownActions.length"
            class="agent-run-drawer__actions"
          >
            <button
              v-for="action in memoryTreeDrilldownActions"
              :key="action.key"
              type="button"
              class="agent-run-drawer__ghost"
              data-testid="memory-tree-drilldown"
              @click="executeMemoryTreeDrilldown(action)"
            >
              {{ action.label }}
            </button>
          </div>
          <form
            class="agent-run-drawer__memory-tree-search"
            @submit.prevent="executeMemoryTreeSearch"
          >
            <input
              v-model="memoryTreeSearchQueryInput"
              type="search"
              data-testid="memory-tree-search-input"
              placeholder="搜索记忆树"
            >
            <button
              type="submit"
              class="agent-run-drawer__ghost"
              data-testid="memory-tree-search-submit"
              :disabled="!memoryTreeSearchAction"
            >
              搜索
            </button>
          </form>
        </section>

        <section
          v-if="hasMemoryTreeLlmCandidateProjection"
          class="agent-run-drawer__memory-tree"
          aria-label="Memory Tree LLM candidates"
        >
          <h4>Memory Tree 候选摘要</h4>
          <dl class="agent-run-drawer__facts">
            <div>
              <dt>状态</dt>
              <dd>{{ memoryTreeStatusLabel(memoryTreeLlmCandidateOutput?.status) }}</dd>
            </div>
            <div>
              <dt>候选</dt>
              <dd>{{ memoryTreeLlmCandidateSummaryLabel }}</dd>
            </div>
            <div v-if="memoryTreeLlmCandidateChapterLabel">
              <dt>章节</dt>
              <dd>{{ memoryTreeLlmCandidateChapterLabel }}</dd>
            </div>
          </dl>
          <ol
            v-if="memoryTreeLlmCandidateRows.length"
            class="agent-run-drawer__memory-tree-nodes"
          >
            <li
              v-for="row in memoryTreeLlmCandidateRows"
              :key="row.key"
              data-testid="memory-tree-llm-candidate"
            >
              <span class="agent-run-drawer__memory-tree-level">候选</span>
              <div class="agent-run-drawer__memory-tree-content">
                <div class="agent-run-drawer__memory-tree-title">
                  <strong>{{ row.label }}</strong>
                  <span v-if="row.sourceLabel">{{ row.sourceLabel }}</span>
                  <span v-if="row.qualityLabel">{{ row.qualityLabel }}</span>
                  <span v-if="row.materializationLabel">{{ row.materializationLabel }}</span>
                </div>
                <p v-if="row.summary">{{ row.summary }}</p>
                <p v-if="row.termsLabel">{{ row.termsLabel }}</p>
              </div>
            </li>
          </ol>
          <div
            v-if="memoryTreeLlmCandidatePrepareActions.length"
            class="agent-run-drawer__actions"
          >
            <button
              v-for="action in memoryTreeLlmCandidatePrepareActions"
              :key="action.key"
              type="button"
              class="agent-run-drawer__ghost"
              data-testid="memory-tree-llm-candidate-prepare"
              @click="executeMemoryTreeLlmCandidatePrepare(action)"
            >
              {{ action.label }}
            </button>
          </div>
        </section>

        <section
          v-if="hasMemoryTreeLlmCandidateBatchProjection"
          class="agent-run-drawer__memory-tree"
          aria-label="Memory Tree LLM candidate batch approval"
        >
          <h4>Memory Tree 批量候选准备</h4>
          <dl class="agent-run-drawer__facts">
            <div>
              <dt>状态</dt>
              <dd>{{ memoryTreeStatusLabel(memoryTreeLlmCandidateBatchOutput?.status) }}</dd>
            </div>
            <div>
              <dt>候选</dt>
              <dd>{{ memoryTreeLlmCandidateBatchSummaryLabel }}</dd>
            </div>
            <div>
              <dt>确认要求</dt>
              <dd>逐条确认</dd>
            </div>
          </dl>
          <ol
            v-if="memoryTreeLlmCandidateBatchRows.length"
            class="agent-run-drawer__memory-tree-nodes"
          >
            <li
              v-for="row in memoryTreeLlmCandidateBatchRows"
              :key="row.key"
              data-testid="memory-tree-llm-candidate-batch"
            >
              <span class="agent-run-drawer__memory-tree-level">准备</span>
              <div class="agent-run-drawer__memory-tree-content">
                <div class="agent-run-drawer__memory-tree-title">
                  <strong>{{ row.label }}</strong>
                  <span v-if="row.executeToolLabel">{{ row.executeToolLabel }}</span>
                </div>
                <p v-if="row.qualityQuery">质量查询：{{ row.qualityQuery }}</p>
              </div>
            </li>
          </ol>
          <div
            v-if="memoryTreeLlmCandidateBatchExecuteActions.length"
            class="agent-run-drawer__actions"
          >
            <button
              v-for="action in memoryTreeLlmCandidateBatchExecuteActions"
              :key="action.key"
              type="button"
              class="agent-run-drawer__execute"
              data-testid="memory-tree-llm-candidate-batch-execute"
              @click="executeMemoryTreeLlmCandidateBatch(action)"
            >
              {{ action.label }}
            </button>
          </div>
        </section>

        <section
          v-if="hasMemoryTreeLlmCandidateBatchExecuteProjection"
          class="agent-run-drawer__memory-tree"
          aria-label="Memory Tree LLM candidate batch execution"
        >
          <h4>Memory Tree 批量候选写入</h4>
          <dl class="agent-run-drawer__facts">
            <div>
              <dt>状态</dt>
              <dd>{{ memoryTreeStatusLabel(memoryTreeLlmCandidateBatchExecuteOutput?.status) }}</dd>
            </div>
            <div>
              <dt>候选</dt>
              <dd>{{ memoryTreeLlmCandidateBatchExecuteSummaryLabel }}</dd>
            </div>
          </dl>
          <ol
            v-if="memoryTreeLlmCandidateBatchExecuteRows.length"
            class="agent-run-drawer__memory-tree-nodes"
          >
            <li
              v-for="row in memoryTreeLlmCandidateBatchExecuteRows"
              :key="row.key"
              data-testid="memory-tree-llm-candidate-batch-execute-result"
            >
              <span class="agent-run-drawer__memory-tree-level">写入</span>
              <div class="agent-run-drawer__memory-tree-content">
                <div class="agent-run-drawer__memory-tree-title">
                  <strong>{{ row.label }}</strong>
                  <span>{{ row.statusLabel }}</span>
                  <span>{{ row.writeLabel }}</span>
                  <span v-if="row.qualityLabel">{{ row.qualityLabel }}</span>
                </div>
              </div>
            </li>
          </ol>
        </section>

        <section
          v-if="hasRecoveryPolicy"
          class="agent-run-drawer__recovery"
          aria-label="Recovery policy"
        >
          <h4>恢复执行策略</h4>
          <dl v-if="executionPolicy" class="agent-run-drawer__facts">
            <div>
              <dt>策略状态</dt>
              <dd>{{ policyStatusLabel(executionPolicy.status) }}</dd>
            </div>
            <div>
              <dt>确认要求</dt>
              <dd>{{ booleanLabel(executionPolicy.requires_confirmation, '需要确认', '无需确认') }}</dd>
            </div>
            <div>
              <dt>计划哈希</dt>
              <dd>{{ booleanLabel(executionPolicy.requires_plan_hash, '需要计划哈希', '无需计划哈希') }}</dd>
            </div>
            <div>
              <dt>自动执行</dt>
              <dd>{{ booleanLabel(executionPolicy.safe_auto_execute, '允许安全自动执行', '不允许自动执行') }}</dd>
            </div>
          </dl>
          <dl v-if="guardrails" class="agent-run-drawer__facts">
            <div>
              <dt>保护策略</dt>
              <dd>{{ guardrailStatusLabel(guardrails.status) }}</dd>
            </div>
          </dl>
          <ul
            v-if="guardrailBlockers.length"
            class="agent-run-drawer__blockers"
          >
            <li
              v-for="(blocker, index) in guardrailBlockers"
              :key="`${blocker.code || 'blocker'}:${index}`"
            >
              <strong>{{ blocker.code }}</strong>
              <span v-if="blocker.tool_name">{{ blocker.tool_name }}</span>
              <p>{{ blocker.message || '未提供阻止原因。' }}</p>
            </li>
          </ul>
          <ul
            v-if="recoveryTools.length"
            class="agent-run-drawer__tools"
          >
            <li
              v-for="(tool, index) in recoveryTools"
              :key="`${tool.tool_name || 'tool'}:${index}`"
            >
              {{ tool.tool_name }}
            </li>
          </ul>
          <div v-if="recoveryExecutePayload" class="agent-run-drawer__actions">
            <button
              type="button"
              class="agent-run-drawer__execute"
              data-testid="execute-recovery"
              @click="executeRecovery"
            >
              确认执行恢复
            </button>
          </div>
        </section>

        <section
          v-if="hasRecommendedFollowupPolicy"
          class="agent-run-drawer__followups"
          aria-label="Recommended follow-up policy"
        >
          <h4>推荐后继策略</h4>
          <dl class="agent-run-drawer__facts">
            <div>
              <dt>自动诊断工具</dt>
              <dd>{{ recommendedFollowupTools.length }} 个</dd>
            </div>
            <div>
              <dt>需确认修复</dt>
              <dd>{{ recommendedFollowupWriteTools.length }} 个</dd>
            </div>
            <div v-if="recommendedFollowupContinuationTools.length">
              <dt>写后续跑</dt>
              <dd>{{ recommendedFollowupContinuationTools.length }} 个工具</dd>
            </div>
            <div v-if="recommendedFollowupWorkerCount !== null">
              <dt>Worker 分派</dt>
              <dd>{{ recommendedFollowupWorkerCount }} 个 worker</dd>
            </div>
            <div v-if="recommendedFollowupPlannedTaskCount !== null">
              <dt>分派任务</dt>
              <dd>{{ recommendedFollowupPlannedTaskCount }} 个任务</dd>
            </div>
            <div v-if="recommendedFollowupRouteRegistryStatus">
              <dt>路由审计</dt>
              <dd>{{ routeRegistryStatusLabel(recommendedFollowupRouteRegistryStatus) }}</dd>
            </div>
            <div v-if="recommendedFollowupUnroutedToolCount !== null">
              <dt>未路由工具</dt>
              <dd>{{ recommendedFollowupUnroutedToolCount }} 个</dd>
            </div>
            <div v-if="recommendedFollowupRouteIssueCount !== null && recommendedFollowupRouteIssueCount > 0">
              <dt>路由问题</dt>
              <dd>{{ recommendedFollowupRouteIssueCount }} 个</dd>
            </div>
          </dl>
          <ul
            v-if="recommendedFollowupTools.length"
            class="agent-run-drawer__tools"
          >
            <li
              v-for="(tool, index) in recommendedFollowupTools"
              :key="`followup:${tool.tool_name || 'tool'}:${index}`"
            >
              {{ tool.tool_name }}
            </li>
          </ul>
          <ul
            v-if="recommendedFollowupWorkerDispatches.length"
            class="agent-run-drawer__worker-dispatches"
          >
            <li
              v-for="(dispatch, index) in recommendedFollowupWorkerDispatches"
              :key="`worker-dispatch:${workerDispatchName(dispatch)}:${index}`"
            >
              <strong>{{ workerDispatchName(dispatch) }}</strong>
              <span v-if="workerDispatchTaskLabel(dispatch)">{{ workerDispatchTaskLabel(dispatch) }}</span>
            </li>
          </ul>
          <ul
            v-if="recommendedFollowupContinuationTools.length"
            class="agent-run-drawer__tools"
          >
            <li
              v-for="(tool, index) in recommendedFollowupContinuationTools"
              :key="`continuation:${tool.tool_name || 'tool'}:${index}`"
            >
              {{ tool.tool_name }}
              <span v-if="toolChapterLabel(tool)">{{ toolChapterLabel(tool) }}</span>
            </li>
          </ul>
          <ul
            v-if="recommendedFollowupWriteTools.length"
            class="agent-run-drawer__write-tools"
          >
            <li
              v-for="(tool, index) in recommendedFollowupWriteTools"
              :key="`write:${tool.tool_name || 'tool'}:${index}`"
            >
              {{ tool.tool_name }}
            </li>
          </ul>
          <div v-if="recommendedFollowupExecutePayload" class="agent-run-drawer__actions">
            <button
              type="button"
              class="agent-run-drawer__execute"
              data-testid="execute-recommended-followups"
              @click="executeRecommendedFollowups"
            >
              确认执行后继
            </button>
          </div>
        </section>

        <section
          v-if="preparedApprovalExecutePayload"
          class="agent-run-drawer__prepared-approval"
          aria-label="Prepared write approval"
        >
          <h4>待审批写入</h4>
          <dl class="agent-run-drawer__facts">
            <div>
              <dt>目标</dt>
              <dd>{{ preparedApprovalTargetLabel }}</dd>
            </div>
            <div>
              <dt>执行工具</dt>
              <dd>{{ preparedApprovalExecuteTool }}</dd>
            </div>
            <div>
              <dt>确认要求</dt>
              <dd>需要确认</dd>
            </div>
          </dl>
          <div class="agent-run-drawer__actions">
            <button
              type="button"
              class="agent-run-drawer__execute"
              data-testid="execute-prepared-approval"
              @click="executePreparedApproval"
            >
              确认执行写入
            </button>
          </div>
        </section>

        <section
          v-if="routeUpgradeContractOutput"
          class="agent-run-drawer__route-upgrade"
          aria-label="Route upgrade approval"
        >
          <h4>路由升级审批</h4>
          <dl class="agent-run-drawer__facts">
            <div>
              <dt>契约状态</dt>
              <dd>{{ routeUpgradeStatusLabel(routeUpgradeStatus) }}</dd>
            </div>
            <div>
              <dt>确认要求</dt>
              <dd>{{ routeUpgradeRequiredConfirmation ? '需要确认' : '无需确认' }}</dd>
            </div>
            <div v-if="routeUpgradePendingActionId">
              <dt>待处理动作</dt>
              <dd>{{ routeUpgradePendingActionId }}</dd>
            </div>
          </dl>
          <div v-if="canApplyRouteUpgrade" class="agent-run-drawer__actions">
            <button
              type="button"
              class="agent-run-drawer__execute"
              data-testid="apply-route-upgrade"
              @click="applyRouteUpgrade"
            >
              确认应用路由升级
            </button>
          </div>
        </section>

        <section class="agent-run-drawer__steps" aria-label="Agent run steps">
          <h4>工具步骤</h4>
          <ol v-if="steps.length">
            <li
              v-for="step in steps"
              :key="step.id"
              class="agent-run-drawer__step"
            >
              <span class="agent-run-drawer__step-index">#{{ step.step_index }}</span>
              <span class="agent-run-drawer__step-tool">{{ step.tool_name }}</span>
              <span class="agent-run-drawer__step-status">{{ step.status }}</span>
            </li>
          </ol>
          <p v-else class="agent-run-drawer__state">暂无工具步骤。</p>
        </section>
      </template>
    </div>
  </BaseModal>
</template>

<style scoped>
.agent-run-drawer {
  display: grid;
  gap: var(--space-4);
}

.agent-run-drawer__state {
  margin: 0;
  color: var(--color-text-secondary);
  font-size: var(--text-sm);
}

.agent-run-drawer__state--error {
  color: var(--color-error);
}

.agent-run-drawer__summary {
  display: grid;
  gap: var(--space-3);
}

.agent-run-drawer__summary-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-3);
}

.agent-run-drawer__eyebrow {
  display: block;
  margin-bottom: var(--space-1);
  color: var(--color-text-tertiary);
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
}

.agent-run-drawer__summary h4,
.agent-run-drawer__execution-plan h4,
.agent-run-drawer__planner h4,
.agent-run-drawer__memory-loop h4,
.agent-run-drawer__world-proposal-review h4,
.agent-run-drawer__world-proposal-resolution h4,
.agent-run-drawer__trace-audit h4,
.agent-run-drawer__trace-anomaly-trends h4,
.agent-run-drawer__trace-anomaly-long-run h4,
.agent-run-drawer__trace-threshold-review h4,
.agent-run-drawer__knowledge-candidate h4,
.agent-run-drawer__memory-tree h4,
.agent-run-drawer__recovery h4,
.agent-run-drawer__followups h4,
.agent-run-drawer__prepared-approval h4,
.agent-run-drawer__steps h4 {
  margin: 0;
  color: var(--color-text-primary);
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
}

.agent-run-drawer__summary dl,
.agent-run-drawer__facts {
  display: grid;
  gap: var(--space-2);
  margin: 0;
}

.agent-run-drawer__summary dl div,
.agent-run-drawer__facts div {
  display: grid;
  grid-template-columns: 5rem minmax(0, 1fr);
  gap: var(--space-3);
}

.agent-run-drawer__summary dt,
.agent-run-drawer__facts dt {
  color: var(--color-text-tertiary);
  font-size: var(--text-xs);
}

.agent-run-drawer__summary dd,
.agent-run-drawer__facts dd {
  margin: 0;
  min-width: 0;
  color: var(--color-text-primary);
  font-size: var(--text-xs);
  overflow-wrap: anywhere;
}

.agent-run-drawer__planner {
  display: grid;
  gap: var(--space-3);
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-secondary);
}

.agent-run-drawer__execution-plan {
  display: grid;
  gap: var(--space-3);
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-secondary);
}

.agent-run-drawer__memory-loop {
  display: grid;
  gap: var(--space-3);
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-secondary);
}

.agent-run-drawer__world-proposal-review {
  display: grid;
  gap: var(--space-3);
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-secondary);
}

.agent-run-drawer__world-proposal-resolution {
  display: grid;
  gap: var(--space-3);
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-secondary);
}

.agent-run-drawer__trace-audit {
  display: grid;
  gap: var(--space-3);
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-secondary);
}

.agent-run-drawer__trace-anomaly-trends {
  display: grid;
  gap: var(--space-3);
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-secondary);
}

.agent-run-drawer__trace-anomaly-long-run {
  display: grid;
  gap: var(--space-3);
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-secondary);
}

.agent-run-drawer__trace-threshold-review {
  display: grid;
  gap: var(--space-3);
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-secondary);
}

.agent-run-drawer__knowledge-candidate {
  display: grid;
  gap: var(--space-3);
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-secondary);
}

.agent-run-drawer__memory-tree {
  display: grid;
  gap: var(--space-3);
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-secondary);
}

.agent-run-drawer__recovery {
  display: grid;
  gap: var(--space-3);
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-secondary);
}

.agent-run-drawer__followups {
  display: grid;
  gap: var(--space-3);
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-secondary);
}

.agent-run-drawer__prepared-approval {
  display: grid;
  gap: var(--space-3);
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-secondary);
}

.agent-run-drawer__route-upgrade {
  display: grid;
  gap: var(--space-3);
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-secondary);
}

.agent-run-drawer__blockers,
.agent-run-drawer__tools,
.agent-run-drawer__write-tools,
.agent-run-drawer__worker-dispatches,
.agent-run-drawer__event-rows,
.agent-run-drawer__execution-tools,
.agent-run-drawer__memory-tree-nodes,
.agent-run-drawer__planner-signals,
.agent-run-drawer__reference-patterns {
  display: grid;
  gap: var(--space-2);
  margin: 0;
  padding: 0;
  list-style: none;
}

.agent-run-drawer__execution-tools li {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  padding: var(--space-1) var(--space-2);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-white);
  color: var(--color-text-primary);
  font-size: var(--text-xs);
  overflow-wrap: anywhere;
}

.agent-run-drawer__execution-tools span {
  min-width: 0;
  overflow-wrap: anywhere;
}

.agent-run-drawer__execution-tools strong {
  flex: 0 0 auto;
  color: var(--color-text-secondary);
  font-weight: var(--font-semibold);
}

.agent-run-drawer__event-rows li {
  display: grid;
  gap: var(--space-1);
  padding: var(--space-2);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-white);
  font-size: var(--text-xs);
  overflow-wrap: anywhere;
}

.agent-run-drawer__event-rows div,
.agent-run-drawer__event-rows p {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  align-items: baseline;
  margin: 0;
}

.agent-run-drawer__event-rows strong {
  color: var(--color-text-primary);
}

.agent-run-drawer__event-rows span,
.agent-run-drawer__event-rows p {
  color: var(--color-text-secondary);
}

.agent-run-drawer__memory-tree-nodes li {
  display: grid;
  grid-template-columns: max-content minmax(0, 1fr);
  gap: var(--space-2);
  align-items: start;
  padding-top: var(--space-2);
  padding-right: var(--space-2);
  padding-bottom: var(--space-2);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-white);
  font-size: var(--text-xs);
}

.agent-run-drawer__memory-tree-level {
  color: var(--color-text-tertiary);
  font-weight: var(--font-semibold);
  white-space: nowrap;
}

.agent-run-drawer__memory-tree-content {
  display: grid;
  gap: 2px;
  min-width: 0;
}

.agent-run-drawer__memory-tree-title {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  align-items: baseline;
}

.agent-run-drawer__memory-tree-title strong {
  color: var(--color-text-primary);
  overflow-wrap: anywhere;
}

.agent-run-drawer__memory-tree-title span,
.agent-run-drawer__memory-tree-content p {
  margin: 0;
  color: var(--color-text-secondary);
  line-height: var(--leading-normal);
  overflow-wrap: anywhere;
}

.agent-run-drawer__memory-tree-history {
  display: grid;
  gap: var(--space-2);
}

.agent-run-drawer__memory-tree-history > span {
  color: var(--color-text-tertiary);
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
}

.agent-run-drawer__memory-tree-history ol {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin: 0;
  padding: 0;
  list-style: none;
}

.agent-run-drawer__memory-tree-history li {
  max-width: 100%;
  padding: 2px var(--space-2);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-white);
  color: var(--color-text-secondary);
  font-size: var(--text-xs);
  overflow-wrap: anywhere;
}

.agent-run-drawer__memory-tree-search {
  display: grid;
  grid-template-columns: minmax(0, 1fr) max-content;
  gap: var(--space-2);
}

.agent-run-drawer__memory-tree-search input {
  min-width: 0;
  min-height: 30px;
  padding: 0 var(--space-2);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-white);
  color: var(--color-text-primary);
  font-size: var(--text-xs);
}

.agent-run-drawer__memory-tree-search input:focus {
  outline: 2px solid var(--color-primary-soft);
  border-color: var(--color-primary);
}

.agent-run-drawer__blockers li {
  display: grid;
  gap: 2px;
  padding: var(--space-2);
  border-left: 3px solid var(--color-warning);
  background: var(--color-bg-white);
  font-size: var(--text-xs);
}

.agent-run-drawer__blockers strong {
  color: var(--color-text-primary);
}

.agent-run-drawer__blockers span {
  color: var(--color-text-secondary);
  overflow-wrap: anywhere;
}

.agent-run-drawer__blockers p {
  margin: 0;
  color: var(--color-text-secondary);
  line-height: var(--leading-normal);
}

.agent-run-drawer__trace-audit-failure {
  display: grid;
  gap: 2px;
  padding: var(--space-2);
  border-left: 3px solid var(--color-warning);
  background: var(--color-bg-white);
  font-size: var(--text-xs);
}

.agent-run-drawer__trace-audit-failure strong {
  color: var(--color-text-primary);
}

.agent-run-drawer__trace-audit-failure span,
.agent-run-drawer__trace-audit-failure p {
  margin: 0;
  color: var(--color-text-secondary);
  line-height: var(--leading-normal);
  overflow-wrap: anywhere;
}

.agent-run-drawer__trace-audit-intent {
  display: grid;
  gap: var(--space-2);
  padding: var(--space-2);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-white);
  font-size: var(--text-xs);
}

.agent-run-drawer__trace-audit-intent > strong {
  color: var(--color-text-primary);
}

.agent-run-drawer__trace-audit-anomaly {
  display: grid;
  gap: var(--space-2);
  padding: var(--space-2);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-white);
  font-size: var(--text-xs);
}

.agent-run-drawer__trace-audit-anomaly > strong {
  color: var(--color-text-primary);
}

.agent-run-drawer__trace-audit-end-to-end {
  display: grid;
  gap: var(--space-2);
  padding: var(--space-2);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-white);
  font-size: var(--text-xs);
}

.agent-run-drawer__trace-audit-end-to-end > strong {
  color: var(--color-text-primary);
}

.agent-run-drawer__tools li {
  padding: var(--space-1) var(--space-2);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-white);
  color: var(--color-text-primary);
  font-size: var(--text-xs);
  overflow-wrap: anywhere;
}

.agent-run-drawer__planner-signals li {
  display: grid;
  gap: 2px;
  padding: var(--space-2);
  border-left: 3px solid var(--color-warning);
  background: var(--color-bg-white);
  color: var(--color-text-primary);
  font-size: var(--text-xs);
  overflow-wrap: anywhere;
}

.agent-run-drawer__planner-signals strong {
  color: var(--color-text-primary);
}

.agent-run-drawer__planner-signals span {
  color: var(--color-text-secondary);
}

.agent-run-drawer__reference-patterns li {
  display: grid;
  gap: var(--space-1);
  padding: var(--space-2);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-white);
  font-size: var(--text-xs);
  overflow-wrap: anywhere;
}

.agent-run-drawer__reference-patterns div {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  align-items: baseline;
}

.agent-run-drawer__reference-patterns strong {
  color: var(--color-text-primary);
}

.agent-run-drawer__reference-patterns span,
.agent-run-drawer__reference-patterns p {
  margin: 0;
  color: var(--color-text-secondary);
  line-height: var(--leading-normal);
}

.agent-run-drawer__write-tools li {
  padding: var(--space-1) var(--space-2);
  border: 1px solid var(--color-warning);
  border-radius: var(--radius-sm);
  background: var(--color-bg-white);
  color: var(--color-text-primary);
  font-size: var(--text-xs);
  overflow-wrap: anywhere;
}

.agent-run-drawer__worker-dispatches li {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  align-items: baseline;
  padding: var(--space-1) var(--space-2);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-white);
  font-size: var(--text-xs);
  overflow-wrap: anywhere;
}

.agent-run-drawer__worker-dispatches strong {
  color: var(--color-text-primary);
}

.agent-run-drawer__worker-dispatches span {
  color: var(--color-text-secondary);
}

.agent-run-drawer__actions {
  display: flex;
  justify-content: flex-end;
}

.agent-run-drawer__execute {
  min-height: 32px;
  padding: 0 var(--space-3);
  border: 1px solid var(--color-primary);
  border-radius: var(--radius-sm);
  background: var(--color-primary);
  color: var(--color-bg-white);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  cursor: pointer;
}

.agent-run-drawer__execute:hover {
  filter: brightness(0.96);
}

.agent-run-drawer__ghost {
  min-height: 30px;
  padding: 0 var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-white);
  color: var(--color-text-secondary);
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  white-space: nowrap;
  cursor: pointer;
}

.agent-run-drawer__ghost:hover {
  border-color: var(--color-border-strong);
  color: var(--color-text-primary);
}

.agent-run-drawer__steps {
  display: grid;
  gap: var(--space-2);
}

.agent-run-drawer__steps ol {
  display: grid;
  gap: var(--space-2);
  margin: 0;
  padding: 0;
  list-style: none;
}

.agent-run-drawer__step {
  display: grid;
  grid-template-columns: 3rem minmax(0, 1fr) max-content;
  gap: var(--space-2);
  align-items: center;
  padding: var(--space-2);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-secondary);
  font-size: var(--text-xs);
}

.agent-run-drawer__step-index,
.agent-run-drawer__step-status {
  color: var(--color-text-tertiary);
}

.agent-run-drawer__step-tool {
  min-width: 0;
  color: var(--color-text-primary);
  font-weight: var(--font-medium);
  overflow-wrap: anywhere;
}
</style>
