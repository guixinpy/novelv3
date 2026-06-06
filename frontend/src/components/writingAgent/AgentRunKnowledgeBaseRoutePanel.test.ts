// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import AgentRunKnowledgeBaseRoutePanel from './AgentRunKnowledgeBaseRoutePanel.vue'

describe('AgentRunKnowledgeBaseRoutePanel', () => {
  it('renders knowledge base route projection without internal source ids', () => {
    const wrapper = mount(AgentRunKnowledgeBaseRoutePanel, {
      props: {
        output: {
          status: 'completed',
          chapter_index: 3,
          query: '雾港追踪写法',
          route: {
            status: 'ready',
            reason: 'knowledge_base_available',
            can_inform_generation: true,
            recommended_tools: [
              'summarize_longform_context',
              'preflight_writing',
              'review_chapter_quality',
            ],
          },
          author_preferences: {
            status: 'configured',
            facets: [
              {
                key: 'tone_preferences',
                value: ['冷峻', '悬疑'],
                source: 'Project.style_config',
              },
            ],
            source_ref: 'Project.style_config',
          },
          learned_rules: {
            total: 3,
            returned: 2,
            limit: 2,
            has_more: true,
            items: [
              {
                id: 'rule-secret-id',
                condition: '用户反馈章节像大纲',
                action: '增加场景动作和角色即时反应',
                source_ref: 'PromptRule:rule-secret-id',
              },
            ],
            source_ref: 'PromptRule(rule_type=learned)',
          },
          knowledge_candidates: {
            total: 2,
            returned: 1,
            limit: 2,
            has_more: true,
            items: [
              {
                id: 'candidate-secret-id',
                title: '雾港追踪写法',
                memory_type: 'writing_pattern',
                summary: '使用冷峻短句和章末行动压力。',
                source_refs: ['chapter_content:chapter-content-3'],
              },
            ],
            source_ref: 'Project.style_config.knowledge_base_candidates',
          },
          reference_patterns: {
            available: true,
            returned: 2,
            items: [
              {
                input_preview: '章节生成输入',
                output_preview: '冷峻段落输出',
                source_ref: 'FewShotExampleLibrary',
              },
            ],
            source_ref: 'FewShotExampleLibrary',
          },
          diagnostics: [
            {
              code: 'world_truth_boundary',
              severity: 'info',
              message: '知识库是作者偏好、项目策略和写法经验，不是 Athena 世界真相。',
            },
          ],
        },
      },
    })

    const text = wrapper.text()
    expect(text).toContain('知识库路由')
    expect(text).toContain('可用于生成')
    expect(text).toContain('第3章')
    expect(text).toContain('雾港追踪写法')
    expect(text).toContain('作者偏好 1')
    expect(text).toContain('学习规则 2 / 3')
    expect(text).toContain('知识库候选 1 / 2')
    expect(text).toContain('写法参考 2')
    expect(text).toContain('summarize_longform_context')
    expect(text).toContain('preflight_writing')
    expect(text).toContain('使用冷峻短句和章末行动压力。')
    expect(text).toContain('知识库是作者偏好、项目策略和写法经验')
    expect(text).not.toContain('rule-secret-id')
    expect(text).not.toContain('candidate-secret-id')
    expect(text).not.toContain('chapter_content:chapter-content-3')
    expect(text).not.toContain('chapter-content-3')
    expect(text).not.toContain('PromptRule:')
    expect(text).not.toContain('Project.style_config')
    expect(text).not.toContain('FewShotExampleLibrary')
    expect(text).not.toContain('source_ref')
    expect(text).not.toContain('source_refs')
  })
})
