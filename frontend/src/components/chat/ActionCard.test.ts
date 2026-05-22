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
})
