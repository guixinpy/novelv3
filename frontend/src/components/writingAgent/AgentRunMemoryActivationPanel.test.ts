// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import AgentRunMemoryActivationPanel from './AgentRunMemoryActivationPanel.vue'

describe('AgentRunMemoryActivationPanel', () => {
  it('renders memory activation plan projection without prompt or provenance internals', () => {
    const wrapper = mount(AgentRunMemoryActivationPanel, {
      props: {
        output: {
          status: 'degraded',
          version: 'phase241.memory_activation.v1',
          project_id: 'project-secret-id',
          chapter_index: 5,
          query: '灯塔旧回声',
          activation: {
            longform: [
              {
                kind: 'longform_memory',
                memory_id: 'memory-secret-1',
                memory_type: 'chapter',
                scope_key: 'chapter:2',
                title: '灯塔回声',
                summary: '顾衍确认旧回声与灯塔地下室有关。',
                chapter_range: { start: 2, end: 2 },
                source_ref: 'longform_memory:memory-secret-1',
              },
            ],
            foreshadowing: [
              {
                kind: 'foreshadowing',
                title: '空白信来源',
                summary: '空白信来自黑潮门内部。',
                introduced_chapter: 1,
                source_ref: 'storyline:story-secret:foreshadowing:0',
              },
            ],
            memory_tree: [
              {
                kind: 'memory_tree_node',
                node_id: 'chapter:2',
                level: 'chapter',
                chapter_index: 2,
                title: '灯塔旧回声',
                summary: '旧回声与地下室有关。',
                relevance: {
                  score: 0.91,
                  matched_terms: ['灯塔', '旧回声'],
                  matched_fields: ['summary'],
                  match_reasons: ['semantic_token_overlap'],
                },
                source_ref: 'memory_tree:chapter:2',
              },
            ],
            world_model: [
              {
                kind: 'world_model',
                proposal_item_id: 'world-secret-1',
                chapter_index: 2,
                subject_ref: 'char.hero',
                predicate: 'knows_secret',
                status: 'pending',
                summary: '顾衍知道旧灯塔密室。',
                source_ref: 'world_proposal_item:world-secret-1',
              },
            ],
            knowledge_base: [
              {
                kind: 'knowledge_base_candidate',
                candidate_id: 'candidate-secret-1',
                memory_type: 'writing_pattern',
                title: '章末钩子',
                summary: '每章结尾保留一个可追踪的实物线索。',
                confidence: 0.86,
                status: 'active',
                source_refs: ['chapter_content:2'],
                source_ref: 'knowledge_base_candidate:candidate-secret-1',
              },
            ],
            style: [
              {
                kind: 'style_anchor',
                title: 'style_config.tone',
                summary: '冷峻短句。',
                source_ref: 'project:project-secret-id:style_config:tone',
              },
            ],
          },
          coverage: {
            activated_counts: {
              longform: 1,
              foreshadowing: 1,
              memory_tree: 1,
              world_model: 1,
              knowledge_base: 1,
              style: 1,
            },
            memory_coverage_debt: {
              status: 'degraded',
              issue_count: 2,
              missing_memory_count: 1,
              stale_retrieval_count: 1,
            },
          },
          risks: [
            {
              code: 'memory_coverage_debt',
              severity: 'warning',
              message: '长篇记忆或检索索引存在缺口，生成前应修复或明确降级使用。',
              issue_count: 2,
            },
          ],
          recommended_next_tools: ['prepare_repair_longform_maintenance', 'inspect_agent_memory_route'],
          prompt_block: '【Writing Agent 长记忆激活】目标：第5章\n- prompt-only raw context',
          memory_provenance: {
            version: 'phase241.memory_activation_provenance.v1',
            status: 'available',
            sources: [
              {
                source_type: 'longform_memory',
                source_ref: 'longform_memory:memory-secret-1',
                title: '灯塔回声',
              },
              {
                source_type: 'memory_tree_node',
                source_ref: 'memory_tree:chapter:2',
                title: '灯塔旧回声',
              },
            ],
            windows: { longform: { total: 1, returned: 1, limit: 8, has_more: false } },
            trace: {
              source: 'build_memory_activation_plan',
              version: 'phase241.memory_activation_provenance.v1',
              mutability: 'read',
            },
          },
          trace: {
            source: 'build_memory_activation_plan',
            version: 'phase241.memory_activation.v1',
            mutability: 'read',
            future_leak_guard: 'end_chapter_index_before_target',
          },
        },
      },
    })

    const text = wrapper.text()
    expect(text).toContain('记忆激活计划')
    expect(text).toContain('降级')
    expect(text).toContain('第5章')
    expect(text).toContain('灯塔旧回声')
    expect(text).toContain('长篇记忆 1')
    expect(text).toContain('伏笔 1')
    expect(text).toContain('Memory Tree 1')
    expect(text).toContain('世界模型 1')
    expect(text).toContain('知识库经验 1')
    expect(text).toContain('风格 1')
    expect(text).toContain('来源覆盖')
    expect(text).toContain('可用')
    expect(text).toContain('覆盖问题 2')
    expect(text).toContain('缺失记忆 1')
    expect(text).toContain('检索陈旧 1')
    expect(text).toContain('灯塔回声')
    expect(text).toContain('空白信来源')
    expect(text).toContain('章末钩子')
    expect(text).toContain('冷峻短句')
    expect(text).toContain('memory_coverage_debt')
    expect(text).toContain('长篇记忆或检索索引存在缺口')
    expect(text).toContain('prepare_repair_longform_maintenance')
    expect(text).toContain('inspect_agent_memory_route')
    expect(text).not.toContain('project-secret-id')
    expect(text).not.toContain('memory-secret-1')
    expect(text).not.toContain('candidate-secret-1')
    expect(text).not.toContain('world-secret-1')
    expect(text).not.toContain('chapter:2')
    expect(text).not.toContain('char.hero')
    expect(text).not.toContain('style_config.tone')
    expect(text).not.toContain('source_ref')
    expect(text).not.toContain('source_refs')
    expect(text).not.toContain('source_type')
    expect(text).not.toContain('prompt-only raw context')
    expect(text).not.toContain('phase241.memory_activation')
    expect(text).not.toContain('build_memory_activation_plan')
    expect(text).not.toContain('future_leak_guard')
    expect(text).not.toContain('end_chapter_index_before_target')
  })
})
