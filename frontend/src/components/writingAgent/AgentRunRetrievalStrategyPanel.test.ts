// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import AgentRunRetrievalStrategyPanel from './AgentRunRetrievalStrategyPanel.vue'

describe('AgentRunRetrievalStrategyPanel', () => {
  it('renders retrieval strategy projection without raw tool call internals', () => {
    const wrapper = mount(AgentRunRetrievalStrategyPanel, {
      props: {
        output: {
          status: 'completed',
          version: 'phase253.agent_retrieval_strategy.v1',
          project_id: 'project-secret-id',
          inputs: {
            chapter_index: 5,
            query: '旧灯塔回声',
            limit: 6,
            candidate_limit: 50,
          },
          strategy: {
            name: 'query_aware_retrieval',
            read_mode: 'search_then_summarize',
            filters: {
              query: '旧灯塔回声',
              max_chapter_index: 4,
              limit: 6,
              candidate_limit: 50,
            },
          },
          recommended_next_tools: ['search_agent_retrieval_context', 'summarize_longform_context'],
          recommended_next_tool_calls: [
            {
              tool_name: 'search_agent_retrieval_context',
              params: {
                query: '旧灯塔回声',
                source_ref: 'retrieval-secret-ref',
              },
            },
          ],
          trace: {
            source: 'inspect_agent_retrieval_strategy',
            version: 'phase253.agent_retrieval_strategy.v1',
          },
        },
      },
    })

    const text = wrapper.text()
    expect(text).toContain('检索策略摘要')
    expect(text).toContain('已完成')
    expect(text).toContain('查询感知检索')
    expect(text).toContain('旧灯塔回声')
    expect(text).toContain('第4章前')
    expect(text).toContain('限制 6')
    expect(text).toContain('候选 50')
    expect(text).toContain('search_agent_retrieval_context')
    expect(text).toContain('summarize_longform_context')
    expect(text).not.toContain('project-secret-id')
    expect(text).not.toContain('recommended_next_tool_calls')
    expect(text).not.toContain('retrieval-secret-ref')
    expect(text).not.toContain('phase253.agent_retrieval_strategy')
  })
})
