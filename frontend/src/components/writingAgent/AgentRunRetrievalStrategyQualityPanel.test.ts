// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import AgentRunRetrievalStrategyQualityPanel from './AgentRunRetrievalStrategyQualityPanel.vue'

describe('AgentRunRetrievalStrategyQualityPanel', () => {
  it('renders retrieval strategy quality projection without dogfood or tool call internals', () => {
    const wrapper = mount(AgentRunRetrievalStrategyQualityPanel, {
      props: {
        output: {
          status: 'needs_dogfood_review',
          version: 'phase255.agent_retrieval_strategy_quality.v1',
          project_id: 'project-secret-id',
          inputs: {
            chapter_index: 5,
            query: '旧灯塔回声',
            limit: 6,
            candidate_limit: 50,
          },
          quality: {
            status: 'needs_dogfood_review',
            strategy_name: 'query_aware_retrieval',
            query_available: true,
            retrieval_documents: 8,
            retrieval_chunks: 32,
            maintenance_ready: true,
            dogfood_status: 'ready',
            dogfood_evidence_count: 9,
            dogfood_ready_evidence_count: 9,
            dogfood_open_findings: 2,
          },
          strategy: {
            status: 'completed',
            name: 'query_aware_retrieval',
            reason: 'query_available',
            filters: {
              query: '旧灯塔回声',
              max_chapter_index: 4,
              limit: 6,
              candidate_limit: 50,
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
          },
          dogfood_evidence: {
            status: 'ready',
            summary: {
              evidence_count: 9,
              ready_evidence_count: 9,
              open_finding_count: 2,
              generated_chapter_count: 4,
            },
            recommended_next_tools: ['inspect_agent_dogfood_evidence'],
            source_refs: ['dogfood-secret-source'],
          },
          diagnostics: [
            {
              code: 'retrieval_strategy_dogfood_open_findings',
              message: 'retrieval-secret-internal message should stay hidden',
            },
          ],
          recommended_next_tools: [
            'search_agent_retrieval_context',
            'summarize_longform_context',
            'inspect_agent_dogfood_evidence',
          ],
          trace: {
            source: 'inspect_agent_retrieval_strategy_quality',
            version: 'phase255.agent_retrieval_strategy_quality.v1',
            dogfood_evidence_version: 'phase251.agent_dogfood_evidence.v1',
          },
        },
      },
    })

    const text = wrapper.text()
    expect(text).toContain('检索策略质量复核')
    expect(text).toContain('需要自吃复核')
    expect(text).toContain('查询感知检索')
    expect(text).toContain('旧灯塔回声')
    expect(text).toContain('第4章前')
    expect(text).toContain('检索文档 8')
    expect(text).toContain('Dogfood 9 / 9')
    expect(text).toContain('开放问题 2')
    expect(text).toContain('search_agent_retrieval_context')
    expect(text).toContain('summarize_longform_context')
    expect(text).toContain('inspect_agent_dogfood_evidence')
    expect(text).not.toContain('project-secret-id')
    expect(text).not.toContain('recommended_next_tool_calls')
    expect(text).not.toContain('retrieval-secret-ref')
    expect(text).not.toContain('dogfood-secret-source')
    expect(text).not.toContain('phase255.agent_retrieval_strategy_quality')
    expect(text).not.toContain('phase251.agent_dogfood_evidence')
    expect(text).not.toContain('retrieval-secret-internal')
  })
})
