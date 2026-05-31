import { describe, expect, it } from 'vitest'
import {
  MEMORY_LOOP_AGENT_RUN_ACTION_DESCRIPTORS,
  MEMORY_LOOP_AGENT_RUN_ACTION_TYPES,
  type MemoryLoopAgentRunActionType,
} from './memoryLoopAgentRunProjection'

function buildMemoryLoopView(
  type: MemoryLoopAgentRunActionType,
  status: string,
  data: Record<string, unknown>,
) {
  return MEMORY_LOOP_AGENT_RUN_ACTION_DESCRIPTORS[type].buildView({ type, status, data }, status)
}

describe('memoryLoopAgentRunProjection', () => {
  it('exposes memory loop action descriptors', () => {
    expect(MEMORY_LOOP_AGENT_RUN_ACTION_TYPES).toEqual([
      'search_agent_retrieval_context',
      'plan_post_chapter_memory_capture',
    ])
    for (const type of MEMORY_LOOP_AGENT_RUN_ACTION_TYPES) {
      expect(MEMORY_LOOP_AGENT_RUN_ACTION_DESCRIPTORS[type]?.type).toBe(type)
      expect(typeof MEMORY_LOOP_AGENT_RUN_ACTION_DESCRIPTORS[type]?.buildView).toBe('function')
    }
  })

  it('builds retrieval context views without leaking raw provenance or snippets', () => {
    const view = buildMemoryLoopView('search_agent_retrieval_context', 'success', {
      status: 'completed',
      summary: { total: 3, returned: 2 },
      items: [
        {
          source_type: 'chapter',
          source_ref: 'chapter:2',
          title: '雾港追踪',
          chapter_index: 2,
          score: 0.91,
          snippet: '主角在码头发现伪造货单。',
        },
      ],
      recommended_next_tools: ['summarize_longform_context'],
      memory_provenance: {
        status: 'available',
        trace_id: 'trace-secret',
      },
    })

    expect(view.label).toBe('检索证据已返回')
    expect(view.variant).toBe('success')
    expect(view.detail_items).toContainEqual({ label: '检索证据', value: '返回 2 / 共 3' })
    expect(view.detail_items).toContainEqual({ label: '首个来源', value: '雾港追踪 · 第2章' })
    expect(view.detail_items).toContainEqual({ label: '下一步', value: '1 个工具' })
    expect(JSON.stringify(view)).not.toContain('memory_provenance')
    expect(JSON.stringify(view)).not.toContain('trace-secret')
    expect(JSON.stringify(view)).not.toContain('伪造货单')
  })

  it('builds post-chapter memory capture views without leaking candidate bodies', () => {
    const view = buildMemoryLoopView('plan_post_chapter_memory_capture', 'success', {
      status: 'completed',
      chapter_index: 3,
      capture_status: 'ready',
      summary: {
        chapter_available: true,
        review_step_count: 2,
        candidate_count: 2,
      },
      candidates: [
        { memory_type: 'writing_pattern', title: '第3章写作沉淀：雾港追踪' },
        { memory_type: 'self_optimization_lesson', title: '第3章审稿经验：雾港追踪' },
      ],
      recommended_next_tools: ['prepare_record_agent_knowledge_base_candidate'],
      memory_provenance: {
        status: 'available',
        trace_id: 'trace-secret',
      },
    })

    expect(view.label).toBe('写后记忆候选已规划')
    expect(view.variant).toBe('success')
    expect(view.detail_items).toContainEqual({ label: '章节', value: '第3章' })
    expect(view.detail_items).toContainEqual({ label: '写后记忆', value: '可写入候选' })
    expect(view.detail_items).toContainEqual({ label: '候选', value: '2 个' })
    expect(view.detail_items).toContainEqual({ label: '审稿证据', value: '2 个' })
    expect(view.detail_items).toContainEqual({ label: '下一步', value: '1 个工具' })
    expect(JSON.stringify(view)).not.toContain('memory_provenance')
    expect(JSON.stringify(view)).not.toContain('trace-secret')
    expect(JSON.stringify(view)).not.toContain('第3章写作沉淀')
  })
})
