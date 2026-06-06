// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import AgentRunPostChapterMemoryPanel from './AgentRunPostChapterMemoryPanel.vue'

describe('AgentRunPostChapterMemoryPanel', () => {
  it('renders post-chapter memory capture projection without source refs or provenance internals', () => {
    const wrapper = mount(AgentRunPostChapterMemoryPanel, {
      props: {
        output: {
          status: 'completed',
          version: 'phase242.post_chapter_memory_capture.v1',
          project_id: 'project-secret-id',
          chapter_index: 3,
          target_type: 'agent_post_chapter_memory_capture_plan',
          capture_status: 'ready',
          summary: {
            chapter_available: true,
            review_step_count: 2,
            candidate_count: 2,
          },
          candidates: [
            {
              memory_type: 'writing_pattern',
              title: '第3章写作沉淀：雾港追踪',
              summary: '第3章结尾形成雾港追踪线索，后续章节应延续。',
              source_refs: ['chapter_content:chapter-content-3'],
              confidence: 0.72,
              status: 'candidate',
              tags: ['post-chapter-capture', 'chapter:3'],
              evidence: {
                chapter_content_id: 'chapter-content-3',
                chapter_index: 3,
                title: '雾港追踪',
                word_count: 8200,
              },
              next_tool_call: {
                tool_name: 'prepare_record_agent_knowledge_base_candidate',
                params: {
                  memory_type: 'writing_pattern',
                  title: '第3章写作沉淀：雾港追踪',
                  summary: '第3章结尾形成雾港追踪线索，后续章节应延续。',
                  source_refs: ['chapter_content:chapter-content-3'],
                  confidence: 0.72,
                  status: 'candidate',
                  tags: ['post-chapter-capture', 'chapter:3'],
                },
              },
            },
            {
              memory_type: 'self_optimization_lesson',
              title: '第3章审稿经验：雾港追踪',
              summary: 'medium pacing_issue: 中段节奏松散。后续生成应优先避免这些重复问题。',
              source_refs: ['chapter_content:chapter-content-3', 'writing_agent_step:review-step-secret-1'],
              confidence: 0.78,
              status: 'candidate',
              tags: ['post-review', 'self-optimization', 'chapter:3'],
              evidence: {
                chapter_content_id: 'chapter-content-3',
                chapter_index: 3,
                review_step_ids: ['review-step-secret-1', 'review-step-secret-2'],
                finding_count: 1,
              },
              next_tool_call: {
                tool_name: 'prepare_record_agent_knowledge_base_candidate',
                params: {
                  memory_type: 'self_optimization_lesson',
                  title: '第3章审稿经验：雾港追踪',
                  summary: 'medium pacing_issue: 中段节奏松散。后续生成应优先避免这些重复问题。',
                  source_refs: ['chapter_content:chapter-content-3', 'writing_agent_step:review-step-secret-1'],
                  confidence: 0.78,
                  status: 'candidate',
                  tags: ['post-review', 'self-optimization', 'chapter:3'],
                },
              },
            },
          ],
          recommended_next_tools: ['prepare_record_agent_knowledge_base_candidate'],
          memory_provenance: {
            version: 'phase242.post_chapter_memory_capture.v1',
            status: 'available',
            sources: [
              {
                source_type: 'chapter_content',
                source_ref: 'chapter_content:chapter-content-3',
                chapter_index: 3,
              },
              {
                source_type: 'writing_agent_step',
                source_ref: 'writing_agent_step:review-step-secret-1',
                tool_name: 'review_chapter_quality',
                chapter_index: 3,
              },
            ],
            windows: {
              chapter: { total: 1, returned: 1, limit: 1, has_more: false },
              review_steps: { total: 2, returned: 2, limit: 2, has_more: false },
            },
            recovery: {
              status: 'action_required',
              reason: 'approval_required_before_memory_write',
              next_tools: ['prepare_record_agent_knowledge_base_candidate'],
            },
            trace: {
              source: 'plan_post_chapter_memory_capture',
              version: 'phase242.post_chapter_memory_capture.v1',
            },
          },
          trace: {
            source: 'plan_post_chapter_memory_capture',
            version: 'phase242.post_chapter_memory_capture.v1',
            mutability: 'read',
            write_performed: false,
          },
        },
      },
    })

    const text = wrapper.text()
    expect(text).toContain('写后记忆沉淀规划')
    expect(text).toContain('已完成')
    expect(text).toContain('第3章')
    expect(text).toContain('可写入候选')
    expect(text).toContain('章节可用')
    expect(text).toContain('候选 2')
    expect(text).toContain('审稿证据 2')
    expect(text).toContain('来源覆盖')
    expect(text).toContain('可用')
    expect(text).toContain('第3章写作沉淀：雾港追踪')
    expect(text).toContain('写法模式')
    expect(text).toContain('置信 0.72')
    expect(text).toContain('第3章结尾形成雾港追踪线索')
    expect(text).toContain('第3章审稿经验：雾港追踪')
    expect(text).toContain('自优化经验')
    expect(text).toContain('置信 0.78')
    expect(text).toContain('中段节奏松散')
    expect(text).toContain('prepare_record_agent_knowledge_base_candidate')
    expect(text).not.toContain('project-secret-id')
    expect(text).not.toContain('chapter-content-3')
    expect(text).not.toContain('review-step-secret')
    expect(text).not.toContain('chapter_content:')
    expect(text).not.toContain('writing_agent_step:')
    expect(text).not.toContain('source_ref')
    expect(text).not.toContain('source_refs')
    expect(text).not.toContain('source_type')
    expect(text).not.toContain('memory_provenance')
    expect(text).not.toContain('target_type')
    expect(text).not.toContain('agent_post_chapter_memory_capture_plan')
    expect(text).not.toContain('next_tool_call')
    expect(text).not.toContain('phase242.post_chapter_memory_capture')
  })
})
