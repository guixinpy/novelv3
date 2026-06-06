// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import AgentRunLongformContextPanel from './AgentRunLongformContextPanel.vue'

describe('AgentRunLongformContextPanel', () => {
  it('renders longform context summary projection without prompt or provenance internals', () => {
    const wrapper = mount(AgentRunLongformContextPanel, {
      props: {
        output: {
          status: 'completed',
          project_id: 'project-secret-id',
          chapter_index: 6,
          project: {
            id: 'project-secret-id',
            name: '雾港项目',
            genre: '悬疑科幻',
            target_chapter_count: 600,
            target_word_count: 1800000,
            current_word_count: 48000,
            status: 'drafting',
          },
          progress: {
            generated_chapter_count: 5,
            latest_generated_chapter_index: 5,
            generated_word_count: 48000,
          },
          context_summary: {
            goal: '灯塔旧回声',
            active_state: {
              target_outline: {
                chapter_index: 6,
                title: '潮下车站',
                summary: '林深追查旧灯塔回声。',
                characters: ['林深', '苏晚晴'],
                purpose: '揭示潮下车站入口。',
              },
              previous_chapter: {
                chapter_index: 5,
                title: '黑潮门回声',
                word_count: 9200,
              },
            },
            recent_chapters: [
              {
                id: 'memory-secret-5',
                memory_type: 'chapter',
                scope_key: 'chapter:5',
                title: '黑潮门回声',
                summary: '第5章里旧灯塔回声指向潮下车站。',
                chapter_range: { start: 5, end: 5 },
              },
            ],
            critical_context: [],
            remaining_work: [
              { code: 'missing_retrieval', message: '检索索引需要刷新。' },
            ],
          },
          sections: [
            {
              key: 'recent_chapters',
              title: '近期章节',
              item_count: 2,
              items: [
                {
                  id: 'memory-secret-5',
                  memory_type: 'chapter',
                  scope_key: 'chapter:5',
                  title: '黑潮门回声',
                  summary: '第5章里旧灯塔回声指向潮下车站。',
                  chapter_range: { start: 5, end: 5 },
                  metadata: { source_id: 'chapter-content-5' },
                },
                {
                  id: 'memory-secret-4',
                  memory_type: 'chapter',
                  scope_key: 'chapter:4',
                  title: '雾港追踪',
                  summary: '苏晚晴锁定旧灯塔。',
                  chapter_range: { start: 4, end: 4 },
                },
              ],
            },
            {
              key: 'manual_overflow',
              title: '人工溢出上下文',
              item_count: 6,
              items: [
                {
                  id: 'memory-overflow-1',
                  memory_type: 'arc',
                  scope_key: 'arc:1',
                  title: '雾港主线',
                  summary: '黑潮门正在回收旧信。',
                },
              ],
            },
          ],
          source_sections: [
            {
              key: 'recent_chapters',
              title: '近期章节',
              item_count: 2,
              source_type: 'longform_context_package',
            },
            {
              key: 'manual_overflow',
              title: '人工溢出上下文',
              item_count: 6,
              source_type: 'longform_context_package',
            },
          ],
          source_section_keys: ['recent_chapters', 'manual_overflow'],
          memory_provenance: {
            version: 'phase223.longform_memory_provenance.v1',
            status: 'truncated',
            sources: [
              {
                source_ref: 'longform_context_package:recent_chapters',
                source_type: 'recent_chapters',
                title: '近期章节',
                item_count: 2,
                returned_count: 2,
                limit: 5,
                has_more: false,
              },
              {
                source_ref: 'longform_context_package:manual_overflow',
                source_type: 'manual_overflow',
                title: '人工溢出上下文',
                item_count: 6,
                returned_count: 1,
                limit: 5,
                has_more: true,
              },
            ],
            windows: {
              sections: {
                recent_chapters: { total: 2, returned: 2, limit: 5, has_more: false },
                manual_overflow: { total: 6, returned: 1, limit: 5, has_more: true },
              },
            },
            recovery: {
              status: 'optional',
              reason: 'longform_context_window_limited',
              next_tools: ['summarize_longform_context'],
              tools: [
                {
                  tool_name: 'summarize_longform_context',
                  params: {
                    chapter_index: 6,
                    query: '缩小上下文窗口后重新汇总第6章写作上下文。',
                    max_chars: 2400,
                  },
                },
              ],
            },
            trace: {
              source: 'summarize_longform_context',
              version: 'phase223.longform_memory_provenance.v1',
              mutability: 'read',
            },
            prompt_context: {
              chars: 3600,
              max_chars: 1200,
              included: true,
              truncated: true,
            },
            boundaries: {
              world_truth: {
                status: 'separated',
                canonical_source: 'Athena/world_model',
                longform_context_role: 'retrieved_memory_rollups_and_generation_context',
              },
            },
          },
          diagnostics: [
            {
              code: 'section_items_limited',
              severity: 'info',
              message: '上下文 section 条目超过摘要上限，已截断。',
              section_key: 'manual_overflow',
              item_count: 6,
              returned_count: 1,
            },
            {
              code: 'prompt_context_truncated',
              severity: 'info',
              message: '完整上下文超过本次摘要预算。',
              prompt_context_chars: 3600,
              max_chars: 1200,
            },
          ],
          decision: {
            status: 'ready',
            reason: 'longform_context_ready',
            message: '长篇上下文可用于后续生成。',
          },
          should_generate_next_chapter: true,
          recommended_actions: ['preflight_writing'],
          prompt_context_chars: 3600,
          limits: { max_chars: 1200, include_prompt_context: true, section_item_limit: 5 },
          prompt_context: '【完整提示上下文】raw prompt context should stay hidden',
          trace: {
            summary_version: 'phase52.longform_context_summary.v1',
            source: 'build_longform_context_package',
            source_section_count: 2,
          },
        },
      },
    })

    const text = wrapper.text()
    expect(text).toContain('长篇上下文摘要')
    expect(text).toContain('已完成')
    expect(text).toContain('第6章')
    expect(text).toContain('灯塔旧回声')
    expect(text).toContain('可用于生成')
    expect(text).toContain('已生成 5')
    expect(text).toContain('最新章节 第5章')
    expect(text).toContain('字数 48000')
    expect(text).toContain('上下文字符 3600')
    expect(text).toContain('预算 1200')
    expect(text).toContain('来源覆盖')
    expect(text).toContain('截断')
    expect(text).toContain('近期章节 2')
    expect(text).toContain('人工溢出上下文 6')
    expect(text).toContain('黑潮门回声')
    expect(text).toContain('雾港追踪')
    expect(text).toContain('潮下车站')
    expect(text).toContain('preflight_writing')
    expect(text).toContain('section_items_limited')
    expect(text).toContain('prompt_context_truncated')
    expect(text).toContain('上下文 section 条目超过摘要上限')
    expect(text).not.toContain('project-secret-id')
    expect(text).not.toContain('memory-secret-5')
    expect(text).not.toContain('memory-secret-4')
    expect(text).not.toContain('memory-overflow-1')
    expect(text).not.toContain('chapter:5')
    expect(text).not.toContain('chapter:4')
    expect(text).not.toContain('arc:1')
    expect(text).not.toContain('source_ref')
    expect(text).not.toContain('source_type')
    expect(text).not.toContain('source_sections')
    expect(text).not.toContain('source_section_keys')
    expect(text).not.toContain('longform_context_package:recent_chapters')
    expect(text).not.toContain('longform_context_package:manual_overflow')
    expect(text).not.toContain('phase223.longform_memory_provenance.v1')
    expect(text).not.toContain('phase52.longform_context_summary.v1')
    expect(text).not.toContain('build_longform_context_package')
    expect(text).not.toContain('Athena/world_model')
    expect(text).not.toContain('retrieved_memory_rollups_and_generation_context')
    expect(text).not.toContain('raw prompt context should stay hidden')
    expect(text).not.toContain('chapter-content-5')
  })
})
