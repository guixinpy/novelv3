// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import AgentRunContextCompressionPanel from './AgentRunContextCompressionPanel.vue'

describe('AgentRunContextCompressionPanel', () => {
  it('renders context compression projection without provenance internals', () => {
    const wrapper = mount(AgentRunContextCompressionPanel, {
      props: {
        output: {
          status: 'warning',
          version: 'phase225.agent_context_compression_projection.v1',
          project_id: 'project-secret-id',
          chapter_index: 8,
          strategy: {
            granularity: 'chapter_window',
            protect_current_chapter: true,
            protect_head_sections: ['project', 'active_state'],
            protect_tail_sections: ['recent_chapters', 'critical_context'],
          },
          summary: {
            prompt_context_chars: 3800,
            max_chars: 4000,
            usage_ratio: 0.95,
            truncated_section_count: 2,
            context_guard_failure_count: 1,
          },
          risks: [
            {
              code: 'context_window_pressure',
              severity: 'warning',
              message: '章节上下文接近当前摘要窗口上限，应先压缩或扩大窗口再继续生成。',
              threshold: 0.85,
              observed: 0.95,
            },
            {
              code: 'prompt_context_truncated',
              severity: 'warning',
              message: '完整上下文已被截断，继续生成前应复查 longform context 来源窗口。',
            },
          ],
          compression_plan: {
            status: 'recommended',
            mode: 'head_tail_protected_pretrim',
            target_max_chars: 3000,
            protected_head_sections: ['project', 'active_state'],
            protected_tail_sections: ['recent_chapters', 'critical_context'],
            pretrim_order: ['source_sections', 'critical_context', 'recent_chapters'],
            summary_tool: {
              tool_name: 'summarize_longform_context',
              params: { chapter_index: 8, max_chars: 3000, include_prompt_context: false },
            },
            payload_tool: {
              tool_name: 'build_agent_context_compression_payload',
              params: { chapter_index: 8, max_chars: 4000, context_guard_failure_count: 1 },
            },
            llm_summary_required: true,
          },
          recommended_next_tools: ['build_agent_context_compression_payload', 'inspect_agent_memory_route'],
          recovery: {
            status: 'optional',
            reason: 'context_compression_window_pressure',
            next_tools: ['build_agent_context_compression_payload', 'inspect_agent_memory_route'],
            tools: [
              {
                tool_name: 'build_agent_context_compression_payload',
                params: { chapter_index: 8, max_chars: 4000, context_guard_failure_count: 1 },
              },
            ],
          },
          memory_provenance: {
            status: 'truncated',
            sources: [
              { source_type: 'LongformMemory', source_ref: 'longform-memory-secret-id' },
            ],
            windows: {
              sections: {
                source_sections: { has_more: true, source_ids: ['source-secret-id'] },
                critical_context: { has_more: true, source_ids: ['critical-secret-id'] },
              },
            },
          },
          trace: {
            source: 'inspect_agent_context_compression_projection',
            version: 'phase225.agent_context_compression_projection.v1',
            mutability: 'read',
            runtime_behavior_changed: false,
          },
        },
      },
    })

    const text = wrapper.text()
    expect(text).toContain('上下文压缩')
    expect(text).toContain('警告')
    expect(text).toContain('第8章')
    expect(text).toContain('章节窗口')
    expect(text).toContain('保护当前章节')
    expect(text).toContain('上下文字符 3800')
    expect(text).toContain('预算 4000')
    expect(text).toContain('使用率 95%')
    expect(text).toContain('截断分区 2')
    expect(text).toContain('Guard 失败 1')
    expect(text).toContain('目标 3000')
    expect(text).toContain('头部保护 2')
    expect(text).toContain('尾部保护 2')
    expect(text).toContain('预修剪 3')
    expect(text).toContain('需要 LLM 摘要')
    expect(text).toContain('build_agent_context_compression_payload')
    expect(text).toContain('inspect_agent_memory_route')
    expect(text).toContain('context_window_pressure')
    expect(text).toContain('章节上下文接近当前摘要窗口上限')
    expect(text).toContain('prompt_context_truncated')
    expect(text).toContain('完整上下文已被截断')
    expect(text).not.toContain('project-secret-id')
    expect(text).not.toContain('longform-memory-secret-id')
    expect(text).not.toContain('source-secret-id')
    expect(text).not.toContain('critical-secret-id')
    expect(text).not.toContain('source_ref')
    expect(text).not.toContain('source_type')
    expect(text).not.toContain('memory_provenance')
    expect(text).not.toContain('phase225.agent_context_compression_projection.v1')
    expect(text).not.toContain('runtime_behavior_changed')
    expect(text).not.toContain('include_prompt_context')
    expect(text).not.toContain('context_guard_failure_count')
  })
})
