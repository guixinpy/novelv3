// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import AgentRunWorldModelSemanticCheckPanel from './AgentRunWorldModelSemanticCheckPanel.vue'

describe('AgentRunWorldModelSemanticCheckPanel', () => {
  it('renders world model semantic check projection without internal ids', () => {
    const wrapper = mount(AgentRunWorldModelSemanticCheckPanel, {
      props: {
        output: {
          status: 'completed',
          project_id: 'project-secret-id',
          chapter_index: 3,
          subject_ref: 'char.hero',
          profile: {
            id: 'profile-secret-id',
            version: 2,
            contract_version: 'world.contract.v1',
          },
          semantic_check: {
            layer: 'L5 Semantic Checks',
            checker_name: 'semantic_consistency_llm',
            status: 'issues_found',
            issue_count: 1,
            summary: '章节死亡叙述和确认事实冲突。',
          },
          fact_window: {
            total_confirmed_facts: 7,
            returned_facts: 2,
            limit: 5,
            facts: [
              {
                claim_id: 'claim.secret.hero.status',
                subject_ref: 'char.hero',
                predicate: 'status',
                object_ref_or_value: 'alive',
                evidence_refs: ['chapter:1', 'world_profile:secret'],
              },
            ],
          },
          issues: [
            {
              code: 'fact_semantic_conflict',
              severity: 'warning',
              message: '章节声称顾衍死亡，但世界模型确认其状态为存活。',
              subject_ref: 'char.hero',
              predicate: 'status',
              claim_id: 'claim.secret.hero.status',
              evidence_excerpt: '众人确认他已经死亡',
            },
          ],
          recommended_next_tools: [
            'prepare_analyze_chapter_world_model_execution',
            'review_world_model_proposals',
            'inspect_agent_world_model_route',
          ],
          llm_prompt_contract: {
            prompt_id: 'athena.world_model_semantic_check',
            template_hash: 'sha256:prompt-secret-hash',
            user_prompt: 'raw prompt content should stay hidden',
          },
          trace: {
            trace_id: 'trace-secret-id',
            trace_type: 'world_model_semantic_check',
            version: 'phase254.world_model_semantic_check.v1',
            source: 'inspect_agent_world_model_semantic_check',
          },
        },
      },
    })

    const text = wrapper.text()
    expect(text).toContain('世界模型语义检查')
    expect(text).toContain('已发现问题')
    expect(text).toContain('第3章')
    expect(text).toContain('char.hero')
    expect(text).toContain('确认事实 2 / 7')
    expect(text).toContain('检查事实上限 5')
    expect(text).toContain('章节死亡叙述和确认事实冲突')
    expect(text).toContain('fact_semantic_conflict')
    expect(text).toContain('警告')
    expect(text).toContain('章节声称顾衍死亡，但世界模型确认其状态为存活')
    expect(text).toContain('众人确认他已经死亡')
    expect(text).toContain('prepare_analyze_chapter_world_model_execution')
    expect(text).toContain('review_world_model_proposals')
    expect(text).toContain('inspect_agent_world_model_route')
    expect(text).not.toContain('project-secret-id')
    expect(text).not.toContain('profile-secret-id')
    expect(text).not.toContain('claim.secret.hero.status')
    expect(text).not.toContain('chapter:1')
    expect(text).not.toContain('world_profile:secret')
    expect(text).not.toContain('trace-secret-id')
    expect(text).not.toContain('phase254.world_model_semantic_check.v1')
    expect(text).not.toContain('sha256:prompt-secret-hash')
    expect(text).not.toContain('raw prompt content')
    expect(text).not.toContain('llm_prompt_contract')
    expect(text).not.toContain('evidence_refs')
  })
})
