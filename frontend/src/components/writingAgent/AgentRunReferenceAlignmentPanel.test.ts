// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import AgentRunReferenceAlignmentPanel from './AgentRunReferenceAlignmentPanel.vue'

describe('AgentRunReferenceAlignmentPanel', () => {
  it('renders reference alignment projection without source path internals', () => {
    const wrapper = mount(AgentRunReferenceAlignmentPanel, {
      props: {
        output: {
          status: 'completed',
          version: 'phase232.reference_alignment_inspection.v1',
          source_refs: [
            'references/agent-projects/hermes-agent',
            'references/agent-projects/openhuman',
            'references/agent-projects/openclaw',
          ],
          summary: {
            source_count: 3,
            pattern_count: 5,
            decision_count: 9,
            capability_area_count: 10,
            adapter_backed_tool_count: 42,
          },
          patterns: [
            {
              pattern_id: 'tool_registry_visible_surface',
              source: 'hermes-agent',
              source_path: 'references/agent-projects/hermes-agent/AGENTS.md',
              source_lines: ['263-301'],
              applied_patterns: ['tool_lifecycle_hooks', 'toolset_visibility_boundary'],
              decision: 'Keep Writing Agent tools registered through descriptors/adapters.',
            },
            {
              pattern_id: 'permission_audit_gate',
              source: 'openhuman',
              source_path: 'references/agent-projects/openhuman/docs/agent-subagent-tool-flow.md',
              source_lines: ['312-325'],
              applied_patterns: ['approval_gated_execution'],
              decision: 'High-risk writes must pass approval gates.',
            },
          ],
          capability_alignment: [
            {
              area: 'Hermes/dialog',
              current_decision: 'Dialog intent routes enter Writing Agent plan tools.',
              module_paths: ['backend/app/services/writing_agent/dialog_intent_planner.py'],
              evidence_tools: ['plan_dialog_intent_agent_run'],
              adapter_backed_tools: ['plan_dialog_intent_agent_run'],
              status: 'implemented',
            },
            {
              area: 'frontend',
              current_decision: 'Frontend actions expose Agent routes.',
              module_paths: ['frontend/src/components/chat/agentRunProjection.ts'],
              evidence_tools: ['inspect_agent_dialog_control_plane_projection'],
              adapter_backed_tools: [],
              status: 'descriptor_only',
            },
          ],
          recommended_next_tools: ['inspect_agent_tool_contracts', 'inspect_agent_health_projection'],
          trace: {
            reference_pattern_version: 'phase107.reference_pattern_projection.v1',
            adapter_backed_tool_count: 42,
          },
        },
      },
    })

    const text = wrapper.text()
    expect(text).toContain('参考项目对齐')
    expect(text).toContain('已完成')
    expect(text).toMatch(/参考项目\s*3/)
    expect(text).toMatch(/模式\s*5/)
    expect(text).toMatch(/决策\s*9/)
    expect(text).toMatch(/能力域\s*10/)
    expect(text).toMatch(/适配工具\s*42/)
    expect(text).toContain('hermes-agent')
    expect(text).toContain('openhuman')
    expect(text).toContain('tool_lifecycle_hooks')
    expect(text).toContain('approval_gated_execution')
    expect(text).toContain('Hermes/dialog')
    expect(text).toContain('frontend')
    expect(text).toContain('已实现')
    expect(text).toContain('仅描述符')
    expect(text).toContain('inspect_agent_tool_contracts')
    expect(text).toContain('inspect_agent_health_projection')
    expect(text).not.toContain('references/agent-projects')
    expect(text).not.toContain('backend/app/services')
    expect(text).not.toContain('frontend/src/components')
    expect(text).not.toContain('phase232.reference_alignment_inspection')
    expect(text).not.toContain('phase107.reference_pattern_projection')
    expect(text).not.toContain('tool_registry_visible_surface')
    expect(text).not.toContain('permission_audit_gate')
  })
})
