import { describe, expect, it } from 'vitest'
import {
  buildAgentRunActionResultView,
  buildAgentRunExecutionFeedback,
  getAgentRunActionDescriptor,
  getAgentRunIdFromMessage,
  isAgentRunActionType,
} from './agentRunProjection'

describe('agentRunProjection', () => {
  it('extracts run ids only from supported agent run action messages', () => {
    expect(getAgentRunIdFromMessage({
      action_result: {
        type: 'plan_recovery_tools',
        status: 'success',
        data: { agent_run_id: 'run-preview' },
      },
    })).toBe('run-preview')

    expect(getAgentRunIdFromMessage({
      action_result_view: {
        type: 'ui_recovery_execute',
        status: 'success',
        label: '恢复执行已完成',
        variant: 'success',
      },
      meta: { agent_run_id: 'run-executed' },
    })).toBe('run-executed')

    expect(getAgentRunIdFromMessage({
      action_result: {
        type: 'unknown_tool',
        status: 'success',
        data: { agent_run_id: 'run-hidden' },
      },
    })).toBe('')
  })

  it('recognizes supported agent run action types', () => {
    expect(isAgentRunActionType('plan_recovery_tools')).toBe(true)
    expect(isAgentRunActionType('ui_recovery_execute')).toBe(true)
    expect(isAgentRunActionType('inspect_agent_trace_audit')).toBe(true)
    expect(isAgentRunActionType('generate_chapter')).toBe(false)
  })

  it('exposes registered agent run action descriptors', () => {
    expect(getAgentRunActionDescriptor('plan_recovery_tools')?.type).toBe('plan_recovery_tools')
    expect(getAgentRunActionDescriptor('ui_recovery_execute')?.type).toBe('ui_recovery_execute')
    expect(getAgentRunActionDescriptor('inspect_agent_trace_audit')?.type).toBe('inspect_agent_trace_audit')
    expect(getAgentRunActionDescriptor('generate_chapter')).toBeNull()
  })

  it('extracts nested run ids from trace audit action results', () => {
    expect(getAgentRunIdFromMessage({
      action_result: {
        type: 'inspect_agent_trace_audit',
        status: 'success',
        data: { run: { id: 'run-audit-1' } },
      },
    })).toBe('run-audit-1')
  })

  it('builds fallback views for recovery preview action results', () => {
    const view = buildAgentRunActionResultView({
      type: 'plan_recovery_tools',
      status: 'success',
      data: {
        source_run_id: 'source-run-123456',
        recovery: { status: 'recommended' },
        execution_policy: { status: 'ready' },
        tools: [{ tool_name: 'prepare_generate_chapter_execution' }],
      },
    })

    expect(view?.label).toBe('恢复预览已生成')
    expect(view?.variant).toBe('success')
    expect(view?.detail_items).toContainEqual({ label: '来源运行', value: 'source-r' })
    expect(view?.detail_items).toContainEqual({ label: '恢复状态', value: '建议恢复' })
    expect(view?.detail_items).toContainEqual({ label: '执行策略', value: '可执行' })
    expect(view?.detail_items).toContainEqual({ label: '恢复工具', value: '1 个' })
  })

  it('does not build fallback views for unknown action results', () => {
    expect(buildAgentRunActionResultView({
      type: 'generate_chapter',
      status: 'success',
      data: { agent_run_id: 'run-hidden' },
    })).toBeNull()
  })

  it('builds fallback views for recovery execution action results', () => {
    const view = buildAgentRunActionResultView({
      type: 'ui_recovery_execute',
      status: 'running',
      data: { agent_run_id: 'run-running' },
    })

    expect(view?.label).toBe('恢复执行中')
    expect(view?.variant).toBe('neutral')
    expect(view?.detail_items).toContainEqual({ label: '运行 ID', value: 'run-running' })
  })

  it('builds fallback views for trace audit action results', () => {
    const view = buildAgentRunActionResultView({
      type: 'inspect_agent_trace_audit',
      status: 'success',
      data: {
        run: { id: 'run-audit-1', status: 'failed' },
        audit: { status: 'failed', step_count: 3, trace_count: 2 },
        failure: { reason_code: 'tool_failed' },
        recommended_actions: [{ tool_name: 'plan_recovery_tools' }],
      },
    })

    expect(view?.label).toBe('Trace 审计已生成')
    expect(view?.variant).toBe('success')
    expect(view?.detail_items).toContainEqual({ label: '运行状态', value: '失败' })
    expect(view?.detail_items).toContainEqual({ label: '工具步骤', value: '3 个' })
    expect(view?.detail_items).toContainEqual({ label: 'Trace', value: '2 条' })
    expect(view?.detail_items).toContainEqual({ label: '失败原因', value: 'tool_failed' })
    expect(view?.detail_items).toContainEqual({ label: '建议动作', value: '1 个' })
  })

  it('builds recovery execution feedback without leaking plan hash', () => {
    const message = buildAgentRunExecutionFeedback({
      id: 'run-executed',
      project_id: 'project-1',
      goal: '执行恢复计划',
      status: 'success',
      entrypoint: 'ui_recovery_execute',
      input: { recovery_plan_hash: 'plan-hash-1' },
      output: null,
      error: null,
      steps: [],
    })

    expect(message.role).toBe('system')
    expect(message.content).toContain('恢复执行已创建')
    expect(message.action_result?.type).toBe('ui_recovery_execute')
    expect(message.action_result?.data).toEqual({ agent_run_id: 'run-executed' })
    expect(message.action_result_view?.label).toBe('恢复执行已完成')
    expect(message.meta?.agent_run_id).toBe('run-executed')
    expect(JSON.stringify(message)).not.toContain('plan-hash-1')
  })

  it('builds failed recovery execution feedback with an error summary', () => {
    const message = buildAgentRunExecutionFeedback({
      id: 'run-failed',
      project_id: 'project-1',
      goal: '执行恢复计划',
      status: 'failed',
      entrypoint: 'ui_recovery_execute',
      input: { recovery_plan_hash: 'plan-hash-2' },
      output: null,
      error: ' 工具执行失败：缺少章节上下文 ',
      steps: [],
    })

    expect(message.action_result_view.label).toBe('恢复执行失败')
    expect(message.action_result_view.variant).toBe('error')
    expect(message.action_result_view.detail_items).toContainEqual({
      label: '错误摘要',
      value: '工具执行失败：缺少章节上下文',
    })
    expect(JSON.stringify(message)).not.toContain('plan-hash-2')
  })
})
