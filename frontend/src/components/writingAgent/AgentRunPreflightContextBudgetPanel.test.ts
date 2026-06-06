// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import AgentRunPreflightContextBudgetPanel from './AgentRunPreflightContextBudgetPanel.vue'

describe('AgentRunPreflightContextBudgetPanel', () => {
  it('renders preflight context budget warning without payload internals', () => {
    const wrapper = mount(AgentRunPreflightContextBudgetPanel, {
      props: {
        step: {
          id: 'step-preflight-budget',
          tool_name: 'preflight_writing',
          input: { chapter_index: 3, max_context_chars: 500 },
          output: {
            status: 'ready',
            checks: {
              context_compression: {
                status: 'warning',
                summary: {
                  prompt_context_chars: 475,
                  max_chars: 500,
                  usage_ratio: 0.95,
                  context_guard_failure_count: 2,
                },
                compression_plan: {
                  status: 'recommended',
                  target_max_chars: 375,
                },
              },
            },
            context_compression_payload_preview: {
              status: 'ready',
              trace: {
                source: 'load_agent_context_compression_summary',
                version: 'secret-preflight-budget-version',
              },
              record: {
                scope_key: 'context_compression:chapter:3:max_chars:500',
                title: '第3章上下文压缩摘要',
                summary: '已持久化的压缩摘要正文不应出现在预算预览中。',
              },
              compression_payload: {
                execution_mode: 'dry_run',
                target_max_chars: 375,
                compressed_context_chars: 360,
                compressed_context: 'SECRET_COMPRESSED_CONTEXT',
              },
              recommended_next_tools: ['prepare_generate_chapter_execution'],
            },
            issues: [
              {
                code: 'context_compression_window_pressure',
                severity: 'warning',
                message: '上下文窗口接近上限，继续生成前应先压缩。',
                suggested_tool: 'record_agent_context_compression_summary',
                suggested_params: {
                  chapter_index: 3,
                  max_chars: 500,
                  context_guard_failure_count: 2,
                },
              },
            ],
            recommended_next_tools: [
              'record_agent_context_compression_summary',
              'prepare_generate_chapter_execution',
            ],
            trace: {
              source: 'preflight_writing',
              version: 'secret-preflight-budget-version',
            },
          },
        },
      },
    })

    const text = wrapper.text()
    expect(text).toContain('上下文预算')
    expect(text).toContain('警告')
    expect(text).toContain('第3章')
    expect(text).toContain('上下文字符 475')
    expect(text).toContain('预算 500')
    expect(text).toContain('使用率 95%')
    expect(text).toContain('目标 375')
    expect(text).toContain('压缩预览 可用')
    expect(text).toContain('压缩字符 360')
    expect(text).toContain('record_agent_context_compression_summary')
    expect(text).toContain('prepare_generate_chapter_execution')
    expect(text).toContain('context_compression_window_pressure')
    expect(text).toContain('上下文窗口接近上限，继续生成前应先压缩。')
    expect(text).not.toContain('SECRET_COMPRESSED_CONTEXT')
    expect(text).not.toContain('context_compression:chapter:3:max_chars:500')
    expect(text).not.toContain('已持久化的压缩摘要正文不应出现在预算预览中')
    expect(text).not.toContain('scope_key')
    expect(text).not.toContain('suggested_params')
    expect(text).not.toContain('context_guard_failure_count')
    expect(text).not.toContain('load_agent_context_compression_summary')
    expect(text).not.toContain('compressed_context')
    expect(text).not.toContain('secret-preflight-budget-version')
  })
})
