// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import ActionCard from './ActionCard.vue'

describe('ActionCard', () => {
  it('renders execution previews for approval-backed pending actions', () => {
    const wrapper = mount(ActionCard, {
      props: {
        disabled: false,
        action: {
          id: 'pending-1',
          type: 'generate_chapter',
          description: '第2章正文已准备好审批，确认后将正式写入正文。',
          params: {},
          requires_confirmation: true,
          execution_preview: {
            title: '待执行：生成正文',
            summary: '确认后将执行 1 个写入步骤。',
            write_step_count: 1,
            approval_contract_hash: 'approval:abc123',
            audit: {
              kind: 'approval_contract',
              approval_contract_hash: 'approval:abc123',
              approval_contract_version: 'phase108.agent_plan_approval_contract.v1',
              plan_id: 'direct-generate:project-1:chapter:2',
              source_projection_id: 'projection-1',
              planner_version: 'phase114.generate_chapter_execution_prepare.v1',
              intent_class: 'direct_generate_chapter',
            },
            steps: [
              {
                tool_name: 'generate_chapter',
                label: '生成正文',
                reason: '直接生成指定章节正文。',
                params: { chapter_index: 2 },
              },
            ],
          },
        },
      },
    })

    expect(wrapper.text()).toContain('待执行：生成正文')
    expect(wrapper.text()).toContain('确认后将执行 1 个写入步骤。')
    expect(wrapper.text()).toContain('生成正文')
    expect(wrapper.text()).toContain('直接生成指定章节正文。')
    expect(wrapper.text()).toContain('审批依据')
    expect(wrapper.text()).toContain('direct_generate_chapter')
    expect(wrapper.text()).toContain('projection-1')
    expect(wrapper.text()).not.toContain('approval:abc123')
  })

  it('renders safe pending action recommendations without internal tool details', async () => {
    const wrapper = mount(ActionCard, {
      props: {
        disabled: false,
        action: {
          id: 'pending-2',
          type: 'preview_setup',
          description: '我建议先为项目生成设定，这样后续创作更有基础。',
          params: {},
          requires_confirmation: true,
          safety_view: {
            kind: 'pending_action_safety',
            recommendations: [
              {
                kind: 'route_upgrade_preview',
                title: '可先生成路由升级审批契约',
                message: '这只生成审批准备信息，不会执行当前待确认操作。',
                severity: 'info',
                auto_execute: false,
                guarded_apply: false,
                action: {
                  kind: 'prepare_route_upgrade_contract',
                  label: '生成审批契约',
                  pending_action_id: 'pending-2',
                  auto_execute: false,
                  guarded_apply: false,
                  tool_name: 'preview_pending_action_route_approval_opt_in_apply_contract',
                },
                approval_contract_hash: 'approval:secret',
                tool_name: 'preview_pending_action_route_approval_opt_in_apply_contract',
              },
            ],
          },
        },
      },
    })

    expect(wrapper.text()).toContain('可先生成路由升级审批契约')
    expect(wrapper.text()).toContain('这只生成审批准备信息，不会执行当前待确认操作。')
    expect(wrapper.text()).not.toContain('approval:secret')
    expect(wrapper.text()).not.toContain('preview_pending_action_route_approval_opt_in_apply_contract')

    await wrapper.get('[data-testid="pending-action-safety-prepare"]').trigger('click')

    expect(wrapper.emitted('safetyAction')?.[0]?.[0]).toEqual({
      kind: 'prepare_route_upgrade_contract',
      label: '生成审批契约',
      pending_action_id: 'pending-2',
      auto_execute: false,
      guarded_apply: false,
    })
  })
})
