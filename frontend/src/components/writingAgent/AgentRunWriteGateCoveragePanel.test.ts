// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import AgentRunWriteGateCoveragePanel from './AgentRunWriteGateCoveragePanel.vue'

describe('AgentRunWriteGateCoveragePanel', () => {
  it('renders write gate coverage projection without adapter or gate internals', () => {
    const wrapper = mount(AgentRunWriteGateCoveragePanel, {
      props: {
        output: {
          status: 'completed',
          version: 'phase113.write_gate_coverage.v1',
          summary: {
            write_tool_count: 12,
            agent_plan_gate_enforced_count: 8,
            direct_confirmation_guard_count: 5,
            missing_agent_plan_gate_count: 3,
            high_risk_direct_write_count: 1,
          },
          write_tools: [
            {
              tool_name: 'generate_setup',
              category: 'generation',
              target_type: 'setup',
              sort_key: 'secret-sort-key',
              adapter_exists: true,
              adapter_type: 'static',
              handler_name: 'handler_secret_generate_setup',
              mutability: 'guarded_write',
              requires_confirmation: false,
              direct_confirmation_guard: false,
              direct_write_policy: null,
              direct_write_blocked: false,
              confirmation_fields: [],
              agent_plan_gate_status: 'missing_agent_plan_gate',
              gate_version: null,
              gate_type: null,
              indirect_coverage: [],
              risk_level: 'high',
              recommended_action: 'add_direct_agent_plan_approval_gate',
            },
            {
              tool_name: 'generate_chapter',
              category: 'generation',
              target_type: 'chapter',
              sort_key: 'secret-sort-key',
              adapter_exists: true,
              adapter_type: 'static',
              handler_name: 'handler_secret_generate_chapter',
              mutability: 'guarded_write',
              requires_confirmation: false,
              direct_confirmation_guard: false,
              direct_write_policy: 'approval_required_redirect',
              direct_write_blocked: true,
              confirmation_fields: [],
              agent_plan_gate_status: 'indirect_agent_gate_available',
              gate_version: null,
              gate_type: null,
              indirect_coverage: [
                {
                  consumer_tool: 'execute_generate_chapter_with_approval',
                  gate_version: 'phase114.direct_generate_agent_plan_approval.v1',
                  scope: 'only_when_called_through_consumer',
                },
              ],
              risk_level: 'low',
              recommended_action: 'route_direct_calls_to_approval_executor',
            },
            {
              tool_name: 'execute_generate_chapter_with_approval',
              category: 'generation',
              target_type: 'chapter',
              sort_key: 'secret-sort-key',
              adapter_exists: true,
              adapter_type: 'static',
              handler_name: 'handler_secret_execute_generate_chapter',
              mutability: 'write',
              requires_confirmation: true,
              direct_confirmation_guard: true,
              direct_write_policy: null,
              direct_write_blocked: false,
              confirmation_fields: ['approval_contract_hash', 'confirm_execute'],
              agent_plan_gate_status: 'enforced',
              gate_version: 'phase114.direct_generate_agent_plan_approval.v1',
              gate_type: 'stateless_agent_plan_approval',
              indirect_coverage: [],
              risk_level: 'low',
              recommended_action: 'monitor_gate_drift',
            },
          ],
          recommended_next_targets: [
            {
              tool_name: 'generate_setup',
              category: 'generation',
              risk_level: 'high',
              agent_plan_gate_status: 'missing_agent_plan_gate',
              recommended_action: 'add_direct_agent_plan_approval_gate',
            },
            {
              tool_name: 'generate_chapter',
              category: 'generation',
              risk_level: 'low',
              agent_plan_gate_status: 'indirect_agent_gate_available',
              recommended_action: 'route_direct_calls_to_approval_executor',
            },
          ],
          trace: {
            source: 'inspect_agent_write_gate_coverage',
            coverage_basis: 'tool_descriptor_plus_adapter_metadata',
          },
        },
      },
    })

    const text = wrapper.text()
    expect(text).toContain('写入门禁覆盖')
    expect(text).toContain('已完成')
    expect(text).toMatch(/写入工具\s*12/)
    expect(text).toMatch(/Agent 审批\s*8/)
    expect(text).toMatch(/确认守卫\s*5/)
    expect(text).toMatch(/门禁缺口\s*3/)
    expect(text).toMatch(/高风险直写\s*1/)
    expect(text).toContain('generate_setup')
    expect(text).toContain('高风险')
    expect(text).toContain('缺少 Agent 计划门禁')
    expect(text).toContain('补齐 Agent 计划审批门禁')
    expect(text).toContain('generate_chapter')
    expect(text).toContain('低风险')
    expect(text).toContain('间接审批可用')
    expect(text).toContain('转到审批执行器')
    expect(text).not.toContain('handler_secret')
    expect(text).not.toContain('phase113.write_gate_coverage')
    expect(text).not.toContain('phase114.direct_generate_agent_plan_approval')
    expect(text).not.toContain('tool_descriptor_plus_adapter_metadata')
    expect(text).not.toContain('approval_required_redirect')
    expect(text).not.toContain('adapter_type')
    expect(text).not.toContain('handler_name')
    expect(text).not.toContain('confirmation_fields')
    expect(text).not.toContain('gate_version')
    expect(text).not.toContain('gate_type')
    expect(text).not.toContain('indirect_coverage')
    expect(text).not.toContain('sort_key')
    expect(text).not.toContain('guarded_write')
    expect(text).not.toContain('stateless_agent_plan_approval')
  })
})
