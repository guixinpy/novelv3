// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import AgentRunRetrievalContextPanel from './AgentRunRetrievalContextPanel.vue'

describe('AgentRunRetrievalContextPanel', () => {
  it('renders retrieval context projection without source refs or provenance internals', () => {
    const wrapper = mount(AgentRunRetrievalContextPanel, {
      props: {
        output: {
          status: 'completed',
          version: 'phase243.agent_retrieval_context.v1',
          project_id: 'project-secret-id',
          query: '灯塔旧回声',
          filters: {
            source_type: 'knowledge_base_candidate',
            max_chapter_index: 5,
            limit: 8,
            candidate_limit: 200,
          },
          summary: { total: 4, returned: 2 },
          items: [
            {
              source_type: 'knowledge_base_candidate',
              source_ref: 'knowledge_base_candidate:candidate-secret-1',
              source_id: 'retrieval-secret-1',
              title: '低细节续写可行',
              snippet: 'Agent 先读取知识库后可从低细节目标续写。',
              score: 0.91,
              chapter_index: 5,
            },
            {
              source_type: 'longform_memory',
              source_ref: 'longform_memory:memory-secret-2',
              source_id: 'retrieval-secret-2',
              title: '灯塔地下室回声',
              content: '顾衍在第4章确认灯塔地下室回声仍在。',
              score: 0.78,
              chapter_index: 4,
            },
          ],
          retrieval: {
            internal_debug_ref: 'retrieval_internal_secret',
            query_vector_cache_key: 'retrieval-vector-secret',
          },
          recommended_next_tools: ['summarize_longform_context'],
          memory_provenance: {
            version: 'phase243.agent_retrieval_context_provenance.v1',
            status: 'available',
            sources: [
              {
                source_type: 'knowledge_base_candidate',
                source_ref: 'knowledge_base_candidate:candidate-secret-1',
                title: '低细节续写可行',
                chapter_index: 5,
                score: 0.91,
              },
            ],
            windows: {
              retrieval_items: { total: 4, returned: 2, limit: 8, has_more: true },
            },
            recovery: { status: 'none', reason: 'retrieval_context_available', next_tools: [] },
            trace: {
              source: 'search_agent_retrieval_context',
              version: 'phase243.agent_retrieval_context_provenance.v1',
              mutability: 'read',
            },
          },
          trace: {
            source: 'search_agent_retrieval_context',
            version: 'phase243.agent_retrieval_context.v1',
            mutability: 'read',
            write_performed: false,
          },
        },
      },
    })

    const text = wrapper.text()
    expect(text).toContain('检索证据摘要')
    expect(text).toContain('已完成')
    expect(text).toContain('灯塔旧回声')
    expect(text).toContain('返回 2 / 共 4')
    expect(text).toContain('限制 8')
    expect(text).toContain('候选 200')
    expect(text).toContain('第5章前')
    expect(text).toContain('来源覆盖')
    expect(text).toContain('可用')
    expect(text).toContain('低细节续写可行')
    expect(text).toContain('知识库候选')
    expect(text).toContain('第5章')
    expect(text).toContain('分数 0.91')
    expect(text).toContain('Agent 先读取知识库后可从低细节目标续写')
    expect(text).toContain('灯塔地下室回声')
    expect(text).toContain('长篇记忆')
    expect(text).toContain('第4章')
    expect(text).toContain('顾衍在第4章确认灯塔地下室回声仍在')
    expect(text).toContain('summarize_longform_context')
    expect(text).not.toContain('project-secret-id')
    expect(text).not.toContain('candidate-secret-1')
    expect(text).not.toContain('memory-secret-2')
    expect(text).not.toContain('retrieval-secret-1')
    expect(text).not.toContain('retrieval-secret-2')
    expect(text).not.toContain('source_ref')
    expect(text).not.toContain('source_type')
    expect(text).not.toContain('memory_provenance')
    expect(text).not.toContain('retrieval_items')
    expect(text).not.toContain('phase243.agent_retrieval_context')
    expect(text).not.toContain('retrieval_internal_secret')
    expect(text).not.toContain('retrieval-vector-secret')
  })
})
