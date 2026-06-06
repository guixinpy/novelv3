// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import AgentRunRetrievalPrefetchPanel from './AgentRunRetrievalPrefetchPanel.vue'

describe('AgentRunRetrievalPrefetchPanel', () => {
  it('renders retrieval prefetch plan projection without raw tool call internals', () => {
    const wrapper = mount(AgentRunRetrievalPrefetchPanel, {
      props: {
        output: {
          status: 'ready',
          version: 'phase256.agent_retrieval_prefetch_plan.v1',
          project_id: 'project-secret-id',
          inputs: {
            chapter_index: 5,
            query: '旧灯塔回声',
            limit: 6,
            candidate_limit: 50,
          },
          strategy: {
            status: 'completed',
            version: 'phase253.agent_retrieval_strategy.v1',
            name: 'query_aware_retrieval',
            reason: 'query_available',
            filters: {
              query: '旧灯塔回声',
              max_chapter_index: 4,
              limit: 6,
              candidate_limit: 50,
            },
            recommended_next_tool_calls: [
              {
                tool_name: 'search_agent_retrieval_context',
                params: {
                  source_ref: 'strategy-secret-ref',
                },
              },
            ],
          },
          prefetch_plan: {
            status: 'ready',
            mode: 'query_aware_prefetch',
            target_chapter_index: 5,
            query: '旧灯塔回声',
            max_chapter_index: 4,
            read_tools: ['search_agent_retrieval_context', 'summarize_longform_context'],
            tool_calls: [
              {
                tool_name: 'search_agent_retrieval_context',
                params: {
                  query: '旧灯塔回声',
                  source_ref: 'prefetch-secret-ref',
                },
              },
            ],
            coverage: {
              strategy_name: 'query_aware_retrieval',
              retrieval_documents: 8,
              retrieval_chunks: 32,
              maintenance_ready: true,
            },
          },
          recommended_next_tools: ['search_agent_retrieval_context', 'summarize_longform_context'],
          recommended_next_tool_calls: [
            {
              tool_name: 'search_agent_retrieval_context',
              params: {
                source_ref: 'recommended-secret-ref',
              },
            },
          ],
          trace: {
            source: 'inspect_agent_retrieval_prefetch_plan',
            version: 'phase256.agent_retrieval_prefetch_plan.v1',
            strategy_version: 'phase253.agent_retrieval_strategy.v1',
          },
        },
      },
    })

    const text = wrapper.text()
    expect(text).toContain('检索预取计划')
    expect(text).toContain('预取就绪')
    expect(text).toContain('查询感知预取')
    expect(text).toContain('查询感知检索')
    expect(text).toContain('旧灯塔回声')
    expect(text).toContain('第5章')
    expect(text).toContain('第4章前')
    expect(text).toContain('只读工具 2')
    expect(text).toContain('检索文档 8')
    expect(text).toContain('search_agent_retrieval_context')
    expect(text).toContain('summarize_longform_context')
    expect(text).not.toContain('project-secret-id')
    expect(text).not.toContain('recommended_next_tool_calls')
    expect(text).not.toContain('tool_calls')
    expect(text).not.toContain('strategy-secret-ref')
    expect(text).not.toContain('prefetch-secret-ref')
    expect(text).not.toContain('recommended-secret-ref')
    expect(text).not.toContain('phase256.agent_retrieval_prefetch_plan')
    expect(text).not.toContain('phase253.agent_retrieval_strategy')
  })
})
