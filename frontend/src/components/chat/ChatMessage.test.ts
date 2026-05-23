// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import ChatMessage from './ChatMessage.vue'

describe('ChatMessage', () => {
  it('shows assistant message creation time to separate old answers from current context', () => {
    const wrapper = mount(ChatMessage, {
      props: {
        msg: {
          role: 'assistant',
          content: '这是历史回复。',
          created_at: '2026-05-12T12:34:56Z',
        },
        isLatest: false,
        loading: false,
      },
    })

    expect(wrapper.text()).toContain('2026-05-12 12:34')
  })

  it('emits openTrace when clicking assistant trace button', async () => {
    const wrapper = mount(ChatMessage, {
      props: {
        msg: {
          role: 'assistant',
          content: '这是带模型调用上下文的回复。',
          trace_id: 'trace-1',
        },
        isLatest: false,
        loading: false,
      },
    })

    await wrapper.get('[data-testid="open-trace"]').trigger('click')

    expect(wrapper.emitted('openTrace')).toEqual([['trace-1']])
  })

  it('does not render trace button without trace id', () => {
    const wrapper = mount(ChatMessage, {
      props: {
        msg: {
          role: 'assistant',
          content: '这是普通回复。',
        },
        isLatest: false,
        loading: false,
      },
    })

    expect(wrapper.find('[data-testid="open-trace"]').exists()).toBe(false)
  })

  it('does not render trace button for user messages', () => {
    const wrapper = mount(ChatMessage, {
      props: {
        msg: {
          role: 'user',
          content: '用户消息不显示上下文按钮。',
          trace_id: 'trace-user',
        },
        isLatest: false,
        loading: false,
      },
    })

    expect(wrapper.find('[data-testid="open-trace"]').exists()).toBe(false)
  })

  it('emits openTrace for system action messages with trace id', async () => {
    const wrapper = mount(ChatMessage, {
      props: {
        msg: {
          role: 'system',
          content: '设定生成完成。',
          trace_id: 'trace-system',
          action_result: { type: 'generate_setup', status: 'success' },
        },
        isLatest: false,
        loading: false,
      },
    })

    await wrapper.get('[data-testid="open-trace"]').trigger('click')

    expect(wrapper.emitted('openTrace')).toEqual([['trace-system']])
  })

  it('renders chapter generation action results with a user-facing label', () => {
    const wrapper = mount(ChatMessage, {
      props: {
        msg: {
          role: 'system',
          message_type: 'plain',
          content: '第1章正文生成完成。',
          action_result: { type: 'generate_chapter', status: 'success' },
        },
        isLatest: false,
        loading: false,
      },
    })

    expect(wrapper.text()).toContain('生成正文执行成功')
    expect(wrapper.text()).not.toContain('generate_chapter')
  })

  it('renders chapter approval-required action results with a user-facing label', () => {
    const wrapper = mount(ChatMessage, {
      props: {
        msg: {
          role: 'system',
          message_type: 'plain',
          content: '第2章正文生成计划已准备完成，等待确认执行。',
          action_result: { type: 'generate_chapter', status: 'approval_required' },
        },
        isLatest: false,
        loading: false,
      },
    })

    expect(wrapper.text()).toContain('生成正文等待确认')
    expect(wrapper.text()).not.toContain('approval_required')
  })

  it('prefers backend-projected action result labels when available', () => {
    const wrapper = mount(ChatMessage, {
      props: {
        msg: {
          role: 'system',
          message_type: 'plain',
          content: '状态已更新。',
          action_result: { type: 'generate_chapter', status: 'raw_status' },
          action_result_view: {
            type: 'generate_chapter',
            status: 'raw_status',
            label: '后端投影文案',
            variant: 'success',
          },
        },
        isLatest: false,
        loading: false,
      },
    })

    expect(wrapper.text()).toContain('后端投影文案')
    expect(wrapper.text()).not.toContain('raw_status')
  })

  it('renders backend-projected approval decision details without raw hashes', () => {
    const wrapper = mount(ChatMessage, {
      props: {
        msg: {
          role: 'system',
          message_type: 'plain',
          content: '操作已确认，正在生成中...',
          action_result: {
            type: 'generate_chapter',
            status: 'generating',
            data: {
              approval_decision: {
                approval_contract_hash: 'approval:secret-hash',
              },
            },
          },
          action_result_view: {
            type: 'generate_chapter',
            status: 'generating',
            label: '正文生成中...',
            variant: 'neutral',
            detail_items: [
              { label: '用户决策', value: '已确认' },
              { label: '审批契约', value: '已绑定' },
            ],
          },
        },
        isLatest: false,
        loading: false,
      },
    })

    expect(wrapper.text()).toContain('用户决策')
    expect(wrapper.text()).toContain('已确认')
    expect(wrapper.text()).toContain('审批契约')
    expect(wrapper.text()).toContain('已绑定')
    expect(wrapper.text()).not.toContain('approval:secret-hash')
  })

  it('renders pending chapter conflict as a warning before confirmation', () => {
    const wrapper = mount(ChatMessage, {
      props: {
        msg: {
          role: 'assistant',
          message_type: 'plain',
          content: '准备生成章节。',
          pending_action: {
            id: 'pending-1',
            type: 'preview_chapter',
            description: '我可以生成第2章正文，完成后会进入 Calliope 和正文进度。 注意：第2章已有待确认或运行中的生成任务，请确认是否仍要继续。',
            params: {
              chapter_index: 2,
              chapter_target_conflict: {
                status: 'reserved',
                chapter_index: 2,
                reason: 'pending_or_running_generation',
              },
            },
          },
        },
        isLatest: true,
        loading: false,
      },
    })

    const warning = wrapper.get('[data-testid="chapter-target-conflict"]')
    expect(warning.text()).toContain('第2章已有待确认或运行中的生成任务')
    expect(warning.text()).toContain('确认前请检查是否要继续覆盖同一章节')
    expect(wrapper.get('.action-card__copy').text()).not.toContain('注意：')
  })

  it('renders pending chapter conflict source labels', () => {
    const wrapper = mount(ChatMessage, {
      props: {
        msg: {
          role: 'assistant',
          message_type: 'plain',
          content: '准备生成章节。',
          pending_action: {
            id: 'pending-1',
            type: 'preview_chapter',
            description: '我可以生成第2章正文，完成后会进入 Calliope 和正文进度。 注意：第2章已有批量生成任务，请确认是否仍要继续。',
            params: {
              chapter_index: 2,
              chapter_target_conflict: {
                status: 'reserved',
                chapter_index: 2,
                reason: 'pending_or_running_generation',
                source: 'range_task',
                source_label: '批量生成任务',
              },
            },
          },
        },
        isLatest: true,
        loading: false,
      },
    })

    const warning = wrapper.get('[data-testid="chapter-target-conflict"]')
    expect(warning.text()).toContain('第2章已有批量生成任务')
    expect(wrapper.get('.action-card__copy').text()).not.toContain('注意：')
  })

  it('renders generating action progress without repeating the action verb', () => {
    const wrapper = mount(ChatMessage, {
      props: {
        msg: {
          role: 'system',
          message_type: 'plain',
          content: '操作已确认，正在生成中...',
          action_result: { type: 'generate_setup', status: 'generating' },
        },
        isLatest: false,
        loading: false,
      },
    })

    expect(wrapper.text()).toContain('设定生成中...')
    expect(wrapper.text()).not.toContain('生成设定生成中')
  })
})
