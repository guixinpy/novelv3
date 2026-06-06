// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import AgentRunMemoryRoutePanel from './AgentRunMemoryRoutePanel.vue'

describe('AgentRunMemoryRoutePanel', () => {
  it('renders memory route projection without provenance internals', () => {
    const wrapper = mount(AgentRunMemoryRoutePanel, {
      props: {
        output: {
          status: 'completed',
          project_id: 'project-secret-id',
          chapter_index: 13,
          query: '灯塔旧回声',
          route: {
            status: 'ready',
            reason: 'longform_memory_ready',
            can_use_longform_context: true,
            retrieval_document_count: 0,
            recommended_tools: [
              'inspect_agent_memory_tree',
              'summarize_longform_context',
              'preflight_writing',
            ],
          },
          recommended_next_tools: [
            'inspect_agent_memory_tree',
            'summarize_longform_context',
            'preflight_writing',
          ],
          longform_memory: {
            project_id: 'project-secret-id',
            chapter_count: 12,
            current_word_count: 24000,
            total_memories: 14,
            counts_by_type: { chapter: 12, arc: 1, global: 1 },
            latest_updated_at: '2026-06-01T00:00:00Z',
          },
          longform_maintenance: {
            project_id: 'project-secret-id',
            ready_for_writing: true,
            issue_count: 0,
            recommendations: [],
          },
          retrieval: {
            project_id: 'project-secret-id',
            total_documents: 0,
            total_chunks: 0,
            total_terms: 0,
            total_embeddings: 0,
            documents_by_source_type: {},
          },
          memory_provenance: {
            version: 'phase224.agent_memory_route_provenance.v1',
            status: 'degraded',
            sources: [
              { source_ref: 'LongformMemory', source_type: 'longform_memory', item_count: 14 },
              { source_ref: 'RetrievalDocument', source_type: 'retrieval_index', item_count: 0 },
            ],
            windows: {
              longform_memory: { total: 14, returned: 14, limit: 20 },
              retrieval: { total: 0, returned: 0, limit: 20 },
            },
            recovery: {
              status: 'optional',
              reason: 'retrieval_index_empty',
              next_tools: ['inspect_agent_memory_route', 'prepare_repair_longform_maintenance'],
              tools: [
                {
                  tool_name: 'inspect_agent_memory_route',
                  params: {
                    chapter_index: 13,
                    query: '检索索引为空，诊断第13章长篇记忆与检索覆盖。',
                    include_context_summary: false,
                  },
                },
              ],
              write_tools: [{ tool_name: 'prepare_repair_longform_maintenance', params: {} }],
              write_policy: 'requires_confirmation',
            },
            trace: {
              source: 'inspect_agent_memory_route',
              version: 'phase224.agent_memory_route_provenance.v1',
              mutability: 'read',
            },
            coverage: {
              chapter_count: 12,
              longform_memory_count: 14,
              retrieval_document_count: 0,
              ready_for_writing: true,
            },
            boundaries: {
              world_truth: {
                status: 'separated',
                canonical_source: 'Athena/world_model',
                memory_route_role: 'longform_memory_retrieval_and_maintenance_diagnostics',
              },
            },
          },
          diagnostics: [
            {
              code: 'retrieval_index_empty',
              severity: 'warning',
              message: '项目已有正文，但检索索引为空，跨章节召回质量会下降。',
            },
          ],
          trace: {
            source: 'inspect_agent_memory_route',
            version: 'phase72.agent_memory_route.v1',
            mutability: 'read',
          },
        },
      },
    })

    const text = wrapper.text()
    expect(text).toContain('记忆路由')
    expect(text).toContain('可用')
    expect(text).toContain('第13章')
    expect(text).toContain('灯塔旧回声')
    expect(text).toContain('可用于长篇上下文')
    expect(text).toContain('章节 12')
    expect(text).toContain('记忆 14')
    expect(text).toContain('字数 24000')
    expect(text).toContain('检索文档 0')
    expect(text).toContain('检索分片 0')
    expect(text).toContain('维护可写')
    expect(text).toContain('问题 0')
    expect(text).toContain('inspect_agent_memory_tree')
    expect(text).toContain('summarize_longform_context')
    expect(text).toContain('preflight_writing')
    expect(text).toContain('retrieval_index_empty')
    expect(text).toContain('项目已有正文，但检索索引为空')
    expect(text).not.toContain('project-secret-id')
    expect(text).not.toContain('LongformMemory')
    expect(text).not.toContain('RetrievalDocument')
    expect(text).not.toContain('source_ref')
    expect(text).not.toContain('source_type')
    expect(text).not.toContain('phase224.agent_memory_route_provenance.v1')
    expect(text).not.toContain('phase72.agent_memory_route.v1')
    expect(text).not.toContain('Athena/world_model')
    expect(text).not.toContain('longform_memory_retrieval_and_maintenance_diagnostics')
  })
})
