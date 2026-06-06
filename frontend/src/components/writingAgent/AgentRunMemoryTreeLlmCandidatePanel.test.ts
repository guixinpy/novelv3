// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
import { afterEach, describe, expect, it } from 'vitest'
import AgentRunMemoryTreeLlmCandidatePanel from './AgentRunMemoryTreeLlmCandidatePanel.vue'

describe('AgentRunMemoryTreeLlmCandidatePanel', () => {
  afterEach(() => {
    document.body.innerHTML = ''
  })

  it('renders candidate summaries without internal trace details and emits prepare action', async () => {
    const prepareAction = {
      key: 'memory-tree-llm-candidate-prepare:1',
      label: '准备候选摘要：空白信来源',
      payload: {
        sourceRunId: 'run-memory-tree-candidates',
        sourcePlanId: 'memory-tree-llm-candidate-prepare:1',
        goal: '准备 Memory Tree 候选摘要审批：第2章 空白信来源',
        tools: [],
        planner: {},
      },
    }
    const wrapper = mount(AgentRunMemoryTreeLlmCandidatePanel, {
      attachTo: document.body,
      props: {
        prepareActions: [prepareAction],
        output: {
          status: 'ready',
          filters: { chapter_index: 2, limit: 2 },
          summary: {
            candidate_traces: 2,
            ready_candidates: 2,
            materialized_candidates: 0,
            pending_candidates: 2,
          },
          candidates: [
            {
              trace_id: 'trace-secret-1',
              trace_status: 'success',
              chapter_index: 2,
              model: 'deepseek-chat',
              prompt_tokens: 101,
              completion_tokens: 66,
              summary_target: {
                level: 'chapter',
                scope_key: 'chapter:2',
                chapter_index: 2,
              },
              candidate: {
                summary: '顾衍保留灯塔旧回声线索，蓝焰证词仍待复核。',
                salient_terms: ['灯塔旧回声', '蓝焰证词'],
                open_questions: ['蓝焰证词是否可靠？'],
                source_coverage: ['chapter_content', 'outline'],
              },
              source_count: 3,
              source_chars: 848,
              quality_precheck_status: 'degraded',
              materialization: {
                status: 'pending',
                memory_type: 'memory_tree_chapter_summary',
                scope_key: 'chapter:2',
                chapter_index: 2,
                summary_hash_match: null,
                source: 'longform_memories',
              },
            },
            {
              trace_id: 'trace-secret-2',
              trace_status: 'success',
              chapter_index: 2,
              model: 'deepseek-chat',
              candidate: {
                summary: '空白信来源与灯塔暗道记录形成第二条摘要候选。',
                salient_terms: ['空白信来源', '灯塔暗道'],
              },
              source_count: 2,
              source_chars: 612,
              quality_precheck_status: 'ready',
              materialization: {
                status: 'pending',
                scope_key: 'chapter:2',
              },
            },
          ],
        },
      },
    })

    const text = wrapper.text()
    expect(text).toContain('Memory Tree 候选摘要')
    expect(text).toContain('可用')
    expect(text).toContain('候选 2 / 可准备 2 / 已物化 0')
    expect(text).toContain('第2章')
    expect(text).toContain('灯塔旧回声')
    expect(text).toContain('顾衍保留灯塔旧回声线索')
    expect(text).toContain('来源 3 / 848 字')
    expect(text).toContain('质量预检：降级')
    expect(text).toContain('待物化')
    expect(text).toContain('空白信来源')
    expect(text).toContain('空白信来源与灯塔暗道记录形成第二条摘要候选。')
    expect(text).toContain('来源 2 / 612 字')
    expect(text).toContain('质量预检：通过')
    expect(text).not.toContain('trace-secret-1')
    expect(text).not.toContain('trace-secret-2')
    expect(text).not.toContain('candidate_trace_id')
    expect(text).not.toContain('scope_key')
    expect(text).not.toContain('approval_contract')

    await wrapper.get('[data-testid="memory-tree-llm-candidate-prepare"]').trigger('click')

    expect(wrapper.emitted('prepare')).toEqual([[prepareAction]])
  })

  it('renders materialized candidates without prepare actions', () => {
    const wrapper = mount(AgentRunMemoryTreeLlmCandidatePanel, {
      props: {
        prepareActions: [],
        output: {
          status: 'ready',
          filters: { chapter_index: 2, limit: 1 },
          summary: {
            candidate_traces: 1,
            ready_candidates: 1,
            materialized_candidates: 1,
            pending_candidates: 0,
          },
          candidates: [
            {
              trace_id: 'trace-materialized-secret',
              chapter_index: 2,
              candidate: {
                summary: '蓝焰证词已经写入 Memory Tree 章级摘要。',
                salient_terms: ['蓝焰证词'],
              },
              source_count: 1,
              source_chars: 120,
              quality_precheck_status: 'ready',
              materialization: {
                status: 'materialized',
                scope_key: 'chapter:2',
              },
            },
          ],
        },
      },
    })

    const text = wrapper.text()
    expect(text).toContain('候选 1 / 可准备 0 / 已物化 1')
    expect(text).toContain('蓝焰证词已经写入 Memory Tree 章级摘要。')
    expect(text).toContain('已物化')
    expect(text).not.toContain('trace-materialized-secret')
    expect(text).not.toContain('scope_key')
    expect(wrapper.findAll('[data-testid="memory-tree-llm-candidate-prepare"]')).toHaveLength(0)
  })
})
